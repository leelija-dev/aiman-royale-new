'use client';
import Image from 'next/image';
import Link from 'next/link';
import {useRouter} from 'next/navigation';
import {useState} from 'react';
import {Heart, ChevronUp, ArrowDown, ArrowUpRight, LayoutGrid, List} from 'lucide-react';
import {api, err} from '@/lib/client';
import {Product, ProductPage, money, photo} from '@/lib/types';
import type {MenuLink} from '@/lib/menu';
import {type Query, OCCASIONS, list, toParams} from '@/lib/query';

const SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL'];
const COLOURS: [string, string][] = [
  ['Maroon', '#6b1426'], ['Rani Pink', '#d6246e'], ['Rose Gold', '#c9877d'], ['Copper', '#b8642f'],
  ['Wine', '#5c0f2e'], ['Purple', '#4b2a7a'], ['Green', '#3f6b4a'], ['Navy', '#24315e'],
];

/* ---------- Filters sidebar ---------- */
function Group({title, children}: {title: string; children: React.ReactNode}) {
  const [open, setOpen] = useState(true);
  return <div className="cp-group">
    <button type="button" className="cp-group-head" aria-expanded={open} onClick={() => setOpen(!open)}>{title}<ChevronUp size={18} className={open ? '' : 'flip'}/></button>
    {open && <div className="cp-group-body">{children}</div>}
  </div>;
}

export function Filters({base, query, styles}: {base: string; query: Query; styles: MenuLink[]}) {
  const router = useRouter();
  const go = (p: URLSearchParams) => { p.delete('page'); router.push(`${base}${p.size ? `?${p}` : ''}#collection`, {scroll: false}); };
  const toggle = (key: string, value: string) => {
    const p = toParams(query); const cur = p.getAll(key); p.delete(key);
    (cur.includes(value) ? cur.filter(v => v !== value) : [...cur, value]).forEach(v => p.append(key, v));
    go(p);
  };
  const has = (key: string, value: string) => list(query[key]).some(v => v.toLowerCase() === value.toLowerCase());
  const active = ['occasion', 'size', 'colour', 'min', 'max'].some(k => list(query[k]).length);
  const [open, setOpen] = useState(false);
  return <aside className={open ? 'cp-filters open' : 'cp-filters'} aria-label="Filters">
    <div className="cp-filters-head"><h2><button type="button" className="cp-filter-toggle" aria-expanded={open} onClick={() => setOpen(!open)}>Filters<ChevronUp size={18} className={open ? '' : 'flip'}/></button></h2>{active && <Link href={`${base}#collection`} scroll={false}>Clear all</Link>}</div>
    <Group title="Occasion">{OCCASIONS.map(o => <label key={o} className="cp-check"><input type="checkbox" checked={has('occasion', o)} onChange={() => toggle('occasion', o)}/>{o}</label>)}</Group>
    <Group title="Size"><div className="cp-sizes">{SIZES.map(s => <button type="button" key={s} aria-pressed={has('size', s)} className={has('size', s) ? 'on' : ''} onClick={() => toggle('size', s)}>{s}</button>)}</div></Group>
    <Group title="Colour">{COLOURS.map(([c, hex]) => <button type="button" key={c} className={has('colour', c) ? 'cp-colour on' : 'cp-colour'} aria-pressed={has('colour', c)} onClick={() => toggle('colour', c)}><span style={{background: hex}}/>{c}</button>)}</Group>
    <Group title="Price">
      <form className="cp-price" onSubmit={e => { e.preventDefault(); const f = new FormData(e.currentTarget); const p = toParams(query); for (const k of ['min', 'max']) { p.delete(k); const v = String(f.get(k) || '').trim(); if (v) p.set(k, v); } go(p); }}>
        <input name="min" type="number" min={0} inputMode="numeric" placeholder="Min (₹)" aria-label="Minimum price" defaultValue={list(query.min)[0]}/>
        <input name="max" type="number" min={0} inputMode="numeric" placeholder="Max (₹)" aria-label="Maximum price" defaultValue={list(query.max)[0]}/>
        <button className="button outline small">Apply</button>
      </form>
    </Group>
    <Group title="Collection">{styles.map(s => <Link key={s.href} href={s.href} className="cp-collection-link">{s.label}</Link>)}</Group>
    <Link href="/info/size-guide" className="cp-size-guide">Size Guide <ArrowUpRight size={16}/></Link>
  </aside>;
}

