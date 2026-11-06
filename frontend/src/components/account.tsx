'use client';
import Image from 'next/image';
import Link from 'next/link';
import {useEffect, useState} from 'react';
import {useRouter, useSearchParams} from 'next/navigation';
import {Package, CalendarDays, UserRound, Heart, LogOut, MapPin, Check, CircleAlert, Truck, CreditCard, ArrowRight, X, ShoppingBag, FileDown, XCircle, Copy, Ruler, CreditCard as Card, RotateCcw} from 'lucide-react';
import {api, upload, authChanged, bagChanged, err} from '@/lib/client';
import {Order, Product, User, money, photo, discount} from '@/lib/types';
import {useWishlist} from '@/lib/wishlist';

type Appt = {id: string; starts_at: string | null; session_type: string; mode: string; status: string; occasion: string; source?: string; location?: string};
type FullOrder = Order & {address: Record<string, string>; payment_method: string; items: (Order['items'][number] & {slug?: string; image?: string})[]};
const STEPS = ['Placed', 'Confirmed', 'Shipped', 'Delivered'];
const STEP_OF: Record<string, number> = {pending: 0, cod: 1, paid: 1, processing: 1, shipped: 2, delivered: 3};
const LABEL: Record<string, string> = {pending: 'Awaiting payment', paid: 'Confirmed', cod: 'Confirmed · Cash on Delivery', processing: 'Being prepared', shipped: 'Shipped', delivered: 'Delivered',
  cancelled: 'Cancelled', expired: 'Payment not completed', refund_required: 'Cancelled · Refund pending', refunded: 'Cancelled · Refunded'};
const fmtDate = (d: string, time = false) => new Date(d).toLocaleString('en-IN', {day: 'numeric', month: 'short', year: 'numeric', ...(time ? {hour: 'numeric', minute: '2-digit'} : {})});
const initials = (u: User) => (u.name || u.email).split(/[\s@.]+/).filter(Boolean).slice(0, 2).map(w => w[0]?.toUpperCase()).join('');

function Tracker({status}: {status: string}) {
  if (!(status in STEP_OF)) return <p className={`ac-state ${status}`}><CircleAlert size={16}/>{LABEL[status] || status}</p>;
  const at = STEP_OF[status];
  return <ol className="ac-track" aria-label={`Order status: ${LABEL[status]}`}>{STEPS.map((s, i) =>
    <li key={s} className={i < at ? 'done' : i === at ? 'on' : ''}><span>{i <= at && (i < at || status === 'delivered') ? <Check size={13}/> : i + 1}</span>{s}</li>)}</ol>;
}

const RETURN_LABEL: Record<string, string> = {requested: 'Return requested', pickup_booked: 'Return pickup booked', in_transit: 'Return on its way to us', received: 'Return received', rejected: 'Return not approved'};

function CopyAwb({awb}: {awb: string}) {
  const [done, setDone] = useState(false);
  return <button type="button" className="ac-awb-copy" aria-label="Copy waybill number" onClick={async () => { try { await navigator.clipboard.writeText(awb); setDone(true); setTimeout(() => setDone(false), 1800); } catch {} }}>{done ? <Check size={15}/> : <Copy size={15}/>}</button>;
}

