import Image from 'next/image';
import Link from 'next/link';
import {ArrowRight, ArrowUpRight, Shirt, Sparkles, ShieldCheck} from 'lucide-react';
import {get} from '@/lib/server';
import {ProductPage, Facets, Site, ShopPage} from '@/lib/types';
import {Filters, Results} from '@/components/collection-page';
import {toParams, list, type Query} from '@/lib/query';

export const metadata = {title: 'All Products', description: 'Shop designer ethnic wear for women: anarkali suits, salwar kameez, palazzo suits, lehengas, Indo-western and co-ord sets.', alternates: {canonical: '/products'}};
const EMPTY: Facets = {occasions: [], sizes: [], colours: [], price: {min: 0, max: 0}, count: 0};
// Used only if the API does not send page text (older backend). Edit the live text in admin → Site settings → All Products page.
const FALLBACK: ShopPage = {eyebrow: 'The Aiman Royale Collection', title: 'Find your occasion.\nDiscover your style.', text: 'Explore designer ethnic wear, from statement Anarkalis to festive suits and elegant occasion wear.',
  image: '', heading: 'All Products', subheading: 'Explore the collection', fitting: {title: 'Love the dress.\nLet’s find your fit.', text: 'Speak with our team about sizing, styling and your occasion before you choose.', note: 'Choose a date and request your appointment.', image: ''},
  trust: [{title: 'Personal Fit Guidance', text: 'Expert advice for your perfect look'}, {title: 'Designer Ethnic Wear', text: 'Curated for every occasion'}, {title: 'Secure Shopping', text: 'Safe & trusted payments'}]};
const TRUST_ICONS = [<Shirt key="a" size={34} strokeWidth={1.3}/>, <Sparkles key="b" size={34} strokeWidth={1.3}/>, <ShieldCheck key="c" size={34} strokeWidth={1.3}/>];
const lines = (t: string) => t.split('\n').flatMap((l, i) => i ? [<br key={i}/>, l] : [l]);

export default async function Products({searchParams}: {searchParams: Promise<Query>}) {
  const q = await searchParams, params = toParams(q);
  const [data, facets, site] = await Promise.all([
    get<ProductPage>(`products/?${params}`),
    get<Facets>('facets/').catch(() => EMPTY),
    get<Site>('site/').catch(() => null),
  ]);
  const t = site?.shop_page || FALLBACK;
  const picked = list(q.collection);
  const tabs = (facets.collections || []).slice(0, 6);
  const tabHref = (slug?: string) => { const p = toParams(q); p.delete('collection'); p.delete('page'); if (slug) p.set('collection', slug); return `/products${p.size ? `?${p}` : ''}#collection`; };

  return <div className="cp shop">
    <section className="shop-hero">
      <div className="shop-hero-copy">
        <p className="cp-eyebrow">{t.eyebrow}</p>
        <h1>{lines(t.title)}</h1>
        {t.text && <p>{t.text}</p>}
      </div>
      <div className="shop-hero-image"><Image src={t.image || '/images/collection.webp'} alt="" fill priority sizes="(max-width:800px) 100vw, 52vw"/></div>
    </section>

    {tabs.length > 0 && <nav className="shop-tabs" aria-label="Categories">
      <Link href={tabHref()} scroll={false} className={picked.length ? '' : 'on'}>All Products</Link>
      {tabs.map(c => <Link key={c.slug} href={tabHref(c.slug)} scroll={false} className={picked.length === 1 && picked[0] === c.slug ? 'on' : ''}>{c.name}</Link>)}
    </nav>}

    <section id="collection" className="cp-wrap cp-shop">
      <Filters base="/products" query={q} facets={facets} variant="shop"/>
      <Results key={params.toString()} data={data} query={q} base="/products" facets={facets} heading={t.heading} subheading={t.subheading} paging="pages"/>
    </section>

    <section className="shop-fitting">
      <div className="shop-fitting-photo"><Image src={t.fitting.image || '/images/fitting.webp'} alt="A stylist fitting a client" fill sizes="(max-width:800px) 100vw, 53vw"/></div>
      <div className="shop-fitting-copy">
        <h2>{lines(t.fitting.title)}</h2>
        {t.fitting.text && <p>{t.fitting.text}</p>}
        <div className="shop-fitting-actions"><Link href="/appointment" className="button">Book a Fitting <ArrowRight size={16}/></Link><Link href="/info/size-guide" className="button outline">View Size Guide <ArrowUpRight size={16}/></Link></div>
        {t.fitting.note && <small>{t.fitting.note}</small>}
      </div>
    </section>

    {t.trust.length > 0 && <section className="shop-trust">{t.trust.map((x, i) => <div key={x.title}>{TRUST_ICONS[i % 3]}<span><strong>{x.title}</strong>{x.text && <small>{x.text}</small>}</span></div>)}</section>}
  </div>;
}
