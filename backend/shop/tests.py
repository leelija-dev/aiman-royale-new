import uuid,json,hmac,hashlib,base64
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
from django.test import TestCase,override_settings
from django.core.cache import cache
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from rest_framework.test import APIClient
from rest_framework.exceptions import ValidationError
from .models import Customer,Product,Variant,Cart,CartItem,Order,AppointmentSlot,OTPChallenge,SiteSettings
from .services import reserve_order,release_order,settle_payment,ProviderUnavailable

@override_settings(SECURE_SSL_REDIRECT=False,ALLOWED_HOSTS=['testserver'],EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class CommerceTests(TestCase):
    def setUp(self):
        cache.clear();self.u=Customer.objects.create_user(username='test@example.com',email='test@example.com',password='Test-Password-910!')
        self.p=Product.objects.create(name='Test Suit',slug='test-suit',price='2000',mrp='3000')
        self.v=Variant.objects.create(product=self.p,sku='TEST-M',size='M',colour='Pink',stock=3)
        self.cart=Cart.objects.create(user=self.u);CartItem.objects.create(cart=self.cart,variant=self.v,quantity=2)
        self.client=APIClient();self.client.force_login(self.u)
        self.address={'name':'Test Customer','phone':'+919000000001','email':'test@example.com','line1':'Test address','city':'Kolkata','state':'West Bengal','pincode':'700001','country':'IN'}
    def reserve(self):return reserve_order(self.u,self.cart,self.address,uuid.uuid4())[0]
    def payment(self,o):return {'id':'pay_test','order_id':o.gateway_order_id,'currency':'INR','amount':400000,'status':'captured'}
    def test_server_price_stock_and_idempotency(self):
        key=uuid.uuid4();o,created=reserve_order(self.u,self.cart,self.address,key)
        self.assertTrue(created);self.assertEqual(o.total,Decimal('4000'));self.v.refresh_from_db();self.assertEqual(self.v.stock,1)
        again,created=reserve_order(self.u,self.cart,self.address,key);self.assertFalse(created);self.assertEqual(again.pk,o.pk);self.assertEqual(Order.objects.count(),1)
    def test_insufficient_stock_rolls_back(self):
        self.v.stock=1;self.v.save()
        with self.assertRaises(ValidationError):self.reserve()
        self.assertEqual(Order.objects.count(),0);self.assertEqual(self.cart.items.count(),1)
    def test_expiry_releases_once(self):
        o=self.reserve();release_order(o.pk);release_order(o.pk);self.v.refresh_from_db();self.assertEqual(self.v.stock,3)
    def test_captured_payment_is_idempotent(self):
        o=self.reserve();o.gateway_order_id='order_test';o.save();payment=self.payment(o)
        self.assertEqual(settle_payment(payment).status,'paid');self.assertEqual(settle_payment(payment).status,'paid')
        release_order(o.pk);self.v.refresh_from_db();self.assertEqual(self.v.stock,1)
    def test_amount_mismatch_never_marks_paid(self):
        o=self.reserve();o.gateway_order_id='order_test';o.save();payment=self.payment(o);payment['amount']=1
        with self.assertRaises(ValidationError):settle_payment(payment)
        o.refresh_from_db();self.assertEqual(o.status,'pending')
    def test_late_payment_requires_reconciliation(self):
        o=self.reserve();o.gateway_order_id='order_test';o.save();release_order(o.pk)
        self.assertEqual(settle_payment(self.payment(o)).status,'refund_required');self.v.refresh_from_db();self.assertEqual(self.v.stock,3)
    @override_settings(CASHFREE_APP_ID='',CASHFREE_SECRET_KEY='')
    def test_unconfigured_payment_preserves_bag(self):
        r=self.client.post('/api/checkout/',{'key':str(uuid.uuid4()),'address':self.address,'consent':True},format='json')
        self.assertEqual(r.status_code,503);self.assertEqual(self.cart.items.count(),1);self.assertEqual(Order.objects.count(),0)
    def test_user_cannot_read_other_orders(self):
        self.reserve();other=Customer.objects.create_user(username='other',password='Strong-Password90!');self.client.force_login(other)
        self.assertEqual(self.client.get('/api/orders/').json(),[])
    def test_guest_mutations_require_csrf(self):
        client=APIClient(enforce_csrf_checks=True)
        r=client.post('/api/cart/',{'variant':self.v.pk},format='json');self.assertEqual(r.status_code,403)
        token=client.get('/api/csrf/').json()['csrfToken'];r=client.post('/api/cart/',{'variant':self.v.pk},format='json',HTTP_X_CSRFTOKEN=token);self.assertEqual(r.status_code,200)
    def test_authenticated_cart_csrf(self):
        client=APIClient(enforce_csrf_checks=True);client.force_login(self.u)
        self.assertEqual(client.delete('/api/cart/',{'id':self.cart.items.first().pk},format='json').status_code,403)
    def test_appointment_slot_cannot_be_double_booked(self):
        slot=AppointmentSlot.objects.create(starts_at=timezone.now()+timedelta(days=1))
        data={'slot':slot.pk,'name':'Test Customer','phone':'+919000000001','session_type':'fitting','mode':'studio','consent':True}
        self.assertEqual(self.client.post('/api/appointments/',data,format='json').status_code,201)
        self.assertEqual(self.client.post('/api/appointments/',data,format='json').status_code,400)
        self.assertEqual(self.client.get('/api/appointments/slots/').json(),[])
    def test_otp_wrong_attempts_are_persisted(self):
        c=OTPChallenge.objects.create(phone='+919000000001',code_hash=make_password('123456'),expires_at=timezone.now()+timedelta(minutes=5))
        for _ in range(5):self.assertEqual(self.client.post('/api/auth/otp/verify/',{'challenge':str(c.pk),'code':'000000'},format='json').status_code,400)
        c.refresh_from_db();self.assertEqual(c.attempts,5);self.assertTrue(c.used)
        self.assertEqual(self.client.post('/api/auth/otp/verify/',{'challenge':str(c.pk),'code':'123456'},format='json').status_code,400)
    @override_settings(CASHFREE_SECRET_KEY='test-hook-secret')
    @patch('shop.services.gateway')
    def test_signed_webhook_and_replay(self,gateway):
        o=self.reserve();o.gateway_order_id='order_test';o.save()
        gateway.side_effect=lambda method,path: ({'order_id':'order_test','order_currency':'INR','order_amount':4000,'order_status':'PAID'} if not path.endswith('/payments') else [{'order_id':'order_test','payment_currency':'INR','payment_amount':4000,'payment_status':'SUCCESS','cf_payment_id':'123'}])
        data=json.dumps({'type':'PAYMENT_SUCCESS_WEBHOOK','data':{'order':{'order_id':'order_test'},'payment':{'payment_status':'SUCCESS'}}})
        self.assertEqual(self.client.post('/api/payments/webhook/',data,content_type='application/json').status_code,400)
        timestamp='1700000000000'
        signature=base64.b64encode(hmac.new(b'test-hook-secret',(timestamp+data).encode(),hashlib.sha256).digest()).decode()
        for _ in range(2):self.assertEqual(self.client.post('/api/payments/webhook/',data,content_type='application/json',HTTP_X_WEBHOOK_SIGNATURE=signature,HTTP_X_WEBHOOK_TIMESTAMP=timestamp).status_code,200)
        o.refresh_from_db();self.assertEqual(o.status,'paid');self.assertEqual(o.gateway_payment_id,'123')
        self.assertEqual(self.client.post('/api/payments/webhook/',data+' ',content_type='application/json',HTTP_X_WEBHOOK_SIGNATURE=signature,HTTP_X_WEBHOOK_TIMESTAMP=timestamp).status_code,400)
    def test_password_reset_form_renders(self):self.assertEqual(self.client.get('/accounts/password_reset/').status_code,200)
    def test_published_policy_only(self):self.assertEqual(self.client.get('/api/pages/privacy/').status_code,404)
    def test_invalid_quantity_rejected(self):
        self.assertEqual(self.client.post('/api/cart/',{'variant':self.v.pk,'quantity':0},format='json').status_code,400)
    def test_registration_merges_guest_bag(self):
        guest=APIClient()
        self.assertEqual(guest.post('/api/cart/',{'variant':self.v.pk,'quantity':1},format='json').status_code,200)
        r=guest.post('/api/auth/register/',{'email':'new@example.com','name':'New Customer','password':'Another-Strong-Password91!','consent':True},format='json')
        self.assertEqual(r.status_code,201)
        bag=guest.get('/api/cart/').json();self.assertEqual(len(bag['items']),1);self.assertEqual(bag['items'][0]['quantity'],1)
    @override_settings(CASHFREE_APP_ID='rzp_test_example',CASHFREE_SECRET_KEY='test-secret')
    @patch('shop.services.gateway')
    def test_checkout_ignores_client_total_and_reuses_provider_order(self,gateway):
        gateway.side_effect=lambda method,path,payload,idempotency_key: {'order_id':payload['order_id'],'payment_session_id':'session_test'}
        data={'key':str(uuid.uuid4()),'address':self.address,'consent':True,'total':'1.00','method':'cashfree'}
        first=self.client.post('/api/checkout/',data,format='json');self.assertEqual(first.status_code,200)
        self.assertEqual(first.json()['amount'],400000)
        again=self.client.post('/api/checkout/',data,format='json');self.assertEqual(again.status_code,200)
        self.assertEqual(first.json()['order']['id'],again.json()['order']['id']);gateway.assert_called_once()
    @override_settings(CASHFREE_APP_ID='test_app',CASHFREE_SECRET_KEY='test-secret')
    @patch('shop.services.gateway')
    def test_checkout_saves_note_and_opens_chosen_payment_option(self,gateway):
        gateway.side_effect=lambda method,path,payload,idempotency_key: {'order_id':payload['order_id'],'payment_session_id':'session_test'}
        data={'key':str(uuid.uuid4()),'address':self.address,'consent':True,'method':'cashfree','pay_with':'upi','note':'Gift wrap please'}
        r=self.client.post('/api/checkout/',data,format='json');self.assertEqual(r.status_code,200)
        self.assertEqual(r.json()['order']['note'],'Gift wrap please')
        self.assertEqual(gateway.call_args[0][2]['order_meta']['payment_methods'],'upi')
        bad=self.client.post('/api/checkout/',{**data,'key':str(uuid.uuid4()),'pay_with':'bitcoin'},format='json');self.assertEqual(bad.status_code,400)
    def test_guest_can_preview_bag_total_with_coupon(self):
        from shop.models import Coupon
        Coupon.objects.create(code='FEST10',percent=10)
        guest=APIClient();guest.post('/api/cart/',{'variant':self.v.id,'quantity':1},format='json')
        r=guest.post('/api/quote/',{'coupon':'fest10'},format='json')
        self.assertEqual(r.status_code,200);self.assertEqual(Decimal(r.json()['discount']),Decimal('200'))
    def test_reviews_need_sign_in_and_approval(self):
        from shop.models import Review
        guest=APIClient()
        self.assertEqual(guest.post('/api/products/test-suit/reviews/',{'rating':5,'text':'Beautiful work'},format='json').status_code,401)
        r=self.client.post('/api/products/test-suit/reviews/',{'rating':5,'text':'Beautiful work and fit'},format='json');self.assertEqual(r.status_code,201)
        self.assertEqual(guest.get('/api/products/test-suit/reviews/').json()['count'],0)
        Review.objects.update(approved=True)
        d=guest.get('/api/products/test-suit/reviews/').json();self.assertEqual(d['count'],1);self.assertEqual(d['average'],5.0)
    def test_password_reset_sends_valid_account_email(self):
        from django.core import mail
        r=self.client.post('/accounts/password_reset/',{'email':'test@example.com'})
        self.assertEqual(r.status_code,302);self.assertEqual(len(mail.outbox),1);self.assertIn('/accounts/reset/',mail.outbox[0].body)
    @override_settings(WHATSAPP_TOKEN='',WHATSAPP_PHONE_ID='',WHATSAPP_OTP_TEMPLATE='',WHATSAPP_GRAPH_VERSION='')
    def test_unconfigured_whatsapp_fails_closed(self):
        r=self.client.post('/api/auth/otp/send/',{'phone':'+919000000001','purpose':'register','consent':True},format='json')
        self.assertEqual(r.status_code,503);self.assertTrue(OTPChallenge.objects.get(phone='+919000000001').used)

    @patch('shop.services.gateway')
    def test_browser_cannot_claim_cashfree_success(self,gateway):
        o=self.reserve();o.gateway_order_id='order_test';o.save()
        gateway.return_value={'order_id':'order_test','order_currency':'INR','order_amount':4000,'order_status':'ACTIVE'}
        result=self.client.post('/api/payments/verify/',{'order':str(o.pk),'status':'SUCCESS'},format='json')
        self.assertEqual(result.status_code,200);self.assertEqual(result.json()['status'],'pending')
    @patch('shop.services.gateway')
    def test_cashfree_mismatched_amount_rejected(self,gateway):
        o=self.reserve();o.gateway_order_id='order_test';o.save()
        gateway.return_value={'order_id':'order_test','order_currency':'INR','order_amount':1,'order_status':'PAID'}
        self.assertEqual(self.client.post('/api/payments/verify/',{'order':str(o.pk)},format='json').status_code,400)
        o.refresh_from_db();self.assertEqual(o.status,'pending')
    @override_settings(CASHFREE_APP_ID='test',CASHFREE_SECRET_KEY='test')
    @patch('shop.services.gateway')
    def test_cashfree_timeout_reuses_same_provider_id_and_key(self,gateway):
        from .services import cashfree_session
        o=self.reserve();gateway.side_effect=ProviderUnavailable('timeout')
        with self.assertRaises(ProviderUnavailable):cashfree_session(o)
        first=gateway.call_args
        o.refresh_from_db();self.assertEqual(o.gateway_order_id,'ar_'+o.id.hex)
        gateway.side_effect=None;gateway.return_value={'order_id':o.gateway_order_id,'payment_session_id':'session_recovered'}
        self.assertEqual(cashfree_session(o),'session_recovered');self.assertEqual(first,gateway.call_args)
        self.v.refresh_from_db();self.assertEqual(self.v.stock,1)
    @patch('shop.services.gateway')
    def test_other_customer_cannot_verify_order(self,gateway):
        o=self.reserve();other=Customer.objects.create_user(username='another')
        self.client.force_login(other)
        self.assertEqual(self.client.post('/api/payments/verify/',{'order':str(o.pk)},format='json').status_code,404);gateway.assert_not_called()


class MultiValueFilterTests(TestCase):
    def test_occasion_and_colour_accept_several_values(self):
        from shop.models import Product, Variant
        from shop.models import Occasion
        occ={n:Occasion.objects.get_or_create(name=n,defaults={'slug':n.lower()})[0] for n in ['Haldi','Party','Festive']}
        a=Product.objects.create(name='A',slug='a',price=1000,mrp=2000);a.occasions.add(occ['Haldi'])
        b=Product.objects.create(name='B',slug='b',price=1000,mrp=2000);b.occasions.add(occ['Party'])
        c=Product.objects.create(name='C',slug='c',price=1000,mrp=2000);c.occasions.add(occ['Festive'])
        Variant.objects.create(product=a,sku='A-M',size='M',colour='Maroon',stock=2)
        Variant.objects.create(product=b,sku='B-S',size='S',colour='Wine',stock=2)
        r=self.client.get('/api/products/?occasion=Haldi&occasion=Party')
        self.assertEqual({x['slug'] for x in r.json()['results']},{'a','b'})
        r=self.client.get('/api/products/?colour=maroon&colour=wine&size=M&size=S')
        self.assertEqual({x['slug'] for x in r.json()['results']},{'a','b'})

    def test_facets_and_menu_come_from_the_database(self):
        from shop.models import Occasion, Colour, MenuItem, MenuLink, Collection, Product, Variant
        col=Collection.objects.create(name='Gown',slug='gown-test')
        party=Occasion.objects.get_or_create(name='Party',defaults={'slug':'party'})[0]
        Occasion.objects.create(name='Mehendi',slug='mehendi',sort_order=1)
        p=Product.objects.create(name='G',slug='g',price=1500,mrp=3000);p.collections.add(col);p.occasions.add(party)
        Variant.objects.create(product=p,sku='G-L',size='L',colour='teal',stock=1)
        Variant.objects.create(product=p,sku='G-S',size='S',colour='Teal',stock=1)
        Colour.objects.create(name='Teal',hex='#008080')
        f=self.client.get('/api/facets/?collection=gown-test').json()
        counts={o['name']:o['count'] for o in f['occasions']}
        self.assertEqual([o['name'] for o in f['occasions']][:2],['Haldi','Mehendi'])
        self.assertEqual(counts['Party'],1);self.assertEqual(counts['Mehendi'],0)
        self.assertEqual(f['sizes'],['S','L'])
        self.assertEqual(f['colours'],[{'name':'Teal','hex':'#008080','count':1}])
        self.assertEqual(float(f['price']['min']),1500.0)
        MenuItem.objects.all().delete()
        m=MenuItem.objects.create(label='Gown',url='/collections/gown-test')
        MenuLink.objects.create(item=m,group='Style',label='Party Gowns',url='/x')
        menu=self.client.get('/api/site/').json()['menu']
        self.assertEqual(menu[0]['label'],'Gown')
        self.assertEqual([c['title'] for c in menu[0]['columns']],['Style','Occasion'])
        self.assertIn({'label':'Mehendi','href':'/collections/gown-test?occasion=mehendi'},menu[0]['columns'][1]['links'])


class CategoryContentTests(TestCase):
    def test_defaults_then_collection_overrides(self):
        from shop.models import Collection, PageQuestion, SiteSettings
        c=Collection.objects.create(name='Gown',slug='gown-x')
        d=self.client.get('/api/collections/gown-x/').json()['content']
        self.assertEqual(d['eyebrow'],'The Gown Edit')
        self.assertEqual(d['seo_heading'],'Buy Embroidered Gown for Women Online')
        self.assertEqual(len(d['faqs']),3);self.assertIn('Gown',d['faqs'][0]['answer'])
        self.assertEqual(d['fitting']['steps'],['Choose a date.','Meet our team.','Find your fit.'])
        c.hero_tagline='Made for evenings';c.seo_heading='Designer {name}s';c.save()
        PageQuestion.objects.create(collection=c,kind='faq',question='Is lining included?',answer='Yes.')
        s=SiteSettings.current();s.fitting_button='Book Now';s.save()
        d=self.client.get('/api/collections/gown-x/').json()['content']
        self.assertEqual(d['tagline'],'Made for evenings');self.assertEqual(d['seo_heading'],'Designer Gowns')
        self.assertEqual(d['faqs'],[{'question':'Is lining included?','answer':'Yes.'}])
        self.assertEqual(len(d['guides']),3)
        self.assertEqual(d['fitting']['button'],'Book Now')


class HomepageTests(TestCase):
    def test_sections_follow_admin_order_and_visibility(self):
        from shop.models import HomeSection, HomeCard
        d=self.client.get('/api/home/').json()['sections']
        self.assertEqual(d[0]['kind'],'hero');self.assertEqual(len(d),15)
        hero=HomeSection.objects.get(kind='hero');hero.sort_order=999;hero.save()
        HomeSection.objects.filter(kind='story').update(active=False)
        card=HomeCard.objects.filter(section__kind='consult').first();card.title='Custom title';card.save()
        d=self.client.get('/api/home/').json()['sections']
        self.assertEqual(d[-1]['kind'],'hero');self.assertNotIn('story',[x['kind'] for x in d])
        consult=[x for x in d if x['kind']=='consult'][0]
        self.assertEqual(consult['cards'][0]['title'],'Custom title');self.assertEqual(consult['cards'][0]['button'],'Book an Appointment')


class AllProductsPageTests(TestCase):
    def test_category_and_price_range_filters(self):
        from shop.models import Collection, Product
        a=Collection.objects.create(name='Anarkali',slug='anarkali-t');b=Collection.objects.create(name='Lehenga',slug='lehenga-t')
        p1=Product.objects.create(name='P1',slug='p1',price=4000,mrp=5000);p1.collections.add(a)
        p2=Product.objects.create(name='P2',slug='p2',price=9000,mrp=12000);p2.collections.add(b)
        p3=Product.objects.create(name='P3',slug='p3',price=12000,mrp=15000);p3.collections.add(b)
        slugs=lambda u:{x['slug'] for x in self.client.get(u).json()['results']}
        self.assertEqual(slugs('/api/products/?collection=anarkali-t&collection=lehenga-t'),{'p1','p2','p3'})
        self.assertEqual(slugs('/api/products/?price=-5000&price=8000-10000'),{'p1','p2'})
        f=self.client.get('/api/facets/').json()
        self.assertEqual({c['slug']:c['count'] for c in f['collections']},{'lehenga-t':2,'anarkali-t':1})
        self.assertEqual([(r['value'],r['count']) for r in f['price_ranges']],[('-5000',1),('8000-10000',1),('10000-15000',1)])
        self.assertEqual(f['price_ranges'][0]['label'],'Below ₹5,000')
        site=self.client.get('/api/site/').json()['shop_page']
        self.assertEqual(site['heading'],'All Products');self.assertEqual(len(site['trust']),3)


class SizeGuideTests(TestCase):
    def test_size_guide_comes_from_admin_tables(self):
        from shop.models import SizeChartRow
        d=self.client.get('/api/size-guide/').json()
        self.assertEqual([r['size'] for r in d['rows']],['XS','S','M','L','XL','XXL','3XL'])
        self.assertEqual(d['rows'][0],{'size':'XS','alt':'34','bust':34.0,'waist':28.0,'hip':38.5,'armhole':15.5,'uk':'6'})
        self.assertEqual(len(d['steps']),7);self.assertIn('variations',d['note'])
        SizeChartRow.objects.filter(size='XS').update(bust='33.5')
        self.assertEqual(self.client.get('/api/size-guide/').json()['rows'][0]['bust'],33.5)


class ReportedIssuesTests(TestCase):
    def setUp(self):
        from shop.models import Customer, Product, Variant, Collection
        self.u=Customer.objects.create_user(username='p@example.com',email='p@example.com',password='Old-Password-2026!',first_name='Priya')
        self.c=APIClient();self.c.force_login(self.u)
        self.parent=Collection.objects.create(name='Suits',slug='suits-t');self.child=Collection.objects.create(name='Anarkali T',slug='anarkali-t',parent=self.parent)
        self.p=Product.objects.create(name='P',slug='p-t',price=1000,mrp=1500);self.p.collections.add(self.parent,self.child)
        self.v=Variant.objects.create(product=self.p,sku='PT-M',size='M',colour='Red',stock=25)
    def test_no_ten_unit_limit_only_stock(self):
        self.assertEqual(self.c.post('/api/cart/',{'variant':self.v.id,'quantity':15},format='json').status_code,200)
        r=self.c.post('/api/cart/',{'variant':self.v.id,'quantity':11},format='json');self.assertEqual(r.status_code,400);self.assertIn('Only 25 left',str(r.json()))
    def test_profile_edit_and_password_change(self):
        r=self.c.patch('/api/auth/me/',{'first_name':'Priya','last_name':'Sen','phone':'+919812345678','marketing_opt_in':True},format='json')
        self.assertEqual(r.json()['user']['name'],'Priya Sen');self.assertEqual(r.json()['user']['phone'],'+919812345678')
        self.assertEqual(self.c.patch('/api/auth/me/',{'phone':'12'},format='json').status_code,400)
        self.assertEqual(self.c.post('/api/auth/password/',{'current':'wrong','new':'New-Password-2026!'},format='json').status_code,400)
        self.assertEqual(self.c.post('/api/auth/password/',{'current':'Old-Password-2026!','new':'New-Password-2026!'},format='json').status_code,200)
        self.u.refresh_from_db();self.assertTrue(self.u.check_password('New-Password-2026!'))
        self.assertEqual(self.c.get('/api/auth/me/').json()['user']['email'],'p@example.com')
    def test_coupon_list_shows_saving_for_bag(self):
        from shop.models import Coupon
        Coupon.objects.create(code='TEN',percent=10,description='Festive');Coupon.objects.create(code='BIG',percent=20,minimum=5000);Coupon.objects.create(code='HIDDEN',percent=50,public=False)
        self.c.post('/api/cart/',{'variant':self.v.id,'quantity':2},format='json')
        d={x['code']:x for x in self.c.get('/api/coupons/').json()}
        self.assertNotIn('HIDDEN',d);self.assertTrue(d['TEN']['eligible']);self.assertEqual(float(d['TEN']['saving']),200.0)
        self.assertFalse(d['BIG']['eligible']);self.assertEqual(float(d['BIG']['short_by']),3000.0)
    def test_menu_style_tab_lists_sub_collections_with_products(self):
        from shop.models import MenuItem
        MenuItem.objects.all().delete();MenuItem.objects.create(label='Suits',url='/collections/suits-t')
        menu=self.c.get('/api/site/').json()['menu']
        style=[c for c in menu[0]['columns'] if c['title']=='Style'][0]['links']
        self.assertEqual(style[0]['label'],'Anarkali T');self.assertEqual(style[0]['count'],1)
    def test_order_history_has_image_and_address(self):
        from shop.services import reserve_order
        from shop.models import Cart, CartItem
        cart=Cart.objects.create(user=self.u);CartItem.objects.create(cart=cart,variant=self.v,quantity=1)
        reserve_order(self.u,cart,{'name':'Priya','phone':'+919812345678','email':'p@example.com','line1':'1 Road','city':'Kolkata','state':'WB','pincode':'700001','country':'IN'},uuid.uuid4(),'','cod')
        o=self.c.get('/api/orders/').json()[0];self.assertEqual(o['address']['city'],'Kolkata');self.assertEqual(o['items'][0]['slug'],'p-t')
    @override_settings()
    def test_cashfree_test_key_names_are_accepted(self):
        import os,importlib
        from unittest import mock
        with mock.patch.dict(os.environ,{'CASHFREE_ENVIRONMENT':'sandbox','CASHFREE_TEST_APP_ID':'"TESTabc"','CASHFREE_TEST_SECRET_KEY':'cfsk_x'},clear=False):
            os.environ.pop('CASHFREE_APP_ID',None);os.environ.pop('CASHFREE_SECRET_KEY',None)
            import config.settings as st;importlib.reload(st)
            self.assertEqual(st.CASHFREE_APP_ID,'TESTabc');self.assertEqual(st.CASHFREE_SECRET_KEY,'cfsk_x')
        importlib.reload(st)


class EnvFileTests(TestCase):
    def test_env_file_values_are_loaded_without_overriding_real_environment(self):
        import os, tempfile
        from config.settings import _load_env_files
        with tempfile.TemporaryDirectory() as d:
            path=os.path.join(d,'.env')
            with open(path,'w') as f:f.write('# comment\nAR_TEST_ID="TESTfake123"\nexport AR_TEST_SECRET=cfsk_fake\nAR_TEST_MODE=sandbox # note\nAR_TEST_KEEP=from-file\n')
            os.environ['AR_TEST_KEEP']='from-environment'
            try:
                _load_env_files(path)
                self.assertEqual(os.environ['AR_TEST_ID'],'TESTfake123')
                self.assertEqual(os.environ['AR_TEST_SECRET'],'cfsk_fake')
                self.assertEqual(os.environ['AR_TEST_MODE'],'sandbox')
                self.assertEqual(os.environ['AR_TEST_KEEP'],'from-environment')
            finally:
                for k in ['AR_TEST_ID','AR_TEST_SECRET','AR_TEST_MODE','AR_TEST_KEEP']:os.environ.pop(k,None)


class CategoryDetailsTests(TestCase):
    LONG='Delicately crafted with precision, these suits combine comfort and grace for every celebration. '*4
    def page(self,block):
        return f'''<html><head><script>var x=1</script></head><body><header><nav><a href="/collections/wedding">Wedding</a></nav></header>
        <main><div class="grid">{''.join(f'<div class="card"><img src="/a{i}.jpg"><h3>Suit {i}</h3><span>₹11,760</span></div>' for i in range(6))}</div>
        {block}</main><footer><p>Aiman Royale, Kolkata. Contact us any time for help with your order and sizing questions.</p></footer></body></html>'''
    def test_import_teaser_plus_hidden_full_text(self):
        from shop.management.commands.import_live_descriptions import extract
        html=self.page(f'''<div class="seo"><p class="teaser">Shop Salwar Kameez Online What else to ask for...</p><a class="toggle">Read more</a>
          <div class="full hidden"><h1>Shop Salwar Kameez &amp; Suit Online for Women</h1><p>{self.LONG}</p><ul><li>Anarkali</li><li>Palazzo</li></ul></div>
          <button>Show less</button></div>''')
        out=extract(html)
        self.assertIn('<h2>Shop Salwar Kameez &amp; Suit Online for Women</h2>',out)
        self.assertIn('<li>Anarkali</li>',out);self.assertNotIn('Read more',out);self.assertNotIn('Show less',out)
        self.assertNotIn('₹',out);self.assertNotIn('Wedding',out);self.assertNotIn('What else to ask for...',out)
    def test_import_single_clamped_block_with_button(self):
        from shop.management.commands.import_live_descriptions import extract
        out=extract(self.page(f'<section><div class="line-clamp-3"><img src="/banner.jpg" alt="Gown banner"><h2>Gowns</h2><p>{self.LONG}</p><figure><img src="/b.jpg"><figcaption>Photo caption</figcaption></figure></div><button>Read more</button></section>'))
        self.assertNotIn('<img',out);self.assertNotIn('Photo caption',out);self.assertNotIn('banner',out)
        self.assertTrue(out.startswith('<h2>Gowns</h2><p>Delicately'));self.assertNotIn('Read more',out)
    def test_import_fallback_without_toggle(self):
        from shop.management.commands.import_live_descriptions import extract
        out=extract(self.page(f'<article><h2>Bridal</h2><p>{self.LONG}</p><p>Second paragraph about bridal wear and fittings.</p></article>'))
        self.assertIn('Second paragraph',out);self.assertNotIn('Aiman Royale, Kolkata',out)
    def test_cleaner_keeps_formatting_and_strips_unsafe_html(self):
        from shop.richtext import clean_html
        self.assertEqual(clean_html('<h1 style="x">Title</h1><p onclick="evil()">Hi <b>there</b><script>alert(1)</script></p><a href="javascript:x">bad</a>'),'<h2>Title</h2><p>Hi <b>there</b></p><a>bad</a>')
        self.assertEqual(clean_html('First para.\n\nSecond\nline'),'<p>First para.</p><p>Second<br>line</p>')
    def test_details_in_collection_api_and_cleaned_on_save(self):
        from shop.models import Collection
        Collection.objects.create(name='Gown',slug='gown-d',details='<p>Lovely <img src=x onerror=alert(1)>gowns</p>')
        d=self.client.get('/api/collections/gown-d/').json()['content']['details']
        self.assertEqual(d,'<p>Lovely gowns</p>')


class FakeResponse:
    def __init__(self,body,status=200):self.body=body;self.status_code=status
    def json(self):return self.body

DELHIVERY=dict(DELHIVERY_API_TOKEN='test-token',DELHIVERY_MODE='sandbox',DELHIVERY_BASE_URL='https://staging-express.delhivery.com',
               DELHIVERY_PICKUP_LOCATION='Test-Warehouse',DELHIVERY_PICKUP_PINCODE='700125',
               DELHIVERY_PACKING_SLIP_API_URL='https://staging-express.delhivery.com/api/p/packing_slip',DELHIVERY_WEIGHT_GRAMS=500,DELHIVERY_SHIPPING_MODE='Surface')

@override_settings(SECURE_SSL_REDIRECT=False,ALLOWED_HOSTS=['testserver'],**DELHIVERY)
class DelhiveryTests(TestCase):
    def setUp(self):
        cache.clear();self.u=Customer.objects.create_user(username='d@example.com',email='d@example.com',password='Test-Password-910!')
        self.p=Product.objects.create(name='Test Suit',slug='test-suit',price='2000',mrp='3000')
        self.v=Variant.objects.create(product=self.p,sku='TEST-M',size='M',colour='Pink',stock=3)
        cart=Cart.objects.create(user=self.u);CartItem.objects.create(cart=cart,variant=self.v,quantity=1)
        addr={'name':'Test Customer','phone':'+919000000001','email':'d@example.com','line1':'Test address','city':'Kolkata','state':'West Bengal','pincode':'700001','country':'IN'}
        self.o=reserve_order(self.u,cart,addr,uuid.uuid4(),method='cod')[0]
    def test_pincode_api(self):
        body={'delivery_codes':[{'postal_code':{'pin':700001,'pre_paid':'Y','cod':'N','city':'Kolkata','state_code':'WB','remarks':''}}]}
        with patch('shop.delhivery.requests.request',return_value=FakeResponse(body)) as req:
            r=APIClient().get('/api/delivery/pincode/700001/')
        self.assertEqual(r.status_code,200);self.assertTrue(r.data['checked']);self.assertTrue(r.data['serviceable']);self.assertFalse(r.data['cod'])
        self.assertEqual(req.call_args.kwargs['headers']['Authorization'],'Token test-token')
        self.assertEqual(APIClient().get('/api/delivery/pincode/12345/').status_code,400)
    def test_pincode_not_serviceable_and_unconfigured(self):
        with patch('shop.delhivery.requests.request',return_value=FakeResponse({'delivery_codes':[]})):
            self.assertFalse(APIClient().get('/api/delivery/pincode/110001/').data['serviceable'])
        with override_settings(DELHIVERY_API_TOKEN=''):
            r=APIClient().get('/api/delivery/pincode/110002/');self.assertFalse(r.data['checked']);self.assertTrue(r.data['serviceable'])
    def test_create_shipment_and_track(self):
        from . import delhivery
        created={'success':True,'packages':[{'waybill':'1234567890','status':'Success','remarks':[]}]}
        with patch('shop.delhivery.requests.request',return_value=FakeResponse(created)) as req:
            self.assertEqual(delhivery.create_shipment(self.o),'1234567890')
        sent=req.call_args.kwargs['data'].decode()
        self.assertTrue(sent.startswith('format=json&data='));payload=json.loads(sent.split('data=',1)[1])
        self.assertEqual(payload['pickup_location']['name'],'Test-Warehouse');self.assertEqual(payload['shipments'][0]['payment_mode'],'COD')
        self.assertEqual(payload['shipments'][0]['cod_amount'],str(self.o.total));self.assertEqual(payload['shipments'][0]['phone'],'9000000001')
        self.o.refresh_from_db();self.assertEqual(self.o.status,'processing');self.assertIn('1234567890',self.o.tracking_url)
        tracked={'ShipmentData':[{'Shipment':{'Status':{'Status':'Delivered'},'Scans':[{'ScanDetail':{'ScanDateTime':'2026-11-03T10:00:00','Scan':'Manifested','Instructions':'Picked','ScannedLocation':'Kolkata'}},
                 {'ScanDetail':{'ScanDateTime':'2026-11-05T15:00:00','Scan':'Delivered','Instructions':'Delivered to consignee','ScannedLocation':'Kolkata'}}]}}]}
        with patch('shop.delhivery.requests.request',return_value=FakeResponse(tracked)):delhivery.track(self.o)
        self.o.refresh_from_db();self.assertEqual(self.o.status,'delivered');self.assertEqual(self.o.tracking_events[0]['status'],'Delivered')
        c=APIClient();c.force_login(self.u);self.assertEqual(c.get('/api/orders/').data[0]['awb'],'1234567890')
    def test_failed_booking_keeps_order_unshipped(self):
        from . import delhivery
        with patch('shop.delhivery.requests.request',return_value=FakeResponse({'success':False,'packages':[{'status':'Fail','remarks':['Non serviceable pincode']}]})):
            with self.assertRaisesMessage(delhivery.DelhiveryError,'Non serviceable pincode'):delhivery.create_shipment(self.o)
        self.o.refresh_from_db();self.assertEqual(self.o.awb,'');self.assertEqual(self.o.status,'cod')
    def test_bad_token(self):
        from . import delhivery
        with patch('shop.delhivery.requests.request',return_value=FakeResponse({'detail':'no'},401)):
            with self.assertRaisesMessage(delhivery.DelhiveryError,'rejected the API token'):delhivery.pincode('700001')


@override_settings(SECURE_SSL_REDIRECT=False,ALLOWED_HOSTS=['testserver'],STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class ModificationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.u=Customer.objects.create_user(username='c@example.com',email='c@example.com',password='Test-Password-910!')
        self.admin=Customer.objects.create_superuser(username='a@example.com',email='a@example.com',password='Test-Password-910!')
        self.p=Product.objects.create(name='Test Suit',slug='test-suit',price='1000.50',mrp='3000')
        self.v1=Variant.objects.create(product=self.p,sku='T-M',size='M',colour='Pink',stock=5)
        self.v2=Variant.objects.create(product=self.p,sku='T-L',size='L',colour='Pink',stock=5)
        self.addr={'name':'Test Customer','phone':'+919000000001','email':'c@example.com','line1':'Test address','city':'Kolkata','state':'West Bengal','pincode':'700001'}
    def test_admin_and_customer_logins_are_separate(self):
        c=APIClient(enforce_csrf_checks=False)
        c.post('/admin/login/?next=/admin/',{'username':'a@example.com','password':'Test-Password-910!'})
        self.assertIn('admin_sessionid',c.cookies)
        r=c.post('/api/auth/login/',{'email':'c@example.com','password':'Test-Password-910!'},format='json');self.assertEqual(r.status_code,200)
        self.assertEqual(c.get('/api/auth/me/').data['user']['email'],'c@example.com')
        self.assertEqual(c.get('/admin/').status_code,200)  # admin still signed in
        c.post('/api/auth/logout/',{},format='json')
        self.assertEqual(c.get('/admin/').status_code,200)
    def test_buy_now_orders_only_that_item(self):
        cart=Cart.objects.create(user=self.u);a=CartItem.objects.create(cart=cart,variant=self.v1,quantity=1);b=CartItem.objects.create(cart=cart,variant=self.v2,quantity=2)
        c=APIClient();c.force_login(self.u)
        self.assertEqual(Decimal(c.post('/api/quote/',{'items':[b.id]},format='json').data['subtotal']),Decimal('2002.00'))
        o=reserve_order(self.u,cart,self.addr,uuid.uuid4(),method='cod',only=[b.id])[0]
        self.assertEqual(o.subtotal,Decimal('2002.00'));self.assertEqual(list(cart.items.values_list('id',flat=True)),[a.id])
    @override_settings(DELHIVERY_API_TOKEN='t',DELHIVERY_AUTO_SHIP=True,REDIS_URL='')
    def test_cod_order_books_shipment_automatically(self):
        cart=Cart.objects.create(user=self.u);CartItem.objects.create(cart=cart,variant=self.v1,quantity=1)
        with patch('shop.services.start_shipment') as start, self.captureOnCommitCallbacks(execute=True):
            o=reserve_order(self.u,cart,self.addr,uuid.uuid4(),method='cod')[0]
        start.assert_called_once_with(o.pk)
        from .services import ship_now
        with patch('shop.delhivery.create_shipment',return_value='999') as create:
            self.assertEqual(ship_now(o.pk),'999')
        create.assert_called_once()


@override_settings(SECURE_SSL_REDIRECT=False,ALLOWED_HOSTS=['testserver'])
class OrderCareTests(TestCase):
    def setUp(self):
        cache.clear()
        self.u=Customer.objects.create_user(username='o@example.com',email='o@example.com',password='Test-Password-910!')
        self.p=Product.objects.create(name='Rani Suit',slug='rani-suit',price='13419.39',mrp='20000')
        self.v=Variant.objects.create(product=self.p,sku='R-M',size='M',colour='Rani',stock=4)
        cart=Cart.objects.create(user=self.u);CartItem.objects.create(cart=cart,variant=self.v,quantity=1)
        self.addr={'name':'Test Customer','phone':'+919000000001','email':'o@example.com','line1':'Test address','city':'Kolkata','state':'West Bengal','pincode':'700001'}
        self.o=reserve_order(self.u,cart,self.addr,uuid.uuid4(),method='cod')[0]
        self.c=APIClient();self.c.force_login(self.u)
    def test_amounts_are_whole_rupees(self):
        self.assertEqual(self.o.subtotal,Decimal('13419'));self.assertEqual(self.o.total,self.o.total.to_integral_value())
        self.assertEqual(self.o.items.first().unit_price,Decimal('13419'))
    def test_cancel_before_pickup_restocks(self):
        ref=str(self.o.id)[:8]
        self.assertTrue(self.c.get('/api/orders/').data[0]['can_cancel'])
        r=self.c.post(f'/api/orders/{ref}/cancel/',{'reason':'Ordered by mistake'},format='json');self.assertEqual(r.status_code,200)
        self.o.refresh_from_db();self.assertEqual(self.o.status,'cancelled');self.v.refresh_from_db();self.assertEqual(self.v.stock,4)
        self.assertEqual(self.c.post(f'/api/orders/{ref}/cancel/',{},format='json').status_code,400)
    def test_no_cancel_after_pickup_request(self):
        Order.objects.filter(pk=self.o.pk).update(pickup_requested_at=timezone.now())
        self.assertEqual(self.c.post(f'/api/orders/{self.o.id}/cancel/',{},format='json').status_code,400)
    def test_other_customer_cannot_touch_order(self):
        other=Customer.objects.create_user(username='x@example.com',email='x@example.com',password='Test-Password-910!')
        c=APIClient();c.force_login(other)
        self.assertEqual(c.post(f'/api/orders/{self.o.id}/cancel/',{},format='json').status_code,404)
        self.assertEqual(c.get(f'/api/orders/{self.o.id}/invoice/').status_code,404)
    def test_invoice_pdf(self):
        r=self.c.get(f'/api/orders/{str(self.o.id)[:8]}/invoice/')
        self.assertEqual(r.status_code,200);self.assertEqual(r['Content-Type'],'application/pdf');self.assertTrue(r.content.startswith(b'%PDF'))
    def test_tracking_by_order_and_awb(self):
        Order.objects.filter(pk=self.o.pk).update(awb='12345',courier_status='In Transit',status='shipped',tracking_events=[{'time':'2026-11-04T10:00:00','status':'In Transit','detail':'Bag received','location':'Kolkata'}])
        d=self.c.get('/api/track/',{'order':str(self.o.id)[:8]}).data
        self.assertEqual(d['awb'],'12345');self.assertEqual(d['stage'],2);self.assertEqual(len(d['events']),1)
        anon=APIClient()
        self.assertEqual(anon.get('/api/track/',{'awb':'12345'}).data['order'],'')  # no order id leaked
        self.assertEqual(anon.get('/api/track/',{'awb':'999'}).status_code,404)
        self.assertEqual(anon.get('/api/track/',{'order':str(self.o.id)[:8]}).status_code,401)
    def test_contact_and_coupon_check_and_faqs(self):
        from .models import ContactMessage,ProductFAQ,Coupon
        self.assertEqual(APIClient().post('/api/contact/',{'name':'A','email':'a@example.com','message':'Hello, I need help with sizing.'},format='json').status_code,201)
        self.assertEqual(ContactMessage.objects.count(),1)
        Coupon.objects.create(code='FEST10',percent=10)
        self.assertTrue(APIClient().get('/api/coupons/check/',{'code':'fest10'}).data['valid'])
        self.assertFalse(APIClient().get('/api/coupons/check/',{'code':'NOPE'}).data['valid'])
        ProductFAQ.objects.create(product=self.p,question='Is the dupatta included?',answer='Yes.')
        faqs=APIClient().get('/api/products/rani-suit/').data['faqs']
        self.assertEqual(faqs[0]['q'],'Is the dupatta included?');self.assertGreater(len(faqs),1)


@override_settings(SECURE_SSL_REDIRECT=False,ALLOWED_HOSTS=['testserver'])
class Nov4bTests(TestCase):
    def setUp(self):
        cache.clear()
        self.u=Customer.objects.create_user(username='n@example.com',email='n@example.com',password='Test-Password-910!',first_name='Nina')
        self.p=Product.objects.create(name='Rani Suit',slug='rani-suit',price='5000',mrp='8000',custom_fit=True)
        self.v=Variant.objects.create(product=self.p,sku='R-M',size='M',colour='Rani',stock=0)
        self.c=APIClient();self.c.force_login(self.u)
        self.addr={'name':'Nina','phone':'+919000000001','email':'n@example.com','line1':'Test address','city':'Kolkata','state':'West Bengal','pincode':'700001'}
    def test_custom_request_flow(self):
        from .models import CustomRequest
        from django.core.exceptions import ValidationError as VE
        m={'bust':41,'waist':78,'hip':74,'armhole':75,'unit':'cm'}
        r=self.c.post('/api/custom-requests/',{'product':'rani-suit','variant':self.v.id,'measurements':m},format='json');self.assertEqual(r.status_code,201)
        rid=r.data['id'];self.assertEqual(r.data['status'],'requested');self.assertEqual(r.data['colour'],'Rani')
        self.assertEqual(self.c.post('/api/custom-requests/',{'product':'rani-suit','measurements':{'bust':1}},format='json').status_code,400)
        req=CustomRequest.objects.get(pk=rid);req.status='accepted'
        with self.assertRaises(VE):req.full_clean()  # price required to accept
        req.price=Decimal('6500.40');req.save()
        self.assertEqual(Decimal(self.c.post('/api/quote/',{'custom':rid},format='json').data['subtotal']),Decimal('6500.00'))
        SiteSettings.objects.update_or_create(pk=1,defaults={'cod_enabled':True})
        d=self.c.post('/api/checkout/',{'address':self.addr,'key':str(uuid.uuid4()),'method':'cod','custom':rid,'consent':True},format='json')
        self.assertEqual(d.status_code,200,d.data);req.refresh_from_db();self.assertEqual(req.status,'ordered')
        o=Order.objects.get(pk=req.order_id);self.assertEqual(o.total,Decimal('6500')+o.shipping);self.assertEqual(o.items.first().measurements['bust'],41)
        self.v.refresh_from_db();self.assertEqual(self.v.stock,0)  # made to order: no stock used
        # cancelling the order cancels the request and does not add stock
        self.assertEqual(self.c.post(f'/api/orders/{o.id}/cancel/',{},format='json').status_code,200)
        req.refresh_from_db();self.assertEqual(req.status,'cancelled');self.v.refresh_from_db();self.assertEqual(self.v.stock,0)
    def test_unpaid_custom_order_reopens_request(self):
        from .models import CustomRequest
        req=CustomRequest.objects.create(user=self.u,product=self.p,variant=self.v,measurements={'bust':40,'waist':30,'hip':40,'armhole':16,'unit':'in'},status='accepted',price=7000)
        from .services import reserve_custom_order
        o,_=reserve_custom_order(self.u,req.pk,self.addr,uuid.uuid4(),'cashfree');release_order(o.pk)
        req.refresh_from_db();self.assertEqual(req.status,'accepted');self.assertIsNone(req.order_id)
    def test_calendly_booking_shows_in_account(self):
        ev='https://api.calendly.com/scheduled_events/ABCDEF1234';inv=ev+'/invitees/XYZ98765'
        self.assertEqual(self.c.post('/api/appointments/calendly/',{'event_uri':ev,'invitee_uri':inv,'session_type':'styling','mode':'video'},format='json').status_code,201)
        self.c.post('/api/appointments/calendly/',{'event_uri':ev,'invitee_uri':inv},format='json')  # repeated message: no duplicate
        a=self.c.get('/api/appointments/mine/').data;self.assertEqual(len(a),1);self.assertEqual(a[0]['source'],'calendly')
        self.assertEqual(self.c.post('/api/appointments/calendly/',{'event_uri':'https://evil.example/x','invitee_uri':inv},format='json').status_code,400)
    @override_settings(GOOGLE_CLIENT_ID='cid',GOOGLE_CLIENT_SECRET='sec',GOOGLE_REDIRECT_URI='http://localhost:3000/api/auth/google/callback/')
    def test_google_sign_in(self):
        c=APIClient()
        r=c.get('/api/auth/google/',{'next':'/checkout?variant=5'});self.assertEqual(r.status_code,302);self.assertIn('accounts.google.com',r['Location'])
        state=c.session['google_state']
        tok=FakeResponse({'access_token':'at'});info=FakeResponse({'email':'New.Person@Example.com','email_verified':True,'given_name':'New','family_name':'Person'})
        tok.raise_for_status=info.raise_for_status=lambda:None
        with patch('requests.post',return_value=tok),patch('requests.get',return_value=info):
            r=c.get('/api/auth/google/callback/',{'code':'abc','state':state})
        self.assertEqual(r.status_code,302);self.assertEqual(r['Location'],'/checkout?variant=5')
        self.assertEqual(c.get('/api/auth/me/').data['user']['email'],'new.person@example.com')
        r=c.get('/api/auth/google/callback/',{'code':'abc','state':'wrong'});self.assertIn('error=google-expired',r['Location'])
    def test_policy_page_html(self):
        from .models import Page
        Page.objects.create(slug='privacy',title='Privacy Policy',body='<h2>Data</h2><p>We keep it safe.</p><script>alert(1)</script>',published=True)
        d=APIClient().get('/api/pages/privacy/').data
        self.assertIn('<h2>Data</h2>',d['html']);self.assertNotIn('script',d['html'])


ADMIN_STORAGE={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}}
@override_settings(SECURE_SSL_REDIRECT=False,ALLOWED_HOSTS=['testserver'],STORAGES=ADMIN_STORAGE,**DELHIVERY)
class LiveIssuesTests(TestCase):
    def setUp(self):
        cache.clear()
        self.u=Customer.objects.create_user(username='l@example.com',email='l@example.com',password='Test-Password-910!')
        self.staff=Customer.objects.create_superuser(username='s@example.com',email='s@example.com',password='Test-Password-910!')
        self.p=Product.objects.create(name='Gown',slug='gown-x',price='3000',mrp='4000')
        self.v=Variant.objects.create(product=self.p,sku='G-M',size='M',colour='Red',stock=3)
        cart=Cart.objects.create(user=self.u);CartItem.objects.create(cart=cart,variant=self.v,quantity=1)
        self.addr={'name':'Lata','phone':'+919000000001','email':'l@example.com','line1':'Test address','city':'Kolkata','state':'West Bengal','pincode':'700001'}
        self.o=reserve_order(self.u,cart,self.addr,uuid.uuid4(),method='cod')[0]
        self.c=APIClient();self.c.force_login(self.u)
        self.a=APIClient();self.a.force_login(self.staff)
        self.a.cookies['admin_sessionid']=self.a.cookies['sessionid'].value  # admin uses its own session cookie
    def test_media_served_without_debug(self):
        import tempfile,os
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d,'home'));open(os.path.join(d,'home','banner.png'),'wb').write(b'\x89PNG test')
            with override_settings(MEDIA_ROOT=d,DEBUG=False,SECURE_SSL_REDIRECT=True):
                r=APIClient().get('/media/home/banner.png')  # plain HTTP, like Next.js image resizing inside the server
                self.assertEqual(r.status_code,200);self.assertEqual(b''.join(r.streaming_content),b'\x89PNG test')
    def test_upload_folders_created(self):
        import tempfile,os
        from .apps import ensure_media_folders
        with tempfile.TemporaryDirectory() as d, override_settings(MEDIA_ROOT=os.path.join(d,'media')):
            ensure_media_folders()
            for f in ['home','products','collections','menu']:self.assertTrue(os.path.isdir(os.path.join(d,'media',f)),f)
    def test_admin_cancel_cancels_delhivery_shipment(self):
        Order.objects.filter(pk=self.o.pk).update(awb='111',courier_status='Manifested',status='processing',pickup_requested_at=timezone.now())
        with patch('shop.delhivery.requests.request',return_value=FakeResponse({'status':True,'remark':'Shipment has been cancelled'})) as req:
            r=self.a.post('/admin/shop/order/',{'action':'admin_cancel','_selected_action':[str(self.o.pk)]})
        self.assertEqual(r.status_code,302);self.o.refresh_from_db();self.assertEqual(self.o.status,'cancelled');self.assertEqual(self.o.courier_status,'Cancelled')
        self.assertEqual(req.call_args.kwargs['json'],{'waybill':'111','cancellation':'true'});self.v.refresh_from_db();self.assertEqual(self.v.stock,3)
    def test_return_flow(self):
        ref=str(self.o.id)[:8]
        self.assertEqual(self.c.post(f'/api/orders/{ref}/return/',{'reason':'Size issue'},format='json').status_code,400)  # not delivered yet
        Order.objects.filter(pk=self.o.pk).update(status='delivered',awb='111',delivered_at=timezone.now())
        self.assertTrue(self.c.get('/api/orders/').data[0]['can_return'])
        r=self.c.post(f'/api/orders/{ref}/return/',{'reason':'Size issue'},format='json');self.assertEqual(r.status_code,200);self.assertEqual(r.data['return_status'],'requested')
        with patch('shop.delhivery.requests.request',return_value=FakeResponse({'packages':[{'waybill':'999R','status':'Success'}]})) as req:
            self.a.post('/admin/shop/order/',{'action':'return_approve','_selected_action':[str(self.o.pk)]})
        sent=json.loads(req.call_args.kwargs['data'].decode().split('data=',1)[1]);self.assertEqual(sent['shipments'][0]['payment_mode'],'Pickup')
        self.o.refresh_from_db();self.assertEqual(self.o.return_awb,'999R');self.assertEqual(self.o.return_status,'pickup_booked')
        self.a.post('/admin/shop/order/',{'action':'return_received','_selected_action':[str(self.o.pk)]})
        self.o.refresh_from_db();self.assertEqual(self.o.return_status,'received');self.assertEqual(self.o.status,'refund_required')  # COD: manual refund
    def test_return_window_closed(self):
        Order.objects.filter(pk=self.o.pk).update(status='delivered',delivered_at=timezone.now()-timedelta(days=30))
        self.assertFalse(self.c.get('/api/orders/').data[0]['can_return'])
    def test_orders_admin_and_label_tool(self):
        Order.objects.filter(pk=self.o.pk).update(awb='5627861000183')
        self.assertContains(self.a.get('/admin/shop/order/'),'#'+str(self.o.id)[:8].upper())
        self.assertEqual(self.a.get('/admin/shop/shippinglabel/').status_code,200)
        with patch('shop.delhivery.requests.request',return_value=FakeResponse({'packages':[{'pdf_download_link':'https://example.com/label.pdf'}]})):
            r=self.a.get('/admin/shop/shippinglabel/',{'awb':'5627861000183'})
        self.assertEqual(r.status_code,302);self.assertEqual(r['Location'],'https://example.com/label.pdf')
        with patch('shop.delhivery.requests.request',return_value=FakeResponse({'packages':[{'wbn':'5627861000183','name':'Lata','pin':'700001'}]})):
            self.assertContains(self.a.get('/admin/shop/shippinglabel/',{'awb':'5627861000183'}),'Print labels')


