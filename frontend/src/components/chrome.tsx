'use client';
import Link from 'next/link';
import {useEffect, useState} from 'react';
import {usePathname} from 'next/navigation';
import {Search, Heart, ShoppingBag, UserRound, Menu, X, CalendarDays, ArrowRight, MessageCircle, ChevronDown, Phone, Mail, MapPin, Check} from 'lucide-react';
import {api, err} from '@/lib/client';
import type {Bag, Site} from '@/lib/types';
import {mainMenu, FEATURE_FALLBACK, type MenuItem} from '@/lib/menu';
import {useWishlistCount} from '@/lib/wishlist';

const badge = (n: number) => n > 99 ? '99+' : String(n);

export function Header({site}: {site: Site}) {
  const [open, setOpen] = useState(false), [search, setSearch] = useState(false), [count, setCount] = useState(0);
  const saved = useWishlistCount();
  useEffect(() => {
    const update = () => api<Bag>('cart/').then(b => setCount(b.items.reduce((n, i) => n + i.quantity, 0))).catch(() => {});
    update(); window.addEventListener('bag-changed', update);
    return () => window.removeEventListener('bag-changed', update);
  }, []);
  return <>
    <div className="announcement">{site.announcement}<span>Made for your moments</span></div>
    <header className="header">
      <button className="icon mobile" aria-label={open ? 'Close menu' : 'Open menu'} aria-expanded={open} onClick={() => setOpen(!open)}>{open ? <X/> : <Menu/>}</button>
      <Link href="/" className="brand">Aiman <em>Royale</em></Link>
      <MainNav items={site.menu?.length ? site.menu : mainMenu} open={open} close={() => setOpen(false)}/>
      <div className="header-actions">
        <Link href="/appointment" className="appointment-link"><CalendarDays size={15}/> Book Appointment</Link>
        <button aria-label="Search" className="icon" onClick={() => setSearch(!search)}><Search/></button>
        <Link href="/account" className="icon hide-xs" aria-label="My account"><UserRound/></Link>
        <Link href="/wishlist" className="icon count-icon" aria-label={`Wishlist, ${saved} saved`}><Heart/>{saved > 0 && <b className="count-badge wish">{badge(saved)}</b>}</Link>
        <Link href="/cart" className="icon count-icon" aria-label={`Shopping bag, ${count} items`}><ShoppingBag/>{count > 0 && <b className="count-badge">{badge(count)}</b>}</Link>
      </div>
    </header>
    {search && <form action="/products" className="search-bar"><Search size={18}/><input autoFocus name="q" aria-label="Search products" placeholder="Find your perfect celebration look…"/><button className="text-button">Search <ArrowRight size={16}/></button></form>}
  </>;
}

function MainNav({items, open, close}: {items: MenuItem[]; open: boolean; close: () => void}) {
  const path = usePathname();
  const [active, setActive] = useState<number | null>(null), [tab, setTab] = useState(0), [mobileItem, setMobileItem] = useState<number | null>(null);
  useEffect(() => { setActive(null); close(); }, [path]); // eslint-disable-line react-hooks/exhaustive-deps
  const show = (i: number) => { setActive(i); setTab(0); };
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
    <div className="nav-mobile-extra"><Link href="/appointment" onClick={done}><CalendarDays size={18}/> Book Appointment</Link><Link href="/account" onClick={done}><UserRound size={18}/> My Account</Link></div>
  </nav>;
}

