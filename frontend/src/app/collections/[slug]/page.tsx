import Image from 'next/image';
import Link from 'next/link';
import {notFound} from 'next/navigation';
import {ArrowRight, ArrowDown, ArrowUpRight, CalendarDays, UserRound, Ruler, HelpCircle, Shirt} from 'lucide-react';
import {get} from '@/lib/server';
import {Collection, ProductPage, Facets, Site} from '@/lib/types';
import {mainMenu, type MenuItem, type MenuLink} from '@/lib/menu';
import {Filters, Results} from '@/components/collection-page';
import {toParams, occasionImage, type Query} from '@/lib/query';

type Props = {params: Promise<{slug: string}>; searchParams: Promise<Query>};

export async function generateMetadata({params}: Props) {
  const {slug} = await params;
  try {
    const c = await get<Collection>(`collections/${slug}/`);
    return {title: c.seo_title || `${c.name} for Women`, description: c.seo_description || c.description, alternates: {canonical: `/collections/${slug}`}};
  } catch { return {title: 'Collection'}; }
}

const STORY_FALLBACK = ['/images/maroon.webp', '/images/green.webp', '/images/gharara.webp', '/images/rani.webp', '/images/wine.webp'];
const EMPTY_FACETS: Facets = {occasions: [], sizes: [], colours: [], price: {min: 0, max: 0}, count: 0};

/** "Style" links for the sidebar: this collection's menu item, else the "Collections" menu item. */
function styleLinks(menu: MenuItem[], base: string): MenuLink[] {
  const style = (m?: MenuItem) => m?.columns.find(c => c.title === 'Style')?.links;
  return style(menu.find(m => m.href === base)) || style(menu.find(m => m.href === '/products')) || [];
}

const faqs = (name: string) => [
  {icon: <CalendarDays size={20}/>, q: 'How do I choose the right size?', a: `Every ${name.toLowerCase()} style has a size chart on its product page. Compare your bust, waist and hip measurements, or choose custom fitting and share your measurements with us.`},
  {icon: <HelpCircle size={20}/>, q: 'Can I book a fitting before ordering?', a: 'Yes. Book a studio or video appointment and our team will help you with measurements, fabric and the right silhouette before you order.'},
  {icon: <Shirt size={20}/>, q: 'Which suit style suits my occasion?', a: 'Rich embroidery and heavier fabrics suit weddings and receptions; lighter colours and flowing silhouettes work beautifully for haldi, festive days and parties.'},
];

