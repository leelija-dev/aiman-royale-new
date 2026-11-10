'use client';
import Image from 'next/image';
import Link from 'next/link';
import {useRouter} from 'next/navigation';
import {useRef, useState} from 'react';
import {Heart, ChevronUp, ChevronDown, ChevronLeft, ChevronRight, ArrowUpRight, ArrowLeft, ArrowRight, Scissors, Truck, Star, Tag, Sparkles} from 'lucide-react';
import {api} from '@/lib/client';
import {useWishlist, loginHere} from '@/lib/wishlist';
import {Product, ProductPage, Facets, money, photo, discount} from '@/lib/types';
import type {MenuLink} from '@/lib/menu';
import {type Query, list, toParams} from '@/lib/query';

/* ---------- Filters sidebar ---------- */
function Group({title, children, start = false}: {title: string; children: React.ReactNode; start?: boolean}) {
  const [open, setOpen] = useState(start);
  return <div className={open ? 'cp-group open' : 'cp-group'}>
    <button type="button" className="cp-group-head" aria-expanded={open} onClick={() => setOpen(!open)}>{title}<ChevronDown size={18} className={open ? 'flip' : ''}/></button>
    {open && <div className="cp-group-body">{children}</div>}
  </div>;
}

export function Filters({base, query, styles = [], facets, variant = 'category'}: {base: string; query: Query; styles?: MenuLink[]; facets: Facets; variant?: 'category' | 'shop'}) {
  const router = useRouter();
  const go = (p: URLSearchParams) => { p.delete('page'); router.push(`${base}${p.size ? `?${p}` : ''}#collection`, {scroll: false}); };
  const toggle = (key: string, value: string) => {
    const p = toParams(query); const cur = p.getAll(key); p.delete(key);
    (cur.includes(value) ? cur.filter(v => v !== value) : [...cur, value]).forEach(v => p.append(key, v));
    go(p);
  };
  const has = (key: string, value: string) => list(query[key]).some(v => v.toLowerCase() === value.toLowerCase());
  const active = ['occasion', 'size', 'colour', 'min', 'max', 'price', 'collection', 'custom', 'sale', 'ready'].some(k => list(query[k]).length);
  const [open, setOpen] = useState(false), [allCats, setAllCats] = useState(false);
  const cats = facets.collections || [];
  const shownCats = allCats ? cats : cats.slice(0, 7);
  const Check = ({k, value, label, count}: {k: string; value: string; label: string; count?: number}) =>
    <label className="cp-check"><input type="checkbox" checked={has(k, value)} onChange={() => toggle(k, value)}/>{label}{count !== undefined && <span className="cp-count">{count}</span>}</label>;
  const category = cats.length > 0 && <Group title="Category" start>{shownCats.map(c => <Check key={c.slug} k="collection" value={c.slug} label={c.name} count={c.count}/>)}
    {cats.length > 7 && <button type="button" className="cp-show-more" onClick={() => setAllCats(!allCats)}>{allCats ? 'Show less' : 'Show more'}</button>}</Group>;
  const occasion = facets.occasions.length > 0 && <Group title="Occasion">{facets.occasions.filter(o => o.count || has('occasion', o.slug)).map(o => <Check key={o.slug} k="occasion" value={o.slug} label={o.name} count={o.count}/>)}</Group>;
  const size = facets.sizes.length > 0 && <Group title="Size"><div className="cp-sizes">{facets.sizes.map(s => <button type="button" key={s} aria-pressed={has('size', s)} className={has('size', s) ? 'on' : ''} onClick={() => toggle('size', s)}>{s}</button>)}</div></Group>;
  const colour = facets.colours.length > 0 && <Group title="Colour">{facets.colours.map(c => <button type="button" key={c.name} className={has('colour', c.name) ? 'cp-colour on' : 'cp-colour'} aria-pressed={has('colour', c.name)} onClick={() => toggle('colour', c.name)}><span style={{background: c.hex}}/>{c.name}<em className="cp-count">{c.count}</em></button>)}</Group>;
  const priceRanges = (facets.price_ranges || []).length > 0 && <Group title="Price">{facets.price_ranges!.map(r => <Check key={r.value} k="price" value={r.value} label={r.label} count={r.count}/>)}</Group>;
  const priceInputs = <Group title="Price">
      <form className="cp-price" onSubmit={e => { e.preventDefault(); const f = new FormData(e.currentTarget); const p = toParams(query); for (const k of ['min', 'max']) { p.delete(k); const v = String(f.get(k) || '').trim(); if (v) p.set(k, v); } go(p); }}>
        <input name="min" type="number" min={0} inputMode="numeric" placeholder={`Min ₹${Math.floor(Number(facets.price.min))}`} aria-label="Minimum price" defaultValue={list(query.min)[0]}/>
        <input name="max" type="number" min={0} inputMode="numeric" placeholder={`Max ₹${Math.ceil(Number(facets.price.max))}`} aria-label="Maximum price" defaultValue={list(query.max)[0]}/>
        <button className="button outline small">Apply</button>
      </form>
      {Number(facets.price.max) > 0 && <p className="cp-range">{money(facets.price.min)} – {money(facets.price.max)}</p>}
    </Group>;
  return <aside className={open ? 'cp-filters open' : 'cp-filters'} aria-label="Filters">
    <div className="cp-filters-head"><h2><button type="button" className="cp-filter-toggle" aria-expanded={open} onClick={() => setOpen(!open)}>Filters<ChevronUp size={18} className={open ? '' : 'flip'}/></button></h2>{active && <Link href={`${base}#collection`} scroll={false}>Clear all</Link>}</div>
    {variant === 'shop'
      ? <>{category}{occasion}{colour}{size}{priceRanges || priceInputs}</>
      : <>{styles.length > 0 && <Group title="Sub Category" start>{styles.map(s => <Link key={s.href} href={s.href} className="cp-collection-link"><span>{s.label}</span>{typeof s.count === 'number' && <em className="cp-count">{s.count}</em>}</Link>)}</Group>}{colour}{occasion}{size}{priceInputs}</>}
    <Link href="/info/size-guide" className="cp-size-guide">Size Guide <ArrowUpRight size={16}/></Link>
  </aside>;
}

