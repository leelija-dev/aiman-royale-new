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
from django.db.models import Q,Count,Min,Max,Avg
from django.utils.text import slugify
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
def user_data(u):return {'id':u.pk,'name':u.get_full_name() or u.first_name,'first_name':u.first_name,'last_name':u.last_name,'email':u.email,'phone':u.phone,'marketing_opt_in':u.marketing_opt_in,'joined':u.date_joined.date().isoformat()}
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
            item.quantity=min(item.quantity+i.quantity,i.variant.stock)
            item.measurements=i.measurements
            if item.quantity:item.save()
            else:item.delete()
        guest.delete()
@api_view(['GET'])
def site(request):
    s=SiteSettings.current()
    return Response({'name':s.name,'announcement':s.announcement,'hero_title':s.hero_title,'hero_description':s.hero_description,'hero_image':s.hero_image.url if s.hero_image else '/images/hero.webp','phone':s.phone,'email':s.email,'address':s.address,'cod_enabled':s.cod_enabled,'payment_ready':bool(settings.CASHFREE_APP_ID and settings.CASHFREE_SECRET_KEY),'whatsapp_ready':bool(settings.WHATSAPP_TOKEN and settings.WHATSAPP_PHONE_ID and settings.WHATSAPP_OTP_TEMPLATE and settings.WHATSAPP_GRAPH_VERSION),'collections':CollectionSerializer(Collection.objects.filter(active=True),many=True).data,'menu':menu_data(),'delivery_message':s.delivery_message,'calendly':{'url':s.calendly_url,'primary':s.calendly_primary_color,'text':s.calendly_text_color,'background':s.calendly_background_color} if s.calendly_url else None,'social':{k:getattr(s,k+'_url') for k in ['instagram','facebook','youtube','pinterest'] if getattr(s,k+'_url')},'footer_tagline':s.footer_tagline,'shop_page':shop_page(s),'occasions':[occasion_data(o) for o in Occasion.objects.filter(active=True)]})
PRICE_STEPS=[5000,8000,10000,15000,20000,30000]
SIZE_ORDER=['XXS','XS','S','M','L','XL','XXL','2XL','3XL','4XL','5XL','FREE']
def media_url(f):return f.url if f else ''
def occasion_data(o,count=None):
    d={'name':o.name,'slug':o.slug,'image':media_url(o.image)}
    if count is not None:d['count']=count
    return d
def shop_page(s):
    """Text for the All Products page (Site settings → All Products page)."""
    return {'eyebrow':s.shop_eyebrow,'title':s.shop_title,'text':s.shop_text,'image':media_url(s.shop_image),
            'heading':s.shop_heading,'subheading':s.shop_subheading,
            'fitting':{'title':s.shop_fitting_title,'text':s.shop_fitting_text,'note':s.shop_fitting_note,'image':media_url(s.shop_fitting_image)},
            'trust':[{'title':t.strip(),'text':x.strip()} for t,_,x in (l.partition('|') for l in s.shop_trust.splitlines()) if t.strip()]}
def collection_cover(c):
    """Collection image, or the first photo of one of its products."""
    if c.image:return c.image.url
    im=ProductImage.objects.filter(product__collections=c,product__active=True).order_by('product__created_at','position').first()
    return im.image.url if im and im.image else ''
def style_collections(url):
    """Collections to list under 'Style' for a menu item: sub-collections first, then collections sharing products."""
    with_products=Collection.objects.filter(active=True,products__active=True).annotate(n=Count('products',filter=Q(products__active=True),distinct=True))
    path=url.split('?')[0].rstrip('/')
    if path=='/products':return list(with_products.filter(parent__isnull=False).order_by('sort_order','-n','name')) or list(with_products.order_by('-n','name'))
    if not path.startswith('/collections/'):return []
    me=Collection.objects.filter(slug=path.rsplit('/',1)[-1]).first()
    if not me:return []
    children=list(with_products.filter(parent=me).order_by('sort_order','-n','name'))
    shared=list(with_products.filter(products__collections=me).exclude(pk=me.pk).exclude(pk__in=[c.pk for c in children]).exclude(pk=me.parent_id or 0).distinct().order_by('-n','name'))
    return children+shared
