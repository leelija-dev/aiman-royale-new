from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *
admin.site.site_header='Aiman Royale · Store Management'
class ImageInline(admin.TabularInline):model=ProductImage;extra=1
class VariantInline(admin.TabularInline):model=Variant;extra=1
class ProductFAQInline(admin.TabularInline):
    model=ProductFAQ;extra=1;fields=['question','answer','sort_order','active'];verbose_name_plural='FAQs for this product (shown above the questions shared by all products)'
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display=['name','price','active','featured'];list_filter=['active','featured','collections','occasions'];search_fields=['name','slug'];prepopulated_fields={'slug':('name',)};filter_horizontal=['collections','occasions'];inlines=[ImageInline,VariantInline,ProductFAQInline]
class PageQuestionInline(admin.TabularInline):
    model=PageQuestion;extra=1;fields=['kind','question','answer','sort_order','active'];verbose_name_plural='FAQs & guide entries for this category (leave empty to use the defaults)'
@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    prepopulated_fields={'slug':('name',)};list_display=['name','parent','sort_order','active'];list_editable=['parent','sort_order','active'];list_filter=['parent'];inlines=[PageQuestionInline]
    fieldsets=((None,{'fields':('name','slug','parent','sort_order','description','image','active')}),
               ('SEO',{'fields':('seo_title','seo_description')}),
               ('Category page text (leave blank to use the defaults in Site settings; {name} = collection name)',{'fields':('hero_eyebrow','hero_tagline','seo_heading','seo_body')}),
               ('Category details (bottom of page, with Read more)',{'fields':('details',)}))
@admin.register(PageQuestion)
class PageQuestionAdmin(admin.ModelAdmin):
    list_display=['question','kind','collection','sort_order','active'];list_filter=['kind','collection','active'];list_editable=['sort_order','active'];search_fields=['question','answer']
@admin.register(Customer)
class CustomerAdmin(UserAdmin):
    fieldsets=UserAdmin.fieldsets+ (('WhatsApp',{'fields':('phone','marketing_opt_in')}),)
