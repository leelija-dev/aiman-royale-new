'use client';
import Image from 'next/image';
import Link from 'next/link';
import {useEffect, useRef, useState} from 'react';
import {useRouter} from 'next/navigation';
import {Heart, ShoppingBag, ArrowRight, Check, X, ZoomIn, Ruler, TicketPercent, ChevronDown, ChevronLeft, ChevronRight, Star, PencilLine, CircleAlert, Link2, Share2, Truck, Phone, Mail} from 'lucide-react';
import {rememberViewed} from '@/components/product-extras';
import {Bag, Product, money, photo, discount} from '@/lib/types';
import {api, bagChanged, err} from '@/lib/client';
import type {PinInfo} from '@/lib/types';
import {useWishlist, loginHere} from '@/lib/wishlist';
import {COUPON_KEY} from '@/components/bag';
import {CustomizeModal, type CustomPayload} from '@/components/customize-modal';

type Popup = {ok: true; title: string; detail: string; image: string} | {ok: false; title: string; detail: string};
type Reviews = {average: number | null; count: number; reviews: {name: string; rating: number; text: string; date: string}[]};
const FIELDS = ['bust', 'waist', 'hip', 'armhole'] as const;

function WhatsAppIcon() {
  return <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden fill="currentColor"><path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2Zm0 18.2a8.2 8.2 0 0 1-4.2-1.2l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2Zm4.5-6.1c-.2-.1-1.5-.7-1.7-.8-.2-.1-.4-.1-.6.1l-.8 1c-.1.2-.3.2-.5.1a6.7 6.7 0 0 1-3.3-2.9c-.3-.4.3-.4.8-1.4.1-.2 0-.3 0-.4l-.8-1.8c-.2-.5-.4-.4-.6-.4h-.5a1 1 0 0 0-.7.3 3 3 0 0 0-.9 2.2 5.2 5.2 0 0 0 1.1 2.7 11.8 11.8 0 0 0 4.5 4c1.7.7 2.3.8 3.2.6.5-.1 1.5-.6 1.7-1.2.2-.6.2-1.1.2-1.2-.1-.1-.3-.2-.5-.3Z"/></svg>;
}

