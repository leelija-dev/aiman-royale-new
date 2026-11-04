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

PAY_WITH={'upi':'upi','card':'cc,dc','netbanking':'nb'}
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
    # Open Cashfree on the option the customer picked (all options if none).
    methods=PAY_WITH.get(order.pay_with)
    if methods:payload['order_meta']['payment_methods']=methods
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
def rupees(value):
    """Whole rupees (₹13,419.39 → ₹13,419). Every amount shown and charged is a whole number."""
    from decimal import ROUND_HALF_UP
    return Decimal(value).quantize(Decimal('1'),rounding=ROUND_HALF_UP)
def totals(items,code=''):
    subtotal=money(sum((rupees(i.variant.product.price)*i.quantity for i in items),Decimal('0')))
    discount=Decimal('0')
    if code:
        c=Coupon.objects.filter(code=code.strip().upper(),active=True).first()
        if not c or (c.expires_at and c.expires_at<=timezone.now()) or subtotal<c.minimum:raise ValidationError('Coupon is invalid, expired or the minimum order value has not been met.')
        discount=money(rupees(subtotal*Decimal(c.percent)/100))
    s=SiteSettings.current()
    shipping=Decimal('0') if subtotal-discount>=s.free_shipping_above else money(rupees(s.shipping_fee))
    return {'subtotal':subtotal,'discount':discount,'shipping':shipping,'total':money(subtotal-discount+shipping)}

@transaction.atomic
def reserve_order(user,cart,address,key,code='',method='cashfree',only=None):
    """Create the order from the bag. 'only' = list of bag item ids (Buy Now); other bag items stay in the bag."""
    # Serialise a customer's checkout requests, including repeated idempotency keys.
    Customer.objects.select_for_update().get(pk=user.pk)
    existing=Order.objects.filter(idempotency_key=key,user=user).first()
    if existing:return existing,False
    if Order.objects.filter(idempotency_key=key).exists():raise ValidationError('Invalid checkout key.')
    Cart.objects.select_for_update().get(pk=cart.pk)
    chosen=cart.items.filter(pk__in=only) if only else cart.items.all()
    items=list(chosen.select_related('variant__product').order_by('variant_id'))
    if not items:raise ValidationError('Your bag is empty.' if not only else 'This item is no longer in your bag.')
    for item in items:
        v=Variant.objects.select_for_update().select_related('product').get(pk=item.variant_id)
        if not v.product.active or v.stock<item.quantity:raise ValidationError(f'{v.product.name}: selected size is no longer available.')
        item.variant=v
    amounts=totals(items,code)
    order=Order.objects.create(user=user,idempotency_key=key,address=address,payment_method=method,status='cod' if method=='cod' else 'pending',expires_at=timezone.now()+timedelta(minutes=30),**amounts)
    for item in items:
        Variant.objects.filter(pk=item.variant_id).update(stock=F('stock')-item.quantity)
        OrderItem.objects.create(order=order,variant=item.variant,name=item.variant.product.name,unit_price=rupees(item.variant.product.price),quantity=item.quantity,measurements=item.measurements)
    cart.items.filter(pk__in=[i.pk for i in items]).delete()
    if order.status=='cod':schedule_shipment(order)
    return order,True

@transaction.atomic
def release_order(order_id,status='expired'):
    order=Order.objects.select_for_update().get(pk=order_id)
    if order.status!='pending':return
    custom=CustomRequest.objects.filter(order=order).first()
    if custom:CustomRequest.objects.filter(pk=custom.pk).update(status='accepted',order=None)
    else:
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
    if order.status=='paid':schedule_shipment(order)
    return order

def send_otp(phone,code):
    if not all([settings.WHATSAPP_TOKEN,settings.WHATSAPP_PHONE_ID,settings.WHATSAPP_OTP_TEMPLATE,settings.WHATSAPP_GRAPH_VERSION]):raise ProviderUnavailable('WhatsApp verification is not configured. Please use the email registration form.')
    payload={'messaging_product':'whatsapp','to':phone.lstrip('+'),'type':'template','template':{'name':settings.WHATSAPP_OTP_TEMPLATE,'language':{'code':'en_US'},'components':[{'type':'body','parameters':[{'type':'text','text':code}]},{'type':'button','sub_type':'url','index':'0','parameters':[{'type':'text','text':code}]}]}}
    try:
        r=requests.post(f'https://graph.facebook.com/{settings.WHATSAPP_GRAPH_VERSION}/{settings.WHATSAPP_PHONE_ID}/messages',json=payload,headers={'Authorization':'Bearer '+settings.WHATSAPP_TOKEN},timeout=12);r.raise_for_status()
    except requests.RequestException:raise ProviderUnavailable('We could not send the WhatsApp code. Please try again later.')