@override_settings(SECURE_SSL_REDIRECT=False,ALLOWED_HOSTS=['testserver'],INTERNAL_API_TOKEN='internal-test-token')
class ThrottleTests(TestCase):
    def setUp(self):cache.clear()
    def test_visitor_limited_but_site_server_not(self):
        from rest_framework.throttling import AnonRateThrottle
        with patch.object(AnonRateThrottle,'THROTTLE_RATES',{'anon':'3/min','user':'360/min','auth':'10/min'}):
            c=APIClient()
            codes=[c.get('/api/site/').status_code for _ in range(5)]
            self.assertEqual(codes[:3],[200,200,200]);self.assertEqual(codes[-1],429)
            # the Next.js server (page renders, prefetches) is never limited
            self.assertTrue(all(c.get('/api/site/',HTTP_X_INTERNAL_TOKEN='internal-test-token').status_code==200 for _ in range(10)))
            self.assertEqual(c.get('/api/site/',HTTP_X_INTERNAL_TOKEN='wrong').status_code,429)


@override_settings(SECURE_SSL_REDIRECT=False,ALLOWED_HOSTS=['testserver'])
class AvatarTests(TestCase):
    def test_upload_and_remove_photo(self):
        import io,tempfile
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        u=Customer.objects.create_user(username='p@example.com',email='p@example.com',password='Test-Password-910!',first_name='Priya')
        c=APIClient();c.force_login(u)
        self.assertEqual(c.get('/api/auth/me/').data['user']['avatar'],'')
        buf=io.BytesIO();Image.new('RGB',(20,20),'red').save(buf,'PNG')
        with tempfile.TemporaryDirectory() as d, override_settings(MEDIA_ROOT=d):
            r=c.post('/api/auth/avatar/',{'photo':SimpleUploadedFile('me.png',buf.getvalue(),'image/png')},format='multipart')
            self.assertEqual(r.status_code,200);self.assertTrue(r.data['user']['avatar'].startswith('/media/avatars/'))
            bad=c.post('/api/auth/avatar/',{'photo':SimpleUploadedFile('x.png',b'not an image','image/png')},format='multipart');self.assertEqual(bad.status_code,400)
            self.assertEqual(c.delete('/api/auth/avatar/').data['user']['avatar'],'')
        self.assertEqual(APIClient().post('/api/auth/avatar/',{},format='multipart').status_code,403)


