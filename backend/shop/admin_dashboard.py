"""Store dashboard (admin home), Pickup requests and Returns & refunds sections."""
from datetime import timedelta

from django import forms
from django.contrib import admin, messages
from django.db.models import Count, F, Q, Sum
from django.template.response import TemplateResponse
from django.utils import timezone

from . import delhivery
from .admin import OrderAdmin
from .models import (Appointment, ContactMessage, CustomRequest, Order, PickupRequest, ReadyToShip, ReturnOrder,
                     Variant)

ref = lambda o: '#' + str(o.id)[:8].upper()

# ---------- Dashboard (admin home page) ----------
GROUPS = [
    ('Orders & shipping', 'box', ['Order', 'ReadyToShip', 'PickupRequest', 'ShippingLabel', 'ReturnOrder', 'Coupon']),
    ('Customers', 'users', ['Customer', 'CustomRequest', 'Appointment', 'AppointmentSlot', 'ContactMessage', 'Review', 'Subscriber', 'Group']),
    ('Catalogue', 'tag', ['Product', 'Collection', 'Occasion', 'Colour', 'ProductFAQ', 'SizeChartRow', 'MeasureStep']),
    ('Website content', 'layout', ['HomeSection', 'MenuItem', 'FooterLink', 'InstagramPost', 'Page', 'PageQuestion', 'SiteSettings']),
]


def dashboard(request):
    now = timezone.now(); today = timezone.localtime(now).replace(hour=0, minute=0, second=0, microsecond=0)
    live = Order.objects.exclude(status__in=['pending', 'expired'])
    week = live.filter(created_at__gte=now - timedelta(days=7))
    to_ship = Order.objects.filter(status__in=['paid', 'cod', 'processing'])
    stats = [
        ('Orders today', live.filter(created_at__gte=today).count(), '/admin/shop/order/', ''),
        ('Sales · last 7 days', '₹{:,.0f}'.format(week.exclude(status__in=['cancelled', 'refunded']).aggregate(s=Sum('total'))['s'] or 0), '/admin/shop/order/', ''),
        ('Need a waybill', to_ship.filter(awb='').count(), '/admin/shop/readytoship/?awb__exact=', 'warn'),
        ('Waiting for pickup', to_ship.exclude(awb='').filter(pickup_requested_at__isnull=True).exclude(courier_status='Cancelled').count(), '/admin/shop/readytoship/', 'warn'),
        ('Custom requests to review', CustomRequest.objects.filter(status='requested').count(), '/admin/shop/customrequest/?status__exact=requested', 'warn'),
        ('Returns to handle', Order.objects.filter(return_status__in=['requested', 'pickup_booked', 'in_transit', 'received']).exclude(status='refunded').count(), '/admin/shop/returnorder/', 'warn'),
        ('New messages', ContactMessage.objects.filter(handled=False).count(), '/admin/shop/contactmessage/?handled__exact=0', ''),
        ('Low stock (≤ 2)', Variant.objects.filter(stock__lte=2, product__active=True).count(), '/admin/shop/product/', ''),
    ]
    models = {m['object_name']: m for app in admin.site.get_app_list(request) for m in app['models']}
    groups, used = [], set()
    for title, icon, names in GROUPS:
        items = [models[n] for n in names if n in models]; used |= {n for n in names}
        if items:
            groups.append({'title': title, 'icon': icon, 'models': items})
    rest = [m for n, m in models.items() if n not in used]
    if rest:
        groups.append({'title': 'More', 'icon': 'more', 'models': rest})
    recent = live.select_related('user').order_by('-created_at')[:8]
    upcoming = Appointment.objects.filter(Q(starts_at__gte=now) | Q(slot__starts_at__gte=now)).exclude(status='cancelled').select_related('slot')[:5]
    return {'stats': stats, 'groups': groups, 'recent': [{'ref': ref(o), 'id': o.pk, 'name': (o.address or {}).get('name') or o.user.email, 'total': o.total,
            'status': o.get_status_display() if hasattr(o, 'get_status_display') else o.status, 'when': o.created_at} for o in recent], 'upcoming': upcoming}


_index = admin.site.index
def index(request, extra_context=None):
    return _index(request, {**dashboard(request), **(extra_context or {})})
admin.site.index = index
admin.site.index_template = 'admin/aiman_index.html'
admin.site.index_title = 'Dashboard'
admin.site.site_title = 'Aiman Royale admin'


# ---------- Pickup requests: orders to ship ----------
class HasAwb(admin.SimpleListFilter):
    title = 'waybill'; parameter_name = 'has_awb'
    def lookups(self, request, model_admin): return [('no', 'Needs waybill'), ('yes', 'Has waybill')]
    def queryset(self, request, q):
        return q.filter(awb='') if self.value() == 'no' else q.exclude(awb='') if self.value() == 'yes' else q


class PickupState(admin.SimpleListFilter):
    title = 'pickup'; parameter_name = 'pickup'
    def lookups(self, request, model_admin): return [('waiting', 'Not requested yet'), ('requested', 'Pickup requested')]
    def queryset(self, request, q):
        return q.filter(pickup_requested_at__isnull=True) if self.value() == 'waiting' else q.filter(pickup_requested_at__isnull=False) if self.value() == 'requested' else q


class PickupForm(forms.Form):
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    time = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}), initial='11:00')


