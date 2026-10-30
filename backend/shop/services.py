import hashlib,hmac,secrets
from datetime import timedelta
from decimal import Decimal
import requests
from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import ValidationError, APIException
from .models import *

class ProviderUnavailable(APIException):
    status_code=503
    default_detail='This service is not configured yet. Please contact the store.'

def gateway(method,path,payload=None,idempotency_key=None):
    if not settings.CASHFREE_APP_ID or not settings.CASHFREE_SECRET_KEY:
        raise ProviderUnavailable('Cashfree payments are not configured yet.')
    base='https://api.cashfree.com/pg/' if settings.CASHFREE_ENVIRONMENT=='production' else 'https://sandbox.cashfree.com/pg/'
    headers={'x-client-id':settings.CASHFREE_APP_ID,'x-client-secret':settings.CASHFREE_SECRET_KEY,'x-api-version':settings.CASHFREE_API_VERSION,'Content-Type':'application/json'}
    if idempotency_key:headers['x-idempotency-key']=str(idempotency_key)
    try:
        response=requests.request(method,base+path,json=payload,headers=headers,timeout=15)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException,ValueError):
        raise ProviderUnavailable('Cashfree could not be reached. Your order is saved. Retry this checkout with the same order reference; do not start another payment if charged.')

def cashfree_session(order):
    if order.payment_method!='cashfree':raise ValidationError('This order does not use Cashfree.')
    if order.status!='pending':return ''
    if order.expires_at<=timezone.now():
        release_order(order.pk)
        raise ValidationError('This payment reservation has expired. Check your account before placing another order.')
    if order.payment_session_id:return order.payment_session_id
    # Persist a deterministic provider identifier BEFORE the network request.
    # Retries use the same Cashfree UUID idempotency key and exact request body.
    provider_id='ar_'+order.id.hex
    Order.objects.filter(pk=order.pk).update(gateway_order_id=provider_id)
    order.gateway_order_id=provider_id
    payload={'order_id':provider_id,'order_amount':float(order.total),'order_currency':'INR',
        'customer_details':{'customer_id':'customer_'+str(order.user_id),'customer_name':order.address['name'],'customer_email':order.address['email'],'customer_phone':order.address['phone']},
        'order_expiry_time':order.expires_at.isoformat(),
        'order_meta':{'return_url':settings.PUBLIC_SITE_URL+'/payment/return?order='+str(order.id)}}
    result=gateway('POST','orders',payload,idempotency_key=order.idempotency_key)
    if result.get('order_id')!=provider_id or not result.get('payment_session_id'):
        raise ProviderUnavailable('Cashfree returned an invalid checkout session. Contact the studio with your order reference.')
    order.payment_session_id=result['payment_session_id']
    Order.objects.filter(pk=order.pk).update(payment_session_id=order.payment_session_id)
    return order.payment_session_id

def verify_cashfree(order):
    if order.payment_method!='cashfree' or not order.gateway_order_id:
        raise ValidationError('Cashfree payment session does not exist for this order.')
    details=gateway('GET','orders/'+order.gateway_order_id)
    try:amount=Decimal(str(details.get('order_amount')))
    except Exception:raise ValidationError('Invalid Cashfree order amount.')
    if details.get('order_id')!=order.gateway_order_id or details.get('order_currency')!='INR' or amount!=order.total:
        raise ValidationError('Cashfree order details do not match.')
    if details.get('order_status')!='PAID':
        order.refresh_from_db()
        return order
    payments=gateway('GET','orders/'+order.gateway_order_id+'/payments')
    if not isinstance(payments,list):raise ProviderUnavailable('Payment verification is temporarily unavailable.')
    for payment in payments:
        if payment.get('payment_status')!='SUCCESS':continue
        try:paid=Decimal(str(payment.get('payment_amount')))
        except Exception:continue
        if payment.get('order_id')!=order.gateway_order_id or payment.get('payment_currency')!='INR' or paid!=order.total or not payment.get('cf_payment_id'):continue
        return settle_payment({'id':str(payment['cf_payment_id']),'order_id':order.gateway_order_id,'currency':'INR','amount':int(paid*100),'status':'captured'})
    raise ValidationError('No matching successful Cashfree payment was found. Please contact the studio if charged.')