function OrderCard({o: initial}: {o: FullOrder}) {
  const [returning, setReturning] = useState(false), [rReason, setRReason] = useState('');
  const [o, setO] = useState(initial), [asking, setAsking] = useState(false), [reason, setReason] = useState(''), [busy, setBusy] = useState(false), [msg, setMsg] = useState('');
  const a = o.address || {};
  const ref = o.id.slice(0, 8).toUpperCase();
  async function requestReturn() {
    setBusy(true); setMsg('');
    try { const d = await api<FullOrder>(`orders/${o.id}/return/`, 'POST', {reason: rReason}); setO({...o, ...d}); setReturning(false); setMsg('Return requested. We’ll confirm and arrange a Delhivery pickup from your address.'); }
    catch (e) { setMsg(err(e)); } finally { setBusy(false); }
  }
  async function cancel() {
    setBusy(true); setMsg('');
    try { const d = await api<FullOrder>(`orders/${o.id}/cancel/`, 'POST', {reason}); setO({...o, ...d}); setAsking(false);
      setMsg(d.status === 'refunded' ? 'Your order is cancelled. The refund has been started to your original payment method.' : d.status === 'refund_required' ? 'Your order is cancelled. Our team will process your refund shortly.' : 'Your order is cancelled.'); }
    catch (e) { setMsg(err(e)); } finally { setBusy(false); }
  }
  return <article className="ac-order">
    <header><div><p className="ac-ref">Order #{o.id.slice(0, 8).toUpperCase()}</p><small>Placed on {fmtDate(o.created_at, true)}</small></div><span className={`ac-pill ${o.status}`}>{LABEL[o.status] || o.status}</span></header>
    <Tracker status={o.status}/>
    <div className="ac-order-body">
      <div className="ac-items">{o.items.map((i, n) => <div className="ac-item" key={n}>
        <div className="ac-item-img">{i.image ? <Image src={i.image} alt={i.name} fill sizes="80px"/> : <Package/>}</div>
        <div><p>{i.slug ? <Link href={`/products/${i.slug}`}>{i.name}</Link> : i.name}</p><small>Size {i.size} · {i.colour} · Qty {i.quantity}</small></div>
        <strong>{money(Number(i.unit_price) * i.quantity)}</strong></div>)}</div>
      <div className="ac-ship"><h4><MapPin size={16}/> Delivery address</h4>
        <p><strong>{a.name}</strong><br/>{a.line1}{a.line2 ? `, ${a.line2}` : ''}<br/>{a.city}, {a.state} {a.pincode}<br/>{a.phone}</p>
        <h4><CreditCard size={16}/> Payment</h4><p>{o.payment_method === 'cod' ? 'Cash on Delivery' : 'Paid online (Cashfree)'}{o.pay_with ? ` · ${o.pay_with.toUpperCase()}` : ''}</p>
        {o.note && <><h4>Note</h4><p>“{o.note}”</p></>}
        {['paid', 'cod', 'processing', 'shipped', 'delivered'].includes(o.status) && <div className="ac-awb">
          <span className="ac-awb-ico"><Truck size={18}/></span>
          <div><small>Delhivery waybill (AWB)</small>{o.awb ? <strong>{o.awb}</strong> : <em>Assigned once your parcel is booked</em>}</div>
          {o.awb && <CopyAwb awb={o.awb}/>}
        </div>}</div>
    </div>
    <footer><div className="ac-totals"><span>Subtotal {money(o.subtotal)}</span>{Number(o.discount) > 0 && <span>Discount −{money(o.discount)}</span>}<span>Shipping {Number(o.shipping) ? money(o.shipping) : 'Free'}</span><strong>Total {money(o.total)}</strong></div>
      <div className="ac-actions">
        {['paid', 'cod', 'processing', 'shipped', 'delivered'].includes(o.status) && <Link className="pd-btn-sm ac-track-btn" href={`/track?order=${ref}`}><Truck size={15}/> Track order</Link>}
        {!['pending', 'expired'].includes(o.status) && <a className="pd-btn-sm ac-inv-btn" href={`/api/orders/${o.id}/invoice/`} download><FileDown size={15}/> Download invoice</a>}
        {o.can_return && !returning && <button type="button" className="pd-btn-sm ac-return-btn" onClick={() => setReturning(true)}><RotateCcw size={15}/> Return order</button>}
        {o.can_cancel && !asking && <button type="button" className="pd-btn-sm ac-cancel-btn" onClick={() => setAsking(true)}><XCircle size={15}/> Cancel order</button>}
      </div>
      {o.status === 'pending' && <Link className="pd-btn-sm" href={`/payment/return?order=${o.id}`}>Check payment status</Link>}</footer>
    {returning && <div className="ac-cancel-box ac-return-box" role="group" aria-label="Return this order">
      <p><strong>Return order #{ref}?</strong> We’ll book a Delhivery pickup from your delivery address once your request is approved. Please keep the outfit unused with its tags.</p>
      <select value={rReason} onChange={e => setRReason(e.target.value)} aria-label="Reason for return"><option value="">Choose a reason</option>
        {['Size does not fit', 'Colour or design looks different', 'Damaged or defective item', 'Received the wrong item', 'Quality not as expected', 'Other'].map(r => <option key={r}>{r}</option>)}</select>
      <div><button type="button" className="pd-btn-sm ac-return-btn" disabled={busy || !rReason} onClick={requestReturn}>{busy ? 'Sending…' : 'Request return'}</button>
        <button type="button" className="pd-btn-sm" onClick={() => setReturning(false)}>Keep order</button></div></div>}
    {o.return_status && <div className="ac-return-status"><RotateCcw size={16}/><div><strong>{RETURN_LABEL[o.return_status] || o.return_status}</strong>
      <span>{o.return_reason}{o.return_awb ? ` · Return AWB ${o.return_awb}` : ''}{o.return_courier_status ? ` · ${o.return_courier_status}` : ''}</span>
      {o.return_status === 'received' && <span>Refund: {o.status === 'refunded' ? 'started to your original payment method.' : 'our team will contact you for your refund details.'}</span>}</div></div>}
    {asking && <div className="ac-cancel-box" role="group" aria-label="Cancel this order">
      <p><strong>Cancel order #{ref}?</strong> You can cancel until the parcel is picked up by Delhivery.{o.payment_method !== 'cod' ? ' Online payments are refunded to the original payment method.' : ''}</p>
      <select value={reason} onChange={e => setReason(e.target.value)} aria-label="Reason for cancelling"><option value="">Reason (optional)</option>
        {['Ordered by mistake', 'Found a better price', 'Delivery is too late', 'Want to change size or colour', 'Other'].map(r => <option key={r}>{r}</option>)}</select>
      <div><button type="button" className="pd-btn-sm ac-cancel-btn" disabled={busy} onClick={cancel}>{busy ? 'Cancelling…' : 'Yes, cancel order'}</button>
        <button type="button" className="pd-btn-sm" onClick={() => setAsking(false)}>Keep order</button></div></div>}
    {msg && <p className="ac-hint" role="status">{msg}</p>}
    {o.status === 'pending' && <p className="ac-hint">Payment is awaiting confirmation. Unpaid orders are released after 30 minutes. If you were charged, contact us with this order number before paying again.</p>}
    {o.cancelled_at && <p className="ac-hint">Cancelled on {fmtDate(o.cancelled_at, true)}{o.cancel_reason ? ` · ${o.cancel_reason}` : ''}.{o.status === 'refund_required' ? ' Our team will process your refund shortly.' : o.status === 'refunded' ? ' Refund started to your original payment method.' : ''}</p>}
    {o.status === 'refund_required' && !o.cancelled_at && <p className="ac-hint">Your payment arrived after the reservation closed. Our team will reconcile it — please contact us with this order number.</p>}
  </article>;
}

