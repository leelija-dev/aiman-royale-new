from celery import shared_task
from django.utils import timezone
from .models import Order
from .services import release_order
@shared_task
def expire_orders():
    for pk in Order.objects.filter(status='pending',expires_at__lt=timezone.now()).values_list('pk',flat=True):release_order(pk)

@shared_task
def sync_shipments():
    """Refresh Delhivery tracking for orders that are on their way."""
    from . import delhivery
    if not delhivery.configured():return
    for order in Order.objects.exclude(awb='').filter(status__in=['processing','shipped']).exclude(courier_status='Cancelled')[:200]:
        try:delhivery.track(order)
        except delhivery.DelhiveryError:continue
