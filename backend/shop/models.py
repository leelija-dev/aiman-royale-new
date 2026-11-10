import re
import uuid
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings

class Customer(AbstractUser):
    phone=models.CharField(max_length=16,unique=True,null=True,blank=True)
    marketing_opt_in=models.BooleanField(default=False)
    avatar=models.ImageField('Profile photo',upload_to='avatars/',blank=True)
    avatar_url=models.URLField('Photo from Google',max_length=500,blank=True)


def parse_schema(text):
    """Custom JSON-LD pasted in admin -> list of schema objects.
    Accepts plain JSON (an object or a list) or one/more <script type="application/ld+json"> blocks."""
    import json
    text=(text or '').strip()
    if not text:return []
    blocks=re.findall(r'<script[^>]*>(.*?)</script>',text,re.S|re.I) or [text]
    out=[]
    for b in blocks:
        v=json.loads(b.strip())
        out+=v if isinstance(v,list) else [v]
    if not all(isinstance(x,dict) for x in out):raise ValueError('Each schema must be a JSON object.')
    return out


def validate_schema(text):
    from django.core.exceptions import ValidationError as VE
    try:parse_schema(text)
    except Exception as e:
        raise VE(f'This is not valid JSON-LD schema ({e}). Paste the JSON from a schema generator, e.g. {{"@context": "https://schema.org", "@type": "Product", ...}}.')


SCHEMA_HELP='Optional. Paste your own JSON-LD (schema.org) — plain JSON or &lt;script type="application/ld+json"&gt; blocks. It is added to this page as-is, after the automatic schema.'

