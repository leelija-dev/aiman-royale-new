'use client';
import Link from 'next/link';
import {useEffect,useState} from 'react';
import {usePathname} from 'next/navigation';
import {Search,Heart,ShoppingBag,UserRound,Menu,X,CalendarDays,ArrowRight,Instagram,MessageCircle,ChevronDown} from 'lucide-react';
import {api,err} from '@/lib/client';
import type {Bag,Site} from '@/lib/types';
import {mainMenu} from '@/lib/menu';
export function Header({site}:{site:Site}){
 const [open,setOpen]=useState(false),[search,setSearch]=useState(false),[count,setCount]=useState(0);
 useEffect(()=>{const update=()=>api<Bag>('cart/').then(b=>setCount(b.items.reduce((n,i)=>n+i.quantity,0))).catch(()=>{});update();window.addEventListener('bag-changed',update);return()=>window.removeEventListener('bag-changed',update);},[]);
 return <><div className="announcement">{site.announcement}<span>Made for your moments</span></div><header className="header"><button className="icon mobile" aria-label="Open menu" onClick={()=>setOpen(!open)}>{open?<X/>:<Menu/>}</button><Link href="/" className="brand">Aiman <em>Royale</em></Link><MainNav open={open} close={()=>setOpen(false)}/><div className="header-actions"><Link href="/appointment" className="appointment-link"><CalendarDays size={15}/> Book Appointment</Link><button aria-label="Search" className="icon" onClick={()=>setSearch(!search)}><Search/></button><Link href="/account" className="icon" aria-label="My account"><UserRound/></Link><Link href="/wishlist" className="icon desktop" aria-label="Wishlist"><Heart/></Link><Link href="/cart" className="icon bag-icon" aria-label={`Shopping bag, ${count} items`}><ShoppingBag/>{count>0&&<b>{count}</b>}</Link></div></header>{search&&<form action="/products" className="search-bar"><Search size={18}/><input autoFocus name="q" aria-label="Search products" placeholder="Find your perfect celebration look…"/><button className="text-button">Search <ArrowRight size={16}/></button></form>}</>;
}
export function Footer({site}:{site:Site}){
 const [message,setMessage]=useState('');const [busy,setBusy]=useState(false);
 return <><section className="newsletter"><div><p className="eyebrow">THE ROYALE EDIT</p><h2>A little inspiration, delivered.</h2><p>New collections, celebration stories and a little something special.</p></div><form onSubmit={async e=>{e.preventDefault();setBusy(true);const f=new FormData(e.currentTarget);try{await api('subscribe/','POST',{email:f.get('email'),consent:true});setMessage('You’re on the list. Thank you!');}catch(e){setMessage(err(e));}finally{setBusy(false);}}}><div className="email-line"><input required type="email" name="email" aria-label="Your email address" placeholder="Your email address"/><button disabled={busy} aria-label="Subscribe"><ArrowRight/></button></div><label className="check tiny"><input required type="checkbox"/> I agree to receive email updates. <Link href="/info/privacy">Privacy policy</Link></label><p role="status">{message}</p></form></section><footer><div><Link href="/" className="brand">Aiman <em>Royale</em></Link><p>Timeless elegance.<br/>Made for your moments.</p><a href={`https://wa.me/${site.phone.replace(/\D/g,'')}`} className="social"><MessageCircle size={20}/> Let’s talk style</a></div><div><h4>Explore</h4>{site.collections.slice(0,4).map(c=><Link key={c.id} href={`/collections/${c.slug}`}>{c.name}</Link>)}<Link href="/products">All Collections</Link></div><div><h4>Here to Help</h4><Link href="/appointment">Book an Appointment</Link><Link href="/info/size-guide">Size & Fit</Link><Link href="/info/shipping">Shipping & Delivery</Link><Link href="/info/returns">Returns & Exchanges</Link><Link href="/account">My Orders</Link></div><div><h4>Visit Our Studio</h4><p>{site.address}</p><a href={`mailto:${site.email}`}>{site.email}</a><a href={`tel:+${site.phone.replace(/\D/g,'')}`}>+{site.phone.replace(/\D/g,'')}</a></div><div className="footer-bottom"><span>© {new Date().getFullYear()} Aiman Royale. All rights reserved.</span><span><Link href="/info/privacy">Privacy</Link> · <Link href="/info/terms">Terms</Link></span><span>SECURE CHECKOUT · MADE IN INDIA</span></div></footer><a className="whatsapp-float" href={`https://wa.me/${site.phone.replace(/\D/g,'')}`} aria-label="Chat with Aiman Royale on WhatsApp"><MessageCircle size={23}/></a></>;
}

function MainNav({open,close}:{open:boolean;close:()=>void}){
 const path=usePathname();
 const [active,setActive]=useState<number|null>(null),[tab,setTab]=useState(0),[mobileItem,setMobileItem]=useState<number|null>(null);
 useEffect(()=>{setActive(null);close();},[path]); // eslint-disable-line react-hooks/exhaustive-deps
 const show=(i:number)=>{setActive(i);setTab(0);};
 return <nav className={open?'nav open':'nav'} aria-label="Main" onMouseLeave={()=>setActive(null)}>
  <ul className="menu-bar">{mainMenu.map((item,i)=>{const current=active===i||(active===null&&path===item.href);return <li key={item.label} onMouseEnter={()=>show(i)} onFocus={()=>show(i)} onKeyDown={e=>{if(e.key==='Escape')setActive(null);}}>
   <div className="menu-top"><Link href={item.href} className={current?'menu-link current':'menu-link'} aria-expanded={active===i} onClick={()=>{setActive(null);close();}}>{item.label}</Link>
    <button className="menu-expand" aria-label={`Show ${item.label} menu`} aria-expanded={mobileItem===i} onClick={()=>setMobileItem(mobileItem===i?null:i)}><ChevronDown size={18}/></button></div>
   <div className={`mega${active===i?' show':''}${mobileItem===i?' mobile-show':''}`}>
    <div className="mega-tabs" role="tablist" aria-label={`${item.label} menu`}>{item.columns.map((c,t)=><button key={c.title} role="tab" type="button" aria-selected={tab===t} className={tab===t?'on':''} onMouseEnter={()=>setTab(t)} onFocus={()=>setTab(t)} onClick={()=>setTab(t)}>{c.title}</button>)}</div>
    <div className="mega-links">{item.columns.map((c,t)=><div key={c.title} role="tabpanel" className={tab===t?'mega-panel on':'mega-panel'}><p className="mega-mobile-title">{c.title}</p><ul>{c.links.map(l=><li key={l.label+l.href}><Link href={l.href} onClick={()=>{setActive(null);close();}}>{l.label}</Link></li>)}</ul></div>)}</div>
    {item.feature&&<Link href={item.feature.href} className="mega-feature" onClick={()=>setActive(null)}><img src={item.feature.image} alt="" loading="lazy" width={260} height={320}/><span>{item.feature.title} <ArrowRight size={16}/></span></Link>}
   </div>
  </li>;})}</ul>
 </nav>;
}
