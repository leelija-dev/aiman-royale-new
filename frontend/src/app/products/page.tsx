import Image from 'next/image';
import Link from 'next/link';
import {get} from '@/lib/server';
import {ProductPage, Facets, Site} from '@/lib/types';
import {mainMenu} from '@/lib/menu';
import {Filters, Results} from '@/components/collection-page';
import {toParams, type Query} from '@/lib/query';

export const metadata = {title: 'All Collections', alternates: {canonical: '/products'}};
const EMPTY: Facets = {occasions: [], sizes: [], colours: [], price: {min: 0, max: 0}, count: 0};

export default async function Products({searchParams}: {searchParams: Promise<Query>}) {
  const q = await searchParams, params = toParams(q);
  const [data, facets, site] = await Promise.all([
    get<ProductPage>(`products/?${params}`),
    get<Facets>('facets/').catch(() => EMPTY),
    get<Site>('site/').catch(() => null),
  ]);
  const menu = site?.menu?.length ? site.menu : mainMenu;
  const styles = menu.find(m => m.href === '/products')?.columns.find(c => c.title === 'Style')?.links || [];
  return <div className="cp">
    <section className="cp-hero">
      <Image src="/images/collection.webp" alt="" fill priority sizes="100vw"/>
      <div className="cp-hero-copy">
        <nav className="cp-crumbs" aria-label="Breadcrumb"><Link href="/">Home</Link> / <span>Collections</span></nav>
        <p className="cp-eyebrow">The Aiman Royale Collection</p>
        <h1>All Collections</h1>
        <p className="cp-tagline">For every version of beautiful you.</p>
        <p className="cp-intro">Designer ethnic wear, thoughtfully selected. Find the piece that tells your story.</p>
        <a href="#collection" className="cp-explore">Explore the Collection</a>
      </div>
    </section>
    <section id="collection" className="cp-wrap cp-shop">
      <Filters base="/products" query={q} styles={styles} facets={facets}/>
      <Results key={params.toString()} data={data} query={q} base="/products"/>
    </section>
  </div>;
}