/* ---------- Product card ---------- */
function WishHeart({id, slug}: {id: number; slug: string}) {
  const router = useRouter(); const [on, toggle] = useWishlist(id);
  return <button type="button" className={on ? 'cp-heart on' : 'cp-heart'} aria-label={on ? 'Remove from wishlist' : 'Add to wishlist'} aria-pressed={on}
    onClick={async () => { try { if (await toggle() === 'login') router.push(loginHere()); } catch {} }}>
    <Heart size={20} fill={on ? 'currentColor' : 'none'}/>
  </button>;
}

/** Product tag with an icon: Custom-fit (red), Ready to Ship (black), others (pink). */
export function TagPill({t}: {t: string}) {
  const k = /custom/i.test(t) ? 'custom' : /ready/i.test(t) ? 'ready' : /best/i.test(t) ? 'best' : /off/i.test(t) ? 'off' : 'other';
  const icon = k === 'custom' ? <Scissors size={12} aria-hidden/> : k === 'ready' ? <Truck size={12} aria-hidden/> : k === 'best' ? <Star size={12} aria-hidden/> : k === 'off' ? <Tag size={12} aria-hidden/> : <Sparkles size={12} aria-hidden/>;
  return <span className={`tag-pill tag-${k}`}>{icon}{t}</span>;
}

export function Card({p}: {p: Product; hex?: Record<string, string>}) {
  const off = discount(p);
  const ready = p.variants.some(v => v.stock > 0);
  const tags = [p.custom_fit && 'Custom-fit', ready && 'Ready to Ship', p.featured && 'Bestseller'].filter(Boolean) as string[];
  return <article className="cp-card">
    <div className="cp-photo">
      <Link href={`/products/${p.slug}`} aria-label={p.name}><Image src={photo(p)} alt={p.images[0]?.alt || p.name} fill sizes="(max-width:700px) 46vw, (max-width:1100px) 30vw, 24vw"/></Link>
      <WishHeart id={p.id} slug={p.slug}/>
    </div>
    <div className="cp-info">
      <p className="cp-brand">Aiman Royale</p>
      <h3><Link href={`/products/${p.slug}`} title={p.name}>{p.name}</Link></h3>
      <p className="cp-price-line"><strong>{money(p.price)}</strong>{off > 0 && <><del>{money(p.mrp)}</del><em>{off}% OFF</em></>}</p>
      {tags.length > 0 && <div className="cp-tags">{tags.slice(0, 2).map(t => <TagPill key={t} t={t}/>)}</div>}
    </div>
  </article>;
}

/** Peach band at the top of a category page: a scrollable row of rounded image cards. */
export function BandCarousel({cards}: {cards: {title: string; href: string; image: string}[]}) {
  const row = useRef<HTMLDivElement>(null);
  const move = (d: number) => row.current?.scrollBy({left: d * row.current.clientWidth * .8, behavior: 'smooth'});
  if (!cards.length) return null;
  return <div className="az-band-inner">
    <button type="button" className="az-arrow prev" aria-label="Previous" onClick={() => move(-1)}><ChevronLeft size={20}/></button>
    <div className="az-band-row" ref={row}>{cards.map(c => <Link key={c.href} href={c.href} className="az-band-card">
      <span className="az-band-img"><Image src={c.image} alt="" fill sizes="(max-width:700px) 60vw, 22vw"/></span>
      <span className="az-band-copy"><strong>{c.title}</strong><small>Shop Now</small></span>
    </Link>)}</div>
    <button type="button" className="az-arrow next" aria-label="Next" onClick={() => move(1)}><ChevronRight size={20}/></button>
  </div>;
}