# ---------- Delhivery: book the shipment as soon as an order is confirmed ----------
def schedule_shipment(order):
    """After the order is saved, book it with Delhivery in the background (never slows down checkout)."""
    from . import delhivery
    if not settings.DELHIVERY_AUTO_SHIP or not delhivery.configured():return
    pk=order.pk
    transaction.on_commit(lambda:start_shipment(pk))

def start_shipment(pk):
    if settings.REDIS_URL:
        from .tasks import ship_order
        try:ship_order.delay(str(pk));return
        except Exception:pass  # broker down: fall back to a background thread
    import threading
    threading.Thread(target=_ship_in_thread,args=(pk,),daemon=True).start()

def _ship_in_thread(pk):
    from django.db import connection
    try:ship_now(pk)
    finally:connection.close()  # a thread gets its own DB connection; close it when done

def ship_now(pk):
    """Create the Delhivery shipment for one order. A failure is shown on the order in admin."""
    from . import delhivery
    order=Order.objects.get(pk=pk)
    if order.awb:return order.awb
    try:return delhivery.create_shipment(order)
    except delhivery.DelhiveryError as e:
        Order.objects.filter(pk=pk,awb='').update(courier_status=('Booking failed: '+str(e))[:80])


# ---------- Customer cancellation ----------
NOT_PICKED={'','manifested','not picked','pending','open','cancelled'}
def can_cancel(order):
    """Customers may cancel until Delhivery collects the parcel (or a pickup has been requested)."""
    cs=(order.courier_status or '').strip().lower()
    return order.status in ('paid','cod','processing') and not order.pickup_requested_at and (cs in NOT_PICKED or cs.startswith('booking failed'))

def cancel_order(order_id,user,reason=''):
    from . import delhivery
    with transaction.atomic():
        order=Order.objects.select_for_update().get(pk=order_id,user=user)
        if not can_cancel(order):raise ValidationError('This order can no longer be cancelled because it has been handed to the courier. Please contact us for help.')
        if order.awb and order.courier_status!='Cancelled' and delhivery.configured():
            try:delhivery.cancel(order)
            except delhivery.DelhiveryError:raise ValidationError('We could not cancel the courier booking right now. Please try again in a few minutes or contact us.')
        if CustomRequest.objects.filter(order=order).exists():CustomRequest.objects.filter(order=order).update(status='cancelled')
        else:
            for item in order.items.all():Variant.objects.filter(pk=item.variant_id).update(stock=F('stock')+item.quantity)
        order.cancelled_at=timezone.now();order.cancel_reason=reason[:200]
        if order.payment_method=='cod' or not order.gateway_payment_id:
            order.status='cancelled'
        else:
            # Paid online: ask Cashfree to refund in full; if that fails our team refunds manually.
            try:
                gateway('POST',f'orders/{order.gateway_order_id}/refunds',{'refund_amount':float(order.total),'refund_id':f'cancel-{str(order.id)[:8]}','refund_note':'Order cancelled by customer'},idempotency_key=f'refund-{order.id}')
                order.status='refunded'
            except ProviderUnavailable:
                order.status='refund_required'
        order.save(update_fields=['status','cancelled_at','cancel_reason'])
    return order


# ---------- Custom (made-to-measure) requests ----------
def custom_totals(req):
    subtotal=money(rupees(req.price)*req.quantity)
    s=SiteSettings.current()
    shipping=Decimal('0') if subtotal>=s.free_shipping_above else money(rupees(s.shipping_fee))
    return {'subtotal':subtotal,'discount':Decimal('0'),'shipping':shipping,'total':money(subtotal+shipping)}

@transaction.atomic
def reserve_custom_order(user,req_id,address,key,method='cashfree'):
    """Order for an accepted custom request (made to measure: no stock is reserved)."""
    Customer.objects.select_for_update().get(pk=user.pk)
    existing=Order.objects.filter(idempotency_key=key,user=user).first()
    if existing:return existing,False
    if Order.objects.filter(idempotency_key=key).exists():raise ValidationError('Invalid checkout key.')
    req=CustomRequest.objects.select_for_update(of=('self',)).select_related('product','variant').filter(pk=req_id,user=user).first()
    if not req or req.status!='accepted' or not req.price:raise ValidationError('This custom request is not ready for payment.')
    variant=req.variant or req.product.variants.first()
    if not variant:raise ValidationError('This product is not available.')
    order=Order.objects.create(user=user,idempotency_key=key,address=address,payment_method=method,status='cod' if method=='cod' else 'pending',
                               expires_at=timezone.now()+timedelta(minutes=30),**custom_totals(req))
    OrderItem.objects.create(order=order,variant=variant,name=f'{req.product.name} (custom fit)',unit_price=rupees(req.price),quantity=req.quantity,measurements=req.measurements)
    req.status='ordered';req.order=order;req.save(update_fields=['status','order','updated_at'])
    if order.status=='cod':schedule_shipment(order)
    return order,True
