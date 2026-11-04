'use client';
import Image from 'next/image';
import Link from 'next/link';
import {useEffect, useState} from 'react';
import {useRouter, useSearchParams} from 'next/navigation';
import {Package, CalendarDays, UserRound, Heart, LogOut, MapPin, Check, CircleAlert, Truck, CreditCard, ArrowRight, X, ShoppingBag, FileDown, XCircle} from 'lucide-react';
import {api, bagChanged, err} from '@/lib/client';
import {Order, Product, User, money, photo, discount} from '@/lib/types';
import {useWishlist} from '@/lib/wishlist';

type Appt = {id: string; starts_at: string; session_type: string; mode: string; status: string; occasion: string};
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

function OrderCard({o: initial}: {o: FullOrder}) {
  const [o, setO] = useState(initial), [asking, setAsking] = useState(false), [reason, setReason] = useState(''), [busy, setBusy] = useState(false), [msg, setMsg] = useState('');
  const a = o.address || {};
  const ref = o.id.slice(0, 8).toUpperCase();
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
        {['paid', 'cod', 'processing', 'shipped', 'delivered'].includes(o.status) && <><h4><Truck size={16}/> Shipment (Delhivery)</h4>
          <p>{o.awb ? <>Waybill (AWB) <strong>{o.awb}</strong>{o.courier_status ? ` · ${o.courier_status}` : ''}</> : 'Waybill number will appear here once your parcel is booked with Delhivery.'}</p></>}
        {o.awb && <>
          {!!o.tracking_events?.length && <ol className="ac-scans">{o.tracking_events.slice(0, 4).map((e, k) => <li key={k}><strong>{e.status}</strong>{e.location && ` · ${e.location}`}<small>{e.time ? new Date(e.time).toLocaleString('en-IN', {dateStyle: 'medium', timeStyle: 'short'}) : ''}{e.detail && ` — ${e.detail}`}</small></li>)}</ol>}</>}</div>
    </div>
    <footer><div className="ac-totals"><span>Subtotal {money(o.subtotal)}</span>{Number(o.discount) > 0 && <span>Discount −{money(o.discount)}</span>}<span>Shipping {Number(o.shipping) ? money(o.shipping) : 'Free'}</span><strong>Total {money(o.total)}</strong></div>
      <div className="ac-actions">
        {['paid', 'cod', 'processing', 'shipped', 'delivered'].includes(o.status) && <Link className="pd-btn-sm ac-track-btn" href={`/track?order=${ref}`}><Truck size={15}/> Track order</Link>}
        {!['pending', 'expired'].includes(o.status) && <a className="pd-btn-sm ac-inv-btn" href={`/api/orders/${o.id}/invoice/`} download><FileDown size={15}/> Download invoice</a>}
        {o.can_cancel && !asking && <button type="button" className="pd-btn-sm ac-cancel-btn" onClick={() => setAsking(true)}><XCircle size={15}/> Cancel order</button>}
      </div>
      {o.status === 'pending' && <Link className="pd-btn-sm" href={`/payment/return?order=${o.id}`}>Check payment status</Link>}</footer>
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
  const tab = section || (['appointments', 'profile'].includes(params.get('tab') || '') ? params.get('tab')! : params.get('tab') === 'orders' ? 'orders' : 'profile');
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
  async function signOut() { try { await api('auth/logout/', 'POST', {}); bagChanged(); router.push('/'); router.refresh(); } catch (e) { setError(err(e)); } }

  if (!user) return <section className="ac-page"><p className="ac-loading">{error || 'Loading your account…'}</p></section>;
  const tabs: [string, string, React.ReactNode, number?][] = [['profile', 'Profile Settings', <UserRound key="p" size={18}/>], ['orders', 'Order History', <Package key="o" size={18}/>, orders?.length], ['appointments', 'Appointments', <CalendarDays key="a" size={18}/>, appts?.length]];
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
        : appts.map(a => <article key={a.id} className="ac-appt"><div><strong>{a.session_type === 'fitting' ? 'Fitting & Measurements' : 'Style Consultation'}</strong><small>{a.starts_at ? fmtDate(a.starts_at, true) : ''} · {a.mode === 'video' ? 'Video consultation' : 'At the studio'}{a.occasion ? ` · ${a.occasion}` : ''}</small></div><span className={`ac-pill ${a.status}`}>{a.status}</span></article>)}</>}
      {tab === 'profile' && <><h2>Profile Settings</h2><Profile user={user} onSaved={setUser}/></>}
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