class SiteSettings(models.Model):
    schema_json=models.TextField('Custom schema (JSON-LD)',blank=True,validators=[validate_schema],help_text=SCHEMA_HELP)
    name=models.CharField(max_length=80,default='Aiman Royale')
    gstin=models.CharField('GSTIN (printed on invoices)',max_length=20,blank=True)
    return_days=models.PositiveSmallIntegerField('Return window (days after delivery)',default=7)
    announcement=models.CharField(max_length=180,default='New Arrivals Just In | Enjoy Up to 70% OFF')
    hero_title=models.CharField(max_length=180,default='Shop Luxury\nCrafted For You')
    hero_description=models.CharField(max_length=240,default='Designer ethnic wear for every celebration. Find your style, make it yours.')
    hero_image=models.ImageField(upload_to='editorial/',blank=True)
    phone=models.CharField(max_length=20,default='919163892445')
    email=models.EmailField(default='contact.aimanroyale@gmail.com')
    address=models.TextField(default='Islampur, Kadambagachhi, North 24 Parganas, Kol-700125, West Bengal, India')
    shipping_fee=models.DecimalField(max_digits=9,decimal_places=2,default=0)
    free_shipping_above=models.DecimalField(max_digits=9,decimal_places=2,default=999)
    cod_enabled=models.BooleanField(default=False)
    # Category page defaults ({name} = collection name)
    category_tagline=models.CharField(max_length=160,default='Heritage in every detail. Elegance in every moment.')
    category_seo_heading=models.CharField(max_length=160,default='Buy Embroidered {name} for Women Online')
    category_seo_body=models.TextField(default='At Aiman Royale, we treat {name} for women as more than just a collection. They are a reflection of culture, grace, and confidence — designed for every celebration on your calendar.')
    fitting_title=models.CharField('Fitting banner title',max_length=160,default='A style you love.\nA fit that feels like you.')
    fitting_text=models.CharField('Fitting banner text',max_length=300,default='Discuss your measurements, your occasion and your favourite designs with our team.')
    fitting_button=models.CharField('Fitting banner button',max_length=40,default='Book a Fitting')
    fitting_steps=models.CharField('Fitting banner steps',max_length=200,default='Choose a date.|Meet our team.|Find your fit.',help_text='Separate steps with |')
    fitting_image=models.ImageField('Fitting banner image',upload_to='editorial/',blank=True)
    size_guide_note=models.CharField('Size guide note',max_length=300,default='This is a standard size guide for basic body measurements. There may be slight variations depending on the garment type and fit.')
    size_chart_pdf=models.FileField('Size chart PDF',upload_to='size-guide/',blank=True,help_text='Optional. Without a file, the Download button creates a printable PDF of the chart.')
    calendly_url=models.URLField('Calendly link',blank=True,default='https://calendly.com/susmitaghosh-leelija/30min',help_text='Appointment page uses Calendly when set.')
    calendly_primary_color=models.CharField(max_length=6,default='A10000',help_text='Hex without #')
    calendly_text_color=models.CharField(max_length=6,default='EC4899')
    calendly_background_color=models.CharField(max_length=6,default='FCE7F3')
    instagram_url=models.URLField(blank=True)
    facebook_url=models.URLField(blank=True)
    youtube_url=models.URLField(blank=True)
    pinterest_url=models.URLField(blank=True)
    footer_tagline=models.CharField(max_length=80,default='Grace in Every Celebration')
    footer_about=models.TextField('Footer brand text',blank=True)
    newsletter_eyebrow=models.CharField(max_length=60,default='Never miss an update')
    newsletter_title=models.CharField(max_length=120,default='Subscribe to Our Newsletter',help_text='The last word is shown in pink.')
    newsletter_text=models.CharField(max_length=300,blank=True)
    instagram_handle=models.CharField(max_length=60,blank=True,help_text='e.g. @AimanRoyale')
    instagram_note=models.CharField(max_length=80,blank=True,help_text='e.g. Join 40K+ fashion enthusiasts')
    footer_highlights=models.TextField(blank=True,help_text='One per line: TITLE|text (shown bottom-left of the footer)')
    footer_services=models.TextField(blank=True,help_text='One per line: Title|Small text|icon (icons: cod, truck, check, card, box, return)')
    payment_methods=models.CharField(max_length=300,blank=True,help_text='Comma separated, e.g. Mastercard, VISA, COD')
    delivery_partners=models.CharField(max_length=200,blank=True,help_text='Comma separated, e.g. Delhivery')
    footer_note=models.CharField(max_length=120,blank=True,help_text='Small line under the copyright, e.g. Crafted with love in India')
    delivery_message=models.CharField('Delivery check message',max_length=200,default='We deliver across India. Shipping charges and timelines are confirmed at checkout.',help_text='Shown after a customer checks a PIN code on a product page.')
    # All Products page (/products)
    shop_eyebrow=models.CharField('Banner small heading',max_length=80,default='The Aiman Royale Collection')
    shop_title=models.CharField('Banner title',max_length=160,default='Find your occasion.\nDiscover your style.')
    shop_text=models.CharField('Banner text',max_length=300,default='Explore designer ethnic wear, from statement Anarkalis to festive suits and elegant occasion wear.')
    shop_image=models.ImageField('Banner image',upload_to='editorial/',blank=True)
    shop_heading=models.CharField('Product list heading',max_length=80,default='All Products')
    shop_subheading=models.CharField('Product list subheading',max_length=120,default='Explore the collection')
    shop_fitting_title=models.CharField('Fitting banner title',max_length=160,default='Love the dress.\nLet’s find your fit.')
    shop_fitting_text=models.CharField('Fitting banner text',max_length=300,default='Speak with our team about sizing, styling and your occasion before you choose.')
    shop_fitting_note=models.CharField('Fitting banner note',max_length=160,default='Choose a date and request your appointment.')
    shop_fitting_image=models.ImageField('Fitting banner image',upload_to='editorial/',blank=True)
    shop_trust=models.TextField('Trust strip',default='Personal Fit Guidance|Expert advice for your perfect look\nDesigner Ethnic Wear|Curated for every occasion\nSecure Shopping|Safe & trusted payments',help_text='One per line: Title|Small text')
    class Meta:verbose_name='Site settings';verbose_name_plural='Site settings'
    @classmethod
    def current(cls): return cls.objects.get_or_create(pk=1)[0]
    def save(self,*args,**kwargs): self.pk=1;super().save(*args,**kwargs)
    def __str__(self):return self.name

