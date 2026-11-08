import hmac,hashlib,base64,json,secrets,uuid,re
from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.contrib.auth import authenticate,login,logout
from django.contrib.auth.hashers import make_password,check_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from rest_framework.exceptions import NotFound,NotAuthenticated
from django.db import transaction,IntegrityError
from django.db.models import Q,Count,Min,Max,Avg,F
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
def user_data(u):return {'id':u.pk,'avatar':(u.avatar.url if u.avatar else u.avatar_url),'name':u.get_full_name() or u.first_name,'first_name':u.first_name,'last_name':u.last_name,'email':u.email,'phone':u.phone,'marketing_opt_in':u.marketing_opt_in,'joined':u.date_joined.date().isoformat()}
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
    return Response({'name':s.name,'announcement':s.announcement,'hero_title':s.hero_title,'hero_description':s.hero_description,'hero_image':s.hero_image.url if s.hero_image else '/images/hero.webp','phone':s.phone,'email':s.email,'address':s.address,'cod_enabled':s.cod_enabled,'payment_ready':bool(settings.CASHFREE_APP_ID and settings.CASHFREE_SECRET_KEY),'google_ready':bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET),'whatsapp_ready':bool(settings.WHATSAPP_TOKEN and settings.WHATSAPP_PHONE_ID and settings.WHATSAPP_OTP_TEMPLATE and settings.WHATSAPP_GRAPH_VERSION),'collections':CollectionSerializer(Collection.objects.filter(active=True),many=True).data,'menu':menu_data(),'delivery_message':s.delivery_message,'calendly':{'url':s.calendly_url,'primary':s.calendly_primary_color,'text':s.calendly_text_color,'background':s.calendly_background_color} if s.calendly_url else None,'social':{k:getattr(s,k+'_url') for k in ['instagram','facebook','youtube','pinterest'] if getattr(s,k+'_url')},'footer_tagline':s.footer_tagline,'footer':footer_data(s),'shop_page':shop_page(s),'occasions':[occasion_data(o) for o in Occasion.objects.filter(active=True)]})
PRICE_STEPS=[5000,8000,10000,15000,20000,30000]
SIZE_ORDER=['XXS','XS','S','M','L','XL','XXL','2XL','3XL','4XL','5XL','FREE']
def media_url(f):return f.url if f else ''
def occasion_data(o,count=None):
    d={'name':o.name,'slug':o.slug,'image':media_url(o.image)}
    if count is not None:d['count']=count
    return d