class ItemInline(admin.TabularInline):
    model=OrderItem;extra=0;can_delete=False;readonly_fields=['variant','name','unit_price','quantity','measurements']
    def has_add_permission(self,*args):return False
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    # Every order, newest first, with filters by status, payment, returns and date.
    list_filter=['status','payment_method','return_status','created_at','courier_status'];inlines=[ItemInline];date_hierarchy='created_at';list_per_page=50
    list_display=['ref','created_at','customer','phone','items_summary','total','payment','status','awb','courier_status','return_status']
    list_display_links=['ref'];list_select_related=['user']
    search_fields=['id','user__email','user__first_name','user__last_name','gateway_payment_id','awb','return_awb','address__phone','address__name']
    readonly_fields=['id','user','idempotency_key','status','cancelled_at','cancel_reason','note','pay_with','subtotal','discount','shipping','total','address','payment_method','gateway_order_id','payment_session_id','gateway_payment_id','created_at','expires_at','courier_status','tracking_view','tracking_synced_at','delivered_at','return_status','return_reason','return_requested_at','return_awb','return_courier_status']
    exclude=['tracking_events']
    actions=['export_csv','download_invoice','admin_cancel','return_approve','return_received','return_reject','mark_processing','mark_shipped','mark_delivered','delhivery_create','delhivery_track','delhivery_slip','delhivery_pickup','delhivery_cancel']
    @admin.action(description='Download invoice (PDF, first selected order)')
    def download_invoice(self,request,q):
        from django.http import HttpResponse
        from . import invoice
        o=q.first()
        r=HttpResponse(invoice.render(o),content_type='application/pdf');r['Content-Disposition']=f'attachment; filename="Invoice-{invoice.number(o)}.pdf"';return r
    @admin.display(description='Tracking history')
    def tracking_view(self,o):
        from django.utils.html import format_html_join
        return format_html_join('','<div>{} — <b>{}</b> {} <small>{}</small></div>',((e.get('time',''),e.get('status',''),e.get('detail',''),e.get('location','')) for e in o.tracking_events)) or '—'
    def _each(self,request,q,fn,ok):
        from django.contrib import messages
        from . import delhivery
        done=0
        for o in q:
            try:fn(o);done+=1
            except delhivery.DelhiveryError as e:self.message_user(request,f'Order {str(o.id)[:8].upper()}: {e}',messages.ERROR)
        if done:self.message_user(request,ok.format(done),messages.SUCCESS)
    @admin.action(description='Delhivery: create shipment (get AWB)')
    def delhivery_create(self,request,q):
        from . import delhivery
        self._each(request,q,delhivery.create_shipment,'{} shipment(s) booked with Delhivery.')
    @admin.action(description='Delhivery: refresh tracking')
    def delhivery_track(self,request,q):
        from . import delhivery
        self._each(request,q,delhivery.track,'Tracking refreshed for {} order(s).')
    @admin.action(description='Delhivery: download packing slips')
    def delhivery_slip(self,request,q):
        from django.contrib import messages
        from django.shortcuts import redirect
        from django.utils.html import format_html_join
        from . import delhivery
        awbs=[o.awb for o in q if o.awb]
        if not awbs:return self.message_user(request,'Create the Delhivery shipment first (no AWB on the selected orders).',messages.WARNING)
        try:slip=delhivery.packing_slip(awbs)
        except delhivery.DelhiveryError as e:return self.message_user(request,str(e),messages.ERROR)
        if len(slip['links'])==1:return redirect(slip['links'][0])
        if slip['links']:return self.message_user(request,format_html_join(' ','<a href="{}" target="_blank" rel="noopener">Packing slip {}</a>',((l,i+1) for i,l in enumerate(slip['links']))),messages.SUCCESS)
        self.message_user(request,'Delhivery returned the slip data without a PDF link. Download it from the Delhivery dashboard.',messages.WARNING)
    @admin.action(description='Delhivery: request pickup for tomorrow')
    def delhivery_pickup(self,request,q):
        from django.contrib import messages
        from . import delhivery
        n=q.exclude(awb='').count()
        if not n:return self.message_user(request,'None of the selected orders has an AWB yet.',messages.WARNING)
        try:
            delhivery.request_pickup(n)
            from django.utils import timezone
            q.exclude(awb='').update(pickup_requested_at=timezone.now())
            self.message_user(request,f'Pickup requested for {n} parcel(s). Customers can no longer cancel these orders.',messages.SUCCESS)
        except delhivery.DelhiveryError as e:self.message_user(request,str(e),messages.ERROR)
    @admin.action(description='Delhivery: cancel shipment')
    def delhivery_cancel(self,request,q):
        from . import delhivery
        self._each(request,q.exclude(awb=''),delhivery.cancel,'{} shipment(s) cancelled.')
    @admin.action(description='Mark paid/COD orders processing')
    def mark_processing(self,request,q):q.filter(status__in=['paid','cod']).update(status='processing')
    @admin.action(description='Mark processing orders shipped (set tracking URL first)')
    def mark_shipped(self,request,q):q.filter(status='processing').exclude(tracking_url='').update(status='shipped')
    @admin.action(description='Mark shipped orders delivered')
    def mark_delivered(self,request,q):
        from django.utils import timezone
        q.filter(status='shipped').update(status='delivered',delivered_at=timezone.now())
    def get_queryset(self,request):return super().get_queryset(request).prefetch_related('items')
    @admin.display(description='Order',ordering='created_at')
    def ref(self,o):return '#'+str(o.id)[:8].upper()
    @admin.display(description='Customer',ordering='user__email')
    def customer(self,o):return (o.address or {}).get('name') or o.user.get_full_name() or o.user.email
    @admin.display(description='Phone')
    def phone(self,o):return (o.address or {}).get('phone','')
    @admin.display(description='Items')
    def items_summary(self,o):
        it=list(o.items.all());return ', '.join(f'{i.name} ×{i.quantity}' for i in it[:2])+(f' +{len(it)-2} more' if len(it)>2 else '')
    @admin.display(description='Payment',ordering='payment_method')
    def payment(self,o):return 'COD' if o.payment_method=='cod' else 'Online'+(f' · {o.pay_with.upper()}' if o.pay_with else '')
    @admin.action(description='Export selected orders to CSV')
    def export_csv(self,request,q):
        import csv
        from django.http import HttpResponse
        r=HttpResponse(content_type='text/csv');r['Content-Disposition']='attachment; filename="orders.csv"'
        w=csv.writer(r);w.writerow(['Order','Date','Customer','Email','Phone','City','PIN','Items','Subtotal','Discount','Shipping','Total','Payment','Status','AWB','Courier status','Return'])
        for o in q.prefetch_related('items').select_related('user'):
            a=o.address or {}
            w.writerow(['#'+str(o.id)[:8].upper(),o.created_at.strftime('%Y-%m-%d %H:%M'),a.get('name',''),a.get('email') or o.user.email,a.get('phone',''),a.get('city',''),a.get('pincode',''),
                        '; '.join(f'{i.name} x{i.quantity}' for i in o.items.all()),o.subtotal,o.discount,o.shipping,o.total,self.payment(o),o.status,o.awb,o.courier_status,o.get_return_status_display() if o.return_status else ''])
        return r
    @admin.action(description='Cancel order (also cancels the Delhivery shipment and refunds online payments)')
    def admin_cancel(self,request,q):
        from django.contrib import messages
        from rest_framework.exceptions import ValidationError as APIError
        from .services import cancel_order
        done=0
        for o in q:
            try:cancel_order(o.pk,reason='Cancelled by store',by_admin=True);done+=1
            except APIError as e:self.message_user(request,f'#{str(o.id)[:8].upper()}: {e.detail[0] if isinstance(e.detail,list) else e.detail}',messages.ERROR)
        if done:self.message_user(request,f'{done} order(s) cancelled.',messages.SUCCESS)
    @admin.action(description='Return: approve and book Delhivery reverse pickup')
    def return_approve(self,request,q):
        from . import delhivery
        self._each(request,q.filter(status='delivered').exclude(return_status__in=['received','rejected']),delhivery.create_return,'Reverse pickup booked for {} order(s).')
    @admin.action(description='Return: parcel received — refund the customer')
    def return_received(self,request,q):
        from django.contrib import messages
        from .services import refund_order
        n=0
        for o in q.filter(status='delivered').exclude(return_status__in=['','rejected','received']):
            o.status=refund_order(o,'Return received');o.return_status='received';o.save(update_fields=['status','return_status']);n+=1
        self.message_user(request,f'{n} return(s) received. Online payments are refunded through Cashfree; COD orders are marked "refund_required" for a manual refund.',messages.SUCCESS)
    @admin.action(description='Return: reject request')
    def return_reject(self,request,q):
        n=q.filter(return_status='requested').update(return_status='rejected');self.message_user(request,f'{n} return request(s) rejected.')
    def has_add_permission(self,*args):return False
    def has_delete_permission(self,*args):return False