class Collection(models.Model):
    schema_json=models.TextField('Custom schema (JSON-LD)',blank=True,validators=[validate_schema],help_text=SCHEMA_HELP)
    name=models.CharField(max_length=100)
    slug=models.SlugField(unique=True)
    description=models.TextField(blank=True)
    image=models.ImageField(upload_to='collections/',blank=True)
    seo_title=models.CharField(max_length=150,blank=True)
    seo_description=models.CharField(max_length=300,blank=True)
    active=models.BooleanField(default=True)
    parent=models.ForeignKey('self',on_delete=models.SET_NULL,null=True,blank=True,related_name='children',help_text='e.g. Anarkali Suits belongs to Salwar Kameez. Sub-collections appear under their parent in the menu.')
    sort_order=models.PositiveIntegerField(default=0)
    # Category page text. Leave blank to use the defaults from Site settings. {name} is replaced with the collection name.
    hero_eyebrow=models.CharField('Banner small heading',max_length=80,blank=True,help_text='Default: "The {name} Edit"')
    hero_tagline=models.CharField('Banner tagline',max_length=160,blank=True)
    seo_heading=models.CharField('SEO section heading',max_length=160,blank=True)
    seo_body=models.TextField('SEO section text',blank=True)
    details=models.TextField('Category details (bottom of page)',blank=True,help_text='Long description shown above "Join Our Inner Circle", collapsed to 3 lines with Read more. Headings, paragraphs, lists, bold and links are kept. Plain text works too (blank line = new paragraph).')
    def save(self,*args,**kwargs):
        from .richtext import clean_html
        self.details=clean_html(self.details)
        super().save(*args,**kwargs)
    def __str__(self):return self.name

class PageQuestion(models.Model):
    """FAQ or guide entry on category pages. With no collection it is a default shown on every category without its own."""
    KINDS=[('faq','FAQ ("A little guidance")'),('guide','SEO section accordion')]
    collection=models.ForeignKey('Collection',on_delete=models.CASCADE,null=True,blank=True,related_name='questions',help_text='Leave empty to use on all categories that have none of their own.')
    kind=models.CharField(max_length=10,choices=KINDS,default='faq')
    question=models.CharField('Question / title',max_length=200)
    answer=models.TextField()
    sort_order=models.PositiveIntegerField(default=0)
    active=models.BooleanField(default=True)
    class Meta:ordering=['sort_order','id'];verbose_name='Category FAQ / guide';verbose_name_plural='Category FAQs & guides'
    def __str__(self):return self.question

class Occasion(models.Model):
    """Shown in category filters, 'Shop by Occasion' cards and the mega menu."""
    name=models.CharField(max_length=60,unique=True)
    slug=models.SlugField(unique=True)
    image=models.ImageField(upload_to='occasions/',blank=True,help_text='Card image for "Shop by Occasion".')
    sort_order=models.PositiveIntegerField(default=0)
    active=models.BooleanField(default=True)
    class Meta:ordering=['sort_order','name']
    def __str__(self):return self.name

class Colour(models.Model):
    """Swatch colours for the filter. Names must match the colour written on product variants."""
    name=models.CharField(max_length=40,unique=True)
    hex=models.CharField('Swatch colour',max_length=7,default='#999999',help_text='e.g. #6b1426')
    sort_order=models.PositiveIntegerField(default=0)
    class Meta:ordering=['sort_order','name']
    def __str__(self):return self.name

class MenuItem(models.Model):
    """Top-level item in the main menu (Wedding, Bridal, ...)."""
    label=models.CharField(max_length=40)
    url=models.CharField(max_length=200,help_text='e.g. /collections/salwar-kameez')
    sort_order=models.PositiveIntegerField(default=0)
    active=models.BooleanField(default=True)
    show_occasions=models.BooleanField(default=True,help_text='Add an "Occasion" tab listing every active occasion automatically.')
    auto_styles=models.BooleanField(default=True,help_text='Fill the "Style" tab automatically with the collections that have products here (sub-collections first).')
    feature_title=models.CharField(max_length=60,blank=True)
    feature_image=models.ImageField(upload_to='menu/',blank=True)
    feature_url=models.CharField(max_length=200,blank=True)
    class Meta:ordering=['sort_order','id']
    def __str__(self):return self.label

class MenuLink(models.Model):
    GROUPS=[('Style','Style'),('Occasion','Occasion'),('Collection','Collection')]
    item=models.ForeignKey(MenuItem,on_delete=models.CASCADE,related_name='links')
    group=models.CharField(max_length=20,choices=GROUPS,default='Style')
    label=models.CharField(max_length=60)
    url=models.CharField(max_length=200)
    sort_order=models.PositiveIntegerField(default=0)
    class Meta:ordering=['sort_order','id']
    def __str__(self):return f'{self.item} › {self.group} › {self.label}'