def footer_data(s):
    """Everything the live-style footer shows, managed in admin."""
    lines=lambda t:[[x.strip() for x in l.split('|')] for l in (t or '').splitlines() if l.strip()]
    groups={}
    for l in FooterLink.objects.filter(active=True):groups.setdefault(l.group,[]).append({'label':l.label,'href':l.url})
    insta=s.instagram_url
    return {'about':s.footer_about,'newsletter':{'eyebrow':s.newsletter_eyebrow,'title':s.newsletter_title,'text':s.newsletter_text},
            'instagram':{'handle':s.instagram_handle,'note':s.instagram_note,'url':insta,
                         'posts':[{'caption':p.caption,'image':media_url(p.image) or p.image_path,'href':p.url or insta} for p in InstagramPost.objects.filter(active=True)[:8]]},
            'links':groups,'highlights':[{'title':l[0],'text':l[1] if len(l)>1 else ''} for l in lines(s.footer_highlights)],
            'services':[{'title':l[0],'text':l[1] if len(l)>1 else '','icon':l[2] if len(l)>2 else ''} for l in lines(s.footer_services)],
            'payments':[x.strip() for x in s.payment_methods.split(',') if x.strip()],'delivery':[x.strip() for x in s.delivery_partners.split(',') if x.strip()],
            'note':s.footer_note}
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
def occasion_cover(o,used=None):
    """Occasion image, or a product photo from that occasion (not already used by another card)."""
    if o.image:return o.image.url
    used=used if used is not None else set()
    ims=ProductImage.objects.filter(product__occasions=o,product__active=True).exclude(image='').order_by('position','-product__featured','product__created_at')
    pick=next((i for i in ims if i.product_id not in used),None) or ims.first()
    if not pick:return ''
    used.add(pick.product_id);return pick.image.url
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
                    'href':sec.button_url,'mobile_image':media_url(sec.mobile_image),'alt':sec.alt_text,'image_title':sec.image_title,
                    'product_filter':sec.product_filter,'product_count':sec.product_count,
                    'cards':[{'label':c.label,'title':c.title,'text':c.text,'bullets':[b.strip() for b in c.bullets.splitlines() if b.strip()],
                              'caption':c.caption,'href':c.url,'button':c.button_label,'icon':c.icon,'image':img(c),
                              'mobile_image':media_url(c.mobile_image),'alt':c.alt_text,'image_title':c.image_title} for c in sec.cards.all() if c.active]})
        if sec.kind=='occasions':
            # Always the live occasions (Haldi, Wedding, Party, Festive…) from admin → Occasions, in their order.
            used=set()
            out[-1]['cards']=[{'label':'','title':o.name,'text':'','bullets':[],'caption':'Shop Now','href':f'/products?occasion={o.slug}','button':'Shop Now','icon':'',
                               'image':occasion_cover(o,used),'mobile_image':'','alt':f'{o.name} collection','image_title':o.name} for o in Occasion.objects.filter(active=True)]
        if sec.kind=='strip' and not out[-1]['cards']:
            # No cards entered in admin: show the collections that have products, each linking to its own page.
            cols=Collection.objects.filter(active=True,products__active=True).annotate(n=Count('products',distinct=True)).order_by('-n','name')[:8]
            out[-1]['cards']=[{'label':'','title':c.name,'text':'','bullets':[],'caption':'Shop Now →','href':f'/collections/{c.slug}','button':'','icon':'','image':collection_cover(c)} for c in cols]
    return Response({'sections':out})
@api_view(['GET'])
def products(request,slug=None):
    q=Product.objects.filter(active=True).prefetch_related('images','variants','collections','occasions')
    if slug:
        prod=get_object_or_404(q,slug=slug);data=ProductSerializer(prod).data
        # Product FAQs: this product's own questions first, then the ones shared by all products.
        faqs=ProductFAQ.objects.filter(active=True).filter(Q(product=prod)|Q(product__isnull=True)).order_by(F('product').asc(nulls_last=True),'sort_order','id')
        data['faqs']=[{'q':f.question,'a':f.answer} for f in faqs]
        return Response(data)
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
    # Quick filter chips on category pages
    if p.get('custom')=='1':q=q.filter(custom_fit=True)
    if p.get('sale')=='1':q=q.filter(mrp__gt=F('price'))
    if p.get('ready')=='1':q=q.filter(variants__stock__gt=0).distinct()
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
    subtotal=sum((rupees(i.variant.product.price)*i.quantity for i in items),Decimal('0'))
    now=timezone.now();out=[]
    for c in Coupon.objects.filter(active=True,public=True).filter(Q(expires_at__isnull=True)|Q(expires_at__gt=now)).order_by('-percent','minimum'):
        ok=bool(items) and subtotal>=c.minimum
        out.append({'code':c.code,'percent':c.percent,'minimum':c.minimum,'description':c.description,'expires_at':c.expires_at,
                    'eligible':ok,'saving':rupees(subtotal*Decimal(c.percent)/100) if ok else Decimal('0'),'short_by':max(Decimal('0'),c.minimum-subtotal)})
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
def chosen_items(request):
    """Bag item ids sent by Buy Now ('items'); empty = the whole bag."""
    raw=request.data.get('items') or []
    if not isinstance(raw,list):raise ValidationError('Invalid items.')
    try:return [int(x) for x in raw][:50]
    except (TypeError,ValueError):raise ValidationError('Invalid items.')
