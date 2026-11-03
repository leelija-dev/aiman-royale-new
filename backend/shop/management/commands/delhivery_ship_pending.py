from django.core.management.base import BaseCommand
from shop import delhivery
from shop.models import Order
from shop.services import ship_now


class Command(BaseCommand):
    help = 'Create Delhivery shipments (AWB) for paid / COD orders that do not have one yet.'

    def handle(self, *args, **opts):
        if not delhivery.configured():
            self.stderr.write('DELHIVERY_API_TOKEN is not set in backend/.env.')
            return
        for o in Order.objects.filter(awb='', status__in=['paid', 'cod', 'processing']):
            awb = ship_now(o.pk)
            o.refresh_from_db()
            self.stdout.write(f'{str(o.id)[:8].upper()}: ' + (f'AWB {awb}' if awb else o.courier_status or 'not booked'))
