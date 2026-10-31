from pathlib import Path
from datetime import timedelta, datetime, time
from django.core.management.base import BaseCommand
from django.core.files import File
from django.conf import settings
from django.utils import timezone
from shop.models import Collection, Product, ProductImage, Variant, SiteSettings, AppointmentSlot, Page

class Command(BaseCommand):
    help='Load an editable demonstration catalogue and optional appointment slots. Never imports live inventory.'
    def add_arguments(self,parser):parser.add_argument('--demo-slots',action='store_true')
    def handle(self,*args,**options):
        SiteSettings.current()
        root=Path(settings.BASE_DIR)/'seed-assets'
        cols={}
        for name,slug in [('Salwar Kameez','salwar-kameez'),('Lehengas','lehengas'),('Palazzo Sets','palazzo-sets'),('Indo-western','indo-western'),('Co-ords','co-ords'),('Bridal','bridal'),('Wedding','wedding'),('Gown','gown'),('Anarkali Suits','anarkali-suits'),('Kurta Sets','kurta-sets'),('Palazzo Suits','palazzo-suits'),('Sharara Suits','sharara-suits'),('Patiala Suits','patiala-suits'),('Jump Suits','jump-suits'),('Kaftan','kaftan'),('Co-ord Sets','co-ord-sets'),('Crop Top Styles','crop-top-styles')]:
            cols[slug],_=Collection.objects.get_or_create(slug=slug,defaults={'name':name,'description':f'Discover {name.lower()} made for your unforgettable moments.'})
        catalogue=[('Rani Paplom Suit with Skirt','rani-paplom-suit-with-skirt','rani','Rani pink','salwar-kameez',4999,7999,['Wedding','Party']),('Maroon Embroidered Palazzo Set','maroon-palazzo-set','maroon','Maroon','palazzo-sets',5499,8499,['Wedding','Festive']),('Wine Festive Suit','wine-festive-suit','wine','Wine','salwar-kameez',4299,6499,['Party','Festive']),('Purple Celebration Set','purple-celebration-set','purple','Purple','indo-western',4699,6999,['Party']),('Midnight Blue Palazzo Set','midnight-blue-palazzo','navy','Navy','palazzo-sets',5999,8999,['Wedding']),('Rose Embroidered Co-ord','rose-embroidered-coord','pink','Pink','co-ords',3999,5999,['Party','Festive']),('Celebration Gharara Set','celebration-gharara','gharara','Red','bridal',6999,9999,['Wedding']),('Mehendi Green Suit','mehendi-green-suit','green','Green','salwar-kameez',4499,6999,['Haldi','Festive'])]
        for name,slug,asset,colour,col,price,mrp,occasions in catalogue:
            p,created=Product.objects.get_or_create(slug=slug,defaults={'name':name,'price':price,'mrp':mrp,'description':'An expressive celebration silhouette with ornate detailing. Style it your way, with a personal fitting consultation available. Demonstration catalogue: confirm fabric, inclusions and price before publishing.','fabric':'Confirm fabric with the studio','care':'Professional dry clean recommended. Store away from direct sunlight.','occasions':occasions,'featured':True})
            if created:
                p.collections.add(cols[col])
                for size in ['XS','S','M','L','XL','XXL']:Variant.objects.create(product=p,sku=f'AR-{asset.upper()}-{size}',size=size,colour=colour,stock=5)
                image=root/f'{asset}.webp'
                if image.exists():
                    with image.open('rb') as f:
                        pi=ProductImage(product=p,alt=name);pi.image.save(image.name,File(f),save=True)
        for slug,title in [('privacy','Privacy Policy'),('terms','Terms & Conditions'),('shipping','Shipping & Delivery'),('returns','Returns & Exchanges'),('size-guide','Size & Fit Guide')]:Page.objects.get_or_create(slug=slug,defaults={'title':title,'body':'Replace this draft with your approved store policy before launch.','published':False})
        if options['demo_slots']:
            for day in range(1,15):
                d=timezone.localdate()+timedelta(days=day)
                for hour in [11,12,14,15,16]:AppointmentSlot.objects.get_or_create(starts_at=timezone.make_aware(datetime.combine(d,time(hour))))
        self.stdout.write(self.style.SUCCESS('Demo catalogue loaded. Review prices, product descriptions, stock and policies in admin before launch.'))