export function ProductDetails({product: p, phone, deliveryMessage, swatches = {}, email = '', crumbs = [], paired = []}: {product: Product; phone: string; deliveryMessage: string; swatches?: Record<string, string>;
  email?: string; crumbs?: {label: string; href: string}[]; paired?: Product[]}) {
  const router = useRouter();
  const colours = [...new Set(p.variants.map(v => v.colour))];
  const firstInStock = p.variants.find(v => v.stock > 0);
  const [colour, setColour] = useState(firstInStock?.colour || colours[0] || '');
  const sizes = p.variants.filter(v => v.colour === colour);
  const [variantId, setVariantId] = useState(firstInStock?.id || 0);
  const variant = p.variants.find(v => v.id === variantId && v.colour === colour);
  const [image, setImage] = useState(0), [zoom, setZoom] = useState(false);
  const [qty, setQty] = useState(1), [type, setType] = useState<'stitched' | 'custom'>('stitched');
  const [m, setM] = useState<Record<string, string>>({unit: 'cm', bust: '', waist: '', hip: '', armhole: ''}), [mSaved, setMSaved] = useState(false), [mMsg, setMMsg] = useState('');
  const [busy, setBusy] = useState<'' | 'bag' | 'buy'>(''), [popup, setPopup] = useState<Popup | null>(null), [note, setNote] = useState('');
  const [saved, toggleWish] = useWishlist(p.id);
  const [inBag, setInBag] = useState<Set<number>>(new Set());
  const refreshBag = () => api<Bag>('cart/').then(b => setInBag(new Set(b.items.map(i => i.variant.id)))).catch(() => {});
  useEffect(() => { refreshBag(); window.addEventListener('bag-changed', refreshBag); return () => window.removeEventListener('bag-changed', refreshBag); }, []);
  const variantInBag = !!variant && inBag.has(variant.id);
  const [pin, setPin] = useState(''), [pinMsg, setPinMsg] = useState<{ok: boolean; text: string} | null>(null);
  const checkPin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!/^[1-9]\d{5}$/.test(pin)) return setPinMsg({ok: false, text: 'Please enter a valid 6-digit PIN code.'});
    setPinMsg({ok: true, text: 'Checking…'});
    try {
      const r = await api<PinInfo>(`delivery/pincode/${pin}/`);
      if (!r.checked) return setPinMsg({ok: true, text: deliveryMessage});
      setPinMsg(r.serviceable ? {ok: true, text: `Delivery available${r.city ? ` to ${r.city}` : ''} via Delhivery. ${r.cod ? 'Cash on Delivery available.' : 'Prepaid orders only.'} ${deliveryMessage}`.trim()}
        : {ok: false, text: 'Sorry, we can’t deliver to this PIN code yet. Message us on WhatsApp and we’ll help.'});
    } catch { setPinMsg({ok: true, text: deliveryMessage}); }
  };
  const [pageUrl, setPageUrl] = useState('');
  useEffect(() => setPageUrl(window.location.href.split('#')[0]), []);
  const measureRef = useRef<HTMLDivElement>(null), popupBtn = useRef<HTMLAnchorElement | HTMLButtonElement>(null);
  const off = discount(p);
  const maxQty = Math.max(1, variant?.stock || 1);
  const images = p.images.length ? p.images : [{id: 0, url: photo(p), alt: p.name}];

  useEffect(() => { if (popup) popupBtn.current?.focus(); }, [popup]);
  useEffect(() => { const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') { setPopup(null); setZoom(false); } }; window.addEventListener('keydown', esc); return () => window.removeEventListener('keydown', esc); }, []);
  useEffect(() => {
    if (!zoom) return;
    const n = Math.max(1, p.images.length);
    const keys = (e: KeyboardEvent) => { if (e.key === 'ArrowRight') setImage(x => (x + 1) % n); if (e.key === 'ArrowLeft') setImage(x => (x - 1 + n) % n); };
    window.addEventListener('keydown', keys); return () => window.removeEventListener('keydown', keys);
  }, [zoom, p.images.length]);
  useEffect(() => { if (qty > maxQty) setQty(maxQty); }, [maxQty, qty]);

  function pickColour(c: string) {
    setColour(c);
    const same = p.variants.find(v => v.colour === c && v.size === variant?.size && v.stock > 0) || p.variants.find(v => v.colour === c && v.stock > 0);
    setVariantId(same?.id || 0);
  }

  /** Puts the selection in the bag. Returns false (and shows why) if it could not. */
  /** Puts the selection in the bag. Returns the bag item id (or 0 and shows why) — Buy Now checks out just that item. */
  async function addToBag(buyNow = false): Promise<number> {
    if (!variant || !variant.stock) { setPopup({ok: false, title: 'Please choose a size', detail: 'Select an available size before adding this style to your bag.'}); return 0; }
    if (type === 'custom' && !mSaved) {
      setPopup({ok: false, title: 'Add your measurements', detail: 'You chose Custom Measurements. Enter and save your measurements below, or choose Stitched.'});
      measureRef.current?.scrollIntoView({behavior: 'smooth', block: 'center'});
      return 0;
    }
    try {
      // Buy Now: if this exact size/colour is already in the bag, set its quantity instead of adding more.
      const existing = buyNow ? (await api<Bag>('cart/')).items.find(i => i.variant.id === variant.id) : undefined;
      if (existing && type !== 'custom') await api('cart/', 'PATCH', {id: existing.id, quantity: qty});
      else await api('cart/', 'POST', {variant: variant.id, quantity: qty, measurements: type === 'custom' ? m : {}});
      bagChanged();
      const bag = await api<Bag>('cart/');
      setInBag(new Set(bag.items.map(i => i.variant.id)));
      return bag.items.find(i => i.variant.id === variant.id)?.id || -1;
    } catch (e) {
      setPopup({ok: false, title: 'Could not add to bag', detail: err(e)});
      return 0;
    }
  }

  const CUSTOM_DRAFT = 'ar-custom-draft';
  const [customDone, setCustomDone] = useState(false);
  const [customize, setCustomize] = useState(false);
  async function sendCustom(body: CustomPayload) {
    setBusy('bag');
    try {
      const me = await api<{user: unknown}>('auth/me/').catch(() => ({user: null}));
      if (!me.user) { try { localStorage.setItem(CUSTOM_DRAFT, JSON.stringify({slug: p.slug, ...body})); } catch {} router.push(loginHere()); return; }
      await api('custom-requests/', 'POST', {product: p.slug, variant: body.variant || undefined, measurements: body.m, options: body.options, quantity: body.qty});
      try { localStorage.removeItem(CUSTOM_DRAFT); } catch {}
      setCustomize(false); setLastCustom(body); setCustomDone(true);
    } catch (e) { setPopup({ok: false, title: 'Could not send your request', detail: err(e)}); }
    finally { setBusy(''); }
  }
  const [lastCustom, setLastCustom] = useState<CustomPayload | null>(null);
  // Came back from sign-in with a custom request started: send it now.
  useEffect(() => {
    let d: (CustomPayload & {slug: string}) | null = null;
    try { d = JSON.parse(localStorage.getItem(CUSTOM_DRAFT) || 'null'); } catch {}
    if (d && d.slug === p.slug && d.m) { setType('custom'); api<{user: unknown}>('auth/me/').then(r => { if (r.user) sendCustom(d!); }).catch(() => {}); }
  }, [p.slug]); // eslint-disable-line react-hooks/exhaustive-deps

  async function onAdd() {
    setBusy('bag');
    if (await addToBag()) setPopup({ok: true, title: 'Added to your bag', detail: `${p.name} · Size ${variant!.size} · ${colour} · Qty ${qty}`, image: images[0].url});
    setBusy('');
  }

  async function onBuyNow() {
    setBusy('buy');
    const id = await addToBag(true);
    if (id) {
      const me = await api<{user: unknown}>('auth/me/').catch(() => ({user: null}));
      // Use the size/colour (variant), not the bag line: signing in moves the bag and gives lines new ids.
      const next = id > 0 && variant ? `/checkout?variant=${variant.id}&qty=${qty}` : '/checkout';
      // Not signed in: sign in (or create an account) first, then come straight back to checkout.
      router.push(me.user ? next : `/login?next=${encodeURIComponent(next)}`);
      return;
    }
    setBusy('');
  }

  async function onWish() {
    try {
      const r = await toggleWish();
      if (r === 'login') router.push(loginHere());
      else setNote(r === 'added' ? 'Saved to your wishlist.' : 'Removed from your wishlist.');
    } catch (e) { setNote(err(e)); }
  }

  function saveMeasurements() {
    const bad = FIELDS.find(k => { const n = Number(m[k]); return !m[k] || !(n >= 5 && n <= 250); });
    if (bad) { setMMsg(`Please enter your ${bad} (between 5 and 250 ${m.unit}).`); return; }
    setMSaved(true); setType('custom'); setMMsg('Saved. These measurements will be added to this style when you add it to your bag.');
  }

  const origin = pageUrl ? new URL(pageUrl).origin : '';
  const absImage = images[image]?.url ? (images[image].url.startsWith('http') ? images[image].url : origin + images[image].url) : '';
  const waText = [
    "Hello Aiman Royale, I'd like to order:",
    `*${p.name}*`,
    `Price: ${money(Number(p.price) * qty)}${off > 0 ? ` (MRP ${money(Number(p.mrp) * qty)}, ${off}% off)` : ''}${qty > 1 ? ` for ${qty} pieces` : ''}`,
    `Size: ${variant?.size || 'not selected'} · Colour: ${colour} · Qty: ${qty}`,
    `Type: ${type === 'custom' ? `Custom measurements${mSaved ? ` (bust ${m.bust}, waist ${m.waist}, hip ${m.hip}, armhole ${m.armhole} ${m.unit})` : ''}` : 'Stitched'}`,
    absImage && `Photo: ${absImage}`,
    `Product link: ${pageUrl}`,
  ].filter(Boolean).join('\n');
  const waHref = `https://wa.me/${phone.replace(/\D/g, '')}?text=${encodeURIComponent(waText)}`;

  const ready = p.variants.some(v => v.stock > 0);
  const tags = [p.custom_fit && 'Custom-fit', ready && 'Ready to Ship', off > 0 && `${off}% Off`, ...p.occasions.slice(0, 2)].filter(Boolean) as string[];
  const digits = phone.replace(/\D/g, '');
  const stylistHref = digits ? `https://wa.me/${digits}?text=${encodeURIComponent(`Hello Aiman Royale, I'd like to speak to a stylist about ${p.name}.\n${pageUrl}`)}` : '/appointment';
  const eta = (() => { const d = new Date(); d.setDate(d.getDate() + 10); return d.toLocaleDateString('en-IN', {weekday: 'short', day: 'numeric', month: 'short'}); })();
  const mainBtn = useRef<HTMLDivElement>(null), [showBar, setShowBar] = useState(false);
  useEffect(() => {
    const el = mainBtn.current; if (!el || typeof IntersectionObserver === 'undefined') return;
    const o = new IntersectionObserver(([e]) => setShowBar(!e.isIntersecting && e.boundingClientRect.top < 0)); o.observe(el); return () => o.disconnect();
  }, []);
  // Remember this product for "Recently Viewed".
  useEffect(() => { rememberViewed({slug: p.slug, name: p.name, price: p.price, mrp: p.mrp, image: images[0]?.url || ''}); }, [p.slug]); // eslint-disable-line react-hooks/exhaustive-deps
  const addButton = (cls = '') => type === 'custom'
    ? <button type="button" className={`pd-btn pd-btn-bag ${cls}`} disabled={!!busy} onClick={() => setCustomize(true)}><Ruler size={18}/>Customize &amp; Send Request</button>
    : variantInBag ? <Link href="/cart" className={`pd-btn pd-btn-bag pd-go-bag ${cls}`}><ShoppingBag size={18}/>Go to Bag <ArrowRight size={16}/></Link>
    : <button type="button" className={`pd-btn pd-btn-bag ${cls}`} disabled={!!busy} onClick={onAdd}>{busy === 'bag' ? 'Adding…' : 'Add To Cart'}</button>;

  return <>
    <div className="az-pd">
      <div className="az-gal">
        <div className={`az-shots${images.length === 1 ? ' one' : images.length % 2 ? ' odd' : ''}`}>{images.map((im, i) => <button key={im.id + '-' + i} type="button" className="az-shot" aria-label={`Zoom photo ${i + 1}`} onClick={() => { setImage(i); setZoom(true); }}>
          <Image src={im.url} alt={im.alt || p.name} fill priority={i < 2} sizes="(max-width:800px) 88vw, 29vw" quality={88}/><span className="az-zoom" aria-hidden><ZoomIn size={18}/></span></button>)}</div>
        {crumbs.length > 0 && <nav className="az-crumbs" aria-label="Breadcrumb">{crumbs.map((c, i) => <span key={c.href + i}>{i > 0 && <i aria-hidden> / </i>}{i < crumbs.length - 1 ? <Link href={c.href}>{c.label}</Link> : <span aria-current="page">{c.label}</span>}</span>)}</nav>}
      </div>

      <div className="az-panel">
        {tags.length > 0 && <div className="az-pills">{tags.map(t => <span key={t}>{t}</span>)}</div>}
        <Link href="/products" className="az-brand">Aiman Royale <ChevronRight size={18}/></Link>
        <h1 className="az-name">{p.name}</h1>
        <div className="az-price"><strong>{money(p.price)}</strong>{off > 0 && <><del>{money(p.mrp)}</del><em>({off}% OFF)</em></>}</div>
        <p className="az-tax">(inclusive of all taxes)</p>

        {colours.length > 0 && <div className="az-block"><p className="pd-label">Colour: <span>{colour}</span></p>
          <div className="pd-colours">{colours.map(c => <button type="button" key={c} aria-label={c} aria-pressed={c === colour} className={c === colour ? 'on' : ''} onClick={() => pickColour(c)}><span style={{background: swatches[c.toLowerCase()] || COLOUR_HEX[c.toLowerCase()] || '#b9aca3'}}/></button>)}</div></div>}

        {p.custom_fit && <div className="az-block"><p className="pd-label">Select Type</p>
          <div className="pd-options"><button type="button" className={type === 'stitched' ? 'on' : ''} aria-pressed={type === 'stitched'} onClick={() => setType('stitched')}>Stitched</button>
            <button type="button" className={type === 'custom' ? 'on' : ''} aria-pressed={type === 'custom'} onClick={() => { setType('custom'); setCustomize(true); }}>Custom Measurements</button></div></div>}

        <div className="az-block">
          <div className="pd-row"><p className="pd-label">Select size</p><Link href="/info/size-guide" className="pd-size-guide"><Ruler size={15}/> Size guide</Link></div>
          <div className="pd-sizes">{sizes.map(v => <button type="button" key={v.id} disabled={!v.stock} aria-pressed={variant?.id === v.id} className={variant?.id === v.id ? 'on' : ''} onClick={() => setVariantId(v.id)} title={v.stock ? '' : 'Out of stock'}>{v.size}</button>)}</div>
        </div>

        <label className="az-qty">Qty <select value={qty} onChange={e => setQty(Number(e.target.value))} aria-label="Quantity">{Array.from({length: Math.min(maxQty, 10)}, (_, i) => i + 1).map(n => <option key={n} value={n}>{n}</option>)}</select></label>

        <div className="az-actions" ref={mainBtn}>
          {addButton()}
          <a className="pd-btn az-stylist" href={stylistHref} target={digits ? '_blank' : undefined} rel="noopener noreferrer">Speak To Stylist</a>
        </div>
        {type === 'custom' ? <p className="pd-custom-note">Our team checks your measurements and confirms the price. You pay once it’s accepted — from My Account → Custom Requests.</p>
          : <button type="button" className="pd-btn az-buy" disabled={!!busy} onClick={onBuyNow}>{busy === 'buy' ? 'Please wait…' : <>Buy Now <ArrowRight size={17}/></>}</button>}
        <div className="az-minor">
          <button type="button" className={saved ? 'on' : ''} aria-pressed={saved} onClick={onWish}><Heart size={17} fill={saved ? 'currentColor' : 'none'}/>{saved ? 'Wishlisted' : 'Add to Wishlist'}</button>
          <a href={waHref} target="_blank" rel="noopener noreferrer"><WhatsAppIcon/>Order on WhatsApp</a>
        </div>
        <p className="pd-note" role="status">{note}</p>

        <div className="az-delivery">
          <p className="pd-label">Delivery &amp; Services</p>
          <form onSubmit={checkPin}>
            <input value={pin} onChange={e => setPin(e.target.value.replace(/\D/g, '').slice(0, 6))} inputMode="numeric" placeholder="Enter PIN code" aria-label="PIN code"/><button className="az-check">Check</button>
          </form>
          {pinMsg ? <p className={pinMsg.ok ? 'pd-ok' : 'pd-err'}>{pinMsg.ok ? <Check size={16}/> : <CircleAlert size={16}/>}{pinMsg.text}</p>
            : <p className="az-eta"><Truck size={16}/> Estimated delivery by <strong>{eta}</strong></p>}
        </div>

        <div className="az-confidence"><p className="pd-label">Shop with Confidence</p>
          <ul>{['100% Authentic Products', 'Secure Payments', 'Easy Returns', 'Custom Fitting Available', 'Quality Checked', 'Pan-India Delivery'].map(x => <li key={x}><Check size={15}/>{x}</li>)}</ul></div>

        <ProductCoupons/>

        <div className="az-acc">
          <details open><summary>Product Details<ChevronDown size={18}/></summary><div>
            {p.description && <p>{p.description}</p>}
            <dl>{[['Colour', colour], ['Fabric', p.fabric], ['Fit', p.fit], ['Includes', p.includes]].filter(([, v]) => v).map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl></div></details>
          <details><summary>Measurements &amp; Fit<ChevronDown size={18}/></summary><div><p>Choose <strong>Stitched</strong> for our standard sizes, or <strong>Custom Measurements</strong> to have this style made to your bust, waist, hip and armhole measurements. Our team confirms measurements before stitching.</p><Link href="/info/size-guide" className="pd-link">Open the size guide <ArrowRight size={14}/></Link></div></details>
          <details><summary>Care<ChevronDown size={18}/></summary><div><p>{p.care || 'Professional dry clean recommended.'}</p></div></details>
          <details><summary>Shipping &amp; Returns<ChevronDown size={18}/></summary><div><p>{deliveryMessage}</p><Link href="/info/shipping" className="pd-link">Shipping policy <ArrowRight size={14}/></Link> <Link href="/info/returns" className="pd-link">Return &amp; refund policy <ArrowRight size={14}/></Link></div></details>
        </div>

        <div className="az-support"><p className="pd-label">Customer Support</p>
          <div>{digits && <a href={`https://wa.me/${digits}`} target="_blank" rel="noopener noreferrer"><WhatsAppIcon/> Chat with us</a>}
            {digits && <a href={`tel:+${digits}`}><Phone size={16}/> +{digits}</a>}
            {email && <a href={`mailto:${email}`}><Mail size={16}/> Mail us</a>}</div></div>

        <ShareBar name={p.name} url={pageUrl}/>

        {paired.length > 0 && <div className="az-paired"><p className="pd-label">Perfectly Paired</p>
          <div className="az-paired-row">{paired.map(r => <Link key={r.id} href={`/products/${r.slug}`} className="az-paired-card"><span><Image src={photo(r)} alt="" fill sizes="140px"/></span><strong>{r.name}</strong><em>{money(r.price)}</em></Link>)}</div></div>}
      </div>
    </div>

    {p.custom_fit && <div className="pd-measure pd-measure-cta" ref={measureRef} id="measurements">
      <div><h2>Custom Measurements option</h2><p>Made personal, with your measurements — choose a size, add your measurements and design changes. Our team confirms the price before you pay.</p></div>
      <button type="button" className="pd-btn pd-btn-bag" onClick={() => { setType('custom'); setCustomize(true); }}><Ruler size={17}/> Customize this outfit</button>
    </div>}
    {customize && <CustomizeModal p={p} phone={phone} colour={colour} busy={busy === 'bag'} onClose={() => setCustomize(false)} onSend={sendCustom}/>}

    <ReviewsBlock slug={p.slug} section/>

    <div className={showBar ? 'az-bar show' : 'az-bar'} aria-hidden={!showBar}>
      <Image src={images[0].url} alt="" width={44} height={58}/>
      <div><strong>{p.name}</strong><span>{money(p.price)}</span></div>
      {addButton('az-bar-btn')}
    </div>

    {customDone && <div className="pd-modal" role="dialog" aria-modal="true" aria-labelledby="pd-custom-title" onClick={e => { if (e.target === e.currentTarget) setCustomDone(false); }}>
      <div className="pd-modal-box ok"><button type="button" className="pd-modal-close" aria-label="Close" onClick={() => setCustomDone(false)}><X size={20}/></button>
        <div className="pd-modal-icon"><Check size={28}/></div><h2 id="pd-custom-title">Custom request sent</h2>
        <div className="pd-modal-item"><Image src={images[0].url} alt="" width={64} height={84}/><p>{p.name} · {colour}{lastCustom && <><br/>{Object.entries(lastCustom.m).filter(([k]) => k !== 'unit').map(([k, v]) => `${k.replace('_', ' ')} ${v}`).join(' · ')} {lastCustom.m.unit}</>}</p></div>
        <p>We’ll review your measurements and confirm the price by email. Once accepted, pay from My Account.</p>
        <div className="pd-modal-actions"><Link href="/account?tab=custom" className="pd-btn pd-btn-bag">View my requests <ArrowRight size={17}/></Link>
          <button type="button" className="pd-modal-link" onClick={() => setCustomDone(false)}>Continue shopping</button></div></div></div>}

    {popup && <div className="pd-modal" role="dialog" aria-modal="true" aria-labelledby="pd-modal-title" onClick={e => { if (e.target === e.currentTarget) setPopup(null); }}>
      <div className={popup.ok ? 'pd-modal-box ok' : 'pd-modal-box bad'}>
        <button type="button" className="pd-modal-close" aria-label="Close" onClick={() => setPopup(null)}><X size={20}/></button>
        <div className="pd-modal-icon">{popup.ok ? <Check size={28}/> : <CircleAlert size={28}/>}</div>
        <h2 id="pd-modal-title">{popup.title}</h2>
        {popup.ok ? <div className="pd-modal-item"><Image src={popup.image} alt="" width={64} height={84}/><p>{popup.detail}</p></div> : <p>{popup.detail}</p>}
        {popup.ok ? <div className="pd-modal-actions"><Link href="/checkout" className="pd-btn pd-btn-bag" ref={popupBtn as React.Ref<HTMLAnchorElement>}>Checkout <ArrowRight size={17}/></Link>
          <Link href="/cart" className="pd-btn pd-btn-buy">View Bag</Link>
          <button type="button" className="pd-modal-link" onClick={() => setPopup(null)}>Continue shopping</button></div>
          : <div className="pd-modal-actions"><button type="button" className="pd-btn pd-btn-bag" ref={popupBtn as React.Ref<HTMLButtonElement>} onClick={() => setPopup(null)}>OK</button></div>}
      </div>
    </div>}

    {zoom && <div className="pd-lightbox" role="dialog" aria-modal="true" aria-label={`Photo ${image + 1} of ${images.length}`} onClick={e => { if (e.target === e.currentTarget) setZoom(false); }}>
      <button type="button" className="pd-modal-close" aria-label="Close" onClick={() => setZoom(false)}><X size={24}/></button>
      <div className="pd-lb-img" onClick={() => setZoom(false)}><Image key={images[image]?.url} priority src={images[image]?.url} alt={images[image]?.alt || p.name} fill sizes="100vw" quality={92}/></div>
      {images.length > 1 && <>
        <button type="button" className="pd-lb-nav prev" aria-label="Previous photo" onClick={() => setImage((image - 1 + images.length) % images.length)}><ChevronLeft size={28}/></button>
        <button type="button" className="pd-lb-nav next" aria-label="Next photo" onClick={() => setImage((image + 1) % images.length)}><ChevronRight size={28}/></button>
        <div className="pd-lb-thumbs">{images.map((im, k) => <button key={im.id + '-' + k} type="button" aria-label={`Show photo ${k + 1}`} aria-pressed={k === image} className={k === image ? 'on' : ''} onClick={() => setImage(k)}><Image src={im.url} alt="" width={60} height={80}/></button>)}</div>
        <p className="pd-lb-count">{image + 1} / {images.length}</p></>}
    </div>}
  </>;
}

function Stars({value, size = 16}: {value: number; size?: number}) {
  return <span className="pd-stars" aria-label={`${value} out of 5`}>{[1, 2, 3, 4, 5].map(i => <Star key={i} size={size} fill={i <= Math.round(value) ? 'currentColor' : 'none'}/>)}</span>;
}

function ReviewsBlock({slug, section = false}: {slug: string; section?: boolean}) {
  const router = useRouter();
  const [data, setData] = useState<Reviews | null>(null), [open, setOpen] = useState(false), [rating, setRating] = useState(0), [text, setText] = useState(''), [msg, setMsg] = useState(''), [busy, setBusy] = useState(false);
  const DRAFT = 'ar-review-draft';
  useEffect(() => {
    api<Reviews>(`products/${slug}/reviews/`).then(setData).catch(() => setData({average: null, count: 0, reviews: []}));
    // Came back from sign-in with a review typed before: save it now.
    if (!section) return;
    let draft: {slug: string; rating: number; text: string} | null = null;
    try { draft = JSON.parse(localStorage.getItem(DRAFT) || 'null'); } catch {}
    if (!draft || draft.slug !== slug) return;
    api<{message: string}>(`products/${slug}/reviews/`, 'POST', {rating: draft.rating, text: draft.text})
      .then(r => { try { localStorage.removeItem(DRAFT); } catch {} setMsg(r.message); document.getElementById('reviews')?.scrollIntoView({behavior: 'smooth', block: 'center'}); })
      .catch(() => { setRating(draft!.rating); setText(draft!.text); setOpen(true); }); // still signed out: keep the draft in the form
  }, [slug, section]);
  async function submit(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setMsg('');
    try { const r = await api<{message: string}>(`products/${slug}/reviews/`, 'POST', {rating, text}); setMsg(r.message); setOpen(false); setText(''); setRating(0); try { localStorage.removeItem(DRAFT); } catch {} }
    catch (e2) {
      const m = err(e2);
      if (/sign in/i.test(m)) { try { localStorage.setItem(DRAFT, JSON.stringify({slug, rating, text})); } catch {} router.push(`/login?next=${encodeURIComponent(`/products/${slug}#reviews`)}`); }
      else setMsg(m);
    }
    finally { setBusy(false); }
  }
  return <section className={section ? 'pd-reviews pd-section' : 'pd-reviews'} id={section ? 'reviews' : undefined}>
    <div className="pd-reviews-head"><div><h2>Customer Reviews</h2>
      {data && (data.count ? <p><Stars value={data.average || 0}/> {data.average} out of 5 · {data.count} review{data.count === 1 ? '' : 's'}</p> : <p>No reviews yet. Be the first to share your experience.</p>)}</div>
      <button type="button" className="pd-btn-outline" onClick={() => setOpen(!open)}><PencilLine size={17}/> Write a Review</button></div>
    {open && <form className="pd-review-form" onSubmit={submit}>
      <div className="pd-rate" role="radiogroup" aria-label="Your rating">{[1, 2, 3, 4, 5].map(i => <button type="button" key={i} role="radio" aria-checked={rating === i} aria-label={`${i} star${i > 1 ? 's' : ''}`} onClick={() => setRating(i)}><Star size={26} fill={i <= rating ? 'currentColor' : 'none'}/></button>)}</div>
      <textarea value={text} onChange={e => setText(e.target.value)} rows={4} placeholder="Tell us about the fit, fabric and how it felt to wear." aria-label="Your review" minLength={10} required/>
      <button className="pd-btn pd-btn-bag" disabled={busy || !rating}>{busy ? 'Sending…' : 'Submit Review'}</button></form>}
    {msg && <p className="pd-ok pd-review-ok" role="status"><Check size={16}/>{msg}</p>}
    {data?.reviews.map((r, i) => <article key={i} className="pd-review"><Stars value={r.rating} size={14}/><p>{r.text}</p><small>{r.name} · {new Date(r.date).toLocaleDateString('en-IN', {day: 'numeric', month: 'short', year: 'numeric'})}</small></article>)}
  </section>;
}

// Fallback swatch colours for common names; the colour filter list in admin (Colours) is the source of truth on listing pages.
const COLOUR_HEX: Record<string, string> = {maroon: '#6b1426', 'rani pink': '#d6246e', rani: '#c71f63', 'rose gold': '#c9877d', copper: '#b8642f', wine: '#5c0f2e', purple: '#4b2a7a',
  green: '#3f6b4a', navy: '#24315e', red: '#b3202a', pink: '#e48aa6', beige: '#d9c4a5', white: '#f4f1ea', black: '#1f1a18', ivory: '#efe6d2', gold: '#c9a54c', mouse: '#9b8f86', teal: '#1f6f6b'};


/* ---------- Coupons: active offers with Apply; the chosen code is used at checkout ---------- */
type CouponInfo = {code: string; percent: number; minimum: string; description: string; expires_at: string | null};
function ProductCoupons() {
  const [list, setList] = useState<CouponInfo[]>([]), [applied, setApplied] = useState(''), [code, setCode] = useState(''), [msg, setMsg] = useState<{ok: boolean; text: string} | null>(null);
  useEffect(() => {
    api<CouponInfo[]>('coupons/').then(setList).catch(() => {});
    try { setApplied(localStorage.getItem(COUPON_KEY) || ''); } catch {}
  }, []);
  const save = (c: string) => { try { localStorage.setItem(COUPON_KEY, c); } catch {} setApplied(c); setMsg({ok: true, text: `${c} applied — the discount will be taken off at checkout.`}); };
  const remove = () => { try { localStorage.removeItem(COUPON_KEY); } catch {} setApplied(''); setMsg(null); };
  async function apply(e: React.FormEvent) {
    e.preventDefault();
    const c = code.trim().toUpperCase(); if (!c) return;
    try { const r = await api<{valid: boolean; code?: string; message?: string}>(`coupons/check/?code=${encodeURIComponent(c)}`); if (r.valid) { save(r.code!); setCode(''); } else setMsg({ok: false, text: r.message || 'Invalid coupon.'}); }
    catch (e2) { setMsg({ok: false, text: err(e2)}); }
  }
  return <div className="pd-coupons">
    <p className="pd-label"><TicketPercent size={18}/> Available offers</p>
    {list.length > 0 && <ul>{list.map(c => <li key={c.code} className={applied === c.code ? 'on' : ''}>
      <div><strong>{c.code}</strong><span>{c.description || `${c.percent}% off`}{Number(c.minimum) > 0 ? ` · on orders above ${money(c.minimum)}` : ''}</span>
        {c.expires_at && <small>Valid till {new Date(c.expires_at).toLocaleDateString('en-IN', {day: 'numeric', month: 'short', year: 'numeric'})}</small>}</div>
      {applied === c.code ? <button type="button" className="pd-cp-btn on" onClick={remove}><Check size={14}/> Applied</button> : <button type="button" className="pd-cp-btn" onClick={() => save(c.code)}>Apply</button>}</li>)}</ul>}
    <form onSubmit={apply}><input value={code} onChange={e => setCode(e.target.value)} placeholder="Enter coupon code" aria-label="Coupon code"/><button className="pd-btn-sm">Apply</button></form>
    {applied && !list.some(c => c.code === applied) && <p className="pd-ok"><Check size={16}/>{applied} applied. <button type="button" className="pd-link-btn" onClick={remove}>Remove</button></p>}
    {msg && <p className={msg.ok ? 'pd-ok' : 'pd-err'}>{msg.ok ? <Check size={16}/> : <CircleAlert size={16}/>}{msg.text}</p>}
  </div>;
}

/* ---------- Share: WhatsApp, Telegram, Facebook, copy link ---------- */
function ShareBar({name, url}: {name: string; url: string}) {
  const [copied, setCopied] = useState(false);
  const text = `${name} — Aiman Royale`;
  const u = encodeURIComponent(url), t = encodeURIComponent(text);
  async function copy() {
    try { await navigator.clipboard.writeText(url); }
    catch { const i = document.createElement('input'); i.value = url; document.body.appendChild(i); i.select(); document.execCommand('copy'); i.remove(); }
    setCopied(true); setTimeout(() => setCopied(false), 2000);
  }
  return <div className="pd-share"><p className="pd-label"><Share2 size={17}/> Share</p>
    <div>
      <a className="sh-wa" href={`https://wa.me/?text=${encodeURIComponent(`${text}\n${url}`)}`} target="_blank" rel="noopener noreferrer" aria-label="Share on WhatsApp"><WhatsAppIcon/></a>
      <a className="sh-tg" href={`https://t.me/share/url?url=${u}&text=${t}`} target="_blank" rel="noopener noreferrer" aria-label="Share on Telegram"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden><path d="M21.9 4.3 18.7 19.4c-.2 1-.9 1.3-1.7.8l-4.8-3.6-2.3 2.2c-.3.3-.5.5-1 .5l.3-4.9 8.9-8c.4-.3-.1-.5-.6-.2L6.5 13.1 1.8 11.6c-1-.3-1-1 .2-1.5L20.6 3c.9-.3 1.6.2 1.3 1.3Z"/></svg></a>
      <a className="sh-fb" href={`https://www.facebook.com/sharer/sharer.php?u=${u}`} target="_blank" rel="noopener noreferrer" aria-label="Share on Facebook"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden><path d="M14 8V6.2c0-.8.5-1.2 1.2-1.2H17V2h-2.6C11.7 2 11 3.9 11 5.9V8H8.5v3H11v11h3V11h2.6l.4-3H14Z"/></svg></a>
      <button type="button" className="sh-copy" onClick={copy} aria-label="Copy product link">{copied ? <><Check size={16}/> Copied</> : <><Link2 size={16}/> Copy link</>}</button>
    </div>
  </div>;
}
