'use client';
import Image from 'next/image';
import Link from 'next/link';
import {useEffect, useState} from 'react';
import {useRouter} from 'next/navigation';
import {ArrowRight, Minus, Plus, Lock, ChevronDown, ShoppingBag, Check} from 'lucide-react';
import {api, bagChanged, err} from '@/lib/client';
import {Bag, Product, User, money, photo} from '@/lib/types';
import {SavingZone} from '@/components/saving-zone';

type Quote = {subtotal: string; discount: string; shipping: string; total: string};
export const COUPON_KEY = 'ar-coupon', NOTE_KEY = 'ar-note';
const read = (k: string) => { try { return localStorage.getItem(k) || ''; } catch { return ''; } };
const write = (k: string, v: string) => { try { if (v) localStorage.setItem(k, v); else localStorage.removeItem(k); } catch {} };

export function Steps({at}: {at: 1 | 2 | 3}) {
  return <ol className="bag-steps" aria-label="Checkout progress">{['Bag', 'Delivery', 'Payment'].map((s, i) =>
    <li key={s} className={i + 1 < at ? 'done' : i + 1 === at ? 'on' : ''} aria-current={i + 1 === at ? 'step' : undefined}><span>{i + 1 < at ? <Check size={14}/> : at === 3 ? i + 1 : ''}</span>{s}</li>)}</ol>;
}

