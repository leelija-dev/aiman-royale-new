import Image from 'next/image';
import Link from 'next/link';
import {notFound} from 'next/navigation';
import {ArrowRight} from 'lucide-react';
import {get, origin} from '@/lib/server';
import {Facets, Product, ProductPage, Site, money, photo} from '@/lib/types';
import {ProductDetails} from '@/components/product-details';

type Props = {params: Promise<{slug: string}>};

export async function generateMetadata({params}: Props) {
  const {slug} = await params;
  try {
    const p = await get<Product>(`products/${slug}/`);
    return {title: p.seo_title || p.name, description: p.seo_description || p.description.slice(0, 160), alternates: {canonical: `/products/${slug}`}, openGraph: {images: [photo(p)]}};
  } catch { return {title: 'Product'}; }
}

export default async function Detail({params}: Props) {
  const {slug} = await params;
  let p: Product;
  try { p = await get<Product>(`products/${slug}/`); }
  catch (e) { if (e instanceof Error && e.message === 'Not found') notFound(); throw e; }
  const col = p.collections[0];
  const [site, sameCol, featured, facets] = await Promise.all([
    get<Site>('site/').catch(() => null),
    col ? get<ProductPage>(`products/?collection=${col.slug}`).catch(() => null) : Promise.resolve(null),
    get<ProductPage>('products/?featured=1').catch(() => null),
    get<Facets>('facets/').catch(() => null),
  ]);
  // Related: same collection first, then featured styles.
  const seen = new Set([p.id]);
  const related = [...(sameCol?.results || []), ...(featured?.results || [])].filter(x => !seen.has(x.id) && seen.add(x.id)).slice(0, 3);
  const swatches = Object.fromEntries((facets?.colours || []).map(c => [c.name.toLowerCase(), c.hex]));
  const json = {'@context': 'https://schema.org', '@type': 'Product', name: p.name, image: p.images.map(i => new URL(i.url, origin).href), description: p.description,
    brand: {'@type': 'Brand', name: 'Aiman Royale'}, offers: {'@type': 'Offer', url: `${origin}/products/${p.slug}`, priceCurrency: 'INR', price: p.price,
      availability: p.variants.some(v => v.stock > 0) ? 'https://schema.org/InStock' : 'https://schema.org/OutOfStock', itemCondition: 'https://schema.org/NewCondition'}};

  return <div className="cp pd-page">
    <script type="application/ld+json" dangerouslySetInnerHTML={{__html: JSON.stringify(json).replace(/</g, '\\u003c')}}/>
    <nav className="pd-crumbs" aria-label="Breadcrumb"><Link href="/">Home</Link> / {col ? <Link href={`/collections/${col.slug}`}>{col.name}</Link> : <Link href="/products">Collections</Link>} / <span>{p.name}</span></nav>
    <ProductDetails product={p} phone={site?.phone || ''} deliveryMessage={site?.delivery_message || 'We deliver across India. Shipping charges and timelines are confirmed at checkout.'} swatches={swatches}/>
    {related.length > 0 && <section className="pd-section pd-related">
      <div className="pd-related-head"><h2>Related Products</h2><Link href={col ? `/collections/${col.slug}` : '/products'} className="pd-link">View All Products <ArrowRight size={14}/></Link></div>
      <div className="pd-related-grid">{related.map(r => <Link key={r.id} href={`/products/${r.slug}`} className="pd-related-card">
        <div><Image src={photo(r)} alt={r.images[0]?.alt || r.name} fill sizes="(max-width:700px) 90vw, 30vw"/></div><h3>{r.name}</h3><strong>{money(r.price)}</strong></Link>)}</div>
    </section>}
  </div>;
}