/* ---------- Product card ---------- */
function WishHeart({id}: {id: number}) {
  const router = useRouter(); const [on, setOn] = useState(false);
  return <button type="button" className={on ? 'cp-heart on' : 'cp-heart'} aria-label="Add to wishlist" aria-pressed={on}
    onClick={async () => { try { await api('wishlist/', 'POST', {product: id}); setOn(true); } catch (e) { if (/auth|login|credentials/i.test(err(e))) router.push('/login'); } }}>
    <Heart size={20} fill={on ? 'currentColor' : 'none'}/>
  </button>;
}

function Card({p}: {p: Product}) {
  const off = Number(p.mrp) > Number(p.price) ? Math.round((1 - Number(p.price) / Number(p.mrp)) * 100) : 0;
  return <article className="cp-card">
    <div className="cp-photo">
      <Link href={`/products/${p.slug}`} aria-label={p.name}><Image src={photo(p)} alt={p.images[0]?.alt || p.name} fill sizes="(max-width:700px) 46vw, (max-width:1100px) 30vw, 22vw"/></Link>
      {off > 0 && <span className="cp-badge">{off}% OFF</span>}
      <WishHeart id={p.id}/>
      <Link href={`/products/${p.slug}`} className="cp-quick">Quick View</Link>
    </div>
    <div className="cp-info">
      <p className="cp-brand">Aiman Royale</p>
      <h3><Link href={`/products/${p.slug}`}>{p.name}</Link></h3>
      <p className="cp-price-line"><strong>{money(p.price)}</strong>{off > 0 && <del>{money(p.mrp)}</del>}</p>
    </div>
  </article>;
}

/* ---------- Results: sort, view toggle, grid, load more ---------- */
export function Results({data, query, base, extra = {}}: {data: ProductPage; query: Query; base: string; extra?: Record<string, string>}) {
  const router = useRouter();
  const [items, setItems] = useState(data.results), [page, setPage] = useState(data.page), [busy, setBusy] = useState(false), [view, setView] = useState<'grid' | 'list'>('grid');
  const sort = list(query.sort)[0] || '';
  const more = async () => {
    setBusy(true);
    try { const p = toParams({...query, ...extra}); p.set('page', String(page + 1)); const next = await api<ProductPage>(`products/?${p}`); setItems(i => [...i, ...next.results]); setPage(next.page); }
    finally { setBusy(false); }
  };
  return <div className="cp-results">
    <div className="cp-results-head">
      <h2>The Collection <small>{data.count} {data.count === 1 ? 'style' : 'styles'}</small></h2>
      <div className="cp-tools">
        <select aria-label="Sort by" value={sort} onChange={e => { const p = toParams(query); p.delete('page'); if (e.target.value) p.set('sort', e.target.value); else p.delete('sort'); router.push(`${base}${p.size ? `?${p}` : ''}#collection`, {scroll: false}); }}>
          <option value="">Sort by: Featured</option><option value="newest">Newest first</option><option value="price-asc">Price: Low to High</option><option value="price-desc">Price: High to Low</option>
        </select>
        <button type="button" aria-label="Grid view" aria-pressed={view === 'grid'} className={view === 'grid' ? 'on' : ''} onClick={() => setView('grid')}><LayoutGrid size={20}/></button>
        <button type="button" aria-label="List view" aria-pressed={view === 'list'} className={view === 'list' ? 'on' : ''} onClick={() => setView('list')}><List size={20}/></button>
      </div>
    </div>
    {items.length ? <div className={`cp-grid ${view}`}>{items.map(p => <Card key={p.id} p={p}/>)}</div>
      : <div className="empty"><h2>A new story is coming.</h2><p>No styles match these filters yet.</p><Link className="button outline" href={`${base}#collection`} scroll={false}>Clear filters</Link></div>}
    {page < data.pages && <div className="center"><button type="button" className="cp-more" disabled={busy} onClick={more}>{busy ? 'Loading…' : <>Load More Styles <ArrowDown size={17}/></>}</button></div>}
  </div>;
}