@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display=['name','email','when','session_type','mode','source','status'];list_filter=['status','mode','source'];search_fields=['name','email','phone'];readonly_fields=['consent','created_at','calendly_event','calendly_invitee']
    @admin.display(description='Date & time')
    def when(self,a):return a.starts_at or (a.slot.starts_at if a.slot_id else '—')
@admin.register(SiteSettings)
class SettingsAdmin(admin.ModelAdmin):
    fieldsets=((None,{'fields':('name','announcement','hero_title','hero_description','hero_image')}),
               ('Contact',{'fields':('phone','email','address','gstin','delivery_message')}),
               ('Size guide popup',{'fields':('size_guide_note','size_chart_pdf')}),
               ('Appointments (Calendly)',{'fields':('calendly_url','calendly_primary_color','calendly_text_color','calendly_background_color')}),
               ('Footer & social links',{'fields':('footer_tagline','footer_about','newsletter_eyebrow','newsletter_title','newsletter_text','instagram_handle','instagram_note','instagram_url','facebook_url','youtube_url','pinterest_url','footer_highlights','footer_services','payment_methods','delivery_partners','footer_note')}),
               ('Checkout',{'fields':('shipping_fee','free_shipping_above','cod_enabled')}),
               ('Category page defaults ({name} = collection name)',{'fields':('category_tagline','category_seo_heading','category_seo_body')}),
               ('Fitting banner (all category pages)',{'fields':('fitting_title','fitting_text','fitting_button','fitting_steps','fitting_image')}),
               ('All Products page (/products)',{'fields':('shop_eyebrow','shop_title','shop_text','shop_image','shop_heading','shop_subheading','shop_fitting_title','shop_fitting_text','shop_fitting_note','shop_fitting_image','shop_trust')}))
    def has_add_permission(self,request):return not SiteSettings.objects.exists()
    def has_delete_permission(self,*args):return False
