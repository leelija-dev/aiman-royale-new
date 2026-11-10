'use client';
import Image from 'next/image';
import Link from 'next/link';
import {useEffect, useState} from 'react';
import {useRouter} from 'next/navigation';
import {ArrowLeft, ArrowRight, ChevronRight, Landmark, Banknote, CreditCard, Headphones, Phone, Mail, TicketPercent, CheckCircle2, Lock} from 'lucide-react';
import {api, bagChanged, err} from '@/lib/client';
import type {PinInfo} from '@/lib/types';
import {Bag, Order, Site, User, money, photo} from '@/lib/types';
import {Steps, COUPON_KEY, NOTE_KEY} from '@/components/bag';
import {SavingZone} from '@/components/saving-zone';

type Quote = {subtotal: string; discount: string; shipping: string; total: string};
type Address = Record<'name' | 'phone' | 'email' | 'line1' | 'line2' | 'city' | 'state' | 'pincode', string>;
type Method = 'upi' | 'card' | 'netbanking' | 'cod';
type CashfreeClient = {checkout: (o: {paymentSessionId: string; redirectTarget: string}) => Promise<{error?: {message?: string}; redirect?: boolean}>};
declare global { interface Window { Cashfree?: (o: {mode: 'sandbox' | 'production'}) => CashfreeClient } }

const ADDRESS_KEY = 'ar-address';
const read = (k: string) => { try { return localStorage.getItem(k) || ''; } catch { return ''; } };
const write = (k: string, v: string) => { try { if (v) localStorage.setItem(k, v); else localStorage.removeItem(k); } catch {} };
const FIELDS: [keyof Address, string, string, string?][] = [
  ['name', 'Full name', 'name'], ['phone', 'Mobile number', 'tel', '\\+?[1-9][0-9]{9,14}'], ['email', 'Email address', 'email'], ['pincode', 'PIN code', 'postal-code', '[1-9][0-9]{5}'],
  ['line1', 'House / street address', 'address-line1'], ['line2', 'Apartment / landmark (optional)', 'address-line2'], ['city', 'City', 'address-level2'], ['state', 'State', 'address-level1'],
];

let sdk: Promise<void> | null = null;
function loadCashfree() {
  if (window.Cashfree) return Promise.resolve();
  if (!sdk) sdk = new Promise<void>((resolve, reject) => {
    const s = document.createElement('script'); s.src = 'https://sdk.cashfree.com/js/v3/cashfree.js';
    s.onload = () => resolve(); s.onerror = () => { sdk = null; s.remove(); reject(Error('Could not load the secure payment window. Please check your connection and try again.')); };
    document.head.appendChild(s);
  });
  return sdk;
}

function UpiArt() {
  return <svg viewBox="0 0 150 130" className="co-upi-art" aria-hidden>
    <circle cx="80" cy="66" r="52" fill="#f6dfe2"/>
    <path d="M28 108c10-18 22-26 34-30M30 96c6-2 12 0 15 6M26 84c7 0 12 4 13 10" stroke="#c9a27a" strokeWidth="2" fill="none"/>
    <path d="M130 108c-8-16-18-24-30-28M126 94c-5-1-10 1-12 6M132 82c-6 0-10 3-11 9" stroke="#c9a27a" strokeWidth="2" fill="none"/>
    <rect x="58" y="12" width="48" height="96" rx="9" fill="#2b2523" transform="rotate(8 82 60)"/>
    <rect x="62" y="18" width="40" height="84" rx="6" fill="#fbf6f1" transform="rotate(8 82 60)"/>
    <text x="70" y="52" fontFamily="Arial" fontWeight="700" fontStyle="italic" fontSize="14" fill="#5b5552" transform="rotate(8 82 60)">UPI</text>
    <path d="M70 68h-4v8M94 68h4v8M70 92h-4v-8M94 92h4v-8" stroke="#2b2523" strokeWidth="2.4" fill="none" transform="rotate(8 82 60)"/>
  </svg>;
}