@api_view(['POST'])
def quote(request):
    if request.data.get('custom'):
        if not request.user.is_authenticated:raise NotAuthenticated()
        req=CustomRequest.objects.filter(pk=request.data.get('custom'),user=request.user,status='accepted').exclude(price=None).first()
        if not req:raise ValidationError('This custom request is not ready for payment.')
        return Response(custom_totals(req))
    only=chosen_items(request);q=get_cart(request).items.select_related('variant__product')
    items=list(q.filter(pk__in=only) if only else q)
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
    if request.data.get('custom'):
        try:req_id=int(request.data.get('custom'))
        except (TypeError,ValueError):raise ValidationError('Invalid custom request.')
        o,created=reserve_custom_order(request.user,req_id,address.validated_data,key,method)
    else:o,created=reserve_order(request.user,get_cart(request),address.validated_data,key,str(request.data.get('coupon','')),method,only=chosen_items(request))
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
def appointments(request):
    q=Appointment.objects.filter(Q(user=request.user)|Q(email__iexact=request.user.email,user__isnull=True)).exclude(status='cancelled').select_related('slot')
    return Response(AppointmentSerializer(sorted(q,key=lambda a:a.starts_at or (a.slot.starts_at if a.slot_id else a.created_at),reverse=True),many=True).data)
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
    from .richtext import clean_html
    # Imported policy pages hold HTML (headings, lists); it is cleaned to a safe allow-list before display.
    html=clean_html(p.body) if re.search(r'<(p|h[2-4]|ul|ol|li|br|strong)\b',p.body,re.I) else ''
    return Response({'title':p.title,'body':'' if html else p.body,'html':html,'updated':p.updated_at if hasattr(p,'updated_at') else None})
@api_view(['GET'])
def health(request):return Response({'status':'ok'})


@api_view(['GET'])
def delivery_pincode(request,pin):
    """Delhivery serviceability for a PIN code (product page and checkout)."""
    from . import delhivery
    if not re.fullmatch(r'[1-9]\d{5}',pin):return Response({'detail':'Please enter a valid 6-digit PIN code.'},status=400)
    if not delhivery.configured():return Response({'checked':False,'serviceable':True,'cod':True,'prepaid':True,'city':'','state':''})
    try:info=delhivery.pincode(pin)
    except delhivery.DelhiveryError:return Response({'checked':False,'serviceable':True,'cod':True,'prepaid':True,'city':'','state':''})
    return Response({'checked':True,**info})


