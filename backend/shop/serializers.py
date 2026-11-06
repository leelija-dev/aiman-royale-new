from rest_framework import serializers
from .models import *
class ImageSerializer(serializers.ModelSerializer):
    url=serializers.SerializerMethodField()
    class Meta:model=ProductImage;fields=['id','url','alt']
    def get_url(self,obj):return obj.image.url if obj.image else ''
class VariantSerializer(serializers.ModelSerializer):
    class Meta:model=Variant;fields=['id','sku','size','colour','stock']
class CollectionSerializer(serializers.ModelSerializer):
    class Meta:model=Collection;fields=['id','name','slug','description','image','seo_title','seo_description']
class ProductSerializer(serializers.ModelSerializer):
    occasions=serializers.SlugRelatedField(slug_field='name',many=True,read_only=True)
    images=ImageSerializer(many=True,read_only=True)
    variants=VariantSerializer(many=True,read_only=True)
    collections=CollectionSerializer(many=True,read_only=True)
    class Meta:model=Product;fields=['id','name','slug','description','care','fabric','fit','includes','occasions','price','mrp','featured','custom_fit','images','variants','collections','seo_title','seo_description','updated_at']
class AddressSerializer(serializers.Serializer):
    name=serializers.CharField(max_length=100)
    phone=serializers.RegexField(r'^\+?[1-9]\d{9,14}$')
    email=serializers.EmailField()
    line1=serializers.CharField(max_length=220)
    line2=serializers.CharField(max_length=220,required=False,allow_blank=True)
    city=serializers.CharField(max_length=100)
    state=serializers.CharField(max_length=100)
    pincode=serializers.RegexField(r'^[1-9]\d{5}$')
    country=serializers.ChoiceField(choices=['IN'],default='IN')
class AppointmentSerializer(serializers.ModelSerializer):
    starts_at=serializers.SerializerMethodField()
    slot=serializers.PrimaryKeyRelatedField(queryset=AppointmentSlot.objects.all())
    def get_starts_at(self,a):
        t=a.starts_at or (a.slot.starts_at if a.slot_id else None)
        return t.isoformat() if t else None
    phone=serializers.RegexField(r'^\+?[1-9]\d{9,14}$')
    class Meta:model=Appointment;fields=['id','slot','starts_at','name','phone','email','session_type','mode','occasion','notes','consent','status','source','location'];read_only_fields=['id','status','source','location']
    def validate_consent(self,value):
        if not value:raise serializers.ValidationError('Please consent to appointment-related contact.')
        return value
class OrderItemSerializer(serializers.ModelSerializer):
    size=serializers.CharField(source='variant.size')
    colour=serializers.CharField(source='variant.colour')
    slug=serializers.CharField(source='variant.product.slug')
    image=serializers.SerializerMethodField()
    class Meta:model=OrderItem;fields=['name','unit_price','quantity','size','colour','measurements','slug','image']
    def get_image(self,obj):
        im=obj.variant.product.images.first()
        return im.image.url if im and im.image else ''
class OrderSerializer(serializers.ModelSerializer):
    items=OrderItemSerializer(many=True,read_only=True)
    can_cancel=serializers.SerializerMethodField()
    can_return=serializers.SerializerMethodField()
    def get_can_cancel(self,o):
        from .services import can_cancel
        return can_cancel(o)
    def get_can_return(self,o):
        from .services import can_return
        return can_return(o)
    class Meta:model=Order;fields=['id','status','subtotal','discount','shipping','total','address','payment_method','pay_with','note','gateway_order_id','created_at','tracking_url','awb','courier_status','tracking_events','cancelled_at','cancel_reason','can_cancel','delivered_at','can_return','return_status','return_reason','return_awb','return_courier_status','items']
