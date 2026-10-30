import hmac,hashlib,base64,json,secrets,uuid,re
from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.contrib.auth import authenticate,login,logout
from django.contrib.auth.hashers import make_password,check_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db import transaction,IntegrityError
from django.db.models import Q
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view,permission_classes,authentication_classes,throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle,SimpleRateThrottle
from rest_framework.exceptions import ValidationError
from rest_framework.views import exception_handler as drf_exception_handler
from .models import *
from .serializers import *
from .services import *

class AuthThrottle(SimpleRateThrottle):
    scope='auth'
    def get_cache_key(self,request,view):return self.cache_format%{'scope':self.scope,'ident':self.get_ident(request)}

@ensure_csrf_cookie
def csrf(request):return JsonResponse({'csrfToken':get_token(request)})
def user_data(u):return {'id':u.pk,'name':u.first_name,'email':u.email,'phone':u.phone}
def get_cart(request):
    if request.user.is_authenticated:return Cart.objects.get_or_create(user=request.user)[0]
    if not request.session.session_key:request.session.create()
    return Cart.objects.get_or_create(session_key=request.session.session_key)[0]
def merge_cart(request,old_key):
    guest=Cart.objects.filter(session_key=old_key).first() if old_key else None
    cart=get_cart(request)
    if guest and guest.pk!=cart.pk:
        for i in guest.items.select_related('variant'):
            item,_=CartItem.objects.get_or_create(cart=cart,variant=i.variant,defaults={'quantity':0})
            item.quantity=min(10,item.quantity+i.quantity,i.variant.stock)
            item.measurements=i.measurements
            if item.quantity:item.save()
            else:item.delete()
        guest.delete()
@api_view(['GET'])
def site(request):
    s=SiteSettings.current()
    return Response({'name':s.name,'announcement':s.announcement,'hero_title':s.hero_title,'hero_description':s.hero_description,'hero_image':s.hero_image.url if s.hero_image else '/images/hero.webp','phone':s.phone,'email':s.email,'address':s.address,'cod_enabled':s.cod_enabled,'payment_ready':bool(settings.CASHFREE_APP_ID and settings.CASHFREE_SECRET_KEY),'whatsapp_ready':bool(settings.WHATSAPP_TOKEN and settings.WHATSAPP_PHONE_ID and settings.WHATSAPP_OTP_TEMPLATE and settings.WHATSAPP_GRAPH_VERSION),'collections':CollectionSerializer(Collection.objects.filter(active=True),many=True).data})
