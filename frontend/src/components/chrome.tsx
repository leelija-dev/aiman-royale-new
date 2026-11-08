'use client';
import Link from 'next/link';
import {AccountMenu} from '@/components/account-menu';
import {useEffect, useRef, useState} from 'react';
import Image from 'next/image';
import {useRouter} from 'next/navigation';
import {usePathname} from 'next/navigation';
import {Home, LayoutGrid, Search, Heart, ShoppingBag, UserRound, Menu, X, CalendarDays, ArrowRight, MessageCircle, ChevronDown, Phone, Mail, MapPin, Banknote, Truck, RotateCcw, Ruler, Headset} from 'lucide-react';
import {api} from '@/lib/client';
import {money, photo, type Bag, type Product, type ProductPage, type Site} from '@/lib/types';
import {mainMenu, FEATURE_FALLBACK, type MenuItem} from '@/lib/menu';
import {useWishlistCount} from '@/lib/wishlist';

const badge = (n: number) => n > 99 ? '99+' : String(n);

/** Header search: on focus it opens a panel with trending searches (categories) and top products, updating as you type. */
function SearchBox({site, cls}: {site: Site; cls: string}) {
  const [open, setOpen] = useState(false), [q, setQ] = useState(''), [top, setTop] = useState<Product[] | null>(null), [hits, setHits] = useState<Product[] | null>(null);
  const box = useRef<HTMLFormElement>(null), router = useRouter(), pathname = usePathname();
  useEffect(() => setOpen(false), [pathname]);
  useEffect(() => {
    if (!open) return;
    if (top === null) api<ProductPage>('products/?featured=1').then(d => setTop(d.results)).catch(() => setTop([]));
    const out = (e: MouseEvent) => { if (box.current && !box.current.contains(e.target as Node)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', out); document.addEventListener('keydown', esc);
    return () => { document.removeEventListener('mousedown', out); document.removeEventListener('keydown', esc); };
  }, [open, top]);
  useEffect(() => {
    const term = q.trim(); if (term.length < 2) { setHits(null); return; }
    const t = setTimeout(() => api<ProductPage>(`products/?q=${encodeURIComponent(term)}`).then(d => setHits(d.results)).catch(() => setHits([])), 250);
    return () => clearTimeout(t);
  }, [q]);
  const term = q.trim().toLowerCase();
  const cats = [...(site.collections || []).map(c => ({label: c.name, href: `/collections/${c.slug}`})), ...(site.occasions || []).map(o => ({label: `${o.name} Collection`, href: `/products?occasion=${o.slug}`}))];
  const trending = (term ? cats.filter(c => c.label.toLowerCase().includes(term)) : cats).slice(0, 8);
  const list = (hits ?? top ?? []).slice(0, 8);
  const submit = (e: React.FormEvent) => { e.preventDefault(); setOpen(false); router.push(q.trim() ? `/products?q=${encodeURIComponent(q.trim())}` : '/products'); };
  return <form ref={box} action="/products" className={`hk-search ${cls}${open ? ' open' : ''}`} role="search" onSubmit={submit}>
    <input name="q" type="search" value={q} onChange={e => { setQ(e.target.value); setOpen(true); }} onFocus={() => setOpen(true)} autoComplete="off"
      onKeyDown={e => { if (e.key === 'Escape') { e.preventDefault(); setOpen(false); e.currentTarget.blur(); } }}
      aria-label="Search products" aria-expanded={open} aria-controls={`${cls}-panel`} placeholder="Search for suits, anarkali, gowns…"/>
    <button type="submit" aria-label="Search"><Search size={18}/></button>
    {open && <div className="hk-panel" id={`${cls}-panel`}>
      <div className="hk-panel-in">
        <div className="hk-trend"><h4>{term ? 'Categories' : 'Trending Searches'}</h4>
          <ul>{trending.map(c => <li key={c.href}><Link href={c.href} onClick={() => setOpen(false)}>{c.label}</Link></li>)}
            {term && <li><Link href={`/products?q=${encodeURIComponent(q.trim())}`} onClick={() => setOpen(false)} className="hk-all">Search for “{q.trim()}” <ArrowRight size={15}/></Link></li>}</ul></div>
        <div className="hk-top"><h4>{hits ? (hits.length ? 'Matching Products' : 'No matching products') : 'Top Products'}</h4>
          {list.length > 0 ? <div className="hk-top-grid">{list.map(p => { const off = Number(p.mrp) > Number(p.price);
            return <Link key={p.id} href={`/products/${p.slug}`} onClick={() => setOpen(false)} className="hk-prod">
              <span><Image src={photo(p)} alt={p.name} fill sizes="(max-width:900px) 40vw, 200px"/></span><strong>{p.name}</strong>
              <em>{off && <del>{money(p.mrp)}</del>} {money(p.price)}</em></Link>; })}</div>
            : top === null ? <p className="hk-muted">Loading…</p> : hits ? <p className="hk-muted">Try another word, or browse the categories.</p> : null}
          {hits && hits.length > 0 && <Link href={`/products?q=${encodeURIComponent(q.trim())}`} onClick={() => setOpen(false)} className="hk-all">View all results <ArrowRight size={15}/></Link>}
        </div>
      </div>
    </div>}
  </form>;
}

export function Header({site}: {site: Site}) {
  const [open, setOpen] = useState(false), [count, setCount] = useState(0);
  const saved = useWishlistCount(), pathname = usePathname();
  // Phone tab bar (hidden where a page has its own bottom bar: product, checkout, payment).
  const tabs = !/^\/(products\/|checkout|payment)/.test(pathname);
  useEffect(() => {
    const update = () => api<Bag>('cart/').then(b => setCount(b.items.reduce((n, i) => n + i.quantity, 0))).catch(() => {});
    update(); window.addEventListener('bag-changed', update);
    return () => window.removeEventListener('bag-changed', update);
  }, []);
  // Several announcements can be separated with "|" in the admin; they scroll in a loop.
  const msgs = (site.announcement || '').split('|').map(m => m.trim()).filter(Boolean);
  const loop = msgs.length ? Array.from({length: Math.max(2, Math.ceil(6 / msgs.length))}, () => msgs).flat() : [];
  const searchForm = (cls: string) => <SearchBox site={site} cls={cls}/>;
  return <>
    {loop.length > 0 && <div className="hk-announce" aria-label="Announcements"><span className="sr-only">{msgs.join('. ')}</span>
      <div className="hk-track" aria-hidden>{[0, 1].map(k => <div key={k} className="hk-seq">{loop.map((m, i) => <span key={i}>{m}</span>)}</div>)}</div></div>}
    <header className="hk-header">
      <div className="hk-row">
        <button className="icon hk-burger" aria-label={open ? 'Close menu' : 'Open menu'} aria-expanded={open} onClick={() => setOpen(!open)}>{open ? <X/> : <Menu/>}</button>
        {searchForm('hk-search-desk')}
        <Link href="/" className="brand hk-logo" aria-label="Aiman Royale home">Aiman <em>Royale</em></Link>
        <div className="hk-actions">
          <Link href="/appointment" className="icon hk-appt" aria-label="Book Appointment" title="Book Appointment"><CalendarDays/></Link>
          <AccountMenu/>
          <Link href="/wishlist" className="icon count-icon" aria-label={`Wishlist, ${saved} saved`} title="Wishlist"><Heart/>{saved > 0 && <b className="count-badge wish">{badge(saved)}</b>}</Link>
          <Link href="/cart" className="icon count-icon" aria-label={`Shopping bag, ${count} items`} title="Bag"><ShoppingBag/>{count > 0 && <b className="count-badge">{badge(count)}</b>}</Link>
        </div>
      </div>
      {searchForm('hk-search-mob')}
      <MainNav items={site.menu?.length ? site.menu : mainMenu} open={open} close={() => setOpen(false)}/>
    </header>
    {tabs && <nav className="mtab" aria-label="Quick links">
      <Link href="/" className={pathname === '/' ? 'on' : ''}><Home size={21}/>Home</Link>
      <button type="button" aria-expanded={open} onClick={() => { setOpen(true); window.scrollTo({top: 0, behavior: 'smooth'}); }}><LayoutGrid size={21}/>Categories</button>
      <Link href="/wishlist" className={pathname === '/wishlist' ? 'on' : ''}><span><Heart size={21}/>{saved > 0 && <b>{badge(saved)}</b>}</span>Wishlist</Link>
      <Link href="/cart" className={pathname === '/cart' ? 'on' : ''}><span><ShoppingBag size={21}/>{count > 0 && <b>{badge(count)}</b>}</span>Bag</Link>
      <Link href="/account" className={pathname.startsWith('/account') ? 'on' : ''}><UserRound size={21}/>Account</Link>
    </nav>}
  </>;
}

function MainNav({items, open, close}: {items: MenuItem[]; open: boolean; close: () => void}) {
  const path = usePathname();
  const [active, setActive] = useState<number | null>(null), [tab, setTab] = useState(0), [mobileItem, setMobileItem] = useState<number | null>(null);
  useEffect(() => { setActive(null); close(); }, [path]); // eslint-disable-line react-hooks/exhaustive-deps
  // Only reset to the first tab when opening a different menu (focus moving inside the open menu must not switch tabs).
  const show = (i: number) => { if (active !== i) { setActive(i); setTab(0); } };
  const done = () => { setActive(null); close(); };
  return <nav className={open ? 'nav open' : 'nav'} aria-label="Main" onMouseLeave={() => setActive(null)}>
    <ul className="menu-bar">{items.map((item, i) => {
      const current = active === i || (active === null && path === item.href.split('?')[0]);
      const cols = item.columns.filter(c => c.links.length);
      return <li key={item.label} onMouseEnter={() => cols.length && show(i)} onFocus={() => cols.length && show(i)} onKeyDown={e => { if (e.key === 'Escape') setActive(null); }}>
        <div className="menu-top"><Link href={item.href} className={current ? 'menu-link current' : 'menu-link'} aria-expanded={cols.length ? active === i : undefined} onClick={done}>{item.label}</Link>
          {cols.length > 0 && <button className="menu-expand" aria-label={`Show ${item.label} menu`} aria-expanded={mobileItem === i} onClick={() => setMobileItem(mobileItem === i ? null : i)}><ChevronDown size={18} className={mobileItem === i ? 'flip' : ''}/></button>}</div>
        {cols.length > 0 && <div className={`mega${active === i ? ' show' : ''}${mobileItem === i ? ' mobile-show' : ''}`}>
          <div className="mega-inner">
            <div className="mega-tabs" role="tablist" aria-label={`${item.label} menu`}>
              <p className="mega-kicker">Shop {item.label}</p>
              {cols.map((c, t) => <button key={c.title} role="tab" type="button" aria-selected={tab === t} className={tab === t ? 'on' : ''} onMouseEnter={() => setTab(t)} onFocus={() => setTab(t)} onClick={() => setTab(t)}>{c.title}<ArrowRight size={15}/></button>)}
              <Link href={item.href} className="mega-all" onClick={done}>View all {item.label} <ArrowRight size={15}/></Link>
            </div>
            <div className="mega-links">{cols.map((c, t) => <div key={c.title} role="tabpanel" className={`mega-panel kind-${c.title.toLowerCase()}${tab === t ? ' on' : ''}`}>
              <p className="mega-mobile-title">{c.title}</p>
              <ul>{c.links.map(l => <li key={l.label + l.href}><Link href={l.href} onClick={done}>
                {c.title === 'Style' && <span className="mega-thumb">{l.image ? <img src={l.image} alt="" loading="lazy" width={52} height={52}/> : <span>{l.label[0]}</span>}</span>}
                <span className="mega-text"><span>{l.label}</span>{typeof l.count === 'number' && <small>{l.count} {l.count === 1 ? 'style' : 'styles'}</small>}</span>
              </Link></li>)}</ul></div>)}</div>
            {item.feature && <Link href={item.feature.href} className="mega-feature" onClick={done}><img src={item.feature.image || FEATURE_FALLBACK[i % FEATURE_FALLBACK.length]} alt="" loading="lazy" width={260} height={320}/><span><small>Featured</small>{item.feature.title} <ArrowRight size={16}/></span></Link>}
          </div>
        </div>}
      </li>;
    })}</ul>
    <div className="nav-mobile-extra"><Link href="/appointment" onClick={done}><CalendarDays size={18}/> Book Appointment</Link><Link href="/account?tab=profile" onClick={done}><UserRound size={18}/> My Account</Link></div>
  </nav>;
}

const SOCIAL: Record<string, {label: string; path: string}> = {
  instagram: {label: 'Instagram', path: 'M12 7.3A4.7 4.7 0 1 0 16.7 12 4.7 4.7 0 0 0 12 7.3Zm0 7.7a3 3 0 1 1 3-3 3 3 0 0 1-3 3Zm6-7.9a1.1 1.1 0 1 1-1.1-1.1A1.1 1.1 0 0 1 18 7.1ZM21.1 8.2a5.4 5.4 0 0 0-1.5-3.8 5.4 5.4 0 0 0-3.8-1.5C14.3 2.8 9.7 2.8 8.2 2.9a5.4 5.4 0 0 0-3.8 1.5 5.4 5.4 0 0 0-1.5 3.8c-.1 1.5-.1 6.1 0 7.6a5.4 5.4 0 0 0 1.5 3.8 5.4 5.4 0 0 0 3.8 1.5c1.5.1 6.1.1 7.6 0a5.4 5.4 0 0 0 3.8-1.5 5.4 5.4 0 0 0 1.5-3.8c.1-1.5.1-6.1 0-7.6Zm-2 9.2a3 3 0 0 1-1.7 1.7c-1.2.5-4 .4-5.4.4s-4.2.1-5.4-.4a3 3 0 0 1-1.7-1.7c-.5-1.2-.4-4-.4-5.4s-.1-4.2.4-5.4a3 3 0 0 1 1.7-1.7c1.2-.5 4-.4 5.4-.4s4.2-.1 5.4.4a3 3 0 0 1 1.7 1.7c.5 1.2.4 4 .4 5.4s.1 4.2-.4 5.4Z'},
  facebook: {label: 'Facebook', path: 'M14 8.5V6.8c0-.8.2-1.3 1.4-1.3H17V2.6A20 20 0 0 0 14.6 2.5C12.2 2.5 10.6 4 10.6 6.6v1.9H8v3.2h2.6V21.5H14v-9.8h2.6l.4-3.2Z'},
  youtube: {label: 'YouTube', path: 'M21.6 7.2a2.6 2.6 0 0 0-1.8-1.8C18.2 5 12 5 12 5s-6.2 0-7.8.4A2.6 2.6 0 0 0 2.4 7.2 27 27 0 0 0 2 12a27 27 0 0 0 .4 4.8 2.6 2.6 0 0 0 1.8 1.8C5.8 19 12 19 12 19s6.2 0 7.8-.4a2.6 2.6 0 0 0 1.8-1.8A27 27 0 0 0 22 12a27 27 0 0 0-.4-4.8ZM10 15V9l5.2 3Z'},
  pinterest: {label: 'Pinterest', path: 'M12.3 2C6.8 2 4 5.9 4 9.2c0 2 .8 3.7 2.4 4.4.3.1.5 0 .6-.3l.2-.9c.1-.3 0-.4-.2-.7a3.4 3.4 0 0 1-.8-2.3 5.6 5.6 0 0 1 5.9-5.7c3.2 0 5 2 5 4.6 0 3.5-1.5 6.4-3.8 6.4a1.9 1.9 0 0 1-1.9-2.3c.4-1.5 1.1-3.2 1.1-4.3a1.6 1.6 0 0 0-1.6-1.8c-1.3 0-2.3 1.3-2.3 3.1a4.6 4.6 0 0 0 .4 1.9l-1.5 6.5a13 13 0 0 0 0 4.5.2.2 0 0 0 .3.1 12 12 0 0 0 2.1-3.8l.8-3.2a3.3 3.3 0 0 0 2.8 1.4c3.7 0 6.2-3.4 6.2-7.9C20.6 5.2 17.3 2 12.3 2Z'},
};

const POLICY = /terms|return|refund|privacy|shipping|policy|cancel/i;
const SERVICES: [React.ReactNode, string, string][] = [[<Headset key="h" size={30} strokeWidth={1.3}/>, '24x7 Customer Support', 'We are here to help'], [<Truck key="t" size={30} strokeWidth={1.3}/>, 'Free Shipping', 'On all prepaid orders'], [<RotateCcw key="r" size={30} strokeWidth={1.3}/>, 'Easy Returns', 'Hassle-free returns'], [<Ruler key="u" size={30} strokeWidth={1.3}/>, 'Custom Fitting', 'Made to your measurements']];

function FooterGroup({id, title, open, toggle, children}: {id: string; title: string; open: string | null; toggle: (k: string) => void; children: React.ReactNode}) {
  const on = open === id;
  return <div className={on ? 'kf-group open' : 'kf-group'}>
    <h4><button type="button" aria-expanded={on} aria-controls={`kf-${id}`} onClick={() => toggle(id)}>{title}<ChevronDown size={18}/></button></h4>
    <div className="kf-body" id={`kf-${id}`}>{children}</div>
  </div>;
}

export function Footer({site}: {site: Site}) {
  const [open, setOpen] = useState<string | null>(null);
  const toggle = (k: string) => setOpen(o => o === k ? null : k);
  const f = site.footer;
  const phone = site.phone.replace(/\D/g, '');
  const social = Object.entries(site.social || {}).filter(([k]) => SOCIAL[k]);
  const links = (k: string) => f?.links[k] || [];
  const explore = links('explore');
  const uniq = (l: {label: string; href: string}[]) => l.filter((x, i) => l.findIndex(y => y.href === x.href) === i);
  const groups: [string, string, {label: string; href: string}[]][] = [
    ['designer', 'Designer Wear', uniq([...links('categories'), ...links('occasions'), {label: 'All Products', href: '/products'}])],
    ['about', 'About Us', uniq([...explore.filter(l => !POLICY.test(l.label + l.href)), {label: 'Book an Appointment', href: '/appointment'}, {label: 'Track Your Order', href: '/track'}])],
    ['policies', 'Policies', uniq([...explore.filter(l => POLICY.test(l.label + l.href)), {label: 'Shipping Policy', href: '/info/shipping'}, {label: 'Size Guide', href: '/info/size-guide'}])],
    ['account', 'My Account', uniq([...links('account'), {label: 'Order History', href: '/account/orders'}])],
  ];
  const list = (l: {label: string; href: string}[]) => <ul>{l.map(x => <li key={x.label + x.href}><Link href={x.href}>{x.label}</Link></li>)}</ul>;
  return <>
    <footer className="kf" aria-label="Site footer">
      <div className="kf-wrap">
        <div className="kf-cols">
          {groups.map(([id, title, l]) => l.length > 0 && <FooterGroup key={id} id={id} title={title} open={open} toggle={toggle}><nav aria-label={title}>{list(l)}</nav></FooterGroup>)}
          <div className="kf-side">
            {f && f.payments.length > 0 && <FooterGroup id="pay" title="Safe & Secure Payment" open={open} toggle={toggle}><div className="kf-pay">{f.payments.map(m => <span key={m}>{m}</span>)}</div>{f.payments.some(m => /cod|cash/i.test(m)) && <p className="kf-note"><Banknote size={14}/> Cash on Delivery available</p>}</FooterGroup>}
            {social.length > 0 && <FooterGroup id="follow" title="Follow Us" open={open} toggle={toggle}><div className="kf-social">{social.map(([k, url]) => <a key={k} href={url} target="_blank" rel="noopener noreferrer" aria-label={SOCIAL[k].label}><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden><path d={SOCIAL[k].path}/></svg></a>)}</div></FooterGroup>}
            {phone && <FooterGroup id="chat" title="Chat With Us" open={open} toggle={toggle}><p className="kf-contact"><a href={`https://wa.me/${phone}`} target="_blank" rel="noopener noreferrer"><MessageCircle size={16}/> WhatsApp</a><a href={`tel:+${phone}`}><Phone size={16}/> +{phone}</a></p></FooterGroup>}
            {site.email && <FooterGroup id="mail" title="Email Us On" open={open} toggle={toggle}><p className="kf-contact"><a href={`mailto:${site.email}`}><Mail size={16}/> {site.email}</a></p></FooterGroup>}
          </div>
        </div>

        {f && f.highlights.length > 0 && <div className="kf-rows">{f.highlights.map(h => {
          const words = h.text.split(/[,|]/).map(w => w.trim()).filter(Boolean);
          return <FooterGroup key={h.title} id={`h-${h.title}`} title={h.title} open={open} toggle={toggle}>
            <p>{words.map((w, i) => <span key={w}>{i > 0 && <i aria-hidden> | </i>}<Link href={`/products?q=${encodeURIComponent(w)}`}>{w}</Link></span>)}</p>
          </FooterGroup>;
        })}</div>}

        <ul className="kf-services">{SERVICES.map(([ico, t, sm]) => <li key={t}><span>{ico}</span><strong>{t}</strong><small>{sm}</small></li>)}</ul>

        <div className="kf-bottom">
          {site.address && <p className="kf-addr"><MapPin size={14}/> {site.address}</p>}
          <p>© {new Date().getFullYear()} Aiman Royale. All rights reserved.</p>
        </div>
      </div>
    </footer>
    {phone && <a className="whatsapp-float" href={`https://wa.me/${phone}`} target="_blank" rel="noopener noreferrer" aria-label="Chat with Aiman Royale on WhatsApp"><MessageCircle size={23}/></a>}
  </>;
}