@override_settings(SECURE_SSL_REDIRECT=False,ALLOWED_HOSTS=['testserver'],STORAGES=ADMIN_STORAGE,**DELHIVERY)
class AdminDashboardTests(TestCase):
    def setUp(self):
        cache.clear()
        self.u=Customer.objects.create_user(username='d2@example.com',email='d2@example.com',password='Test-Password-910!')
        self.staff=Customer.objects.create_superuser(username='s2@example.com',email='s2@example.com',password='Test-Password-910!')
        self.p=Product.objects.create(name='Gown',slug='gown-y',price='3000',mrp='4000',custom_fit=True)
        self.v=Variant.objects.create(product=self.p,sku='G-L',size='L',colour='Red',stock=3)
        cart=Cart.objects.create(user=self.u);CartItem.objects.create(cart=cart,variant=self.v,quantity=1)
        self.addr={'name':'Dia','phone':'+919000000001','email':'d2@example.com','line1':'Test address','city':'Kolkata','state':'West Bengal','pincode':'700001'}
        self.o=reserve_order(self.u,cart,self.addr,uuid.uuid4(),method='cod')[0]
        self.a=APIClient();self.a.force_login(self.staff);self.a.cookies['admin_sessionid']=self.a.cookies['sessionid'].value
    def test_dashboard_and_sections_open(self):
        r=self.a.get('/admin/');self.assertContains(r,'Need a waybill');self.assertContains(r,'Returns &amp; refunds')
        for u in ['/admin/shop/readytoship/','/admin/shop/returnorder/','/admin/shop/pickuprequest/','/admin/shop/customrequest/','/admin/shop/order/','/admin/shop/product/']:
            self.assertEqual(self.a.get(u).status_code,200,u)
        self.assertContains(self.a.get('/admin/shop/readytoship/'),'#'+str(self.o.id)[:8].upper())
    def test_request_pickup_with_date(self):
        from .models import PickupRequest
        Order.objects.filter(pk=self.o.pk).update(awb='5627861000183',status='processing')
        form=self.a.post('/admin/shop/readytoship/',{'action':'request_pickup','_selected_action':[str(self.o.pk)]})
        self.assertContains(form,'Request Delhivery pickup')
        day=(timezone.localtime()+timedelta(days=1)).date().isoformat()
        with patch('shop.delhivery.requests.request',return_value=FakeResponse({'pickup_id':123,'incoming_center_name':'Kolkata'})) as req:
            r=self.a.post('/admin/shop/readytoship/',{'action':'request_pickup','_selected_action':[str(self.o.pk)],'apply':'1','date':day,'time':'11:30'})
        self.assertEqual(r.status_code,302);sent=req.call_args.kwargs['json']
        self.assertEqual(sent['pickup_date'],day);self.assertEqual(sent['pickup_time'],'11:30:00');self.assertEqual(sent['expected_package_count'],1)
        self.o.refresh_from_db();self.assertIsNotNone(self.o.pickup_requested_at);self.assertEqual(PickupRequest.objects.get().orders.get(),self.o)
    def test_returns_section_refund(self):
        Order.objects.filter(pk=self.o.pk).update(status='delivered',return_status='requested',return_reason='Size',delivered_at=timezone.now())
        self.assertContains(self.a.get('/admin/shop/returnorder/'),'Size')
        self.a.post('/admin/shop/returnorder/',{'action':'mark_return_received','_selected_action':[str(self.o.pk)]})
        self.a.post('/admin/shop/returnorder/',{'action':'refund_customer','_selected_action':[str(self.o.pk)]})
        self.o.refresh_from_db();self.assertEqual(self.o.status,'refund_required')  # COD: manual refund
        self.a.post('/admin/shop/returnorder/',{'action':'mark_refunded_manually','_selected_action':[str(self.o.pk)]})
        self.o.refresh_from_db();self.assertEqual(self.o.status,'refunded')
    def test_custom_request_with_customisations(self):
        c=APIClient();c.force_login(self.u)
        r=c.post('/api/custom-requests/',{'product':'gown-y','variant':self.v.id,'measurements':{'unit':'in','height':'64','sleeve':'18'},
                 'options':{'neckline':'Deep V','extra':'Add tassels'}},format='json')
        self.assertEqual(r.status_code,201,r.data);self.assertEqual(r.data['measurements'],{'height':64.0,'sleeve':18.0,'unit':'in'});self.assertEqual(r.data['options']['neckline'],'Deep V')
        self.assertEqual(c.post('/api/custom-requests/',{'product':'gown-y','measurements':{'unit':'in'}},format='json').status_code,400)
        self.assertContains(self.a.get(f"/admin/shop/customrequest/{r.data['id']}/change/"),'Deep V')


