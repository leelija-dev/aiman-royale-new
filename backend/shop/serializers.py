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
    images=ImageSerializer(many=True,read_only=True)
    variants=VariantSerializer(many=True,read_only=True)
    collections=CollectionSerializer(many=True,read_only=True)
    class Meta:model=Product;fields=['id','name','slug','description','care','fabric','occasions','price','mrp','featured','custom_fit','images','variants','collections','seo_title','seo_description','updated_at']
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
    starts_at=serializers.DateTimeField(source='slot.starts_at',read_only=True)
    slot=serializers.PrimaryKeyRelatedField(queryset=AppointmentSlot.objects.all())
    phone=serializers.RegexField(r'^\+?[1-9]\d{9,14}$')
    class Meta:model=Appointment;fields=['id','slot','starts_at','name','phone','email','session_type','mode','occasion','notes','consent','status'];read_only_fields=['id','status']
    def validate_consent(self,value):
        if not value:raise serializers.ValidationError('Please consent to appointment-related contact.')
        return value
class OrderItemSerializer(serializers.ModelSerializer):
    size=serializers.CharField(source='variant.size')
    colour=serializers.CharField(source='variant.colour')
    class Meta:model=OrderItem;fields=['name','unit_price','quantity','size','colour','measurements']
class OrderSerializer(serializers.ModelSerializer):
    items=OrderItemSerializer(many=True,read_only=True)
    class Meta:model=Order;fields=['id','status','subtotal','discount','shipping','total','address','payment_method','gateway_order_id','created_at','tracking_url','items']