function Profile({user, onSaved}: {user: User; onSaved: (u: User) => void}) {
  const [msg, setMsg] = useState<{ok: boolean; text: string} | null>(null), [pwMsg, setPwMsg] = useState<{ok: boolean; text: string} | null>(null), [busy, setBusy] = useState('');
  return <div className="ac-settings">
    <form className="ac-card" onSubmit={async e => {
      e.preventDefault(); setBusy('p'); setMsg(null); const f = new FormData(e.currentTarget);
      try { const r = await api<{user: User}>('auth/me/', 'PATCH', {first_name: f.get('first_name'), last_name: f.get('last_name'), phone: f.get('phone'), marketing_opt_in: f.get('marketing') === 'on'}); onSaved(r.user); setMsg({ok: true, text: 'Your profile has been saved.'}); }
      catch (e2) { setMsg({ok: false, text: err(e2)}); } finally { setBusy(''); }
    }}>
      <h3>Personal details</h3>
      <div className="ac-form">
        <label>First name<input name="first_name" required defaultValue={user.first_name || ''} autoComplete="given-name"/></label>
        <label>Last name<input name="last_name" defaultValue={user.last_name || ''} autoComplete="family-name"/></label>
        <label>Email<input value={user.email} readOnly disabled/><small>Contact us to change your sign-in email.</small></label>
        <label>Mobile number<input name="phone" type="tel" defaultValue={user.phone || ''} placeholder="+919876543210" autoComplete="tel"/></label>
        <label className="ac-check"><input type="checkbox" name="marketing" defaultChecked={!!user.marketing_opt_in}/> Send me new arrivals and exclusive offers</label>
      </div>
      {msg && <p className={msg.ok ? 'pd-ok' : 'pd-err'}>{msg.ok ? <Check size={16}/> : <CircleAlert size={16}/>}{msg.text}</p>}
      <button className="pd-btn pd-btn-bag" disabled={busy === 'p'}>{busy === 'p' ? 'Saving…' : 'Save changes'}</button>
    </form>
    <form className="ac-card" onSubmit={async e => {
      e.preventDefault(); const form = e.currentTarget; const f = new FormData(form); setPwMsg(null);
      if (f.get('new') !== f.get('confirm')) { setPwMsg({ok: false, text: 'The new passwords do not match.'}); return; }
      setBusy('w');
      try { const r = await api<{message: string}>('auth/password/', 'POST', {current: f.get('current'), new: f.get('new')}); setPwMsg({ok: true, text: r.message}); form.reset(); }
      catch (e2) { setPwMsg({ok: false, text: err(e2)}); } finally { setBusy(''); }
    }}>
      <h3>Change password</h3>
      <div className="ac-form one">
        <label>Current password<input name="current" type="password" autoComplete="current-password"/><small>Leave empty if you signed up with WhatsApp.</small></label>
        <label>New password<input name="new" type="password" required minLength={10} autoComplete="new-password"/></label>
        <label>Confirm new password<input name="confirm" type="password" required minLength={10} autoComplete="new-password"/></label>
      </div>
      {pwMsg && <p className={pwMsg.ok ? 'pd-ok' : 'pd-err'}>{pwMsg.ok ? <Check size={16}/> : <CircleAlert size={16}/>}{pwMsg.text}</p>}
      <button className="pd-btn pd-btn-buy" disabled={busy === 'w'}>{busy === 'w' ? 'Updating…' : 'Update password'}</button>
    </form>
  </div>;
}