@override_settings(SECURE_SSL_REDIRECT=False,ALLOWED_HOSTS=['testserver'])
class QuickFilterTests(TestCase):
    def test_chips(self):
        cache.clear()
        a=Product.objects.create(name='A',slug='a',price='100',mrp='200',custom_fit=True);Variant.objects.create(product=a,sku='A1',size='M',colour='Red',stock=2)
        b=Product.objects.create(name='B',slug='b',price='100',mrp='100',custom_fit=False);Variant.objects.create(product=b,sku='B1',size='M',colour='Red',stock=0)
        slugs=lambda q:{x['slug'] for x in APIClient().get('/api/products/?'+q).data['results']}
        self.assertEqual(slugs('custom=1'),{'a'});self.assertEqual(slugs('sale=1'),{'a'});self.assertEqual(slugs('ready=1'),{'a'});self.assertEqual(slugs(''),{'a','b'})


@override_settings(SECURE_SSL_REDIRECT=False,ALLOWED_HOSTS=['testserver'])
class HomeOccasionsSeoTests(TestCase):
    def test_occasion_cards_and_seo_fields(self):
        cache.clear()
        from shop.models import Occasion,HomeSection,HomeCard
        Occasion.objects.all().delete();HomeSection.objects.all().delete()
        for i,n in enumerate(['Haldi','Wedding']):Occasion.objects.create(name=n,slug=n.lower(),sort_order=i)
        Occasion.objects.create(name='Old',slug='old',active=False)
        HomeSection.objects.create(kind='occasions',admin_name='Occ',title='Elegance at Every Wear')
        hero=HomeSection.objects.create(kind='hero',admin_name='Hero',image_path='/images/hero.webp',mobile_image_path='/images/hero-m.webp',button_url='/collections/gown',alt_text='Red gown banner',image_title='Gowns')
        HomeCard.objects.create(section=hero,image_path='/images/b.webp',url='/products?sale=1',alt_text='Sale banner',image_title='Sale')
        d=APIClient().get('/api/home/').data['sections']
        occ=next(s for s in d if s['kind']=='occasions');h=next(s for s in d if s['kind']=='hero')
        self.assertEqual([(c['title'],c['href']) for c in occ['cards']],[('Haldi','/products?occasion=haldi'),('Wedding','/products?occasion=wedding')])
        self.assertEqual((h['href'],h['alt'],h['image_title'],h['mobile_image']),('/collections/gown','Red gown banner','Gowns','/images/hero-m.webp'))
        self.assertEqual((h['cards'][0]['href'],h['cards'][0]['alt'],h['cards'][0]['image_title']),('/products?sale=1','Sale banner','Sale'))


