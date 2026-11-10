import {Fragment} from 'react';
import Image from 'next/image';
import {JsonLd} from '@/components/json-ld';
import Link from 'next/link';
import {ArrowRight, PackageCheck, Headphones, Gem, ShieldCheck, Truck, Award, Heart, Star, Sparkles, CalendarDays, Ruler, Check, Plus, ShoppingBag, Video, UserRound} from 'lucide-react';
import {get} from '@/lib/server';
import {ProductPage, type Site} from '@/lib/types';
import {Card} from '@/components/collection-page';
import {CategoryDetails} from '@/components/category-details';
import {Scroller, HomeSizeGuide, NotesCarousel, HeroSlider, type SizeGuideData} from '@/components/home-extras';

export const metadata = {alternates: {canonical: '/'}};

// Content is managed in Django admin → Homepage sections. Sections render in their admin order.
type Card = {label: string; title: string; text: string; bullets: string[]; caption: string; href: string; button: string; icon: string; image: string;
  mobile_image?: string; alt?: string; image_title?: string};
type Section = {id: number; kind: string; eyebrow: string; title: string; subtitle: string; text: string; button: {label: string; href: string} | null;
  image: string; product_filter: string; product_count: number; cards: Card[];
  href?: string; mobile_image?: string; alt?: string; image_title?: string};

const ICONS = {award: Award, shield: ShieldCheck, truck: Truck, headphones: Headphones, package: PackageCheck, gem: Gem, heart: Heart, star: Star,
  sparkles: Sparkles, calendar: CalendarDays, ruler: Ruler, video: Video, user: UserRound, check: Check} as const;
// Thin line icons for the appointment band (video call / dress).
const VideoIcon = () => <svg viewBox="0 0 48 48" width="54" height="54" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden><rect x="5" y="12" width="27" height="24" rx="3"/><path d="m32 21 11-6v18l-11-6"/><circle cx="18.5" cy="21" r="4"/><path d="M11 31c1.6-3.2 4.3-4.8 7.5-4.8S24.4 27.8 26 31"/></svg>;
const DressIcon = () => <svg viewBox="0 0 48 48" width="54" height="54" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d="M19 4v7M29 4v7"/><path d="M19 11c1 2.5 2.8 4 5 4s4-1.5 5-4"/><path d="M19 11l-2 9 3.5 3L9 43h30L27.5 23l3.5-3-2-9"/><path d="M17 20h14M14 36c3 1.5 6.5 2 10 2s7-.5 10-2"/></svg>;
const Icon = ({name}: {name: string}) => { const I = ICONS[name as keyof typeof ICONS]; return I ? <I/> : null; };
const IMG = '/images/collection.webp';
const lines = (t: string) => t.split('\n').flatMap((l, i) => i ? [<br key={i}/>, l] : [l]);

function EditCard({c}: {c: Card}) {
  return <Link className="home-edit-card" href={c.href || '/products'}><Image src={c.image || IMG} alt={c.title} fill sizes="(max-width:700px) 46vw,24vw" quality={85}/><div>{c.label && <small>{c.label}</small>}<h3>{c.title}</h3>{c.caption && <span>{c.caption}</span>}</div></Link>;
}
// "**bold**" and new lines in admin text.
const rich = (t: string) => t.split('\n').map((line, i) => <Fragment key={i}>{i > 0 && <br/>}{line.split(/\*\*(.+?)\*\*/).map((x, j) => j % 2 ? <b key={j}>{x}</b> : x)}</Fragment>);
function Head({s, cls = ''}: {s: Section; cls?: string}) {
  return s.title || s.subtitle ? <div className={`lh-head ${cls}`}>{s.eyebrow && <small>{s.eyebrow}</small>}{s.title && <h2>{lines(s.title)}</h2>}{s.subtitle && <p>{s.subtitle}</p>}</div> : null;
}
const Wrap = ({children, cls = ''}: {children: React.ReactNode; cls?: string}) => <div className={`home-wrap ${cls}`}>{children}</div>;
const ProductRow = ({s, list}: {s: Section; list: ProductPage['results']}) =>
  <Wrap><section className="lh-products"><div className="lh-row-head">{s.title && <h2>{s.title}</h2>}{s.button && <Link href={s.button.href}>{s.button.label.replace(/\s*→$/, '')} <ArrowRight size={16}/></Link>}</div>
    <Scroller label={s.title}><div className="home-row">{list.map(p => <Card key={p.id} p={p}/>)}</div></Scroller></section></Wrap>;