class Product(models.Model):
    schema_json=models.TextField('Custom schema (JSON-LD)',blank=True,validators=[validate_schema],help_text=SCHEMA_HELP)
    name=models.CharField(max_length=180)
    slug=models.SlugField(unique=True,max_length=200)
    description=models.TextField(blank=True)
    care=models.TextField(blank=True)
    fabric=models.CharField(max_length=100,blank=True)
    fit=models.CharField(max_length=100,blank=True,help_text='e.g. Regular')
    includes=models.CharField(max_length=160,blank=True,help_text='e.g. Suit, skirt & dupatta')
    collections=models.ManyToManyField(Collection,related_name='products')
    occasions=models.ManyToManyField(Occasion,related_name='products',blank=True)
    price=models.DecimalField(max_digits=10,decimal_places=2,validators=[MinValueValidator(Decimal('1'))])
    mrp=models.DecimalField(max_digits=10,decimal_places=2,validators=[MinValueValidator(Decimal('1'))])
    featured=models.BooleanField(default=False)
    active=models.BooleanField(default=True)
    custom_fit=models.BooleanField(default=True)
    seo_title=models.CharField(max_length=150,blank=True)
    seo_description=models.CharField(max_length=300,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta:ordering=['-featured','-created_at'];indexes=[models.Index(fields=['active','price'])]
    def __str__(self):return self.name

MAX_IMAGE_MB=10


def validate_image_size(f):
    """Photos up to 10 MB are accepted."""
    from django.core.exceptions import ValidationError as VE
    if f and getattr(f,'size',0)>MAX_IMAGE_MB*1024*1024:
        raise VE(f'This photo is {f.size/1024/1024:.1f} MB. Please upload a photo up to {MAX_IMAGE_MB} MB.')


def shrink_upload(field_file,max_side=2400):
    """Resize a freshly uploaded photo so its longest side is at most 2400 px (keeps the format).
    A 10 MB camera photo becomes a few hundred KB, so product pages stay fast."""
    from io import BytesIO
    from PIL import Image, ImageOps
    from django.core.files.base import ContentFile
    f=getattr(field_file,'file',None)
    if f is None or getattr(field_file,'_committed',True):return
    try:
        f.seek(0);im=Image.open(f);fmt=(im.format or 'JPEG').upper()
        if fmt not in ('JPEG','PNG','WEBP'):return
        im=ImageOps.exif_transpose(im)
        if max(im.size)<=max_side and getattr(f,'size',0)<=2*1024*1024:
            f.seek(0);return
        im.thumbnail((max_side,max_side),Image.LANCZOS)
        out=BytesIO()
        if fmt=='JPEG':im.convert('RGB').save(out,'JPEG',quality=88,optimize=True,progressive=True)
        elif fmt=='WEBP':im.save(out,'WEBP',quality=88,method=5)
        else:im.save(out,'PNG',optimize=True)
        field_file.save(field_file.name.rsplit('/',1)[-1],ContentFile(out.getvalue()),save=False)
    except Exception:
        try:f.seek(0)
        except Exception:pass


class ProductImage(models.Model):
    product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name='images')
    image=models.ImageField(upload_to='products/',validators=[validate_image_size],help_text='JPG, PNG or WebP up to 10 MB. Large photos are resized automatically to 2400 px.')
    alt=models.CharField('Alt text',max_length=220,blank=True,help_text='Optional – the product name is used when empty.')
    position=models.PositiveIntegerField(default=0)
    class Meta:ordering=['position','id']
    def save(self,*a,**k):
        if not self.alt and self.product_id:self.alt=self.product.name[:220]
        shrink_upload(self.image)
        super().save(*a,**k)

class Variant(models.Model):
    product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name='variants')
    sku=models.CharField(max_length=80,unique=True)
    size=models.CharField(max_length=10)
    colour=models.CharField(max_length=40)
    stock=models.PositiveIntegerField(default=0)
    class Meta:constraints=[models.UniqueConstraint(fields=['product','size','colour'],name='unique_product_size_colour')]
    def __str__(self):return f'{self.product.name} / {self.size} / {self.colour}'

class Cart(models.Model):
    user=models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,null=True,blank=True)
    session_key=models.CharField(max_length=80,unique=True,null=True,blank=True)
    updated_at=models.DateTimeField(auto_now=True)
class CartItem(models.Model):
    cart=models.ForeignKey(Cart,on_delete=models.CASCADE,related_name='items')
    variant=models.ForeignKey(Variant,on_delete=models.CASCADE)
    quantity=models.PositiveIntegerField(default=1,validators=[MinValueValidator(1),MaxValueValidator(10)])
    measurements=models.JSONField(default=dict,blank=True)
    class Meta:constraints=[models.UniqueConstraint(fields=['cart','variant'],name='unique_cart_variant')]