def money(value):return Decimal(value).quantize(Decimal('.01'))
def totals(items,code=''):
    subtotal=money(sum((i.variant.product.price*i.quantity for i in items),Decimal('0')))
    discount=Decimal('0')
    if code:
        c=Coupon.objects.filter(code=code.strip().upper(),active=True).first()
        if not c or (c.expires_at and c.expires_at<=timezone.now()) or subtotal<c.minimum:raise ValidationError('Coupon is invalid, expired or the minimum order value has not been met.')
        discount=money(subtotal*Decimal(c.percent)/100)
    s=SiteSettings.current()
    shipping=Decimal('0') if subtotal-discount>=s.free_shipping_above else s.shipping_fee
    return {'subtotal':subtotal,'discount':discount,'shipping':shipping,'total':money(subtotal-discount+shipping)}

@transaction.atomic
def reserve_order(user,cart,address,key,code='',method='cashfree'):
    # Serialise a customer's checkout requests, including repeated idempotency keys.
    Customer.objects.select_for_update().get(pk=user.pk)
    existing=Order.objects.filter(idempotency_key=key,user=user).first()
    if existing:return existing,False
    if Order.objects.filter(idempotency_key=key).exists():raise ValidationError('Invalid checkout key.')
    Cart.objects.select_for_update().get(pk=cart.pk)
    items=list(cart.items.select_related('variant__product').order_by('variant_id'))
    if not items:raise ValidationError('Your bag is empty.')
    for item in items:
        v=Variant.objects.select_for_update().select_related('product').get(pk=item.variant_id)
        if not v.product.active or v.stock<item.quantity:raise ValidationError(f'{v.product.name}: selected size is no longer available.')
        item.variant=v
    amounts=totals(items,code)
    order=Order.objects.create(user=user,idempotency_key=key,address=address,payment_method=method,status='cod' if method=='cod' else 'pending',expires_at=timezone.now()+timedelta(minutes=30),**amounts)
    for item in items:
        Variant.objects.filter(pk=item.variant_id).update(stock=F('stock')-item.quantity)
        OrderItem.objects.create(order=order,variant=item.variant,name=item.variant.product.name,unit_price=item.variant.product.price,quantity=item.quantity,measurements=item.measurements)
    cart.items.all().delete()
    return order,True

@transaction.atomic
def release_order(order_id,status='expired'):
    order=Order.objects.select_for_update().get(pk=order_id)
    if order.status!='pending':return
    for item in order.items.all():Variant.objects.filter(pk=item.variant_id).update(stock=F('stock')+item.quantity)
    order.status=status;order.save(update_fields=['status'])

@transaction.atomic
def settle_payment(payment):
    order=Order.objects.select_for_update().filter(gateway_order_id=payment.get('order_id')).first()
    if not order:raise ValidationError('Payment order not recognised.')
    if payment.get('currency')!='INR' or payment.get('amount')!=int(order.total*100) or payment.get('status')!='captured':raise ValidationError('Payment is not captured or its amount does not match.')
    if order.status in ['paid','processing','shipped','delivered','refund_required','refunded']:return order
    order.gateway_payment_id=payment['id']
    # Expiry job and webhook acquire same row lock. Never fulfil released inventory.
    order.status='paid' if order.status=='pending' else 'refund_required'
    order.save(update_fields=['status','gateway_payment_id'])
    return order

def send_otp(phone,code):
    if not all([settings.WHATSAPP_TOKEN,settings.WHATSAPP_PHONE_ID,settings.WHATSAPP_OTP_TEMPLATE,settings.WHATSAPP_GRAPH_VERSION]):raise ProviderUnavailable('WhatsApp verification is not configured. Please use the email registration form.')
    payload={'messaging_product':'whatsapp','to':phone.lstrip('+'),'type':'template','template':{'name':settings.WHATSAPP_OTP_TEMPLATE,'language':{'code':'en_US'},'components':[{'type':'body','parameters':[{'type':'text','text':code}]},{'type':'button','sub_type':'url','index':'0','parameters':[{'type':'text','text':code}]}]}}
    try:
        r=requests.post(f'https://graph.facebook.com/{settings.WHATSAPP_GRAPH_VERSION}/{settings.WHATSAPP_PHONE_ID}/messages',json=payload,headers={'Authorization':'Bearer '+settings.WHATSAPP_TOKEN},timeout=12);r.raise_for_status()
    except requests.RequestException:raise ProviderUnavailable('We could not send the WhatsApp code. Please try again later.')