export function AccountPage({section}: {section?: 'orders'}) {
  const router = useRouter(), params = useSearchParams();
  const tab = section || (['appointments', 'profile', 'custom'].includes(params.get('tab') || '') ? params.get('tab')! : params.get('tab') === 'orders' ? 'orders' : 'profile');
  useEffect(() => { if (!section && params.get('tab') === 'orders') router.replace('/account/orders'); }, [section, params, router]);
  const [user, setUser] = useState<User | null>(null), [orders, setOrders] = useState<FullOrder[] | null>(null), [appts, setAppts] = useState<Appt[] | null>(null), [error, setError] = useState('');
  useEffect(() => {
    api<{user: User | null}>('auth/me/').then(async d => {
      if (!d.user) { router.replace(`/login?next=${encodeURIComponent(window.location.pathname + window.location.search)}`); return; }
      setUser(d.user);
      const [o, a] = await Promise.all([api<FullOrder[]>('orders/'), api<Appt[]>('appointments/mine/').catch(() => [])]);
      setOrders(o); setAppts(a);
    }).catch(e => setError(err(e)));
  }, [router]);
  const go = (t: string) => t === 'orders' ? router.push('/account/orders') : section ? router.push(`/account?tab=${t}`) : router.replace(`/account?tab=${t}`, {scroll: false});
  async function signOut() { try { await api('auth/logout/', 'POST', {}); bagChanged(); authChanged(); router.push('/'); router.refresh(); } catch (e) { setError(err(e)); } }

  if (!user) return <section className="ac-page"><p className="ac-loading">{error || 'Loading your account…'}</p></section>;
  const tabs: [string, string, React.ReactNode, number?][] = [['profile', 'Profile Settings', <UserRound key="p" size={18}/>], ['orders', 'Order History', <Package key="o" size={18}/>, orders?.length], ['appointments', 'Appointments', <CalendarDays key="a" size={18}/>, appts?.length], ['custom', 'Custom Requests', <Ruler key="c" size={18}/>]];
  return <section className="ac-page">
    <aside className="ac-side">
      <div className="ac-profile"><span className="ac-avatar">{initials(user)}</span>
        <div><h1>{user.first_name ? `Hello, ${user.first_name}` : 'Welcome back'}</h1><p>{user.email}</p>{user.phone && <p>{user.phone}</p>}{user.joined && <small>Member since {fmtDate(user.joined)}</small>}</div></div>
      {!user.first_name && <button type="button" className="ac-nudge" onClick={() => go('profile')}>Add your name to personalise your account <ArrowRight size={14}/></button>}
      <nav className="ac-nav">{tabs.map(([k, label, icon, n]) => <button key={k} type="button" className={tab === k ? 'on' : ''} aria-current={tab === k ? 'page' : undefined} onClick={() => go(k)}>{icon}{label}{typeof n === 'number' && n > 0 && <em>{n}</em>}</button>)}
        <Link href="/wishlist"><Heart size={18}/>Wishlist</Link>
        <button type="button" onClick={signOut} className="ac-out"><LogOut size={18}/>Sign Out</button></nav>
    </aside>
    <div className="ac-main">
      {error && <p className="pd-err">{error}</p>}
      {tab === 'orders' && <><h2>Order History</h2>{orders === null ? <p>Loading orders…</p> : !orders.length
        ? <div className="ac-empty"><ShoppingBag size={34}/><p>You haven’t placed an order yet.</p><Link href="/products" className="pd-btn pd-btn-bag">Start shopping</Link></div>
        : orders.map(o => <OrderCard key={o.id} o={o}/>)}</>}
      {tab === 'appointments' && <><h2>Appointments</h2>{appts === null ? <p>Loading…</p> : !appts.length
        ? <div className="ac-empty"><CalendarDays size={34}/><p>No appointments yet.</p><Link href="/appointment" className="pd-btn pd-btn-bag">Book a fitting</Link></div>
        : appts.map(a => <article key={a.id} className="ac-appt"><div><strong>{a.session_type === 'fitting' ? 'Fitting & Measurements' : 'Style Consultation'}</strong><small>{a.starts_at ? fmtDate(a.starts_at, true) : 'Date & time in your Calendly confirmation email'} · {a.mode === 'video' ? 'Video consultation' : 'At the studio'}{a.occasion ? ` · ${a.occasion}` : ''}</small>{a.location && (/^https?:/.test(a.location) ? <a className="underlink" href={a.location} target="_blank" rel="noopener noreferrer">Join video call</a> : <small>{a.location}</small>)}</div><span className={`ac-pill ${a.status}`}>{a.status}</span></article>)}</>}
      {tab === 'custom' && <><h2>Custom Requests</h2><CustomRequests/></>}
      {tab === 'profile' && <><h2>Profile Settings</h2><ProfilePhoto user={user} onSaved={setUser}/><Profile user={user} onSaved={setUser}/></>}
    </div>
  </section>;
}