def menu_data():
    """Main menu for the header, managed in admin (Menu items)."""
    occasions=list(Occasion.objects.filter(active=True))
    items=[]
    for m in MenuItem.objects.filter(active=True).prefetch_related('links'):
        groups={'Style':[],'Occasion':[],'Collection':[]}
        if m.auto_styles:
            groups['Style']=[{'label':c.name,'href':f'/collections/{c.slug}','count':c.n,'image':collection_cover(c)} for c in style_collections(m.url)[:12]]
        for l in m.links.all():groups[l.group].append({'label':l.label,'href':l.url})
        if m.show_occasions:
            sep='&' if '?' in m.url else '?'
            groups['Occasion']+= [{'label':o.name,'href':f'{m.url}{sep}occasion={o.slug}'} for o in occasions]
        items.append({'label':m.label,'href':m.url,'columns':[{'title':t,'links':ls} for t,ls in groups.items() if ls],
                      'feature':{'title':m.feature_title or m.label,'image':media_url(m.feature_image),'href':m.feature_url or m.url}})
    return items
@api_view(['GET'])
def facets(request):
    """Filter options built from the products that actually exist in a collection (or the whole store)."""
    base=Product.objects.filter(active=True)
    if request.query_params.get('collection'):base=base.filter(collections__slug=request.query_params['collection'])
    ids=list(base.values_list('id',flat=True).distinct())
    occ=Occasion.objects.filter(active=True).annotate(n=Count('products',filter=Q(products__id__in=ids),distinct=True)).order_by('sort_order','name')
    variants=Variant.objects.filter(product_id__in=ids)
    sizes=sorted({v for v in variants.filter(stock__gt=0).values_list('size',flat=True) if v},key=lambda x:(SIZE_ORDER.index(x.upper()) if x.upper() in SIZE_ORDER else 99,x))
    swatches={c.name.lower():c for c in Colour.objects.all()}
    colours={}
    for name,pid in variants.values_list('colour','product_id'):
        key=name.strip().lower()
        if not key:continue
        c=colours.setdefault(key,{'name':swatches[key].name if key in swatches else name.strip().title(),'hex':swatches[key].hex if key in swatches else '#b9aca3','products':set(),'order':swatches[key].sort_order if key in swatches else 9999})
        c['products'].add(pid)
    price=base.aggregate(min=Min('price'),max=Max('price'))
    cols=Collection.objects.filter(active=True).annotate(n=Count('products',filter=Q(products__id__in=ids),distinct=True)).filter(n__gt=0).order_by('-n','name')
    prices=list(base.values_list('price',flat=True).distinct())
    buckets=[]
    for lo,hi in zip([None]+PRICE_STEPS,PRICE_STEPS+[None]):
        n=sum(1 for x in prices if (lo is None or x>=lo) and (hi is None or x<hi))
        if n:buckets.append({'value':f"{lo or ''}-{hi or ''}",'label':(f'Below ₹{hi:,}' if lo is None else f'₹{lo:,} – ₹{hi:,}' if hi else f'Above ₹{lo:,}'),'count':n})
    return Response({'occasions':[occasion_data(o,o.n) for o in occ],
                     'sizes':sizes,
                     'colours':[{'name':c['name'],'hex':c['hex'],'count':len(c['products'])} for c in sorted(colours.values(),key=lambda c:(c['order'],c['name']))],
                     'price':{'min':price['min'] or 0,'max':price['max'] or 0},
                     'price_ranges':buckets,
                     'collections':[{'name':c.name,'slug':c.slug,'count':c.n} for c in cols],
                     'count':len(ids)})
@api_view(['GET','POST'])
def reviews(request,slug):
    """Approved reviews for a product; signed-in customers can submit one (held for approval)."""
    p=get_object_or_404(Product,slug=slug,active=True)
    if request.method=='POST':
        if not request.user.is_authenticated:return Response({'error':'Please sign in to write a review.'},status=401)
        try:rating=int(request.data.get('rating',0))
        except (TypeError,ValueError):rating=0
        text=str(request.data.get('text','')).strip()
        if not 1<=rating<=5 or len(text)<10:raise ValidationError('Choose a rating and write at least 10 characters.')
        name=(request.user.first_name or request.user.email.split('@')[0])[:80]
        Review.objects.update_or_create(product=p,user=request.user,defaults={'name':name,'rating':rating,'text':text[:2000],'approved':False})
        return Response({'message':'Thank you! Your review will appear once our team has approved it.'},status=201)
    q=p.reviews.filter(approved=True)
    agg=q.aggregate(avg=Avg('rating'),n=Count('id'))
    return Response({'average':round(agg['avg'],1) if agg['avg'] else None,'count':agg['n'],
                     'reviews':[{'name':r.name,'rating':r.rating,'text':r.text,'date':r.created_at.date().isoformat()} for r in q[:50]]})