export function CheckoutPage({site}: {site: Site}) {
  const router = useRouter();
  const [bag, setBag] = useState<Bag | null>(null), [user, setUser] = useState<User | null>(null), [quote, setQuote] = useState<Quote | null>(null);
  const [address, setAddress] = useState<Address | null>(null), [editing, setEditing] = useState(true);
  const [pinInfo, setPinInfo] = useState<PinInfo | null>(null);
  useEffect(() => {
    const pin = address?.pincode;
    if (!pin || !/^[1-9]\d{5}$/.test(pin)) { setPinInfo(null); return; }
    let live = true;
    api<PinInfo>(`delivery/pincode/${pin}/`).then(r => { if (live) setPinInfo(r.checked ? r : null); }).catch(() => live && setPinInfo(null));
    return () => { live = false; };
  }, [address?.pincode]);
  const [method, setMethod] = useState<Method>('upi'), [agree, setAgree] = useState(false);
  const [coupon, setCoupon] = useState(''), [promoMsg, setPromoMsg] = useState<{ok: boolean; text: string} | null>(null), [note, setNote] = useState('');
  const [itemIds, setItemIds] = useState<number[]>([]), [customId, setCustomId] = useState(0);
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [order, setOrder] = useState<Order | null>(null), [key, setKey] = useState('');

  useEffect(() => {
    setKey(crypto.randomUUID());
    setNote(read(NOTE_KEY));
    // Buy Now sends ?variant=<size/colour id>: check out only that product and leave the rest in the bag.
    const qs = new URLSearchParams(window.location.search);
    const onlyVariant = Number(qs.get('variant')) || 0, onlyItem = Number(qs.get('item')) || 0;
    (async () => {
      try {
        const [full, me] = await Promise.all([api<Bag>('cart/'), api<{user: User | null}>('auth/me/')]);
        if (!me.user) { router.replace(`/login?next=${encodeURIComponent(window.location.pathname + window.location.search)}`); return; }
        // Paying for an accepted custom (made-to-measure) request: ?custom=<request id>
        const custom = Number(qs.get('custom')) || 0;
        if (custom) {
          type CR = {id: number; status: string; price: string; quantity: number; colour: string; measurements: Record<string, string>; product: {name: string; slug: string; image: string}};
          const r = (await api<CR[]>('custom-requests/')).find(x => x.id === custom && x.status === 'accepted');
          if (!r) { setError('This custom request is not ready for payment. Please check My Account → Custom Requests.'); setUser(me.user); setBag({...full, items: []}); return; }
          const item = {id: -r.id, quantity: r.quantity, measurements: r.measurements, variant: {id: 0, size: 'Custom fit', colour: r.colour, stock: 1, sku: ''},
            product: {name: `${r.product.name} (custom fit)`, slug: r.product.slug, price: r.price, mrp: r.price, images: r.product.image ? [{id: 0, url: r.product.image, alt: r.product.name}] : []}} as unknown as Bag['items'][number];
          setCustomId(r.id); setUser(me.user); setBag({...full, items: [item]});
          const sa = read(ADDRESS_KEY);
          const ad: Address = sa ? JSON.parse(sa) : {name: me.user.name || '', phone: me.user.phone || '', email: me.user.email || '', line1: '', line2: '', city: '', state: '', pincode: ''};
          setAddress(ad); setEditing(!sa);
          setQuote(await api<Quote>('quote/', 'POST', {custom: r.id}));
          return;
        }
        const picked = onlyVariant ? full.items.filter(i => i.variant.id === onlyVariant).slice(0, 1) : onlyItem ? full.items.filter(i => i.id === onlyItem) : [];
        // Signing in adds the guest bag to the account bag; keep the quantity chosen on Buy Now.
        const wantQty = Number(qs.get('qty')) || 0;
        if (picked.length && wantQty && picked[0].quantity !== wantQty) {
          try { await api('cart/', 'PATCH', {id: picked[0].id, quantity: wantQty}); picked[0] = {...picked[0], quantity: wantQty}; bagChanged(); } catch {}
        }
        const b = picked.length ? {...full, items: picked} : full;
        const ids = picked.map(i => i.id);
        setItemIds(ids);
        setUser(me.user); setBag(b);
        const q = ids.length ? {items: ids} : {};
        const saved = read(ADDRESS_KEY);
        const a: Address = saved ? JSON.parse(saved) : {name: me.user.name || '', phone: me.user.phone || '', email: me.user.email || '', line1: '', line2: '', city: '', state: '', pincode: ''};
        setAddress(a); setEditing(!saved);
        if (b.items.length) {
          const c = read(COUPON_KEY);
          try { setQuote(await api<Quote>('quote/', 'POST', {...q, coupon: c})); if (c) { setCoupon(c); setPromoMsg({ok: true, text: 'Coupon applied.'}); } }
          catch { write(COUPON_KEY, ''); setQuote(await api<Quote>('quote/', 'POST', q)); }
        }
      } catch (e) { setError(err(e)); }
    })();
  }, [router]);

  function saveAddress(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const a = Object.fromEntries(FIELDS.map(([k]) => [k, String(f.get(k) || '').trim()])) as Address;
    setAddress(a); write(ADDRESS_KEY, JSON.stringify(a)); setEditing(false); setError('');
  }

  async function pay() {
    if (busy) return;
    if (!address || editing) { setError('Please save your contact and delivery details first.'); document.getElementById('co-delivery')?.scrollIntoView({behavior: 'smooth'}); return; }
    if (!agree) { setError('Please accept the Terms & Conditions and Return & Refund Policy.'); return; }
    if (pinInfo && !pinInfo.serviceable) { setError('Delhivery does not deliver to this PIN code yet. Please use another address or contact us on WhatsApp.'); return; }
    if (method === 'cod' && pinInfo && !pinInfo.cod) { setError('Cash on Delivery is not available for this PIN code. Please choose an online payment option.'); return; }
    if (method === 'cod' && !site.cod_enabled) { setError('Cash on Delivery is not available for this order.'); return; }
    if (method !== 'cod' && !site.payment_ready) { setError('Online payment is not switched on yet — the Cashfree keys are missing on the server. Please choose another option or contact us to complete your order.'); return; }
    setBusy(true); setError('');
    try {
      const online = method !== 'cod';
      if (online) await loadCashfree();
      const d = await api<{order: Order; payment_session_id: string; mode: 'sandbox' | 'production'}>('checkout/', 'POST', {
        address: {...address, country: 'IN'}, key, coupon: read(COUPON_KEY), method: online ? 'cashfree' : 'cod', pay_with: online ? method : '', note, consent: true, ...(customId ? {custom: customId} : itemIds.length ? {items: itemIds} : {})});
      setOrder(d.order); bagChanged();
      if (d.order.status !== 'pending') { write(COUPON_KEY, ''); write(NOTE_KEY, ''); return; }
      if (!window.Cashfree || !d.payment_session_id) throw Error('The payment window could not open. Your order is saved in your account — please try again from there or contact us.');
      const result = await window.Cashfree({mode: d.mode}).checkout({paymentSessionId: d.payment_session_id, redirectTarget: '_modal'});
      if (result.redirect) return;
      // Never trust the payment window alone: the server confirms the payment with Cashfree.
      const verified = await api<Order>('payments/verify/', 'POST', {order: d.order.id});
      setOrder(verified);
      if (verified.status === 'pending') {
        // Window closed without paying: cancel this attempt so the next try can use any payment method.
        try {
          const c = await api<{order: Order; items: number[]}>('payments/cancel/', 'POST', {order: d.order.id});
          if (c.order.status === 'pending') throw Error('still pending');
          if (['paid', 'processing'].includes(c.order.status)) { setOrder(c.order); write(COUPON_KEY, ''); write(NOTE_KEY, ''); return; }
          setOrder(null); setKey(crypto.randomUUID()); bagChanged();
          const full = await api<Bag>('cart/');
          if (customId) setBag(b => b);
          else if (itemIds.length) { const back = full.items.filter(i => c.items.includes(i.id)); setItemIds(back.map(i => i.id)); setBag({...full, items: back.length ? back : full.items}); }
          else setBag(full);
          setError('Payment was not completed, so nothing was charged. Your items are still in your bag — choose any payment method and try again.');
        } catch {
          setError(result.error?.message ? `Payment was not completed: ${result.error.message}` : 'Payment has not been confirmed yet. If money was taken, do not pay again — check the status in your account.');
        }
      }
      else { write(COUPON_KEY, ''); write(NOTE_KEY, ''); }
    } catch (e) { setError(err(e)); } finally { setBusy(false); }
  }

  if (order && ['paid', 'cod', 'processing', 'shipped', 'delivered'].includes(order.status)) return <section className="cp co-done"><CheckCircle2 size={54}/>
    <p className="cp-eyebrow">Thank you for choosing Aiman Royale</p><h1>Your order is placed.</h1>
    <p>Order <strong>{order.id.slice(0, 8).toUpperCase()}</strong> · {money(order.total)}</p>
    <p>{order.status === 'cod' ? 'Please keep the amount ready — payment is collected on delivery.' : 'Your payment has been received and confirmed.'} We’ll email you updates.</p>
    <div><Link href="/account/orders" className="pd-btn pd-btn-bag">View My Orders</Link><Link href="/products" className="pd-btn pd-btn-buy">Continue Shopping</Link></div></section>;

  const items = bag?.items || [];
  const mrp = items.reduce((n, i) => n + Math.max(Number(i.product.mrp), Number(i.product.price)) * i.quantity, 0);
  const sub = quote ? Number(quote.subtotal) : Number(bag?.subtotal || 0);
  const methods: {id: Method; label: string; icon?: React.ReactNode; hint?: string}[] = [
    {id: 'upi', label: 'UPI'}, {id: 'card', label: 'Credit / Debit Card', icon: <CreditCard size={22}/>}, {id: 'netbanking', label: 'Net Banking', icon: <Landmark size={22}/>},
    {id: 'cod', label: 'Cash on Delivery', icon: <Banknote size={22}/>, hint: site.cod_enabled ? 'Subject to eligibility.' : 'Not available at the moment.'},
  ];

  return <div className="cp co-page">
    <div className="co-top"><Link href="/cart" className="co-back"><ArrowLeft size={18}/> Back to Bag</Link><Steps at={address && !editing ? 3 : 2}/><span className="co-secure"><Lock size={17}/> Secure Checkout</span></div>
    <div className="co-head"><h1>Complete your order</h1><p>A few final steps to bring your Aiman Royale piece home</p></div>
    {!bag || !user ? <p className="bag-wrap" role="status">{error || 'Preparing your secure checkout…'}</p> : !items.length && !order ? <div className="empty"><h2>{error || 'Your bag is empty.'}</h2><Link className="button" href="/products">Discover the Collection</Link></div> :
    <div className="co-grid">
      <div>
        <section className="co-card" id="co-delivery">
          <div className="co-card-head"><span className="co-num">1</span><div><h2>Contact &amp; Delivery</h2>
            {address && !editing ? <p className="co-addr">{address.name} · {address.phone}<br/>{address.line1}{address.line2 ? `, ${address.line2}` : ''}, {address.city}, {address.state} {address.pincode}<br/>{address.email}</p> : <p>Add or review your delivery details.</p>}
            {address && !editing && pinInfo && <p className={pinInfo.serviceable ? 'pd-ok' : 'pd-err'}>{pinInfo.serviceable ? `Delivers via Delhivery${pinInfo.cod ? ' · Cash on Delivery available' : ' · Prepaid only'}` : 'Delhivery does not deliver to this PIN code yet.'}</p>}</div>
            {!editing && <button type="button" className="co-edit" onClick={() => setEditing(true)}>Edit <ChevronRight size={18}/></button>}</div>
          {editing && address && <form className="co-form" onSubmit={saveAddress}>{FIELDS.map(([k, label, auto, pattern]) =>
            <label key={k} className={k === 'line1' || k === 'line2' ? 'wide' : ''}>{label}<input name={k} type={k === 'email' ? 'email' : k === 'phone' ? 'tel' : 'text'} required={k !== 'line2'} defaultValue={address[k]} autoComplete={auto} pattern={pattern} inputMode={k === 'pincode' ? 'numeric' : undefined}/></label>)}
            <p className="co-small wide">We deliver within India.</p>
            <button className="pd-btn pd-btn-bag wide">Save &amp; Continue <ArrowRight size={17}/></button></form>}
        </section>

        <section className="co-card">
          <div className="co-card-head"><span className="co-num on">2</span><div><h2>Payment method</h2></div></div>
          <div className="co-methods" role="radiogroup" aria-label="Payment method">{methods.map(m => {
            const disabled = m.id === 'cod' && !site.cod_enabled, on = method === m.id;
            return <div key={m.id} className={`co-method${on ? ' on' : ''}${disabled ? ' off' : ''}`}>
              <label><input type="radio" name="method" checked={on} disabled={disabled} onChange={() => setMethod(m.id)}/><span className="co-radio"/>{m.icon}<span className="co-method-text"><strong>{m.label}</strong>{m.hint && <small>{m.hint}</small>}</span>{!on && <ChevronRight size={18}/>}</label>
              {on && m.id === 'upi' && <div className="co-method-body"><div><p>Continue to our payment partner to choose your UPI app or scan a QR code.</p><small>Available methods are confirmed at checkout.</small></div><UpiArt/></div>}
              {on && m.id === 'card' && <div className="co-method-body"><div><p>Pay with Visa, Mastercard, RuPay and other cards in our payment partner’s secure window. Card details never touch our servers.</p></div></div>}
              {on && m.id === 'netbanking' && <div className="co-method-body"><div><p>Choose your bank in our payment partner’s secure window and complete the payment there.</p></div></div>}
              {on && m.id === 'cod' && <div className="co-method-body"><div><p>Pay in cash when your order arrives. Please keep the exact amount ready.</p></div></div>}
            </div>; })}</div>
          {!site.payment_ready && method !== 'cod' && <p className="notice">Online payment isn’t available right now. You can still place the order with Cash on Delivery (if offered) or contact us on WhatsApp.</p>}
        </section>

        <section className="co-card">
          <div className="co-card-head"><span className="co-num">3</span><div><h2>Review your order</h2><p>Confirm your delivery details and final total before paying.</p>
            {note && <p className="co-small">Order note: “{note}”</p>}</div></div>
        </section>

        <label className="co-terms"><input type="checkbox" checked={agree} onChange={e => setAgree(e.target.checked)}/> <span>I agree to the <Link href="/info/terms">Terms &amp; Conditions</Link> and <Link href="/info/returns">Return &amp; Refund Policy</Link>.</span></label>
        {error && <p className="pd-err co-error" role="alert">{error}</p>}
        {order && order.status !== 'paid' && <p className="notice">Order reference {order.id.slice(0, 8).toUpperCase()} · {order.status.replace('_', ' ')}. <Link href="/account/orders">View in your account</Link></p>}
        <button type="button" className="pd-btn pd-btn-bag co-pay" disabled={busy || !quote} onClick={pay}>
          {busy ? 'Please wait…' : method === 'cod' ? <>Place Order <ArrowRight size={20}/></> : <>Continue to Secure Payment <ArrowRight size={20}/></>}</button>
        <p className="co-small center">{method === 'cod' ? 'You will pay when your order is delivered.' : 'Payment is completed through our payment partner.'}</p>
      </div>

      <aside className="co-summary">
        <div className="co-sum-head"><h2>Order Summary</h2>{customId ? <Link href="/account?tab=custom">Custom request <ChevronRight size={16}/></Link> : <Link href="/cart">Edit bag <ChevronRight size={16}/></Link>}</div>
        {items.map(i => <div className="co-item" key={i.id}><div className="co-item-img"><Image src={photo(i.product)} alt={i.product.name} fill sizes="170px"/></div>
          <div><h3>{i.product.name}</h3><p>Size {i.variant.size} <span>/</span> {i.variant.colour} <span>/</span> Qty {i.quantity}</p><strong>{money(Number(i.product.price) * i.quantity)}</strong></div></div>)}
        <hr/>
        <div className="sum-line"><span>MRP</span><span>{money(mrp)}</span></div>
        <div className="sum-line"><span>Product discount</span><span>−{money(mrp - sub)}</span></div>
        <hr/>
        <div className="sum-line"><span>Subtotal</span><span>{money(sub)}</span></div>
        {quote && Number(quote.discount) > 0 && <div className="sum-line ok"><span>Promo ({coupon})</span><span>−{money(quote.discount)}</span></div>}
        <div className="sum-line"><span>Shipping</span><span>{!quote ? 'Pending address confirmation' : Number(quote.shipping) === 0 ? 'Free' : money(quote.shipping)}</span></div>
        <hr/>
        <div className="sum-total"><span>Estimated total</span><strong>{money(quote ? quote.total : sub)}</strong></div>
        <p className="co-small">Final payable amount is confirmed on the payment screen.</p>
        {!customId && <SavingZone applied={coupon && promoMsg?.ok ? coupon : ''} refreshKey={bag}
          onApply={async c => { try { const q = await api<Quote>('quote/', 'POST', {coupon: c, ...(itemIds.length ? {items: itemIds} : {})}); setQuote(q); write(COUPON_KEY, c); setCoupon(c); setPromoMsg({ok: true, text: `You save ${money(q.discount)}`}); } catch (e2) { setPromoMsg({ok: false, text: err(e2)}); } }}
          onRemove={async () => { write(COUPON_KEY, ''); setCoupon(''); setPromoMsg(null); try { setQuote(await api<Quote>('quote/', 'POST', itemIds.length ? {items: itemIds} : {})); } catch {} }} message={promoMsg}/>}
        <div className="co-help"><span className="co-help-icon"><Headphones size={22}/></span><div><strong>Need help with your order?</strong><p>We’re here to assist you.</p>
          {site.phone && <a href={`tel:+${site.phone.replace(/\D/g, '')}`}><Phone size={17}/> +{site.phone.replace(/\D/g, '')}</a>}
          {site.email && <a href={`mailto:${site.email}`}><Mail size={17}/> {site.email}</a>}</div></div>
      </aside>
    </div>}
  </div>;
}

