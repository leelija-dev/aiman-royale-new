import uuid
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings

class Customer(AbstractUser):
    phone=models.CharField(max_length=16,unique=True,null=True,blank=True)
    marketing_opt_in=models.BooleanField(default=False)

class SiteSettings(models.Model):
    name=models.CharField(max_length=80,default='Aiman Royale')
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
    @classmethod
    def current(cls): return cls.objects.get_or_create(pk=1)[0]
    def save(self,*args,**kwargs): self.pk=1;super().save(*args,**kwargs)
    def __str__(self):return self.name

class Collection(models.Model):
    name=models.CharField(max_length=100)
    slug=models.SlugField(unique=True)
    description=models.TextField(blank=True)
    image=models.ImageField(upload_to='collections/',blank=True)
    seo_title=models.CharField(max_length=150,blank=True)
    seo_description=models.CharField(max_length=300,blank=True)
    active=models.BooleanField(default=True)
    # Category page text. Leave blank to use the defaults from Site settings. {name} is replaced with the collection name.
    hero_eyebrow=models.CharField('Banner small heading',max_length=80,blank=True,help_text='Default: "The {name} Edit"')
    hero_tagline=models.CharField('Banner tagline',max_length=160,blank=True)
    seo_heading=models.CharField('SEO section heading',max_length=160,blank=True)
    seo_body=models.TextField('SEO section text',blank=True)
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

class ProductImage(models.Model):
    product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name='images')
    image=models.ImageField(upload_to='products/')
    alt=models.CharField(max_length=220)
    position=models.PositiveIntegerField(default=0)
    class Meta:ordering=['position','id']

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
    slot=models.ForeignKey(AppointmentSlot,on_delete=models.PROTECT,related_name='appointments')
    name=models.CharField(max_length=100)
    phone=models.CharField(max_length=16)
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
    slug=models.SlugField(unique=True)
    title=models.CharField(max_length=150)
    body=models.TextField(help_text='Plain text. HTML is escaped in the storefront.')
    published=models.BooleanField(default=False)
    def __str__(self):return self.title


class HomeSection(models.Model):
    """One block of the homepage. Sections show in 'sort_order'; untick 'active' to hide one."""
    KINDS=[('hero','Hero banner'),('featured','Featured cards (4 across)'),('collections','Collection tiles'),('cards','Image cards (4 across)'),
           ('products','Product row'),('confidence','Confidence strip'),('mosaic','Wedding mosaic (6 pictures)'),('banner','Wide promo banner'),
           ('strip','Style strip (8 small pictures)'),('benefits','Benefits row'),('consult','Appointment / consultation'),
           ('notes',"Designer's notes"),('story','Brand story text')]
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
    product_filter=models.CharField(max_length=200,blank=True,default='featured=1',help_text='Product rows only. e.g. featured=1, sort=newest, collection=lehengas, occasion=wedding')
    product_count=models.PositiveIntegerField(default=4)
    sort_order=models.PositiveIntegerField(default=0)
    active=models.BooleanField(default=True)
    class Meta:ordering=['sort_order','id'];verbose_name='Homepage section'
    def __str__(self):return self.admin_name

class HomeCard(models.Model):
    ICONS=[('','None'),('award','Award'),('shield','Shield'),('truck','Truck'),('headphones','Headphones'),('package','Package'),
           ('gem','Gem'),('heart','Heart'),('star','Star'),('sparkles','Sparkles'),('calendar','Calendar'),('ruler','Ruler')]
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
    sort_order=models.PositiveIntegerField(default=0)
    active=models.BooleanField(default=True)
    class Meta:ordering=['sort_order','id']
    def __str__(self):return self.title or self.label or f'Card {self.pk}'