class Coupon(models.Model):
    code=models.CharField(max_length=32,unique=True)
    percent=models.PositiveIntegerField(validators=[MinValueValidator(1),MaxValueValidator(90)])
    minimum=models.DecimalField(max_digits=10,decimal_places=2,default=0)
    active=models.BooleanField(default=True)
    expires_at=models.DateTimeField(null=True,blank=True)
    description=models.CharField(max_length=140,blank=True,help_text='Shown to shoppers, e.g. "Festive offer on all suits"')
    public=models.BooleanField('Show in Saving Zone',default=True,help_text='List this coupon on the bag and checkout pages.')
    def __str__(self):return self.code

class Order(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    idempotency_key=models.UUIDField(unique=True)
    status=models.CharField(max_length=24,default='pending',choices=[(s,s) for s in ['pending','paid','cod','processing','shipped','delivered','cancelled','expired','refund_required','refunded']])
    subtotal=models.DecimalField(max_digits=10,decimal_places=2)
    discount=models.DecimalField(max_digits=10,decimal_places=2,default=0)
    shipping=models.DecimalField(max_digits=10,decimal_places=2,default=0)
    total=models.DecimalField(max_digits=10,decimal_places=2)
    address=models.JSONField()
    payment_method=models.CharField(max_length=20,default='cashfree')
    gateway_order_id=models.CharField(max_length=100,blank=True,db_index=True)
    payment_session_id=models.CharField(max_length=500,blank=True)
    gateway_payment_id=models.CharField(max_length=100,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    expires_at=models.DateTimeField()
    tracking_url=models.URLField(blank=True)
    note=models.TextField('Customer note',blank=True)
    pay_with=models.CharField(max_length=20,blank=True,help_text='Payment option chosen at checkout (upi, card, netbanking)')
    awb=models.CharField('Delhivery AWB (waybill)',max_length=40,blank=True,db_index=True)
    courier_status=models.CharField(max_length=80,blank=True)
    tracking_events=models.JSONField(default=list,blank=True)
    tracking_synced_at=models.DateTimeField(null=True,blank=True)
    pickup_requested_at=models.DateTimeField(null=True,blank=True,help_text='Set when a Delhivery pickup is requested. Customers cannot cancel after this.')
    cancelled_at=models.DateTimeField(null=True,blank=True)
    cancel_reason=models.CharField(max_length=200,blank=True)
    delivered_at=models.DateTimeField(null=True,blank=True)
    # Returns (Delhivery reverse pickup)
    RETURN_STATUSES=[('','—'),('requested','Return requested'),('pickup_booked','Reverse pickup booked'),('in_transit','Return in transit'),('received','Return received'),('rejected','Return rejected')]
    return_status=models.CharField(max_length=16,blank=True,choices=RETURN_STATUSES)
    return_reason=models.CharField(max_length=300,blank=True)
    return_requested_at=models.DateTimeField(null=True,blank=True)
    return_awb=models.CharField('Return AWB (reverse pickup)',max_length=40,blank=True,db_index=True)
    return_courier_status=models.CharField(max_length=80,blank=True)
    class Meta:ordering=['-created_at']

class OrderItem(models.Model):
    order=models.ForeignKey(Order,on_delete=models.CASCADE,related_name='items')
    variant=models.ForeignKey(Variant,on_delete=models.PROTECT)
    name=models.CharField(max_length=180)
    unit_price=models.DecimalField(max_digits=10,decimal_places=2)
    quantity=models.PositiveIntegerField()
    measurements=models.JSONField(default=dict)

class Review(models.Model):
    """Customer review. Shown on the product page only after it is approved in admin."""
    product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name='reviews')
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True)
    name=models.CharField(max_length=80)
    rating=models.PositiveSmallIntegerField(validators=[MinValueValidator(1),MaxValueValidator(5)])
    text=models.TextField(max_length=2000)
    approved=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:ordering=['-created_at'];constraints=[models.UniqueConstraint(fields=['product','user'],name='one_review_per_customer')]
    def __str__(self):return f'{self.product} · {self.rating}★ · {self.name}'