admin.site.register([AppointmentSlot,Subscriber,Page])
@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display=['code','percent','minimum','description','public','active','expires_at'];list_editable=['public','active'];search_fields=['code']

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
    fieldsets=((None,{'fields':('label','url','sort_order','active','auto_styles','show_occasions')}),('Feature picture (right side of the dropdown)',{'fields':('feature_title','feature_image','feature_url')}))
class HomeCardInline(admin.StackedInline):
    model=HomeCard;extra=0
    fields=[('title','label','sort_order','active'),('caption','url','button_label','icon'),'text','bullets',('image','image_path')]
@admin.register(HomeSection)
class HomeSectionAdmin(admin.ModelAdmin):
    list_display=['admin_name','kind','title','sort_order','active'];list_editable=['sort_order','active'];list_filter=['kind','active'];inlines=[HomeCardInline]
    fieldsets=((None,{'fields':('admin_name','kind','sort_order','active')}),
               ('Text',{'fields':('eyebrow','title','subtitle','text','button_label','button_url')}),
               ('Picture',{'fields':('image','image_path')}),
               ('Product rows only',{'fields':('product_filter','product_count')}))
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display=['product','name','rating','approved','created_at'];list_filter=['approved','rating'];list_editable=['approved'];search_fields=['product__name','name','text']
    actions=['approve']
    @admin.action(description='Approve selected reviews')
    def approve(self,request,q):q.update(approved=True)
@admin.register(SizeChartRow)
class SizeChartRowAdmin(admin.ModelAdmin):
    list_display=['size','alt_size','bust','waist','hip','armhole','uk_size','sort_order'];list_editable=['alt_size','bust','waist','hip','armhole','uk_size','sort_order']
@admin.register(MeasureStep)
class MeasureStepAdmin(admin.ModelAdmin):
    list_display=['title','sort_order'];list_editable=['sort_order']
@admin.register(FooterLink)
class FooterLinkAdmin(admin.ModelAdmin):
    list_display=['label','group','url','sort_order','active'];list_editable=['url','sort_order','active'];list_filter=['group']
@admin.register(InstagramPost)
class InstagramPostAdmin(admin.ModelAdmin):
    list_display=['caption','sort_order','active'];list_editable=['sort_order','active']

@admin.register(ProductFAQ)
class ProductFAQAdmin(admin.ModelAdmin):
    list_display=['question','product','sort_order','active'];list_editable=['sort_order','active'];list_filter=['active',('product',admin.EmptyFieldListFilter)]
    search_fields=['question','answer','product__name'];autocomplete_fields=['product']
@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display=['name','email','phone','subject','created_at','handled'];list_editable=['handled'];list_filter=['handled'];search_fields=['name','email','message']
    readonly_fields=['name','email','phone','subject','message','created_at']