@api_view(['GET'])
def size_guide(request):
    """Size Guide popup: chart rows (inches), how-to-measure steps, note and optional PDF."""
    s=SiteSettings.current()
    return Response({'rows':[{'size':r.size,'alt':r.alt_size,'bust':float(r.bust),'waist':float(r.waist),'hip':float(r.hip),'armhole':float(r.armhole),'uk':r.uk_size} for r in SizeChartRow.objects.all()],
                     'steps':[{'title':m.title,'text':m.text,'image':media_url(m.image)} for m in MeasureStep.objects.all()],
                     'note':s.size_guide_note,'pdf':media_url(s.size_chart_pdf)})
@api_view(['GET'])
def home(request):
    """Homepage sections in display order, managed in admin (Homepage sections)."""
    img=lambda o:media_url(o.image) or o.image_path
    out=[]
    for sec in HomeSection.objects.filter(active=True).prefetch_related('cards'):
        out.append({'id':sec.id,'kind':sec.kind,'eyebrow':sec.eyebrow,'title':sec.title,'subtitle':sec.subtitle,'text':sec.text,
                    'button':{'label':sec.button_label,'href':sec.button_url} if sec.button_label else None,'image':img(sec),
                    'product_filter':sec.product_filter,'product_count':sec.product_count,
                    'cards':[{'label':c.label,'title':c.title,'text':c.text,'bullets':[b.strip() for b in c.bullets.splitlines() if b.strip()],
                              'caption':c.caption,'href':c.url,'button':c.button_label,'icon':c.icon,'image':img(c)} for c in sec.cards.all() if c.active]})
        if sec.kind=='strip' and not out[-1]['cards']:
            # No cards entered in admin: show the collections that have products, each linking to its own page.
            cols=Collection.objects.filter(active=True,products__active=True).annotate(n=Count('products',distinct=True)).order_by('-n','name')[:8]
            out[-1]['cards']=[{'label':'','title':c.name,'text':'','bullets':[],'caption':'Shop Now →','href':f'/collections/{c.slug}','button':'','icon':'','image':collection_cover(c)} for c in cols]
    return Response({'sections':out})