class Wishlist(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    product=models.ForeignKey(Product,on_delete=models.CASCADE)
    class Meta:constraints=[models.UniqueConstraint(fields=['user','product'],name='unique_wishlist')]

class AppointmentSlot(models.Model):
    starts_at=models.DateTimeField(unique=True)
    enabled=models.BooleanField(default=True)
    def __str__(self):return str(self.starts_at)
class Appointment(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True)
    slot=models.ForeignKey(AppointmentSlot,on_delete=models.PROTECT,related_name='appointments',null=True,blank=True,help_text='Empty for Calendly bookings')
    starts_at=models.DateTimeField(null=True,blank=True,help_text='Calendly bookings: start time')
    source=models.CharField(max_length=12,default='site',choices=[('site','Website slots'),('calendly','Calendly')])
    calendly_event=models.URLField(max_length=300,blank=True)
    calendly_invitee=models.URLField(max_length=300,blank=True,db_index=True)
    location=models.CharField(max_length=300,blank=True,help_text='Studio address or video-call link')
    name=models.CharField(max_length=100)
    phone=models.CharField(max_length=16,blank=True)
    email=models.EmailField(blank=True)
    session_type=models.CharField(max_length=32,choices=[('fitting','Fitting & Measurements'),('styling','Style Consultation')])
    mode=models.CharField(max_length=16,choices=[('studio','Visit the Studio'),('video','Video Consultation')])
    occasion=models.CharField(max_length=60,blank=True)
    notes=models.TextField(blank=True)
    status=models.CharField(max_length=16,default='requested',choices=[(s,s) for s in ['requested','confirmed','cancelled','completed']])
    consent=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:constraints=[models.UniqueConstraint(fields=['slot'],condition=models.Q(status__in=['requested','confirmed']),name='one_active_booking_per_slot')]

class OTPChallenge(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    phone=models.CharField(max_length=16,db_index=True)
    code_hash=models.CharField(max_length=128)
    expires_at=models.DateTimeField()
    attempts=models.PositiveIntegerField(default=0)
    used=models.BooleanField(default=False)
    name=models.CharField(max_length=100,blank=True)
    purpose=models.CharField(max_length=10,default='login')
    marketing_opt_in=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
class Subscriber(models.Model):
    email=models.EmailField(unique=True)
    created_at=models.DateTimeField(auto_now_add=True)
class Page(models.Model):
    schema_json=models.TextField('Custom schema (JSON-LD)',blank=True,validators=[validate_schema],help_text=SCHEMA_HELP)
    slug=models.SlugField(unique=True)
    title=models.CharField(max_length=150)
    body=models.TextField(help_text='Plain text (blank line = new paragraph), or simple HTML: headings, paragraphs, lists, bold, links.')
    published=models.BooleanField(default=False)
    updated_at=models.DateTimeField(auto_now=True,null=True)
    def __str__(self):return self.title


class HomeSection(models.Model):
    """One block of the homepage. Sections show in 'sort_order'; untick 'active' to hide one."""
    KINDS=[('hero','Hero banner (add cards below for more slides)'),('featured','Featured cards (4 across)'),('collections','Collection tiles'),('cards','Image cards (4 across)'),
           ('products','Product row'),('confidence','Confidence strip'),('mosaic','Wedding mosaic (6 pictures)'),('banner','Wide promo banner'),
           ('strip','Style strip (8 small pictures)'),('benefits','Benefits row'),('consult','Appointment / consultation'),
           ('notes',"Designer's notes"),('story','Brand story text (with Read more)'),('carousel','Promo banner carousel'),('duo','Two large banners'),('sizeguide','Size guide (chart + how to measure)'),('occasions','Occasion cards (automatic: Haldi, Wedding, Party, Festive…)')]
    kind=models.CharField(max_length=20,choices=KINDS)
    admin_name=models.CharField('Name (admin only)',max_length=80)
    eyebrow=models.CharField('Small heading',max_length=120,blank=True)
    title=models.CharField(max_length=200,blank=True,help_text='Use a new line for a line break.')
    subtitle=models.CharField(max_length=300,blank=True)
    text=models.TextField(blank=True)
    button_label=models.CharField(max_length=60,blank=True)
    button_url=models.CharField(max_length=200,blank=True)
    image=models.ImageField(upload_to='home/',blank=True)
    image_path=models.CharField('…or built-in image',max_length=200,blank=True,help_text='Used when no image is uploaded, e.g. /images/hero.webp')
    mobile_image=models.ImageField('Mobile picture',upload_to='home/',blank=True,help_text='Optional picture for phones (portrait, e.g. 800×1000). Hero slides only.')
    mobile_image_path=models.CharField('…or built-in mobile picture',max_length=200,blank=True,help_text='e.g. /images/banners/aiman-banner-1-mobile.webp')
    alt_text=models.CharField('Image alt text (SEO)',max_length=160,blank=True,help_text='Describes the picture for Google and screen readers.')
    image_title=models.CharField('Image title (SEO)',max_length=160,blank=True,help_text='Shown as a tooltip when hovering over the picture.')
    product_filter=models.CharField(max_length=200,blank=True,default='featured=1',help_text='Product rows only. e.g. featured=1, sort=newest, collection=lehengas, occasion=wedding')
    product_count=models.PositiveIntegerField(default=4)
    sort_order=models.PositiveIntegerField(default=0)
    active=models.BooleanField(default=True)
    class Meta:ordering=['sort_order','id'];verbose_name='Homepage section'
    def __str__(self):return self.admin_name

class HomeCard(models.Model):
    ICONS=[('','None'),('award','Award'),('shield','Shield'),('truck','Truck'),('headphones','Headphones'),('package','Package'),
           ('gem','Gem'),('heart','Heart'),('star','Star'),('sparkles','Sparkles'),('calendar','Calendar'),('ruler','Ruler'),('video','Video call'),('user','Person'),('check','Tick'),('dress','Dress')]
    section=models.ForeignKey(HomeSection,on_delete=models.CASCADE,related_name='cards')
    label=models.CharField('Small label',max_length=80,blank=True)
    title=models.CharField(max_length=160,blank=True)
    text=models.TextField(blank=True)
    bullets=models.TextField(blank=True,help_text='One per line')
    caption=models.CharField('Link text',max_length=120,blank=True)
    url=models.CharField(max_length=200,blank=True)
    button_label=models.CharField(max_length=60,blank=True)
    icon=models.CharField(max_length=20,choices=ICONS,blank=True)
    image=models.ImageField(upload_to='home/',blank=True)
    image_path=models.CharField('…or built-in image',max_length=200,blank=True)
    mobile_image=models.ImageField('Mobile picture',upload_to='home/',blank=True,help_text='Optional picture for phones (portrait). Hero slides only.')
    mobile_image_path=models.CharField('…or built-in mobile picture',max_length=200,blank=True)
    alt_text=models.CharField('Image alt text (SEO)',max_length=160,blank=True)
    image_title=models.CharField('Image title (SEO)',max_length=160,blank=True)
    sort_order=models.PositiveIntegerField(default=0)
    active=models.BooleanField(default=True)
    class Meta:ordering=['sort_order','id']
    def __str__(self):return self.title or self.label or f'Card {self.pk}'


class SizeChartRow(models.Model):
    """One row of the Size Guide popup. Enter body measurements in INCHES; the cm view is calculated."""
    size=models.CharField(max_length=20,help_text='e.g. XS')
    alt_size=models.CharField('Alternate size',max_length=20,blank=True,help_text='e.g. 34')
    bust=models.DecimalField(max_digits=5,decimal_places=2)
    waist=models.DecimalField(max_digits=5,decimal_places=2)
    hip=models.DecimalField(max_digits=5,decimal_places=2)
    armhole=models.DecimalField(max_digits=5,decimal_places=2)
    uk_size=models.CharField('UK size',max_length=10,blank=True)
    sort_order=models.PositiveIntegerField(default=0)
    class Meta:ordering=['sort_order','id'];verbose_name='Size chart row'
    def __str__(self):return f'{self.size} ({self.alt_size})' if self.alt_size else self.size

class MeasureStep(models.Model):
    """'How to Measure Yourself' step in the Size Guide popup."""
    title=models.CharField(max_length=80)
    text=models.TextField(blank=True)
    image=models.ImageField(upload_to='size-guide/',blank=True,help_text='Leave empty to show a simple diagram.')
    sort_order=models.PositiveIntegerField(default=0)
    class Meta:ordering=['sort_order','id'];verbose_name='How-to-measure step'
    def __str__(self):return self.title


class FooterLink(models.Model):
    GROUPS=[('categories','Top Categories'),('occasions','Occasions'),('explore','Explore'),('account','My Account')]
    group=models.CharField(max_length=20,choices=GROUPS)
    label=models.CharField(max_length=60)
    url=models.CharField(max_length=200)
    sort_order=models.PositiveIntegerField(default=0)
    active=models.BooleanField(default=True)
    class Meta:ordering=['group','sort_order','id']
    def __str__(self):return f'{self.get_group_display()} › {self.label}'

class InstagramPost(models.Model):
    """Photo tile in the footer's 'Follow Our Instagram' block."""
    caption=models.CharField(max_length=80,blank=True)
    image=models.ImageField(upload_to='instagram/',blank=True)
    image_path=models.CharField('…or built-in image',max_length=200,blank=True)
    url=models.URLField(blank=True,help_text='Post link; leave empty to use the Instagram profile link')
    sort_order=models.PositiveIntegerField(default=0)
    active=models.BooleanField(default=True)
    class Meta:ordering=['sort_order','id']
    def __str__(self):return self.caption or f'Post {self.pk}'


class ProductFAQ(models.Model):
    """Question and answer on the product page. Leave 'product' empty to show it on every product."""
    product=models.ForeignKey(Product,on_delete=models.CASCADE,null=True,blank=True,related_name='faqs',help_text='Empty = shown on all products')
    question=models.CharField(max_length=250)
    answer=models.TextField()
    sort_order=models.PositiveIntegerField(default=0)
    active=models.BooleanField(default=True)
    class Meta:ordering=['sort_order','id'];verbose_name='Product FAQ'
    def __str__(self):return self.question

class ContactMessage(models.Model):
    """Message sent from the Contact Us page."""
    name=models.CharField(max_length=100)
    email=models.EmailField()
    phone=models.CharField(max_length=20,blank=True)
    subject=models.CharField(max_length=150,blank=True)
    message=models.TextField(max_length=3000)
    created_at=models.DateTimeField(auto_now_add=True)
    handled=models.BooleanField(default=False)
    class Meta:ordering=['-created_at']
    def __str__(self):return f'{self.name} · {self.subject or self.message[:40]}'


class CustomRequest(models.Model):
    """A customer's made-to-measure request. Our team checks it, sets a price and accepts (or rejects) it;
    the customer then pays from My Account → Custom Requests, which creates a normal order."""
    STATUSES=[('requested','Requested'),('accepted','Accepted – awaiting payment'),('rejected','Not possible'),('cancelled','Cancelled by customer'),('ordered','Ordered')]
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='custom_requests')
    product=models.ForeignKey(Product,on_delete=models.PROTECT,related_name='custom_requests')
    variant=models.ForeignKey(Variant,on_delete=models.SET_NULL,null=True,blank=True,help_text='Colour (and size used as the base)')
    colour=models.CharField(max_length=60,blank=True)
    measurements=models.JSONField(default=dict,help_text='bust, waist, hip, armhole and unit (cm / in)')
    quantity=models.PositiveIntegerField(default=1)
    note=models.TextField('Customer note',blank=True,max_length=1000)
    options=models.JSONField('Customisations',default=dict,blank=True,help_text='Neckline / back design changes, colour change and other requests')
    status=models.CharField(max_length=12,choices=STATUSES,default='requested')
    price=models.DecimalField('Price per piece (₹)',max_digits=10,decimal_places=2,null=True,blank=True,help_text='Required to accept the request')
    admin_note=models.CharField('Message to customer',max_length=300,blank=True)
    order=models.OneToOneField(Order,on_delete=models.SET_NULL,null=True,blank=True,related_name='custom_request')
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta:ordering=['-created_at'];verbose_name='Custom request'
    def __str__(self):return f'#{self.pk:06d} · {self.product}'
    def clean(self):
        from django.core.exceptions import ValidationError as VE
        if self.status=='accepted' and not self.price:raise VE({'price':'Set the price before accepting the request.'})


class ShippingLabel(Order):
    """Admin tool: download a Delhivery shipping label by waybill number."""
    class Meta:proxy=True;verbose_name='Shipping label';verbose_name_plural='Shipping labels (by AWB)'


class PickupRequest(models.Model):
    """A Delhivery pickup booked from Admin → Pickup requests."""
    pickup_at=models.DateTimeField('Pickup date & time')
    package_count=models.PositiveIntegerField()
    orders=models.ManyToManyField(Order,related_name='pickups',blank=True)
    response=models.JSONField(default=dict,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='+')
    class Meta:ordering=['-created_at'];verbose_name='Pickup request'
    def __str__(self):return f'Pickup {self.pickup_at:%d %b %Y %H:%M} · {self.package_count} parcel(s)'

class ReadyToShip(Order):
    class Meta:proxy=True;verbose_name='Order to ship';verbose_name_plural='Pickup requests · orders to ship'

class ReturnOrder(Order):
    class Meta:proxy=True;verbose_name='Return';verbose_name_plural='Returns & refunds'