const SOCIAL: Record<string, {label: string; path: string}> = {
  instagram: {label: 'Instagram', path: 'M12 7.3A4.7 4.7 0 1 0 16.7 12 4.7 4.7 0 0 0 12 7.3Zm0 7.7a3 3 0 1 1 3-3 3 3 0 0 1-3 3Zm6-7.9a1.1 1.1 0 1 1-1.1-1.1A1.1 1.1 0 0 1 18 7.1ZM21.1 8.2a5.4 5.4 0 0 0-1.5-3.8 5.4 5.4 0 0 0-3.8-1.5C14.3 2.8 9.7 2.8 8.2 2.9a5.4 5.4 0 0 0-3.8 1.5 5.4 5.4 0 0 0-1.5 3.8c-.1 1.5-.1 6.1 0 7.6a5.4 5.4 0 0 0 1.5 3.8 5.4 5.4 0 0 0 3.8 1.5c1.5.1 6.1.1 7.6 0a5.4 5.4 0 0 0 3.8-1.5 5.4 5.4 0 0 0 1.5-3.8c.1-1.5.1-6.1 0-7.6Zm-2 9.2a3 3 0 0 1-1.7 1.7c-1.2.5-4 .4-5.4.4s-4.2.1-5.4-.4a3 3 0 0 1-1.7-1.7c-.5-1.2-.4-4-.4-5.4s-.1-4.2.4-5.4a3 3 0 0 1 1.7-1.7c1.2-.5 4-.4 5.4-.4s4.2-.1 5.4.4a3 3 0 0 1 1.7 1.7c.5 1.2.4 4 .4 5.4s.1 4.2-.4 5.4Z'},
  facebook: {label: 'Facebook', path: 'M14 8.5V6.8c0-.8.2-1.3 1.4-1.3H17V2.6A20 20 0 0 0 14.6 2.5C12.2 2.5 10.6 4 10.6 6.6v1.9H8v3.2h2.6V21.5H14v-9.8h2.6l.4-3.2Z'},
  youtube: {label: 'YouTube', path: 'M21.6 7.2a2.6 2.6 0 0 0-1.8-1.8C18.2 5 12 5 12 5s-6.2 0-7.8.4A2.6 2.6 0 0 0 2.4 7.2 27 27 0 0 0 2 12a27 27 0 0 0 .4 4.8 2.6 2.6 0 0 0 1.8 1.8C5.8 19 12 19 12 19s6.2 0 7.8-.4a2.6 2.6 0 0 0 1.8-1.8A27 27 0 0 0 22 12a27 27 0 0 0-.4-4.8ZM10 15V9l5.2 3Z'},
  pinterest: {label: 'Pinterest', path: 'M12.3 2C6.8 2 4 5.9 4 9.2c0 2 .8 3.7 2.4 4.4.3.1.5 0 .6-.3l.2-.9c.1-.3 0-.4-.2-.7a3.4 3.4 0 0 1-.8-2.3 5.6 5.6 0 0 1 5.9-5.7c3.2 0 5 2 5 4.6 0 3.5-1.5 6.4-3.8 6.4a1.9 1.9 0 0 1-1.9-2.3c.4-1.5 1.1-3.2 1.1-4.3a1.6 1.6 0 0 0-1.6-1.8c-1.3 0-2.3 1.3-2.3 3.1a4.6 4.6 0 0 0 .4 1.9l-1.5 6.5a13 13 0 0 0 0 4.5.2.2 0 0 0 .3.1 12 12 0 0 0 2.1-3.8l.8-3.2a3.3 3.3 0 0 0 2.8 1.4c3.7 0 6.2-3.4 6.2-7.9C20.6 5.2 17.3 2 12.3 2Z'},
};
const handle = (url: string) => { try { return '@' + new URL(url).pathname.split('/').filter(Boolean)[0]; } catch { return 'Follow us'; } };

