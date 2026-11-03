import Image from 'next/image';
import Link from 'next/link';
import {notFound} from 'next/navigation';
import {ArrowRight, ArrowDown, ArrowUpRight, CalendarDays, UserRound, Ruler, HelpCircle, Shirt} from 'lucide-react';
import {get} from '@/lib/server';
import {Collection, ProductPage, Facets, Site, CategoryContent} from '@/lib/types';
import {mainMenu, type MenuItem, type MenuLink} from '@/lib/menu';
import {Filters, Results} from '@/components/collection-page';
import {CategoryDetails} from '@/components/category-details';
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

const FAQ_ICONS = [<CalendarDays key="a" size={20}/>, <HelpCircle key="b" size={20}/>, <Shirt key="c" size={20}/>];
const STEP_ICONS = [<CalendarDays key="a" size={20}/>, <UserRound key="b" size={20}/>, <Ruler key="c" size={20}/>];

/** Used only if the API is an older version without page text. */
const fallbackContent = (name: string): CategoryContent => ({
  eyebrow: `The ${name} Edit`, tagline: 'Heritage in every detail. Elegance in every moment.',
  seo_heading: `Buy Embroidered ${name} for Women Online`, seo_body: '', faqs: [], guides: [],
  fitting: {title: 'A style you love.\nA fit that feels like you.', text: 'Discuss your measurements, your occasion and your favourite designs with our team.', button: 'Book a Fitting', steps: ['Choose a date.', 'Meet our team.', 'Find your fit.'], image: ''},
});
const lines = (t: string) => t.split('\n').flatMap((l, i) => i ? [<br key={i}/>, l] : [l]);

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
  // Sidebar 'Collection' list: collections that have products in this category (with counts),
  // otherwise this category's menu styles.
  const related = (facets.collections || []).filter(c => c.slug !== slug).map(c => ({label: c.name, href: `/collections/${c.slug}`, count: c.count}));
  const styles = related.length ? related : styleLinks(site?.menu?.length ? site.menu : mainMenu, base);
  // Occasion cards: occasions that have products here; if none do yet, every active occasion.
  const withProducts = facets.occasions.filter(o => o.count);
  const occasionCards = (withProducts.length ? withProducts : (site?.occasions || facets.occasions)).slice(0, 4);
  const story = (site?.collections || []).filter(s => s.slug !== slug).slice(0, 3);
  const t = c.content || fallbackContent(c.name), qa = t.faqs, f = t.fitting;
  const faqLd = {'@context': 'https://schema.org', '@type': 'FAQPage', mainEntity: qa.map(x => ({'@type': 'Question', name: x.question, acceptedAnswer: {'@type': 'Answer', text: x.answer}}))};

  return <div className="cp">
    {qa.length > 0 && <script type="application/ld+json" dangerouslySetInnerHTML={{__html: JSON.stringify(faqLd)}}/>}

    <section className="cp-hero">
      <Image src={c.image || '/images/collection.webp'} alt="" fill priority sizes="100vw"/>
      <div className="cp-hero-copy">
        <nav className="cp-crumbs" aria-label="Breadcrumb"><Link href="/">Home</Link> / <Link href="/products">Collections</Link> / <span>{c.name}</span></nav>
        <p className="cp-eyebrow">{t.eyebrow}</p>
        <h1>{c.name}</h1>
        {t.tagline && <p className="cp-tagline">{t.tagline}</p>}
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
      <Results key={apiQuery.toString()} data={data} query={q} base={base} extra={{collection: slug}} facets={facets}/>
    </section>

    <section className="cp-fitting">
      <div className="cp-fitting-photo"><Image src={f.image || '/images/fitting.webp'} alt="A stylist measuring a client for a custom fit" fill sizes="(max-width:800px) 100vw, 50vw"/></div>
      <div className="cp-fitting-copy">
        <h2>{lines(f.title)}</h2>
        {f.text && <p>{f.text}</p>}
        <div className="cp-fitting-actions"><Link href="/appointment" className="cp-light-button">{f.button} <ArrowRight size={16}/></Link><Link href="/info/size-guide" className="cp-light-link">View Size Guide <ArrowUpRight size={16}/></Link></div>
        {f.steps.length > 0 && <ul>{f.steps.map((st, i) => <li key={st}>{STEP_ICONS[i % 3]}{st}</li>)}</ul>}
      </div>
    </section>

    <section className="cp-wrap cp-seo">
      <div>
        <h2>{t.seo_heading}</h2>
        {t.seo_body.split(/\n{2,}/).filter(Boolean).map((para, i) => <p key={i}>{para}</p>)}
        <Link href="/info/size-guide" className="cp-text-link">Read the Collection Guide <ArrowRight size={16}/></Link>
      </div>
      {t.guides.length > 0 && <div className="cp-accordion">{t.guides.map(g => <details key={g.question}><summary>{g.question}</summary><p>{g.answer}</p></details>)}</div>}
    </section>

    {story.length > 0 && <section className="cp-wrap cp-story">
      <h2>Continue your style story.</h2>
      <div className="cp-story-grid">{story.map((s, i) =>
        <Link key={s.slug} href={`/collections/${s.slug}`} className="cp-story-card">
          <div><Image src={s.image || STORY_FALLBACK[i % STORY_FALLBACK.length]} alt={s.name} fill sizes="(max-width:700px) 100vw, 32vw"/></div>
          <span>{s.name} <ArrowRight size={16}/></span>
        </Link>)}</div>
    </section>}

    {qa.length > 0 && <section className="cp-wrap cp-faq">
      <h2>A little guidance, before you choose.</h2>
      <div className="cp-accordion">{qa.map((x, i) => <details key={x.question}><summary><span className="cp-faq-icon">{FAQ_ICONS[i % 3]}</span>{x.question}</summary><p>{x.answer}</p></details>)}</div>
    </section>}
    {t.details && <CategoryDetails html={t.details}/>}
  </div>;
}