function WishCard({p, onGone}: {p: Product; onGone: (id: number) => void}) {
  const [, toggle] = useWishlist(p.id);
  const off = discount(p);
  return <article className="wl-card">
    <Link href={`/products/${p.slug}`} className="wl-img"><Image src={photo(p)} alt={p.images[0]?.alt || p.name} fill sizes="(max-width:700px) 46vw, 23vw"/>{off > 0 && <span className="cp-badge">{off}% OFF</span>}</Link>
    <button type="button" className="wl-remove" aria-label={`Remove ${p.name} from wishlist`} onClick={async () => { try { await toggle(); onGone(p.id); } catch {} }}><X size={18}/></button>
    <div className="wl-info"><h3><Link href={`/products/${p.slug}`}>{p.name}</Link></h3>
      <p className="cp-price-line"><strong>{money(p.price)}</strong>{off > 0 && <del>{money(p.mrp)}</del>}</p>
      <Link href={`/products/${p.slug}`} className="pd-btn pd-btn-bag wl-btn"><ShoppingBag size={16}/> Choose size &amp; add</Link></div>
  </article>;
}

export function WishlistPage() {
  const router = useRouter();
  const [items, setItems] = useState<Product[] | null>(null);
  useEffect(() => {
    // Signed-out visitors go straight to sign in, then come back here.
    api<Product[]>('wishlist/').then(setItems).catch(() => router.replace(`/login?next=${encodeURIComponent('/wishlist')}`));
  }, [router]);
  return <section className="cp wl-page">
    <div className="wl-head"><div><p className="cp-eyebrow">Saved for later</p><h1>My Wishlist</h1></div>{items && items.length > 0 && <p>{items.length} {items.length === 1 ? 'style' : 'styles'} saved</p>}</div>
    {items === null ? <p className="wl-loading">Loading your wishlist…</p> : !items.length
      ? <div className="ac-empty"><Heart size={36}/><h2>Your wishlist is empty</h2><p>Tap the heart on any style to save it here.</p><Link className="pd-btn pd-btn-bag" href="/products">Explore styles</Link></div>
      : <div className="wl-grid">{items.map(p => <WishCard key={p.id} p={p} onGone={id => setItems(list => (list || []).filter(x => x.id !== id))}/>)}</div>}
  </section>;
}