/* ---------- Results: sort, view toggle, grid, load more ---------- */
export function Results({data, query, base, extra = {}, facets, heading, subheading, paging = 'more'}: {data: ProductPage; query: Query; base: string; extra?: Record<string, string>;
  facets?: Facets; heading?: string; subheading?: string; paging?: 'more' | 'pages'}) {
  const hex = Object.fromEntries((facets?.colours || []).map(c => [c.name.toLowerCase(), c.hex]));
  const pageUrl = (n: number) => { const p = toParams(query); if (n > 1) p.set('page', String(n)); else p.delete('page'); return `${base}${p.size ? `?${p}` : ''}#collection`; };
  const router = useRouter();
  const [items, setItems] = useState(data.results), [page, setPage] = useState(data.page), [busy, setBusy] = useState(false);
  const sort = list(query.sort)[0] || '';
  const more = async () => {
    setBusy(true);
    try { const p = toParams({...query, ...extra}); p.set('page', String(page + 1)); const next = await api<ProductPage>(`products/?${p}`); setItems(i => [...i, ...next.results]); setPage(next.page); }
    finally { setBusy(false); }
  };
  const go = (p: URLSearchParams) => { p.delete('page'); router.push(`${base}${p.size ? `?${p}` : ''}#collection`, {scroll: false}); };
  const chip = (k: string, v: string) => { const p = toParams(query); if (p.get(k) === v) p.delete(k); else p.set(k, v); go(p); };
  const CHIPS: [string, string, string][] = [['New', 'sort', 'newest'], ['Ready to Ship', 'ready', '1'], ['On Sale', 'sale', '1'], ['Custom-fit', 'custom', '1']];
  return <div className="cp-results">
    <div className="cp-results-head">
      <div className="cp-chips" role="group" aria-label="Quick filters">{CHIPS.map(([label, k, v]) => { const on = list(query[k])[0] === v;
        return <button type="button" key={label} aria-pressed={on} className={on ? 'on' : ''} onClick={() => chip(k, v)}>{label}</button>; })}</div>
      <div className="cp-tools">
        <span className="cp-total">{data.count} {data.count === 1 ? 'item' : 'items'}</span>
        <label className="cp-sort"><span>Sort By</span>
        <select value={sort} onChange={e => { const p = toParams(query); if (e.target.value) p.set('sort', e.target.value); else p.delete('sort'); go(p); }}>
          <option value="">Featured</option><option value="newest">New Arrivals</option><option value="price-asc">Price: Low to High</option><option value="price-desc">Price: High to Low</option>
        </select></label>
      </div>
    </div>
    {(heading || subheading) && <div className="cp-results-title">{heading && <h2>{heading}</h2>}{subheading && <p className="cp-subheading">{subheading}</p>}</div>}
    {items.length ? <div className="cp-grid grid">{items.map(p => <Card key={p.id} p={p} hex={hex}/>)}</div>
      : <div className="empty"><h2>A new story is coming.</h2><p>No styles match these filters yet.</p><Link className="button outline" href={`${base}#collection`} scroll={false}>Clear filters</Link></div>}
    {paging === 'pages' && data.pages > 1 && <nav className="cp-pages" aria-label="Product pages">
      {data.page > 1 ? <Link href={pageUrl(data.page - 1)} scroll={false} aria-label="Previous page"><ArrowLeft size={16}/></Link> : <span aria-hidden><ArrowLeft size={16}/></span>}
      {Array.from({length: data.pages}, (_, i) => i + 1).map(n => <Link key={n} href={pageUrl(n)} scroll={false} aria-current={n === data.page ? 'page' : undefined} className={n === data.page ? 'on' : ''}>{n}</Link>)}
      {data.page < data.pages ? <Link href={pageUrl(data.page + 1)} scroll={false} aria-label="Next page"><ArrowRight size={16}/></Link> : <span aria-hidden><ArrowRight size={16}/></span>}
    </nav>}
    {paging === 'more' && page < data.pages && <div className="center"><button type="button" className="cp-more" disabled={busy} onClick={more}>{busy ? 'Loading…' : 'Load More'}</button></div>}
  </div>;
}
