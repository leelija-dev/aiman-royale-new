from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *
admin.site.site_header='Aiman Royale · Store Management'
class ImageInline(admin.TabularInline):model=ProductImage;extra=1
class VariantInline(admin.TabularInline):model=Variant;extra=1
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display=['name','price','active','featured'];list_filter=['active','featured','collections','occasions'];search_fields=['name','slug'];prepopulated_fields={'slug':('name',)};filter_horizontal=['collections','occasions'];inlines=[ImageInline,VariantInline]
@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):prepopulated_fields={'slug':('name',)};list_display=['name','active']
@admin.register(Customer)
class CustomerAdmin(UserAdmin):
    fieldsets=UserAdmin.fieldsets+ (('WhatsApp',{'fields':('phone','marketing_opt_in')}),)
class ItemInline(admin.TabularInline):
    model=OrderItem;extra=0;can_delete=False;readonly_fields=['variant','name','unit_price','quantity','measurements']
    def has_add_permission(self,*args):return False
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display=['id','user','status','total','created_at'];list_filter=['status'];search_fields=['id','user__email','gateway_payment_id'];inlines=[ItemInline]
    readonly_fields=['id','user','idempotency_key','status','subtotal','discount','shipping','total','address','payment_method','gateway_order_id','payment_session_id','gateway_payment_id','created_at','expires_at']
    actions=['mark_processing','mark_shipped','mark_delivered']
    @admin.action(description='Mark paid/COD orders processing')
    def mark_processing(self,request,q):q.filter(status__in=['paid','cod']).update(status='processing')
    @admin.action(description='Mark processing orders shipped (set tracking URL first)')
    def mark_shipped(self,request,q):q.filter(status='processing').exclude(tracking_url='').update(status='shipped')
    @admin.action(description='Mark shipped orders delivered')
    def mark_delivered(self,request,q):q.filter(status='shipped').update(status='delivered')
    def has_add_permission(self,*args):return False
    def has_delete_permission(self,*args):return False
@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display=['name','slot','session_type','mode','status'];list_filter=['status','mode'];readonly_fields=['consent','created_at']
@admin.register(SiteSettings)
class SettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self,request):return not SiteSettings.objects.exists()
    def has_delete_permission(self,*args):return False
admin.site.register([AppointmentSlot,Coupon,Subscriber,Page])

@admin.register(Occasion)
class OccasionAdmin(admin.ModelAdmin):
    list_display=['name','slug','sort_order','active'];list_editable=['sort_order','active'];prepopulated_fields={'slug':('name',)}
@admin.register(Colour)
class ColourAdmin(admin.ModelAdmin):
    list_display=['name','hex','sort_order'];list_editable=['hex','sort_order'];search_fields=['name']
class MenuLinkInline(admin.TabularInline):model=MenuLink;extra=1;fields=['group','label','url','sort_order']
@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display=['label','url','sort_order','active'];list_editable=['sort_order','active'];inlines=[MenuLinkInline]
    fieldsets=((None,{'fields':('label','url','sort_order','active','show_occasions')}),('Feature picture (right side of the dropdown)',{'fields':('feature_title','feature_image','feature_url')}))
