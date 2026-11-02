import {Fragment} from 'react';
import Image from 'next/image';
import Link from 'next/link';
import {ArrowRight, PackageCheck, Headphones, Gem, ShieldCheck, Truck, Award, Heart, Star, Sparkles, CalendarDays, Ruler} from 'lucide-react';
import {get} from '@/lib/server';
import {ProductPage} from '@/lib/types';
import {ProductGrid} from '@/components/catalogue';

export const metadata = {alternates: {canonical: '/'}};

// Content is managed in Django admin → Homepage sections. Sections render in their admin order.
type Card = {label: string; title: string; text: string; bullets: string[]; caption: string; href: string; button: string; icon: string; image: string};
type Section = {id: number; kind: string; eyebrow: string; title: string; subtitle: string; text: string; button: {label: string; href: string} | null;
  image: string; product_filter: string; product_count: number; cards: Card[]};

const ICONS = {award: Award, shield: ShieldCheck, truck: Truck, headphones: Headphones, package: PackageCheck, gem: Gem, heart: Heart, star: Star,
  sparkles: Sparkles, calendar: CalendarDays, ruler: Ruler} as const;
const Icon = ({name}: {name: string}) => { const I = ICONS[name as keyof typeof ICONS]; return I ? <I/> : null; };
const IMG = '/images/collection.webp';
const lines = (t: string) => t.split('\n').flatMap((l, i) => i ? [<br key={i}/>, l] : [l]);

function EditCard({c}: {c: Card}) {
  return <Link className="home-edit-card" href={c.href || '/products'}><Image src={c.image || IMG} alt={c.title} fill sizes="(max-width:700px) 46vw,24vw" quality={85}/><div><h3>{c.title}</h3>{c.caption && <span>{c.caption}</span>}</div></Link>;
}
function Heading({s}: {s: Section}) {
  return s.title || s.subtitle ? <div className="home-heading">{s.title && <h2>{s.title}</h2>}{s.subtitle && <p>{s.subtitle}</p>}</div> : null;
}
const Wrap = ({children}: {children: React.ReactNode}) => <div className="home-wrap">{children}</div>;