/* ---------- Custom (made-to-measure) requests ---------- */
type CustomReq = {id: number; ref: string; product: {name: string; slug: string; image: string; price: string}; size: string; colour: string;
  measurements: Record<string, number | string>; quantity: number; note: string; status: string; price: string | null; total: string | null; admin_note: string; order: string; created_at: string};
const CR_LABEL: Record<string, string> = {requested: 'Requested', accepted: 'Accepted', rejected: 'Not possible', cancelled: 'Cancelled', ordered: 'Ordered'};
function CustomRequests() {
  const [list, setList] = useState<CustomReq[] | null>(null), [busy, setBusy] = useState(0), [error, setError] = useState('');
  useEffect(() => { api<CustomReq[]>('custom-requests/').then(setList).catch(e => setError(err(e))); }, []);
  async function cancel(r: CustomReq) {
    if (!window.confirm(`Cancel custom request #${r.ref}?`)) return;
    setBusy(r.id);
    try { const d = await api<CustomReq>(`custom-requests/${r.id}/cancel/`, 'POST', {}); setList(l => (l || []).map(x => x.id === r.id ? d : x)); } catch (e) { setError(err(e)); } finally { setBusy(0); }
  }
  if (error) return <p className="pd-err">{error}</p>;
  if (list === null) return <p>Loading…</p>;
  if (!list.length) return <div className="ac-empty"><Ruler size={34}/><p>No custom requests yet. Choose <strong>Custom Measurements</strong> on a product to request a made-to-measure outfit.</p><Link href="/products" className="pd-btn pd-btn-bag">Browse styles</Link></div>;
  return <div className="cr-list">{list.map(r => { const u = String(r.measurements.unit || 'cm'); return <article key={r.id} className="cr-card">
    <Link href={`/products/${r.product.slug}`} className="cr-img">{r.product.image && <Image src={r.product.image} alt={r.product.name} fill sizes="90px"/>}</Link>
    <div className="cr-main"><h3><Link href={`/products/${r.product.slug}`}>{r.product.name}</Link></h3><p>Request ID: #{r.ref}{r.quantity > 1 ? ` · Qty ${r.quantity}` : ''}</p><small>{fmtDate(r.created_at, true)}</small></div>
    <div className="cr-measure"><h4>Custom Measurements</h4><dl>{['bust', 'waist', 'hip', 'armhole'].map(k => <div key={k}><dt>{k[0].toUpperCase() + k.slice(1)}:</dt><dd>{r.measurements[k]}{u}</dd></div>)}</dl>
      {r.colour && <p className="cr-colour">Colour: <strong>{r.colour}</strong></p>}</div>
    <div className="cr-side"><span className={`cr-pill ${r.status}`}>{CR_LABEL[r.status] || r.status}</span>
      {r.price && r.status !== 'rejected' && <p className="cr-price">{money(r.total || r.price)}<small>{r.quantity > 1 ? ` (${money(r.price)} each)` : ''}</small></p>}
      {r.status === 'accepted' && <Link href={`/checkout?custom=${r.id}`} className="cr-pay"><Card size={16}/> Proceed to Payment</Link>}
      {r.status === 'ordered' && <Link href="/account/orders" className="pd-btn-sm">View order</Link>}
      {['requested', 'accepted'].includes(r.status) && <button type="button" className="cr-cancel" disabled={busy === r.id} onClick={() => cancel(r)}><X size={15}/> Cancel Request</button>}
      {r.status === 'requested' && <small className="cr-hint">We’ll confirm the price by email.</small>}
      {r.admin_note && <small className="cr-hint">“{r.admin_note}”</small>}</div>
  </article>; })}</div>;
}