@api_view(['GET'])
def products(request,slug=None):
    q=Product.objects.filter(active=True).prefetch_related('images','variants','collections')
    if slug:return Response(ProductSerializer(get_object_or_404(q,slug=slug)).data)
    p=request.query_params
    if p.get('collection'):q=q.filter(collections__slug=p['collection'])
    if p.get('q'):q=q.filter(Q(name__icontains=p['q'])|Q(description__icontains=p['q']))
    if p.get('size'):q=q.filter(variants__size=p['size'],variants__stock__gt=0)
    if p.get('colour'):q=q.filter(variants__colour__iexact=p['colour'])
    try:
        if p.get('min'):q=q.filter(price__gte=Decimal(p['min']))
        if p.get('max'):q=q.filter(price__lte=Decimal(p['max']))
        page=max(1,int(p.get('page','1')))
    except (ValueError,ArithmeticError):raise ValidationError('Invalid filter value.')
    if p.get('featured')=='1':q=q.filter(featured=True)
    order={'price-asc':'price','price-desc':'-price','newest':'-created_at','name':'name'}.get(p.get('sort'),'-featured')
    q=q.distinct().order_by(order,'id')
    # JSON filtering works consistently on the optional SQLite development database.
    if p.get('occasion'):
        q=[x for x in q if p['occasion'].lower() in [v.lower() for v in x.occasions]]
        count=len(q)
    else:count=q.count()
    return Response({'count':count,'page':page,'pages':max(1,(count+11)//12),'results':ProductSerializer(q[(page-1)*12:page*12],many=True).data})
@api_view(['GET'])
def collection(request,slug):return Response(CollectionSerializer(get_object_or_404(Collection,slug=slug,active=True)).data)
@api_view(['GET'])
def me(request):return Response({'user':user_data(request.user) if request.user.is_authenticated else None})
@api_view(['POST'])
@throttle_classes([AuthThrottle])
def register(request):
    email=str(request.data.get('email','')).strip().lower();name=str(request.data.get('name','')).strip()[:100]
    validate_email(email)
    if not name or request.data.get('consent') is not True:raise ValidationError('Name and acceptance of terms are required.')
    password=request.data.get('password','');u=Customer(username=email,email=email,first_name=name)
    validate_password(password,user=u)
    try:u.set_password(password);u.save()
    except IntegrityError:raise ValidationError('Unable to create account with these details. Try signing in.')
    old=request.session.session_key;login(request,u);merge_cart(request,old)
    return Response({'user':user_data(u)},status=201)
@api_view(['POST'])
@throttle_classes([AuthThrottle])
def sign_in(request):
    u=authenticate(request,username=str(request.data.get('email','')).strip().lower(),password=request.data.get('password',''))
    if not u:raise ValidationError('Email or password is incorrect.')
    old=request.session.session_key;login(request,u);merge_cart(request,old)
    return Response({'user':user_data(u)})
@api_view(['POST'])
def sign_out(request):logout(request);return Response({'ok':True})
@api_view(['POST'])
@throttle_classes([AuthThrottle])
def otp_send(request):
    phone=str(request.data.get('phone','')).strip()
    if not re.fullmatch(r'\+?[1-9]\d{9,14}',phone):raise ValidationError('Enter a valid international mobile number.')
    phone='+'+phone.lstrip('+')
    purpose=request.data.get('purpose','login')
    if purpose not in ['login','register']:raise ValidationError('Invalid purpose.')
    if request.data.get('consent') is not True:raise ValidationError('Please accept verification contact and terms.')
    if OTPChallenge.objects.filter(phone=phone,created_at__gte=timezone.now()-timedelta(seconds=60)).exists():raise ValidationError('Please wait 60 seconds before requesting another code.')
    if OTPChallenge.objects.filter(phone=phone,created_at__gte=timezone.now()-timedelta(hours=1)).count()>=5:raise ValidationError('Too many requests. Please try later.')
    code=f'{secrets.randbelow(1000000):06d}'
    challenge=OTPChallenge.objects.create(phone=phone,code_hash=make_password(code),expires_at=timezone.now()+timedelta(minutes=5),name=str(request.data.get('name',''))[:100],purpose=purpose,marketing_opt_in=request.data.get('marketing') is True)
    try:send_otp(phone,code)
    except Exception:
        challenge.used=True;challenge.save(update_fields=['used']);raise
    OTPChallenge.objects.filter(phone=phone,used=False).exclude(pk=challenge.pk).update(used=True)
    return Response({'challenge':str(challenge.id),'expires_in':300})
@api_view(['POST'])
@throttle_classes([AuthThrottle])
def otp_verify(request):
    try:challenge_id=uuid.UUID(str(request.data.get('challenge','')))
    except ValueError:raise ValidationError('Invalid verification request.')
    with transaction.atomic():
        c=get_object_or_404(OTPChallenge.objects.select_for_update(),pk=challenge_id)
        valid=not c.used and c.expires_at>timezone.now() and c.attempts<5
        if valid:
            c.attempts+=1
            valid=check_password(str(request.data.get('code','')),c.code_hash)
            c.used=valid or c.attempts>=5;c.save(update_fields=['attempts','used'])
    if not valid:raise ValidationError('Code is invalid or expired. Request a new code.')
    u=Customer.objects.filter(phone=c.phone).first()
    if not u:
        if c.purpose!='register':raise ValidationError('Please register this number first.')
        u=Customer(username='wa_'+c.phone.lstrip('+'),phone=c.phone,first_name=c.name,marketing_opt_in=c.marketing_opt_in);u.set_unusable_password();u.save()
    if not u.is_active:raise ValidationError('This account is not active.')
    old=request.session.session_key;login(request,u,backend='django.contrib.auth.backends.ModelBackend');merge_cart(request,old)
    return Response({'user':user_data(u)})
@api_view(['GET','POST','PATCH','DELETE'])
def cart(request):
    c=get_cart(request)
    if request.method=='POST':
        v=get_object_or_404(Variant.objects.select_related('product'),pk=request.data.get('variant'),product__active=True)
        try:qty=int(request.data.get('quantity',1))
        except (TypeError,ValueError):raise ValidationError('Invalid quantity.')
        measurements=request.data.get('measurements') or {}
        if measurements:
            if not v.product.custom_fit:raise ValidationError('Custom fitting is not available for this product.')
            if set(measurements)-{'bust','waist','hip','armhole','unit'}:raise ValidationError('Invalid measurements.')
            try:
                for k in ['bust','waist','hip','armhole']:
                    value=float(measurements[k])
                    if not 5<=value<=250:raise ValueError()
                if measurements.get('unit') not in ['cm','in']:raise ValueError()
            except (ValueError,TypeError,KeyError):raise ValidationError('Enter all measurements and a valid unit.')
        existing=c.items.filter(variant=v).first();total=qty+(existing.quantity if existing else 0)
        if qty<1 or total>min(v.stock,10):raise ValidationError('Quantity exceeds available stock or the order limit.')
        CartItem.objects.update_or_create(cart=c,variant=v,defaults={'quantity':total,'measurements':measurements})
    elif request.method in ['PATCH','DELETE']:
        i=get_object_or_404(c.items,pk=request.data.get('id'))
        if request.method=='DELETE':i.delete()
        else:
            try:q=int(request.data.get('quantity',1))
            except (ValueError,TypeError):raise ValidationError('Invalid quantity.')
            if not 1<=q<=min(10,i.variant.stock):raise ValidationError('Quantity unavailable.')
            i.quantity=q;i.save()
    items=list(c.items.select_related('variant__product').prefetch_related('variant__product__images'))
    return Response({'items':[{'id':i.pk,'variant':VariantSerializer(i.variant).data,'product':ProductSerializer(i.variant.product).data,'quantity':i.quantity,'measurements':i.measurements} for i in items],'subtotal':str(sum((i.variant.product.price*i.quantity for i in items),Decimal(0)))})
@api_view(['GET','POST','DELETE'])
@permission_classes([IsAuthenticated])
def wishlist(request):
    if request.method!='GET':
        p=get_object_or_404(Product,pk=request.data.get('product'),active=True)
        if request.method=='POST':Wishlist.objects.get_or_create(user=request.user,product=p)
        else:Wishlist.objects.filter(user=request.user,product=p).delete()
    return Response(ProductSerializer(Product.objects.filter(wishlist__user=request.user).prefetch_related('images','variants','collections'),many=True).data)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def quote(request):
    items=list(get_cart(request).items.select_related('variant__product'))
    if not items:raise ValidationError('Your bag is empty.')
    return Response(totals(items,str(request.data.get('coupon',''))))
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def checkout(request):
    address=AddressSerializer(data=request.data.get('address',{}));address.is_valid(raise_exception=True)
    if request.data.get('consent') is not True:raise ValidationError('Accept the checkout terms to continue.')
    try:key=uuid.UUID(str(request.data.get('key','')))
    except ValueError:raise ValidationError('Missing checkout request key.')
    method=request.data.get('method','cashfree')
    if method not in ['cashfree','cod']:raise ValidationError('Unknown payment method.')
    if method=='cod' and not SiteSettings.current().cod_enabled:raise ValidationError('Cash on delivery is not available.')
    if method=='cashfree' and not (settings.CASHFREE_APP_ID and settings.CASHFREE_SECRET_KEY):raise ProviderUnavailable('Online payments are not configured. Your bag has been kept unchanged.')
    o,created=reserve_order(request.user,get_cart(request),address.validated_data,key,str(request.data.get('coupon','')),method)
    session=cashfree_session(o) if method=='cashfree' else ''
    return Response({'order':OrderSerializer(o).data,'payment_session_id':session,'mode':settings.CASHFREE_ENVIRONMENT,'amount':int(o.total*100)})
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_payment(request):
    o=get_object_or_404(Order,user=request.user,pk=request.data.get('order'))
    # Browser callbacks provide only our order UUID, never trusted payment status.
    return Response(OrderSerializer(verify_cashfree(o)).data)
@api_view(['POST'])
@authentication_classes([])
@throttle_classes([])
def payment_webhook(request):
    secret=settings.CASHFREE_SECRET_KEY
    if not secret:return Response(status=503)
    timestamp=request.headers.get('x-webhook-timestamp','')
    signature=request.headers.get('x-webhook-signature','')
    if not timestamp or not signature:return Response(status=400)
    expected=base64.b64encode(hmac.new(secret.encode(),timestamp.encode()+request.body,hashlib.sha256).digest()).decode()
    if not hmac.compare_digest(expected,signature):return Response(status=400)
    data=request.data
    if data.get('type')=='PAYMENT_SUCCESS_WEBHOOK':
        payload=data.get('data',{})
        provider_id=payload.get('order',{}).get('order_id')
        payment=payload.get('payment',{})
        if not provider_id or payment.get('payment_status')!='SUCCESS':return Response(status=400)
        order=Order.objects.filter(gateway_order_id=provider_id,payment_method='cashfree').first()
        if not order:return Response(status=404)
        # Verify with authenticated Cashfree APIs as well as the raw-body signature.
        verify_cashfree(order)
    return Response({'ok':True})
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def orders(request):return Response(OrderSerializer(Order.objects.filter(user=request.user).prefetch_related('items__variant'),many=True).data)
@api_view(['GET'])
def slots(request):
    qs=AppointmentSlot.objects.filter(enabled=True,starts_at__gt=timezone.now()).exclude(appointments__status__in=['requested','confirmed']).order_by('starts_at')[:120]
    return Response([{'id':s.pk,'starts_at':s.starts_at} for s in qs])
@api_view(['POST'])
@throttle_classes([AuthThrottle])
def book(request):
    s=AppointmentSerializer(data=request.data);s.is_valid(raise_exception=True)
    with transaction.atomic():
        slot=AppointmentSlot.objects.select_for_update().get(pk=s.validated_data['slot'].pk)
        if not slot.enabled or slot.starts_at<=timezone.now() or slot.appointments.filter(status__in=['requested','confirmed']).exists():raise ValidationError('This slot is no longer available. Please choose another.')
        a=s.save(user=request.user if request.user.is_authenticated else None)
    return Response({'id':a.pk,'status':a.status,'message':'Appointment requested. Our team will contact you to confirm.'},status=201)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def appointments(request):return Response(AppointmentSerializer(Appointment.objects.filter(user=request.user),many=True).data)
@api_view(['POST'])
@throttle_classes([AuthThrottle])
def subscribe(request):
    email=str(request.data.get('email','')).strip().lower();validate_email(email)
    if request.data.get('consent') is not True:raise ValidationError('Please consent to email updates.')
    Subscriber.objects.get_or_create(email=email)
    return Response({'message':'Thank you for subscribing.'})
@api_view(['GET'])
def page(request,slug):
    p=get_object_or_404(Page,slug=slug,published=True)
    return Response({'title':p.title,'body':p.body})
@api_view(['GET'])
def health(request):return Response({'status':'ok'})