export function BagPage({suggestions, swatches}: {suggestions: Product[]; swatches: Record<string, string>}) {
  const router = useRouter();
  const [bag, setBag] = useState<Bag | null>(null), [user, setUser] = useState<User | null>(null), [error, setError] = useState(''), [busy, setBusy] = useState(false), [info, setInfo] = useState('');
  const [code, setCode] = useState(''), [quote, setQuote] = useState<Quote | null>(null), [promoMsg, setPromoMsg] = useState<{ok: boolean; text: string} | null>(null);
  const [noteOn, setNoteOn] = useState(false), [note, setNote] = useState('');

  useEffect(() => {
    Promise.all([api<Bag>('cart/'), api<{user: User | null}>('auth/me/').catch(() => ({user: null}))]).then(([b, u]) => { setBag(b); setUser(u.user); }).catch(e => setError(err(e)));
    const c = read(COUPON_KEY), n = read(NOTE_KEY);
    if (c) setCode(c);
    if (n) { setNote(n); setNoteOn(true); }
  }, []);
  // Re-check a saved promo code whenever the bag changes.
  useEffect(() => { if (bag?.items.length && code && read(COUPON_KEY) === code) applyPromo(code, true); }, [bag]); // eslint-disable-line react-hooks/exhaustive-deps

  async function change(id: number, quantity?: number) {
    setBusy(true); setError('');
    try { setBag(await api<Bag>('cart/', quantity === undefined ? 'DELETE' : 'PATCH', {id, quantity})); bagChanged(); }
    catch (e) { setError(err(e)); } finally { setBusy(false); }
  }
  async function moveToWishlist(id: number, product: number) {
    if (!user) { router.push(`/login?next=${encodeURIComponent('/cart')}`); return; }
    try { await api('wishlist/', 'POST', {product}); await change(id); setInfo('Moved to your wishlist.'); } catch (e) { setError(err(e)); }
  }
  async function applyPromo(c = code, quiet = false) {
    const value = c.trim().toUpperCase(); if (!value) return;
    try { const q = await api<Quote>('quote/', 'POST', {coupon: value}); setQuote(q); write(COUPON_KEY, value); setCode(value); setPromoMsg({ok: true, text: `You save ${money(q.discount)}`}); }
    catch (e) { setQuote(null); write(COUPON_KEY, ''); if (!quiet) setPromoMsg({ok: false, text: err(e)}); else setPromoMsg(null); }
  }

  const items = bag?.items || [];
  const count = items.reduce((n, i) => n + i.quantity, 0);
  const mrp = items.reduce((n, i) => n + Math.max(Number(i.product.mrp), Number(i.product.price)) * i.quantity, 0);
  const subtotal = Number(bag?.subtotal || 0);
  const promo = quote ? Number(quote.discount) : 0;
  const ids = new Set(items.map(i => i.product.id));
  const also = suggestions.filter(p => !ids.has(p.id)).slice(0, 3);

  return <div className="cp bag-page">
    <div className="bag-top"><div><h1>Your Shopping Bag</h1><p>{count} item{count === 1 ? '' : 's'}</p></div><Steps at={1}/><Link href="/products" className="pd-link">Continue Shopping <ArrowRight size={14}/></Link></div>
    {error && <p className="pd-err bag-wrap" role="alert">{error}</p>}
    {!bag ? <p className="bag-wrap">Loading your bag…</p> : !items.length ? <div className="empty"><ShoppingBag size={35}/><h2>Your bag is empty.</h2><p>Find something beautiful for your next celebration.</p><Link className="button" href="/products">Discover the Collection <ArrowRight size={16}/></Link></div> :
    <div className="bag-grid bag-wrap">
      <div>
        {items.map(i => { const custom = Object.keys(i.measurements || {}).length > 0; const swatch = swatches[i.variant.colour.toLowerCase()];
          return <article className="bag-card" key={i.id}>
            <Link href={`/products/${i.product.slug}`} className="bag-card-img"><Image src={photo(i.product)} alt={i.product.name} fill sizes="240px"/></Link>
            <div className="bag-card-info">
              <h2><Link href={`/products/${i.product.slug}`}>{i.product.name}</Link></h2>
              <dl><div><dt>Size</dt><dd>{i.variant.size}</dd></div><div><dt>Colour</dt><dd>{i.variant.colour}{swatch && <span className="bag-swatch" style={{background: swatch}}/>}</dd></div><div><dt>Type</dt><dd>{custom ? 'Custom measurements' : 'Stitched'}</dd></div></dl>
              <p className="bag-price"><strong>{money(Number(i.product.price) * i.quantity)}</strong>{Number(i.product.mrp) > Number(i.product.price) && <del>{money(Number(i.product.mrp) * i.quantity)}</del>}</p>
              <div className="pd-qty"><button type="button" aria-label="Decrease quantity" disabled={busy || i.quantity <= 1} onClick={() => change(i.id, i.quantity - 1)}><Minus size={16}/></button><span>{i.quantity}</span><button type="button" aria-label="Increase quantity" disabled={busy || i.quantity >= i.variant.stock} onClick={() => change(i.id, i.quantity + 1)}><Plus size={16}/></button></div>
              <p className="bag-links"><Link href={`/products/${i.product.slug}`}>Edit size</Link><span>|</span><button type="button" onClick={() => moveToWishlist(i.id, i.product.id)}>Move to Wishlist</button><span>|</span><button type="button" disabled={busy} onClick={() => change(i.id)}>Remove</button></p>
            </div>
          </article>; })}
        {info && <p className="pd-ok"><Check size={16}/>{info}</p>}
        <label className="bag-note-toggle"><input type="checkbox" checked={noteOn} onChange={e => { setNoteOn(e.target.checked); if (!e.target.checked) { setNote(''); write(NOTE_KEY, ''); } }}/> Add an order note (optional)</label>
        {noteOn && <textarea className="bag-note" rows={3} maxLength={500} value={note} placeholder="e.g. gift wrapping, a preferred delivery time…" onChange={e => { setNote(e.target.value); write(NOTE_KEY, e.target.value); }}/>}
      </div>

      <aside className="bag-summary">
        <h2>Order Summary</h2>
        <div className="sum-line"><span>MRP</span><span>{money(mrp)}</span></div>
        <div className="sum-line"><span>Product discount</span><span>−{money(mrp - subtotal)}</span></div>
        <hr/>
        <div className="sum-line strong"><span>Subtotal</span><span>{money(subtotal)}</span></div>
        {promo > 0 && <div className="sum-line ok"><span>Promo ({code})</span><span>−{money(promo)}</span></div>}
        <div className="sum-line"><span>Shipping</span><span>Calculated at checkout</span></div>
        <hr/>
        <div className="sum-total"><span>Estimated total</span><strong>{money(subtotal - promo)}</strong></div>
        <p className="sum-small">Final total shown before payment</p>
        <SavingZone applied={quote && promo >= 0 && read(COUPON_KEY) ? code : ''} refreshKey={bag}
          onApply={c => applyPromo(c)} onRemove={() => { write(COUPON_KEY, ''); setQuote(null); setCode(''); setPromoMsg(null); }} message={promoMsg}/>
        <button type="button" className="pd-btn pd-btn-bag sum-cta" onClick={() => router.push(user ? '/checkout' : `/login?next=${encodeURIComponent('/checkout')}`)}>Continue to Checkout <ArrowRight size={18}/></button>
        <p className="sum-foot">{!user && <><Link href={`/login?next=${encodeURIComponent('/checkout')}`}>Sign in to continue securely</Link><span>|</span></>}<span className="sum-secure"><Lock size={15}/> Secure checkout</span></p>
      </aside>
    </div>}

    <section className="bag-fit"><div><h2>Not sure about your size?</h2><p>Speak with our team before you place your order.</p><div><Link href="/appointment" className="button">Book a Fitting</Link><Link href="/info/size-guide" className="button outline">Size Guide</Link></div></div>
      <div className="bag-fit-img"><Image src="/images/fitting.webp" alt="A stylist measuring a client" fill sizes="(max-width:800px) 100vw, 50vw"/></div></section>

    {also.length > 0 && <section className="bag-wrap bag-also"><h2>You may also love</h2><div className="bag-also-grid">{also.map(p =>
      <Link key={p.id} href={`/products/${p.slug}`} className="bag-also-card"><div><Image src={photo(p)} alt={p.name} fill sizes="(max-width:700px) 90vw, 30vw"/></div><h3>{p.name}</h3><span>View Dress <ArrowRight size={15}/></span></Link>)}</div></section>}
  </div>;
}