@admin.register(ReadyToShip)
class ReadyToShipAdmin(OrderAdmin):
    """All paid / COD orders that still have to leave the warehouse. Book the shipment (waybill),
    request a Delhivery pickup for the selected parcels, and print labels."""
    list_display = ['ref', 'created_at', 'customer', 'phone', 'destination', 'items_summary', 'total', 'payment', 'awb', 'courier_status', 'pickup']
    list_filter = [HasAwb, PickupState, 'payment_method', 'created_at']
    actions = ['delhivery_create', 'request_pickup', 'delhivery_slip', 'admin_cancel']
    date_hierarchy = None
    def get_queryset(self, request):
        return super().get_queryset(request).filter(status__in=['paid', 'cod', 'processing']).exclude(courier_status='Cancelled')
    def has_add_permission(self, request): return False
    @admin.display(description='Deliver to')
    def destination(self, o): a = o.address or {}; return f"{a.get('city', '')} {a.get('pincode', '')}".strip()
    @admin.display(description='Pickup', ordering='pickup_requested_at')
    def pickup(self, o):
        p = o.pickups.order_by('-pickup_at').first()
        return f'{timezone.localtime(p.pickup_at):%d %b, %H:%M}' if p else ('Requested' if o.pickup_requested_at else '—')

    @admin.action(description='Request Delhivery pickup for selected orders…')
    def request_pickup(self, request, q):
        orders = list(q.exclude(awb=''))
        missing = q.filter(awb='').count()
        if not orders:
            self.message_user(request, 'Create the Delhivery shipment (waybill) for these orders first.', messages.WARNING); return None
        tomorrow = (timezone.localtime() + timedelta(days=1)).date()
        form = PickupForm(request.POST if 'apply' in request.POST else None, initial={'date': tomorrow, 'time': '11:00'})
        if 'apply' in request.POST and form.is_valid():
            when = timezone.make_aware(timezone.datetime.combine(form.cleaned_data['date'], form.cleaned_data['time']))
            if when < timezone.now():
                self.message_user(request, 'Choose a pickup time in the future.', messages.ERROR); return None
            try:
                body = delhivery.request_pickup(len(orders), when)
            except delhivery.DelhiveryError as e:
                self.message_user(request, str(e), messages.ERROR); return None
            p = PickupRequest.objects.create(pickup_at=when, package_count=len(orders), response=body if isinstance(body, dict) else {'response': str(body)}, created_by=request.user)
            p.orders.set(orders)
            Order.objects.filter(pk__in=[o.pk for o in orders]).update(pickup_requested_at=timezone.now())
            self.message_user(request, f'Pickup requested for {len(orders)} parcel(s) on {when:%d %b %Y at %H:%M}. Customers can no longer cancel these orders.', messages.SUCCESS)
            return None
        return TemplateResponse(request, 'admin/shop/pickup_form.html', {**self.admin_site.each_context(request), 'title': 'Request Delhivery pickup',
                                'orders': orders, 'missing': missing, 'form': form, 'opts': self.model._meta, 'action': 'request_pickup',
                                'selected': request.POST.getlist(admin.helpers.ACTION_CHECKBOX_NAME)})


@admin.register(PickupRequest)
class PickupRequestAdmin(admin.ModelAdmin):
    list_display = ['pickup_at', 'package_count', 'orders_list', 'created_by', 'created_at']
    readonly_fields = ['pickup_at', 'package_count', 'orders', 'response', 'created_by', 'created_at']
    def has_add_permission(self, request): return False
    @admin.display(description='Orders')
    def orders_list(self, p): return ', '.join(ref(o) for o in p.orders.all()[:6])


# ---------- Returns & refunds ----------
@admin.register(ReturnOrder)
class ReturnOrderAdmin(OrderAdmin):
    """Every return request: approve (books the Delhivery reverse pickup), mark received when the parcel
    is back, then refund the customer."""
    list_display = ['ref', 'customer', 'phone', 'delivered_at', 'return_reason', 'return_status', 'return_awb', 'return_courier_status', 'payment', 'total', 'refund']
    list_filter = ['return_status', 'payment_method', 'status']
    actions = ['return_approve', 'mark_return_received', 'refund_customer', 'mark_refunded_manually', 'return_reject']
    date_hierarchy = None
    def get_queryset(self, request): return super().get_queryset(request).exclude(return_status='')
    def has_add_permission(self, request): return False
    @admin.display(description='Refund')
    def refund(self, o): return {'refunded': 'Refunded', 'refund_required': 'Refund due (manual)'}.get(o.status, '—')

    @admin.action(description='Mark return received (parcel is back with us)')
    def mark_return_received(self, request, q):
        n = q.exclude(return_status__in=['received', 'rejected']).update(return_status='received')
        self.message_user(request, f'{n} return(s) marked as received. Now refund the customer.', messages.SUCCESS)

    @admin.action(description='Refund customer (Cashfree for online payments)')
    def refund_customer(self, request, q):
        from .services import refund_order
        done = manual = 0
        for o in q.filter(return_status='received').exclude(status='refunded'):
            o.status = refund_order(o, 'Return received'); o.save(update_fields=['status'])
            done += o.status == 'refunded'; manual += o.status == 'refund_required'
        if not done and not manual:
            self.message_user(request, 'Only returns marked “received” and not refunded yet can be refunded.', messages.WARNING)
        if done: self.message_user(request, f'{done} refund(s) started through Cashfree.', messages.SUCCESS)
        if manual: self.message_user(request, f'{manual} order(s) need a manual refund (COD or Cashfree unavailable). Pay the customer, then use “Mark refunded manually”.', messages.WARNING)

    @admin.action(description='Mark refunded manually (COD / bank transfer done)')
    def mark_refunded_manually(self, request, q):
        n = q.filter(status='refund_required').update(status='refunded')
        self.message_user(request, f'{n} order(s) marked as refunded.', messages.SUCCESS)