function render(s: Section, products: Record<number, ProductPage>, sizeGuide: SizeGuideData | null) {
  const c = s.cards;
  switch (s.kind) {
    case 'hero':
      return <div className="lh-hero-wrap"><HeroSlider slides={[
        ...(s.image || s.title ? [{eyebrow: s.eyebrow, title: s.title, subtitle: s.subtitle, button: s.button, image: s.image || '/images/home-hero.webp', mobile: s.mobile_image, alt: s.alt, imageTitle: s.image_title, href: s.href}] : []),
        ...c.map(x => ({eyebrow: x.label, title: x.title, subtitle: x.caption || x.text, button: x.button ? {label: x.button, href: x.href || '/products'} : null, image: x.image || '/images/home-hero.webp',
          mobile: x.mobile_image, alt: x.alt, imageTitle: x.image_title, href: x.href}))]}/></div>;
    case 'featured': // circular "Most Loved" row — shown on phones, like the live site
      return <Wrap cls="lh-mobile-only lh-loved-wrap"><section className="lh-loved" aria-label={s.title || 'Most loved'}>{c.map(x =>
        <Link key={x.title + x.href} href={x.href || '/products'}><span><Image src={x.image || IMG} alt="" fill sizes="96px"/></span><strong>{x.title}</strong>{x.caption && <small>{x.caption}</small>}</Link>)}</section></Wrap>;
    case 'carousel': // old phone-only promo slider: not shown, phones use the main hero slider only
      return null;
    case 'collections':
      return <Wrap><section className="lh-sec"><Head s={s} cls="center pink"/>
        <Scroller label={s.title}><div className="lh-show">{c.map(x => <Link key={x.title + x.href} href={x.href || '/products'} className="lh-show-card">
          <Image src={x.image || IMG} alt={x.title} fill sizes="(max-width:700px) 60vw, 20vw"/>{x.label && <i>{x.label}</i>}<div><h3>{x.title}</h3>{x.caption && <span>{x.caption}</span>}</div></Link>)}</div></Scroller>
        {s.button && <div className="center"><Link className="lh-pill" href={s.button.href}>{s.button.label} <ArrowRight size={16}/></Link></div>}</section></Wrap>;
    case 'cards':
      return <Wrap><section className="lh-sec"><Head s={s} cls="center"/>
        <Scroller label={s.title}><div className="lh-elegance">{c.map((x, k) => <Link key={x.title + k} href={x.href || '/products'}>
          <span><Image src={x.image || IMG} alt={x.title} fill sizes="140px"/></span><h3>{x.title}</h3><small>{x.caption || 'Explore'} <ArrowRight size={12}/></small></Link>)}</div></Scroller></section></Wrap>;
    case 'occasions':
      return c.length ? <Wrap><section className="lh-sec ar-occ"><Head s={s} cls="center"/>
        <Scroller label={s.title || 'Shop by occasion'}><div className="ar-occ-row">{c.map(x => <Link key={x.href} href={x.href} className="ar-occ-card">
          <Image src={x.image || IMG} alt={x.alt || x.title} title={x.image_title || undefined} fill sizes="(max-width:700px) 62vw, 25vw"/>
          <div><h3>{x.title}</h3><span>{x.button || 'Shop Now'}</span></div></Link>)}</div></Scroller></section></Wrap> : null;
    case 'products': {
      const list = products[s.id]?.results.slice(0, s.product_count) || [];
      return list.length ? <ProductRow s={s} list={list}/> : null;
    }
    case 'confidence': {
      const bullets = c.filter(x => !x.image), tiles = c.filter(x => x.image).slice(0, 4);
      return <Wrap><section className="lh-conf">
        <div className="lh-conf-copy">{s.title && <h2>{s.title}</h2>}{s.text && <p>{s.text}</p>}
          <ul>{bullets.map(x => <li key={x.title}><Check size={13}/>{x.title}</li>)}</ul></div>
        {tiles.length > 0 && <div className="lh-conf-art">{tiles.map((x, k) => <Link key={x.title} href={x.href || '/products'} className={`t${k}`} aria-label={x.title}><Image src={x.image} alt="" fill sizes="160px"/>{x.label && <em>{x.label}</em>}</Link>)}
          {s.eyebrow && <div className="lh-conf-pill"><span>{tiles.slice(0, 2).map(x => <Image key={x.title} src={x.image} alt="" width={26} height={26}/>)}</span><div><b>{s.eyebrow}</b><small>{tiles.length}+ stunning designs</small></div><ArrowRight size={14}/></div>}</div>}
        {(s.subtitle || s.button) && <div className="lh-conf-cta">{s.subtitle && <h3>{s.subtitle}</h3>}{s.button && <Link className="lh-grad-btn" href={s.button.href}><ShoppingBag size={16}/> {s.button.label}</Link>}</div>}
      </section></Wrap>;
    }
    case 'mosaic':
      return <Wrap><section className="lh-sec"><Head s={s} cls="left line"/>
        <Scroller label={s.title}><div className="lh-tall">{c.map(x => <Link key={x.title + x.image} href={x.href || '/products'} className="lh-tall-card">
          <Image src={x.image || IMG} alt={x.title} fill sizes="(max-width:700px) 70vw, 24vw"/><div><h3>{x.title}</h3><span>{x.caption || 'Shop now'}</span></div></Link>)}</div></Scroller></section></Wrap>;
    case 'banner':
      if (c.length) return <Wrap><section className="lh-sale"><div className="lh-sale-copy">{s.eyebrow && <small>{s.eyebrow}</small>}{s.title && <h2>{lines(s.title)}</h2>}{s.text && <p>{rich(s.text)}</p>}
        {s.button && <Link className="lh-grad-btn square" href={s.button.href}>{s.button.label} <ArrowRight size={14}/></Link>}</div>
        <Scroller label={s.title}><div className="lh-sale-cards">{c.map(x => <Link key={x.title + x.image} href={x.href || '/products'}><Image src={x.image || IMG} alt={x.title} fill sizes="(max-width:700px) 60vw, 18vw"/><div><h3>{x.title}</h3>{x.caption && <span>{x.caption}</span>}</div></Link>)}</div></Scroller></section></Wrap>;
      return <section className="home-sale">{s.image && <Image src={s.image} alt="" fill sizes="100vw"/>}<div>{s.eyebrow && <p>{s.eyebrow}</p>}{s.title && <h2>{s.title}</h2>}{s.text && <p>{rich(s.text)}</p>}
        {s.button && <Link className="button outline" href={s.button.href}>{s.button.label}</Link>}</div></section>;
    case 'strip':
      return <Wrap><section className="style-strip" aria-label={s.title || 'Style inspiration'}>{c.map(x =>
        <Link key={x.title + x.image} href={x.href || '/products'}><Image src={x.image || IMG} alt={x.title} width={180} height={200}/><h3>{x.title}</h3>{x.caption && <span>{x.caption}</span>}</Link>)}</section></Wrap>;
    case 'benefits':
      return <Wrap><div className="lh-benefits">{c.map(x => <div key={x.title}><Icon name={x.icon}/><strong>{x.title}</strong>{x.text && <small>{x.text}</small>}</div>)}</div></Wrap>;
    case 'duo':
      return <Wrap><section className="lh-sec"><Head s={s} cls="center small"/><div className="lh-duo">{c.map(x => <Link key={x.title + x.href} href={x.href || '/products'}>
        <Image src={x.image || IMG} alt={x.title} fill sizes="(max-width:700px) 100vw, 50vw"/><div><h3>{x.title}</h3>{x.text && <p>{x.text}</p>}<span>{x.caption || 'Shop now'} <ArrowRight size={14}/></span></div></Link>)}</div></section></Wrap>;
    case 'consult':
      return <section className="ar-consult" aria-label={s.title || 'Book an appointment'}>{s.title && <h2 className="ar-consult-title">{s.title}</h2>}
        <div className="ar-consult-row">{c.map(x =>
          <article key={x.title + x.label}><span className="ar-consult-ico">{x.icon === 'dress' ? <DressIcon/> : x.icon === 'video' || !x.icon ? <VideoIcon/> : <Icon name={x.icon}/>}</span>
            <div>{x.title && <h3>{x.title}</h3>}{x.text && <p>{x.text}</p>}
              <Link href={x.href || '/appointment'} className="ar-consult-btn">{x.button || 'Book an Appointment'}</Link></div></article>)}</div></section>;
    case 'notes':
      return c.length ? <NotesCarousel badge={s.eyebrow || s.title} image={s.image || '/images/rani.webp'} notes={c.map(x => ({title: x.title, text: x.text, name: x.label, role: x.caption}))}/> : null;
    case 'story':
      return <Wrap><section className="home-story lh-story">{s.title && <h2>{s.title}</h2>}{/<[a-z][^>]*>/i.test(s.text) ? <CategoryDetails html={s.text} bare/> : <p>{s.text}</p>}
        {s.button && <Link className="underlink" href={s.button.href}>{s.button.label}</Link>}</section></Wrap>;
    case 'sizeguide':
      return sizeGuide ? <Wrap><HomeSizeGuide title={s.title || 'Size Guide'} guide={sizeGuide}/></Wrap> : null;
    default:
      return null;
  }
}

export default async function Home() {
  const {sections} = await get<{sections: Section[]}>('home/');
  const sizeGuide = sections.some(x => x.kind === 'sizeguide') ? await get<SizeGuideData>('size-guide/').catch(() => null) : null;
  const rows = sections.filter(s => s.kind === 'products');
  const pages = await Promise.all(rows.map(s => get<ProductPage>(`products/?${s.product_filter}`).catch(() => null)));
  const products: Record<number, ProductPage> = {};
  rows.forEach((s, i) => { if (pages[i]) products[s.id] = pages[i]!; });
  const site = await get<Site>('site/').catch(() => null);
  return <div className="royale-home"><JsonLd items={site?.schema}/>{sections.map(s => <Fragment key={s.id}>{render(s, products, sizeGuide)}</Fragment>)}</div>;
}