@admin.register(CustomRequest)
class CustomRequestAdmin(admin.ModelAdmin):
    """Check each made-to-measure request, set the price, then choose Accepted (or Not possible).
    The customer is emailed and pays from My Account → Custom Requests."""
    list_display=['ref','customer','product','sizes','colour','quantity','price','status','created_at']
    list_editable=['price','status'];list_filter=['status','created_at'];list_display_links=['ref']
    search_fields=['id','user__email','user__first_name','product__name','colour']
    readonly_fields=['user','product','variant','colour','measurements_view','options_view','quantity','note','order','created_at','updated_at']
    fields=['user','product','variant','colour','measurements_view','options_view','quantity','note','price','status','admin_note','order','created_at','updated_at']
    actions=['export_csv']
    @admin.display(description='Request',ordering='id')
    def ref(self,r):return f'#{r.pk:06d}'
    @admin.display(description='Customer',ordering='user__email')
    def customer(self,r):return r.user.get_full_name() or r.user.email
    @admin.display(description='Measurements')
    def sizes(self,r):
        m=r.measurements or {};u=m.get('unit','cm')
        return ' · '.join(f'{k.replace("_"," ").title()} {m[k]}{u}' for k in ['bust','waist','hip','armhole','shoulder','height','sleeve','top_length','bottom_length','blouse_length'] if k in m)
    measurements_view=sizes
    @admin.display(description='Customisations')
    def options_view(self,r):
        o=r.options or {};names={'neckline':'Neckline','back':'Back design','colour':'Colour','extra':'Other requests'}
        return ' · '.join(f'{names.get(k,k)}: {v}' for k,v in o.items()) or '—'
    def has_add_permission(self,request):return False
    def save_model(self,request,obj,form,change):
        before=CustomRequest.objects.filter(pk=obj.pk).values_list('status',flat=True).first()
        super().save_model(request,obj,form,change)
        if before!=obj.status and obj.status in ('accepted','rejected'):
            from django.core.mail import send_mail
            from django.conf import settings as dj
            ref=f'#{obj.pk:06d}'
            if obj.status=='accepted':
                text=(f'Good news! Your custom request {ref} for {obj.product.name} has been accepted.\n\nPrice: Rs. {obj.price:,.0f} per piece'
                      f'{" × " + str(obj.quantity) if obj.quantity > 1 else ""}.\n{obj.admin_note}\n\nPay from My Account → Custom Requests: {dj.PUBLIC_SITE_URL}/account?tab=custom')
            else:
                text=f'Sorry, we can’t make custom request {ref} for {obj.product.name}.\n{obj.admin_note}\n\nReply to this email or contact us and we’ll help you find an alternative.'
            send_mail(f'Your Aiman Royale custom request {ref}',text,None,[obj.user.email],fail_silently=True)
    @admin.action(description='Export selected to CSV')
    def export_csv(self,request,q):
        import csv
        from django.http import HttpResponse
        r=HttpResponse(content_type='text/csv');r['Content-Disposition']='attachment; filename="custom-requests.csv"'
        w=csv.writer(r);w.writerow(['Request','Date','Customer','Email','Product','Colour','Bust','Waist','Hip','Armhole','Unit','Qty','Price','Status','Note'])
        for c in q.select_related('user','product'):
            m=c.measurements or {}
            w.writerow([f'#{c.pk:06d}',c.created_at.strftime('%Y-%m-%d %H:%M'),c.user.get_full_name(),c.user.email,c.product.name,c.colour,m.get('bust'),m.get('waist'),m.get('hip'),m.get('armhole'),m.get('unit'),c.quantity,c.price or '',c.get_status_display(),c.note])
        return r


@admin.register(ShippingLabel)
class ShippingLabelAdmin(admin.ModelAdmin):
    """Download a Delhivery shipping label by entering one or more waybill (AWB) numbers."""
    def has_add_permission(self,request):return False
    def has_delete_permission(self,request,obj=None):return False
    def has_change_permission(self,request,obj=None):return request.user.is_staff
    def changelist_view(self,request,extra_context=None):
        import re as _re
        from django.contrib import messages
        from django.shortcuts import redirect
        from django.template.response import TemplateResponse
        from . import delhivery
        awbs=_re.findall(r'\d{6,20}',request.GET.get('awb',''))[:25]
        recent=Order.objects.exclude(awb='').order_by('-created_at')[:15]
        ctx={**self.admin_site.each_context(request),'title':'Download shipping label','opts':self.model._meta,'awb':request.GET.get('awb',''),'recent':recent,'packages':[]}
        if awbs:
            try:
                slip=delhivery.packing_slip(awbs)
                if len(slip['links'])==1 and len(awbs)==1:return redirect(slip['links'][0])
                ctx['links']=slip['links'];ctx['packages']=slip['packages']
                if not slip['links'] and not slip['packages']:messages.warning(request,'Delhivery returned no label for these waybill numbers.')
            except delhivery.DelhiveryError as e:messages.error(request,str(e))
        return TemplateResponse(request,'admin/shop/shipping_label.html',ctx)


from . import admin_dashboard  # noqa: E402,F401  (dashboard, pickup requests, returns)