@override_settings(SECURE_SSL_REDIRECT=False,ALLOWED_HOSTS=['testserver'])
class ProductImageUploadTests(TestCase):
    def setUp(self):
        import tempfile;self.media=tempfile.mkdtemp()
    def _jpeg(self,w,h,noise=True):
        from io import BytesIO;import os
        from PIL import Image
        im=Image.frombytes('RGB',(w,h),os.urandom(w*h*3)) if noise else Image.new('RGB',(w,h),(200,30,30))
        b=BytesIO();im.save(b,'JPEG',quality=97);return b.getvalue()
    def test_large_photo_is_accepted_and_resized(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from shop.models import ProductImage
        from PIL import Image
        with self.settings(MEDIA_ROOT=self.media):
            p=Product.objects.create(name='Big',slug='big',price='100',mrp='100')
            data=self._jpeg(2800,2300);self.assertGreater(len(data),5*1024*1024);self.assertLess(len(data),10*1024*1024)
            pi=ProductImage(product=p,alt='x',image=SimpleUploadedFile('big.jpg',data,'image/jpeg'))
            pi.full_clean();pi.save()
            im=Image.open(pi.image.path);self.assertEqual(max(im.size),2400)
    def test_over_10mb_is_rejected_with_message(self):
        from django.core.exceptions import ValidationError
        from django.core.files.uploadedfile import SimpleUploadedFile
        from shop.models import ProductImage
        p=Product.objects.create(name='Huge',slug='huge',price='100',mrp='100')
        f=SimpleUploadedFile('huge.jpg',b'0'*(10*1024*1024+1),'image/jpeg')
        with self.assertRaisesMessage(ValidationError,'up to 10 MB'):
            ProductImage(product=p,alt='x',image=f).full_clean()


@override_settings(SECURE_SSL_REDIRECT=False,ALLOWED_HOSTS=['testserver'],STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class AdminManyPhotosTests(TestCase):
    def test_admin_saves_more_than_three_photos(self):
        import tempfile
        from io import BytesIO
        from PIL import Image
        from django.contrib.auth import get_user_model
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.test import Client
        from shop.models import ProductImage
        def jpg(n):
            b=BytesIO();Image.new('RGB',(60,80),(n*20,0,0)).save(b,'JPEG');return SimpleUploadedFile(f'p{n}.jpg',b.getvalue(),'image/jpeg')
        U=get_user_model();U.objects.create_superuser(username='boss2@example.com',email='boss2@example.com',password='Test-Password-910!')
        c=Client();self.assertTrue(c.login(username='boss2@example.com',password='Test-Password-910!'))
        c.cookies['admin_sessionid']=c.cookies['sessionid'].value
        from shop.models import Collection
        col=Collection.objects.create(name='Suits',slug='suits-many')
        p=Product.objects.create(name='Many',slug='many',price='100',mrp='100')
        url=f'/admin/shop/product/{p.id}/change/'
        page=c.get(url);self.assertContains(page,'Add several photos at once');self.assertContains(page,'shrink-uploads.js')
        form={'name':'Many','slug':'many','price':'100','mrp':'100','active':'on','description':'d','fabric':'','fit':'','care':'','includes':'','collections':[str(col.id)]}
        for k,v in page.context['adminform'].form.initial.items():
            if k not in form and v not in (None,'') and not isinstance(v,(list,tuple)) and not hasattr(v,'pk'):form[k]=v
        for fs in page.context['inline_admin_formsets']:
            pre=fs.formset.prefix
            n=6 if fs.formset.model is ProductImage else 0
            form.update({f'{pre}-TOTAL_FORMS':str(n),f'{pre}-INITIAL_FORMS':'0',f'{pre}-MIN_NUM_FORMS':'0',f'{pre}-MAX_NUM_FORMS':'1000'})
            for i in range(n):form.update({f'{pre}-{i}-image':jpg(i),f'{pre}-{i}-alt':'' ,f'{pre}-{i}-position':str(i)})
        form['bulk_photos']=[jpg(7),jpg(8),jpg(9),jpg(10)]
        with self.settings(MEDIA_ROOT=tempfile.mkdtemp()):
            r=c.post(url,form)
        errs=r.context['adminform'].form.errors if r.status_code==200 else None
        self.assertEqual(r.status_code,302,errs or [f.errors for fs in (r.context or {}).get('inline_admin_formsets',[]) for f in [fs.formset]])
        self.assertEqual(p.images.count(),10)
        self.assertTrue(all(i.alt=='Many' for i in p.images.all()))


@override_settings(SECURE_SSL_REDIRECT=False,ALLOWED_HOSTS=['testserver','sub.aimanroyale.com'],EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
                   STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class GoogleResetPasswordRuleTests(TestCase):
    def test_redirect_uri_choice(self):
        from django.test import RequestFactory
        from shop.api import google_redirect_uri
        rf=RequestFactory()
        r=rf.get('/api/auth/google/',HTTP_HOST='sub.aimanroyale.com',HTTP_X_FORWARDED_PROTO='https')
        with self.settings(GOOGLE_REDIRECT_URI_SET=False,PUBLIC_SITE_URL='http://sub.aimanroyale.com'):
            self.assertEqual(google_redirect_uri(r),'https://sub.aimanroyale.com/api/auth/google/callback/')
        with self.settings(GOOGLE_REDIRECT_URI_SET=False,PUBLIC_SITE_URL='http://localhost:3000'):
            self.assertEqual(google_redirect_uri(r),'https://sub.aimanroyale.com/api/auth/google/callback/')
        with self.settings(GOOGLE_REDIRECT_URI_SET=True,GOOGLE_REDIRECT_URI='https://example.com/cb/'):
            self.assertEqual(google_redirect_uri(r),'https://example.com/cb/')

    def test_google_start_sends_and_remembers_redirect(self):
        with self.settings(GOOGLE_CLIENT_ID='cid',GOOGLE_CLIENT_SECRET='sec',GOOGLE_REDIRECT_URI_SET=False,PUBLIC_SITE_URL='https://sub.aimanroyale.com'):
            r=self.client.get('/api/auth/google/')
        self.assertIn('redirect_uri=https%3A%2F%2Fsub.aimanroyale.com%2Fapi%2Fauth%2Fgoogle%2Fcallback%2F',r['Location'])
        self.assertEqual(self.client.session['google_redirect'],'https://sub.aimanroyale.com/api/auth/google/callback/')

    def test_reset_link_for_google_account(self):
        from django.core import mail
        u=Customer(username='g@example.com',email='g@example.com');u.set_unusable_password();u.save()
        r=self.client.post('/accounts/password_reset/',{'email':'G@example.com'})
        self.assertEqual(r.status_code,302);self.assertEqual(len(mail.outbox),1);self.assertIn('/accounts/reset/',mail.outbox[0].body)
        self.assertContains(self.client.get('/accounts/password_reset/'),'Continue with Google instead')

    def test_password_rule_is_only_length(self):
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError
        u=Customer(username='ravi@example.com',email='ravi@example.com',first_name='Ravi')
        for ok in ['password12','ravi@example.com','1234567890']:validate_password(ok,u)
        with self.assertRaises(ValidationError):validate_password('short1',u)