export function Footer({site}: {site: Site}) {
  const [message, setMessage] = useState<{ok: boolean; text: string} | null>(null), [busy, setBusy] = useState(false);
  const phone = site.phone.replace(/\D/g, '');
  const social = Object.entries(site.social || {});
  return <>
    <section className="newsletter-band" aria-labelledby="nl-title">
      <div className="nl-copy"><h2 id="nl-title">Join Our Inner Circle</h2><p>Be the first to know about new arrivals, exclusive offers and style inspiration.</p></div>
      <form className="nl-form" onSubmit={async e => {
        e.preventDefault(); setBusy(true); setMessage(null); const f = new FormData(e.currentTarget);
        try { await api('subscribe/', 'POST', {email: f.get('email'), consent: true}); setMessage({ok: true, text: 'You’re on the list. Thank you!'}); (e.target as HTMLFormElement).reset(); }
        catch (e2) { setMessage({ok: false, text: err(e2)}); } finally { setBusy(false); }
      }}>
        <div className="nl-row"><input required type="email" name="email" autoComplete="email" aria-label="Your email address" placeholder="Enter your email address"/><button disabled={busy}>{busy ? 'Please wait…' : <>Subscribe <ArrowRight size={16}/></>}</button></div>
        <label className="nl-consent"><input required type="checkbox"/> I agree to receive email updates. <Link href="/info/privacy">Privacy policy</Link></label>
        {message && <p className={message.ok ? 'nl-msg ok' : 'nl-msg'} role="status">{message.ok && <Check size={16}/>}{message.text}</p>}
      </form>
      {site.social?.instagram && <a className="nl-insta" href={site.social.instagram} target="_blank" rel="noopener noreferrer"><svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor" aria-hidden><path d={SOCIAL.instagram.path}/></svg>{handle(site.social.instagram)}</a>}
    </section>
    <footer className="site-footer">
      <div className="ft-grid">
        <div className="ft-brand">
          <Link href="/" className="brand">Aiman <em>Royale</em></Link>
          <p className="ft-tagline">{site.footer_tagline || 'Grace in Every Celebration'}</p>
          {social.length > 0 && <div className="ft-social">{social.map(([k, url]) => SOCIAL[k] && <a key={k} href={url} target="_blank" rel="noopener noreferrer" aria-label={SOCIAL[k].label}><svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden><path d={SOCIAL[k].path}/></svg></a>)}</div>}
          {phone && <a className="ft-chat" href={`https://wa.me/${phone}`} target="_blank" rel="noopener noreferrer"><MessageCircle size={18}/> Let’s talk style</a>}
        </div>
        <div><h4>Shop</h4><Link href="/products?sort=newest">New Arrivals</Link>{site.collections.slice(0, 5).map(c => <Link key={c.id} href={`/collections/${c.slug}`}>{c.name}</Link>)}<Link href="/products">All Collections</Link></div>
        <div><h4>Customer Care</h4><Link href="/account">Track Your Order</Link><Link href="/info/shipping">Shipping &amp; Delivery</Link><Link href="/info/returns">Returns &amp; Exchanges</Link><Link href="/info/size-guide">Size Guide</Link><Link href="/info/privacy">Privacy Policy</Link></div>
        <div><h4>Appointments</h4><Link href="/appointment">Book a Fitting</Link><Link href="/appointment">Style Consultation</Link><Link href="/appointment">Virtual Consultation</Link></div>
        <div className="ft-contact"><h4>Contact Us</h4>
          {phone && <a href={`tel:+${phone}`}><Phone size={16}/> +{phone}</a>}
          {site.email && <a href={`mailto:${site.email}`}><Mail size={16}/> <span>{site.email}</span></a>}
          {site.address && <p><MapPin size={16}/> <span>{site.address}</span></p>}
        </div>
      </div>
      <div className="ft-bottom"><span>© {new Date().getFullYear()} Aiman Royale. All rights reserved.</span><span><Link href="/info/privacy">Privacy Policy</Link><Link href="/info/terms">Terms &amp; Conditions</Link><Link href="/appointment">Contact Us</Link></span></div>
    </footer>
    {phone && <a className="whatsapp-float" href={`https://wa.me/${phone}`} target="_blank" rel="noopener noreferrer" aria-label="Chat with Aiman Royale on WhatsApp"><MessageCircle size={23}/></a>}
  </>;
}