export default async function CollectionPage({params, searchParams}: Props) {
  const {slug} = await params, q = await searchParams;
  let c: Collection;
  try { c = await get<Collection>(`collections/${slug}/`); }
  catch (e) { if (e instanceof Error && e.message === 'Not found') notFound(); throw e; }
  const apiQuery = toParams(q); apiQuery.set('collection', slug);
  const [data, facets, site] = await Promise.all([
    get<ProductPage>(`products/?${apiQuery}`),
    get<Facets>(`facets/?collection=${encodeURIComponent(slug)}`).catch(() => EMPTY_FACETS),
    get<Site>('site/').catch(() => null),
  ]);
  const base = `/collections/${slug}`;
  const styles = styleLinks(site?.menu?.length ? site.menu : mainMenu, base);
  // Occasion cards: occasions that have products here; if none do yet, every active occasion.
  const withProducts = facets.occasions.filter(o => o.count);
  const occasionCards = (withProducts.length ? withProducts : (site?.occasions || facets.occasions)).slice(0, 4);
  const story = (site?.collections || []).filter(s => s.slug !== slug).slice(0, 3);
  const qa = faqs(c.name);
  const faqLd = {'@context': 'https://schema.org', '@type': 'FAQPage', mainEntity: qa.map(f => ({'@type': 'Question', name: f.q, acceptedAnswer: {'@type': 'Answer', text: f.a}}))};

  return <div className="cp">
    <script type="application/ld+json" dangerouslySetInnerHTML={{__html: JSON.stringify(faqLd)}}/>

    <section className="cp-hero">
      <Image src={c.image || '/images/collection.webp'} alt="" fill priority sizes="100vw"/>
      <div className="cp-hero-copy">
        <nav className="cp-crumbs" aria-label="Breadcrumb"><Link href="/">Home</Link> / <Link href="/products">Collections</Link> / <span>{c.name}</span></nav>
        <p className="cp-eyebrow">The {c.name} Edit</p>
        <h1>{c.name}</h1>
        <p className="cp-tagline">Heritage in every detail. Elegance in every moment.</p>
        <p className="cp-intro">{c.description || `Discover embroidered ${c.name.toLowerCase()}, graceful silhouettes and occasion-ready styles, with personal guidance to help you find your fit.`}</p>
        <a href="#collection" className="cp-explore">Explore the Collection <ArrowDown size={16}/></a>
      </div>
    </section>

    {occasionCards.length > 0 && <section className="cp-wrap cp-occasions">
      <h2>Shop by Occasion</h2>
      <div className="cp-occasion-grid">{occasionCards.map((o, i) =>
        <Link key={o.slug} href={`${base}?occasion=${o.slug}#collection`} className="cp-occasion">
          <div><Image src={occasionImage(o, i)} alt={`${o.name} ${c.name}`} fill sizes="(max-width:700px) 46vw, 24vw"/></div>
          <span>{o.name} {c.name} <ArrowRight size={16}/></span>
        </Link>)}</div>
    </section>}

    <section id="collection" className="cp-wrap cp-shop">
      <Filters base={base} query={q} styles={styles} facets={facets}/>
      <Results key={apiQuery.toString()} data={data} query={q} base={base} extra={{collection: slug}}/>
    </section>

    <section className="cp-fitting">
      <div className="cp-fitting-photo"><Image src="/images/fitting.webp" alt="A stylist measuring a client for a custom fit" fill sizes="(max-width:800px) 100vw, 50vw"/></div>
      <div className="cp-fitting-copy">
        <h2>A style you love.<br/>A fit that feels like you.</h2>
        <p>Discuss your measurements, your occasion and your favourite designs with our team.</p>
        <div className="cp-fitting-actions"><Link href="/appointment" className="cp-light-button">Book a Fitting <ArrowRight size={16}/></Link><Link href="/info/size-guide" className="cp-light-link">View Size Guide <ArrowUpRight size={16}/></Link></div>
        <ul><li><CalendarDays size={20}/>Choose a date.</li><li><UserRound size={20}/>Meet our team.</li><li><Ruler size={20}/>Find your fit.</li></ul>
      </div>
    </section>

    <section className="cp-wrap cp-seo">
      <div>
        <h2>Buy Embroidered {c.name} for Women Online</h2>
        <p>At Aiman Royale, we treat {c.name.toLowerCase()} for women as more than just a collection. They are a reflection of culture, grace, and confidence — designed for every celebration on your calendar.</p>
        <Link href="/info/size-guide" className="cp-text-link">Read the Collection Guide <ArrowRight size={16}/></Link>
      </div>
      <div className="cp-accordion">
        <details><summary>Choosing your silhouette</summary><p>Anarkalis flatter with a flowing flare, straight suits feel tailored and modern, while sharara and palazzo sets bring ease and movement.</p></details>
        <details><summary>Styling for your occasion</summary><p>Choose deeper jewel tones and heavy embroidery for weddings, pastels for haldi and day events, and lighter work for festive gatherings.</p></details>
        <details><summary>Finding your size</summary><p>Use our size guide or choose custom fitting on any eligible style. Our team will confirm measurements before stitching.</p></details>
      </div>
    </section>

    {story.length > 0 && <section className="cp-wrap cp-story">
      <h2>Continue your style story.</h2>
      <div className="cp-story-grid">{story.map((s, i) =>
        <Link key={s.slug} href={`/collections/${s.slug}`} className="cp-story-card">
          <div><Image src={s.image || STORY_FALLBACK[i % STORY_FALLBACK.length]} alt={s.name} fill sizes="(max-width:700px) 100vw, 32vw"/></div>
          <span>{s.name} <ArrowRight size={16}/></span>
        </Link>)}</div>
    </section>}

    <section className="cp-wrap cp-faq">
      <h2>A little guidance, before you choose.</h2>
      <div className="cp-accordion">{qa.map(f => <details key={f.q}><summary><span className="cp-faq-icon">{f.icon}</span>{f.q}</summary><p>{f.a}</p></details>)}</div>
    </section>
  </div>;
}
