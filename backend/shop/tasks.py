from celery import shared_task
from django.utils import timezone
from .models import Order
from .services import release_order
@shared_task
def expire_orders():
    for pk in Order.objects.filter(status='pending',expires_at__lt=timezone.now()).values_list('pk',flat=True):release_order(pk)