# ---------- Orders: cancel, invoice, tracking ----------
def own_order(request,ref):
    """Customer's own order by full id or the 8-character reference shown on the site."""
    ref=str(ref).strip().lstrip('#').lower()
    q=Order.objects.filter(user=request.user)
    try:return q.get(pk=uuid.UUID(ref))
    except (ValueError,Order.DoesNotExist):pass
    if re.fullmatch(r'[0-9a-f]{8}',ref):
        found=[o for o in q.only('id') if str(o.id).startswith(ref)]
        if len(found)==1:return q.get(pk=found[0].pk)
    raise NotFound('Order not found in your account.')

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def order_cancel(request,ref):
    o=own_order(request,ref)
    o=cancel_order(o.pk,request.user,str(request.data.get('reason','') or '').strip())
    return Response(OrderSerializer(o).data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_invoice(request,ref):
    from django.http import HttpResponse
    from . import invoice
    o=own_order(request,ref)
    if o.status in ('pending','expired'):raise ValidationError('The invoice is available once the order is confirmed.')
    r=HttpResponse(invoice.render(o),content_type='application/pdf')
    r['Content-Disposition']=f'attachment; filename="Invoice-{invoice.number(o)}.pdf"'
    return r

STAGES=['Confirmed','Packed','Shipped','Out For Delivery','Delivered']
def stage(o):
    cs=(o.courier_status or '').lower()
    if o.status=='delivered' or cs=='delivered':return 4
    if 'out for delivery' in cs or 'dispatched' in cs:return 3
    if o.status=='shipped' or 'transit' in cs or 'picked' in cs or 'reached' in cs:return 2
    if o.awb:return 1
    return 0 if o.status in ('paid','cod','processing') else -1

@api_view(['GET'])
def track(request):
    """Tracking for one order: ?order=<ref> (signed in, own order) or ?awb=<waybill of an Aiman Royale order>."""
    from . import delhivery
    awb=str(request.query_params.get('awb','')).strip();ref=str(request.query_params.get('order','')).strip()
    if awb:
        o=Order.objects.filter(awb=awb).first()
        if not o:raise NotFound('No Aiman Royale shipment found with this waybill number.')
    elif ref:
        if not request.user.is_authenticated:return Response({'error':'Please sign in to track by order ID, or use the waybill number.'},status=401)
        o=own_order(request,ref)
    else:raise ValidationError('Enter an order ID or a waybill number.')
    # Refresh from Delhivery at most every 30 seconds.
    if o.awb and delhivery.configured() and o.status not in ('delivered','cancelled','refunded') and (not o.tracking_synced_at or (timezone.now()-o.tracking_synced_at).total_seconds()>30):
        try:delhivery.track(o);o.refresh_from_db()
        except delhivery.DelhiveryError:pass
    mine=request.user.is_authenticated and o.user_id==request.user.id
    a=o.address or {}
    return Response({'order':str(o.id)[:8].upper() if mine else '','awb':o.awb,'status':o.status,'courier_status':o.courier_status or ('Cancelled' if o.status in ('cancelled','refunded') else ''),
                     'destination':', '.join(x for x in [a.get('city',''),a.get('state','')] if x),'stage':stage(o),'stages':STAGES,
                     'events':o.tracking_events or [],'updated':o.tracking_synced_at,'cancelled':o.status in ('cancelled','refunded','refund_required') and bool(o.cancelled_at)})

# ---------- Contact form and coupon check ----------
@api_view(['POST'])
@throttle_classes([AuthThrottle])
def contact(request):
    d=request.data;name=str(d.get('name','')).strip()[:100];email=str(d.get('email','')).strip()[:254];msg=str(d.get('message','')).strip()
    validate_email(email)
    if not name or len(msg)<10:raise ValidationError('Please enter your name and a message of at least 10 characters.')
    ContactMessage.objects.create(name=name,email=email,phone=str(d.get('phone','')).strip()[:20],subject=str(d.get('subject','')).strip()[:150],message=msg[:3000])
    return Response({'message':'Thank you! Our team will get back to you shortly.'},status=201)

@api_view(['GET'])
def coupon_check(request):
    code=str(request.query_params.get('code','')).strip().upper()
    c=Coupon.objects.filter(code=code,active=True).filter(Q(expires_at__isnull=True)|Q(expires_at__gt=timezone.now())).first()
    if not c:return Response({'valid':False,'message':'This coupon code is not valid or has expired.'})
    return Response({'valid':True,'code':c.code,'percent':c.percent,'minimum':c.minimum,'description':c.description})


# ---------- Continue with Google ----------
def safe_next(value):
    """Only same-site paths, never back to the sign-in pages."""
    v=str(value or '')
    if not v.startswith('/') or v.startswith('//') or re.match(r'^/(login|register)(/|$|\?)',v):return '/account'
    return v[:500]

def google_start(request):
    from urllib.parse import urlencode
    from django.http import HttpResponseRedirect
    if not (settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET):return HttpResponseRedirect('/login?error=google-unavailable')
    state=secrets.token_urlsafe(24)
    request.session['google_state']=state;request.session['google_next']=safe_next(request.GET.get('next'))
    q={'client_id':settings.GOOGLE_CLIENT_ID,'redirect_uri':settings.GOOGLE_REDIRECT_URI,'response_type':'code','scope':'openid email profile','state':state,'prompt':'select_account'}
    return HttpResponseRedirect('https://accounts.google.com/o/oauth2/v2/auth?'+urlencode(q))

def google_callback(request):
    import requests as http
    from django.http import HttpResponseRedirect
    expected=request.session.pop('google_state',None);nxt=request.session.pop('google_next','/account')
    fail=lambda code:HttpResponseRedirect(f'/login?error={code}&next={nxt}')
    if request.GET.get('error'):return fail('google-cancelled')
    if not expected or not hmac.compare_digest(expected,str(request.GET.get('state',''))):return fail('google-expired')
    try:
        tok=http.post('https://oauth2.googleapis.com/token',data={'code':request.GET.get('code',''),'client_id':settings.GOOGLE_CLIENT_ID,'client_secret':settings.GOOGLE_CLIENT_SECRET,
                      'redirect_uri':settings.GOOGLE_REDIRECT_URI,'grant_type':'authorization_code'},timeout=15)
        tok.raise_for_status()
        info=http.get('https://openidconnect.googleapis.com/v1/userinfo',headers={'Authorization':'Bearer '+tok.json()['access_token']},timeout=15)
        info.raise_for_status();info=info.json()
    except (http.RequestException,KeyError,ValueError):return fail('google-failed')
    email=str(info.get('email','')).strip().lower()
    if not email or not info.get('email_verified'):return fail('google-unverified')
    u=Customer.objects.filter(email__iexact=email).first()
    if u and not u.is_active:return fail('google-failed')
    if not u:
        u=Customer(username=email,email=email,first_name=str(info.get('given_name') or info.get('name') or '')[:150],last_name=str(info.get('family_name') or '')[:150])
        u.set_unusable_password();u.save()
    pic=str(info.get('picture') or '')
    if pic.startswith('https://') and not u.avatar and u.avatar_url!=pic[:500]:u.avatar_url=pic[:500];u.save(update_fields=['avatar_url'])
    old=request.session.session_key;login(request,u,backend='django.contrib.auth.backends.ModelBackend');merge_cart(request,old)
    return HttpResponseRedirect(nxt)


# ---------- Calendly bookings ----------
CAL_EVENT=re.compile(r'^https://api\.calendly\.com/scheduled_events/[A-Za-z0-9-]{8,64}$')
CAL_INVITEE=re.compile(r'^https://api\.calendly\.com/scheduled_events/[A-Za-z0-9-]{8,64}/invitees/[A-Za-z0-9-]{8,64}$')
def calendly_get(uri):
    import requests as http
    r=http.get(uri,headers={'Authorization':'Bearer '+settings.CALENDLY_TOKEN},timeout=12);r.raise_for_status()
    return r.json().get('resource',{})

@api_view(['POST'])
@throttle_classes([AuthThrottle])
def calendly_booked(request):
    """Called by the booking page when Calendly reports a new booking, so it shows under My Account → Appointments."""
    from django.utils.dateparse import parse_datetime
    ev=str(request.data.get('event_uri',''));inv=str(request.data.get('invitee_uri',''))
    if not CAL_EVENT.match(ev) or not CAL_INVITEE.match(inv) or not inv.startswith(ev+'/'):raise ValidationError('Invalid Calendly booking.')
    st=request.data.get('session_type');md=request.data.get('mode')
    data={'calendly_event':ev,'source':'calendly','status':'confirmed','session_type':st if st in ('fitting','styling') else 'fitting','mode':md if md in ('studio','video') else 'studio','consent':True}
    u=request.user if request.user.is_authenticated else None
    if u:data.update(user=u,name=(u.get_full_name() or u.first_name or u.email)[:100],email=u.email,phone=u.phone or '')
    if settings.CALENDLY_TOKEN:
        try:
            e=calendly_get(ev);i=calendly_get(inv)
            data.update(starts_at=parse_datetime(e.get('start_time','')) ,name=(i.get('name') or data.get('name') or '')[:100],email=i.get('email') or data.get('email',''))
            loc=e.get('location') or {};data['location']=str(loc.get('join_url') or loc.get('location') or '')[:300]
            if e.get('status')=='canceled':data['status']='cancelled'
        except Exception:pass  # keep the booking even if Calendly's API is unavailable
    if not data.get('name') and not data.get('email'):raise ValidationError('Please sign in so we can save this booking to your account.')
    a,_=Appointment.objects.update_or_create(calendly_invitee=inv,defaults=data)
    return Response({'id':a.pk},status=201)


# ---------- Custom requests (My Account → Custom Requests) ----------
def custom_data(r):
    p=ProductSerializer(r.product).data
    return {'id':r.pk,'ref':f'{r.pk:06d}','product':{'name':p['name'],'slug':p['slug'],'image':(p['images'][0]['url'] if p['images'] else ''),'price':p['price']},
            'variant':r.variant_id,'size':r.variant.size if r.variant_id else '','colour':r.colour,'measurements':r.measurements,'options':r.options,'quantity':r.quantity,'note':r.note,
            'status':r.status,'price':r.price,'total':rupees(r.price)*r.quantity if r.price else None,'admin_note':r.admin_note,
            'order':str(r.order_id) if r.order_id else '','created_at':r.created_at}

MEASURE_KEYS=['bust','waist','hip','armhole']
OPTIONAL_MEASURES=['shoulder','height','sleeve','top_length','bottom_length','blouse_length']
@api_view(['GET','POST'])
@permission_classes([IsAuthenticated])
def custom_requests(request):
    if request.method=='POST':
        d=request.data
        p=Product.objects.filter(active=True,slug=str(d.get('product',''))).first()
        if not p:raise ValidationError('Product not found.')
        if not p.custom_fit:raise ValidationError('Custom measurements are not available for this product.')
        m=d.get('measurements') or {}
        if m.get('unit') not in ('cm','in'):raise ValidationError('Choose inches or cm.')
        clean={}
        for k in MEASURE_KEYS+OPTIONAL_MEASURES:
            v=m.get(k)
            if v in (None,''):continue
            try:v=round(float(v),2)
            except (TypeError,ValueError):raise ValidationError(f'Enter a number for {k.replace("_"," ")}.')
            if not 1<=v<=300:raise ValidationError(f'Check the {k.replace("_"," ")} measurement.')
            clean[k]=v
        o=d.get('options') or {}
        opts={k:str(o.get(k,'') or '').strip()[:500] for k in ('neckline','back','colour','extra') if str(o.get(k,'') or '').strip()}
        if not clean and not opts:raise ValidationError('Enter at least one measurement or customisation.')
        clean['unit']=m['unit']
        v=p.variants.filter(pk=d.get('variant')).first() if d.get('variant') else None
        try:qty=max(1,min(10,int(d.get('quantity',1))))
        except (TypeError,ValueError):qty=1
        r=CustomRequest.objects.create(user=request.user,product=p,variant=v,colour=(v.colour if v else str(d.get('colour','')))[:60],measurements=clean,options=opts,quantity=qty,note=str(d.get('note','') or '')[:1000])
        return Response(custom_data(r),status=201)
    q=CustomRequest.objects.filter(user=request.user).select_related('product','variant').prefetch_related('product__images','product__variants','product__collections','product__occasions')
    return Response([custom_data(r) for r in q])

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def custom_request_cancel(request,pk):
    r=get_object_or_404(CustomRequest,pk=pk,user=request.user)
    if r.status not in ('requested','accepted'):raise ValidationError('This request can no longer be cancelled.')
    r.status='cancelled';r.save(update_fields=['status','updated_at'])
    return Response(custom_data(r))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def order_return(request,ref):
    o=own_order(request,ref)
    o=request_return(o.pk,request.user,str(request.data.get('reason','') or ''))
    return Response(OrderSerializer(o).data)


AVATAR_TYPES={'image/jpeg','image/png','image/webp'}
@api_view(['POST','DELETE'])
@permission_classes([IsAuthenticated])
def avatar(request):
    """Upload (POST, form field 'photo', JPG/PNG/WebP up to 3 MB) or remove (DELETE) the profile photo."""
    u=request.user
    if request.method=='DELETE':
        if u.avatar:u.avatar.delete(save=False)
        u.avatar='';u.avatar_url='';u.save(update_fields=['avatar','avatar_url'])
        return Response({'user':user_data(u)})
    f=request.FILES.get('photo')
    if not f:raise ValidationError('Choose a photo to upload.')
    if f.content_type not in AVATAR_TYPES or f.size>3*1024*1024:raise ValidationError('Please upload a JPG, PNG or WebP photo up to 3 MB.')
    try:
        from PIL import Image
        img=Image.open(f);img.verify();f.seek(0)
    except Exception:raise ValidationError('This file is not a valid image.')
    old=u.avatar.name if u.avatar else ''
    u.avatar.save(f'{u.pk}-{secrets.token_hex(4)}.{f.content_type.split("/")[1].replace("jpeg","jpg")}',f,save=False)
    u.save(update_fields=['avatar'])
    if old:u.avatar.storage.delete(old)
    return Response({'user':user_data(u)})