/* ---------- Profile photo (shown in the header menu) ---------- */
function ProfilePhoto({user, onSaved}: {user: User; onSaved: (u: User) => void}) {
  const [busy, setBusy] = useState(false), [msg, setMsg] = useState<{ok: boolean; text: string} | null>(null);
  const initial = (user.first_name || user.name || user.email || '?').trim()[0]?.toUpperCase();
  async function pick(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]; e.target.value = '';
    if (!f) return;
    if (f.size > 3 * 1024 * 1024) return setMsg({ok: false, text: 'Please choose a photo up to 3 MB.'});
    setBusy(true); setMsg(null);
    try { const fd = new FormData(); fd.append('photo', f); const r = await upload<{user: User}>('auth/avatar/', fd); onSaved(r.user); authChanged(); setMsg({ok: true, text: 'Profile photo updated.'}); }
    catch (e2) { setMsg({ok: false, text: err(e2)}); } finally { setBusy(false); }
  }
  async function remove() {
    setBusy(true); setMsg(null);
    try { const r = await api<{user: User}>('auth/avatar/', 'DELETE'); onSaved(r.user); authChanged(); setMsg({ok: true, text: 'Profile photo removed.'}); }
    catch (e2) { setMsg({ok: false, text: err(e2)}); } finally { setBusy(false); }
  }
  return <div className="ac-photo">
    <span className="ac-photo-img">{user.avatar ? <img src={user.avatar} alt="Your profile photo" referrerPolicy="no-referrer"/> : initial}</span>
    <div><strong>Profile photo</strong><small>JPG, PNG or WebP, up to 3 MB. Shown in the menu at the top of the site.</small>
      <div className="ac-photo-btns"><label className="pd-btn-sm">{busy ? 'Saving…' : user.avatar ? 'Change photo' : 'Upload photo'}<input type="file" accept="image/jpeg,image/png,image/webp" onChange={pick} disabled={busy} hidden/></label>
        {user.avatar && <button type="button" className="pd-btn-sm" onClick={remove} disabled={busy}>Remove</button>}</div>
      {msg && <p className={msg.ok ? 'pd-ok' : 'pd-err'} role="status">{msg.text}</p>}</div>
  </div>;
}
