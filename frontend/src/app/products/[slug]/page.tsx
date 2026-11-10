import Link from 'next/link';
import {notFound} from 'next/navigation';
import {JsonLd} from '@/components/json-ld';
import {get, origin} from '@/lib/server';
import {Facets, Product, ProductPage, Site, money, photo} from '@/lib/types';
import {ProductDetails} from '@/components/product-details';
import {SimilarItems, RecentlyViewed} from '@/components/product-extras';

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
  const [site, sameCol, featured, facets, newest] = await Promise.all([
    get<Site>('site/').catch(() => null),
    col ? get<ProductPage>(`products/?collection=${col.slug}`).catch(() => null) : Promise.resolve(null),
    get<ProductPage>('products/?featured=1').catch(() => null),
    get<Facets>('facets/').catch(() => null),
    get<ProductPage>(`products/?${col ? `collection=${col.slug}&` : ''}sort=newest`).catch(() => null),
  ]);
  const latest = (newest?.results || []).filter(x => x.id !== p.id).slice(0, 5);
  const faqs = p.faqs || [];
  const today = new Date().toLocaleDateString('en-GB', {day: '2-digit', month: '2-digit', year: 'numeric', timeZone: 'Asia/Kolkata'});
  // Related: same collection first, then featured styles.
  const seen = new Set([p.id]);
  const related = [...(sameCol?.results || []), ...(featured?.results || [])].filter(x => !seen.has(x.id) && seen.add(x.id)).slice(0, 9);
  // Perfectly Paired: featured styles from other collections (fallback: anything not shown above).
  const inCol = new Set((sameCol?.results || []).map(x => x.id));
  const paired = (featured?.results || []).filter(x => x.id !== p.id && !inCol.has(x.id)).slice(0, 6);
  const crumbs = [{label: 'Home', href: '/'}, col ? {label: col.name, href: `/collections/${col.slug}`} : {label: 'Collections', href: '/products'}, {label: p.name, href: `/products/${p.slug}`}];
  const swatches = Object.fromEntries((facets?.colours || []).map(c => [c.name.toLowerCase(), c.hex]));
  const json = {'@context': 'https://schema.org', '@type': 'Product', name: p.name, image: p.images.map(i => new URL(i.url, origin).href), description: p.description,
    brand: {'@type': 'Brand', name: 'Aiman Royale'}, offers: {'@type': 'Offer', url: `${origin}/products/${p.slug}`, priceCurrency: 'INR', price: p.price,
      availability: p.variants.some(v => v.stock > 0) ? 'https://schema.org/InStock' : 'https://schema.org/OutOfStock', itemCondition: 'https://schema.org/NewCondition'}};

  return <div className="cp pd-page">
    <JsonLd items={p.schema}/>
    <script type="application/ld+json" dangerouslySetInnerHTML={{__html: JSON.stringify(json).replace(/</g, '\\u003c')}}/>
    {faqs.length > 0 && <script type="application/ld+json" dangerouslySetInnerHTML={{__html: JSON.stringify({'@context': 'https://schema.org', '@type': 'FAQPage',
      mainEntity: faqs.map(f => ({'@type': 'Question', name: f.q, acceptedAnswer: {'@type': 'Answer', text: f.a}}))}).replace(/</g, '\\u003c')}}/>}
    <ProductDetails product={p} phone={site?.phone || ''} email={site?.email || ''} crumbs={crumbs} paired={paired.length ? paired : related.slice(3, 9)}
      deliveryMessage={site?.delivery_message || 'We deliver across India. Shipping charges and timelines are confirmed at checkout.'} swatches={swatches}/>
    <SimilarItems items={related} hex={swatches}/>
    <RecentlyViewed current={p.slug}/>
    {(faqs.length > 0 || latest.length > 0) && <section className="pd-section pd-faq-wrap">
      {faqs.length > 0 && <div className="pd-faq-card">
        <h2>Frequently Asked <em>(FAQs)</em><br/>On {p.name}</h2><p className="pd-faq-sub">Everything you need to know about our ethnic collection</p>
        <div className="pd-faqs">{faqs.map((f, i) => <details key={i}><summary>{f.q}</summary><p>{f.a}</p></details>)}</div>
        <p className="pd-faq-foot">Need more help? <Link href="/info/contact">Contact our fashion experts</Link></p></div>}
      {latest.length > 0 && <div className="pd-faq-card">
        <h2>Latest Products <em>Collection</em> With Price</h2><p className="pd-faq-sub">Handpicked luxury &amp; festive ethnic wear</p>
        <table className="pd-latest"><thead><tr><th>Products list</th><th>Price (INR)</th></tr></thead>
          <tbody>{latest.map(r => <tr key={r.id}><td><Link href={`/products/${r.slug}`}>{r.name}</Link></td><td>{money(r.price)}</td></tr>)}</tbody></table>
        <div className="pd-latest-foot"><span>Prices inclusive of taxes</span><span className="pd-pill">Last updated: {today}</span></div>
        <p className="pd-faq-foot">Customization &amp; bulk order discounts available | <Link href={col ? `/collections/${col.slug}` : '/products'}>Shop now</Link></p></div>}
    </section>}
  </div>;
}
