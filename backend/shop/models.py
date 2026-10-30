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
    def __str__(self):return self.name

class Product(models.Model):
    name=models.CharField(max_length=180)
    slug=models.SlugField(unique=True,max_length=200)
    description=models.TextField(blank=True)
    care=models.TextField(blank=True)
    fabric=models.CharField(max_length=100,blank=True)
    collections=models.ManyToManyField(Collection,related_name='products')
    occasions=models.JSONField(default=list,blank=True)
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
    class Meta:ordering=['-created_at']

class OrderItem(models.Model):
    order=models.ForeignKey(Order,on_delete=models.CASCADE,related_name='items')
    variant=models.ForeignKey(Variant,on_delete=models.PROTECT)
    name=models.CharField(max_length=180)
    unit_price=models.DecimalField(max_digits=10,decimal_places=2)
    quantity=models.PositiveIntegerField()
    measurements=models.JSONField(default=dict)

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