function render(s: Section, products: Record<number, ProductPage>) {
  const c = s.cards;
  switch (s.kind) {
    case 'hero':
      return <section className="luxury-hero"><Image src={s.image || '/images/home-hero.webp'} alt={s.title.replace(/\n/g, ' ') || 'Aiman Royale'} fill priority sizes="100vw" quality={85}/>
        <div>{s.eyebrow && <p className="eyebrow">{s.eyebrow}</p>}<h1>{lines(s.title)}</h1>{s.subtitle && <p>{s.subtitle}</p>}{s.button && <Link className="button" href={s.button.href}>{s.button.label} <ArrowRight size={16}/></Link>}</div></section>;
    case 'featured':
      return <Wrap><section className="home-four home-featured" aria-label={s.title || 'Featured collections'}>{c.map(x => <EditCard key={x.title + x.href} c={x}/>)}</section></Wrap>;
    case 'collections':
      return <Wrap><section><Heading s={s}/><div className="home-four mini-collections">{c.map(x =>
        <Link key={x.title + x.href} href={x.href || '/products'}><Image src={x.image || IMG} alt={x.title} width={180} height={210}/><div><h3>{x.title}</h3>{x.label && <small>{x.label}</small>}{x.caption && <span>{x.caption}</span>}</div></Link>)}</div>
        {s.button && <div className="center"><Link className="underlink" href={s.button.href}>{s.button.label}</Link></div>}</section></Wrap>;
    case 'cards':
      return <Wrap><section><Heading s={s}/><div className="home-four">{c.map(x => <EditCard key={x.title + x.href} c={x}/>)}</div></section></Wrap>;
    case 'products': {
      const list = products[s.id]?.results.slice(0, s.product_count) || [];
      return list.length ? <Wrap><section className="home-products"><div className="home-row-title"><div>{s.title && <h2>{s.title}</h2>}{s.subtitle && <p>{s.subtitle}</p>}</div>
        {s.button && <Link href={s.button.href} className="underlink">{s.button.label}</Link>}</div><ProductGrid products={list}/></section></Wrap> : null;
    }
    case 'confidence':
      return <section className="home-confidence"><div>{s.title && <h2>{s.title}</h2>}{s.text && <p>{s.text}</p>}</div>{c.map(x => <span key={x.title}><Icon name={x.icon}/>{x.title}{x.text && <small>{x.text}</small>}</span>)}</section>;
    case 'mosaic':
      return <Wrap><section><Heading s={s}/><div className="wedding-mosaic">{c.map(x => <EditCard key={x.title + x.image} c={x}/>)}</div></section></Wrap>;
    case 'banner':
      return <section className="home-sale">{s.image && <Image src={s.image} alt="" fill sizes="100vw"/>}<div>{s.eyebrow && <p>{s.eyebrow}</p>}{s.title && <h2>{s.title}</h2>}{s.text && <p>{s.text}</p>}
        {s.button && <Link className="button outline" href={s.button.href}>{s.button.label}</Link>}</div></section>;
    case 'strip':
      return <Wrap><section className="style-strip" aria-label={s.title || 'Style inspiration'}>{c.map(x =>
        <Link key={x.title + x.image} href={x.href || '/products'}><Image src={x.image || IMG} alt={x.title} width={180} height={200}/><h3>{x.title}</h3>{x.caption && <span>{x.caption}</span>}</Link>)}</section></Wrap>;
    case 'benefits':
      return <Wrap><div className="home-benefits">{c.map(x => <div key={x.title}><Icon name={x.icon}/><span><strong>{x.title}</strong>{x.text && <small>{x.text}</small>}</span></div>)}</div></Wrap>;
    case 'consult':
      return <Wrap><section className="home-consult"><div className="consult-photo"><Image src={s.image || '/images/fitting.webp'} alt={s.title || 'Personal styling appointment'} fill sizes="(max-width:700px) 100vw,45vw"/></div>
        <div>{s.title && <h2>{s.title}</h2>}{s.subtitle && <p>{s.subtitle}</p>}<div className="consult-options">{c.map(x =>
          <article key={x.title + x.label}>{x.label && <small>{x.label}</small>}{x.title && <h3>{x.title}</h3>}{x.text && <p>{x.text}</p>}
            {x.bullets.length > 0 && <ul>{x.bullets.map(b => <li key={b}>{b}</li>)}</ul>}{x.button && <Link href={x.href || '/appointment'} className="button">{x.button}</Link>}</article>)}</div></div></section></Wrap>;
    case 'notes':
      return <Wrap><section><Heading s={s}/><div className="designer-notes">{c.map(x => <article key={x.title}><h3>{x.title}</h3>{x.text && <p>{x.text}</p>}{x.label && <strong>{x.label}</strong>}{x.caption && <small>{x.caption}</small>}</article>)}</div></section></Wrap>;
    case 'story':
      return <Wrap><section className="home-story">{s.title && <h2>{s.title}</h2>}<p>{s.text} {s.button && <Link className="underlink" href={s.button.href}>{s.button.label}</Link>}</p></section></Wrap>;
    default:
      return null;
  }
}

export default async function Home() {
  const {sections} = await get<{sections: Section[]}>('home/');
  const rows = sections.filter(s => s.kind === 'products');
  const pages = await Promise.all(rows.map(s => get<ProductPage>(`products/?${s.product_filter}`).catch(() => null)));
  const products: Record<number, ProductPage> = {};
  rows.forEach((s, i) => { if (pages[i]) products[s.id] = pages[i]!; });
  return <div className="royale-home">{sections.map(s => <Fragment key={s.id}>{render(s, products)}</Fragment>)}</div>;
}