@api_view(['GET'])
def products(request,slug=None):
    q=Product.objects.filter(active=True).prefetch_related('images','variants','collections','occasions')
    if slug:return Response(ProductSerializer(get_object_or_404(q,slug=slug)).data)
    p=request.query_params
    cols=[v for v in p.getlist('collection') if v]
    if cols:q=q.filter(collections__slug__in=cols)
    ranges=Q()
    for r in p.getlist('price'):
        lo,_,hi=r.partition('-')
        try:
            rq=Q()
            if lo:rq&=Q(price__gte=Decimal(lo))
            if hi:rq&=Q(price__lt=Decimal(hi))
        except ArithmeticError:raise ValidationError('Invalid price range.')
        ranges|=rq
    if ranges:q=q.filter(ranges)
    if p.get('q'):q=q.filter(Q(name__icontains=p['q'])|Q(description__icontains=p['q']))
    # Filters accept repeated values (e.g. ?size=S&size=M) and match any of them.
    sizes=[v for v in p.getlist('size') if v]
    if sizes:q=q.filter(variants__size__in=sizes,variants__stock__gt=0)
    colours=[v for v in p.getlist('colour') if v]
    if colours:
        cq=Q()
        for c in colours:cq|=Q(variants__colour__iexact=c)
        q=q.filter(cq)
    try:
        if p.get('min'):q=q.filter(price__gte=Decimal(p['min']))
        if p.get('max'):q=q.filter(price__lte=Decimal(p['max']))
        page=max(1,int(p.get('page','1')))
    except (ValueError,ArithmeticError):raise ValidationError('Invalid filter value.')
    if p.get('featured')=='1':q=q.filter(featured=True)
    order={'price-asc':'price','price-desc':'-price','newest':'-created_at','name':'name'}.get(p.get('sort'),'-featured')
    wanted=[slugify(v) for v in p.getlist('occasion') if v]
    if wanted:q=q.filter(occasions__slug__in=wanted,occasions__active=True)
    q=q.distinct().order_by(order,'id')
    count=q.count()
    return Response({'count':count,'page':page,'pages':max(1,(count+11)//12),'results':ProductSerializer(q[(page-1)*12:page*12],many=True).data})
def category_content(c):
    """Text for a category page: the collection's own text, else Site settings defaults. {name} -> collection name."""
    s=SiteSettings.current()
    fill=lambda t:(t or '').replace('{name}',c.name)
    def entries(kind):
        own=c.questions.filter(kind=kind,active=True)
        rows=own if own.exists() else PageQuestion.objects.filter(collection__isnull=True,kind=kind,active=True)
        return [{'question':fill(r.question),'answer':fill(r.answer)} for r in rows]
    return {'eyebrow':fill(c.hero_eyebrow or 'The {name} Edit'),
            'tagline':fill(c.hero_tagline or s.category_tagline),
            'seo_heading':fill(c.seo_heading or s.category_seo_heading),
            'seo_body':fill(c.seo_body or s.category_seo_body),
            'faqs':entries('faq'),'guides':entries('guide'),'details':c.details,
            'fitting':{'title':s.fitting_title,'text':s.fitting_text,'button':s.fitting_button,
                       'steps':[x.strip() for x in s.fitting_steps.split('|') if x.strip()],'image':media_url(s.fitting_image)}}
@api_view(['GET'])
def collection(request,slug):
    c=get_object_or_404(Collection,slug=slug,active=True)
    return Response({**CollectionSerializer(c).data,'content':category_content(c)})
@api_view(['GET','PATCH'])
def me(request):
    if request.method=='PATCH':
        if not request.user.is_authenticated:return Response({'error':'Please sign in.'},status=401)
        u=request.user;d=request.data
        if 'first_name' in d:
            u.first_name=str(d.get('first_name','')).strip()[:150]
            if not u.first_name:raise ValidationError('Please enter your name.')
        if 'last_name' in d:u.last_name=str(d.get('last_name','')).strip()[:150]
        if 'phone' in d:
            phone=re.sub(r'[\s-]','',str(d.get('phone') or ''))
            if phone and not re.fullmatch(r'\+?[1-9]\d{9,14}',phone):raise ValidationError('Enter a valid mobile number, e.g. +919876543210.')
            if phone and Customer.objects.filter(phone=phone).exclude(pk=u.pk).exists():raise ValidationError('This mobile number is already linked to another account.')
            u.phone=phone or None
        if 'marketing_opt_in' in d:u.marketing_opt_in=bool(d.get('marketing_opt_in'))
        u.save()
    return Response({'user':user_data(request.user) if request.user.is_authenticated else None})
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AuthThrottle])
def change_password(request):
    u=request.user
    if u.has_usable_password() and not u.check_password(str(request.data.get('current',''))):raise ValidationError('Your current password is incorrect.')
    new=str(request.data.get('new',''))
    try:validate_password(new,user=u)
    except DjangoValidationError as e:raise ValidationError(' '.join(e.messages))
    u.set_password(new);u.save()
    from django.contrib.auth import update_session_auth_hash
    update_session_auth_hash(request,u)
    return Response({'message':'Your password has been updated.'})
@api_view(['GET'])
def coupons(request):
    """Coupons for the Saving Zone, with what each would save on the current bag."""
    items=list(get_cart(request).items.select_related('variant__product'))
    subtotal=sum((i.variant.product.price*i.quantity for i in items),Decimal('0'))
    now=timezone.now();out=[]
    for c in Coupon.objects.filter(active=True,public=True).filter(Q(expires_at__isnull=True)|Q(expires_at__gt=now)).order_by('-percent','minimum'):
        ok=bool(items) and subtotal>=c.minimum
        out.append({'code':c.code,'percent':c.percent,'minimum':c.minimum,'description':c.description,'expires_at':c.expires_at,
                    'eligible':ok,'saving':money(subtotal*Decimal(c.percent)/100) if ok else Decimal('0'),'short_by':max(Decimal('0'),c.minimum-subtotal)})
    return Response(out)
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
        if qty<1 or total>v.stock:raise ValidationError(f'Only {v.stock} left in this size.' if v.stock else 'This size is out of stock.')
        CartItem.objects.update_or_create(cart=c,variant=v,defaults={'quantity':total,'measurements':measurements})
    elif request.method in ['PATCH','DELETE']:
        i=get_object_or_404(c.items,pk=request.data.get('id'))
        if request.method=='DELETE':i.delete()
        else:
            try:q=int(request.data.get('quantity',1))
            except (ValueError,TypeError):raise ValidationError('Invalid quantity.')
            if not 1<=q<=i.variant.stock:raise ValidationError(f'Only {i.variant.stock} left in this size.')
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
    pay_with=str(request.data.get('pay_with','') or '')
    if pay_with and pay_with not in PAY_WITH:raise ValidationError('Unknown payment option.')
    note=str(request.data.get('note','') or '').strip()[:500]
    o,created=reserve_order(request.user,get_cart(request),address.validated_data,key,str(request.data.get('coupon','')),method)
    if created and (note or pay_with):
        o.note,o.pay_with=note,(pay_with if method=='cashfree' else '')
        o.save(update_fields=['note','pay_with'])
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
