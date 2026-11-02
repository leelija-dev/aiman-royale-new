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
        self.assertEqual(d[0]['kind'],'hero');self.assertEqual(len(d),14)
        hero=HomeSection.objects.get(kind='hero');hero.sort_order=999;hero.save()
        HomeSection.objects.filter(kind='story').update(active=False)
        card=HomeCard.objects.filter(section__kind='consult').first();card.title='Custom title';card.save()
        d=self.client.get('/api/home/').json()['sections']
        self.assertEqual(d[-1]['kind'],'hero');self.assertNotIn('story',[x['kind'] for x in d])
        consult=[x for x in d if x['kind']=='consult'][0]
        self.assertEqual(consult['cards'][0]['title'],'Custom title');self.assertEqual(len(consult['cards'][0]['bullets']),3)


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
        self.assertEqual(len(d['steps']),4);self.assertIn('variations',d['note'])
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
