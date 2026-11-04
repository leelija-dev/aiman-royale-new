import Image from 'next/image';
import Link from 'next/link';
import {ArrowRight, Gem, Ruler, Truck, ShieldCheck} from 'lucide-react';
import {get} from '@/lib/server';

export const metadata = {title: 'About Us', description: 'Aiman Royale — designer ethnic wear for women in India, crafted with care since 2017.', alternates: {canonical: '/info/about'}};

// Text comes from admin → Pages → "about" (blank line = new paragraph; a short line on its own = heading).
export default async function About() {
  const page = await get<{title: string; body: string}>('pages/about/').catch(() => ({title: 'About Us', body: ''}));
  const blocks = page.body.split(/\n\s*\n/).map(b => b.trim()).filter(Boolean);
  const [lead, ...rest] = blocks;
  return <div className="info-page about">
    <section className="info-hero"><Image src="/images/hero.webp" alt="" fill priority sizes="100vw"/><div><p className="eyebrow">Our story</p><h1>{page.title}</h1>{lead && <p>{lead}</p>}</div></section>
    <div className="info-body">
      <article className="info-text">{rest.map((b, i) => { const [first, ...more] = b.split('\n');
        return more.length && first.length < 60 ? <section key={i}><h2>{first}</h2><p>{more.join(' ')}</p></section> : <p key={i}>{b.replace(/\n/g, ' ')}</p>; })}</article>
      <aside className="info-values">{[[Gem, 'Designer craftsmanship', 'Hand-finished embroidery and carefully chosen fabrics.'], [Ruler, 'Made to fit', 'Standard sizes or your own measurements.'],
        [ShieldCheck, 'Quality checked', 'Every piece is inspected before it leaves us.'], [Truck, 'Delivered across India', 'Shipped with Delhivery, tracked to your door.']].map(([I, t, d]) => {
        const Icon = I as typeof Gem; return <div key={t as string}><Icon size={22}/><strong>{t as string}</strong><span>{d as string}</span></div>; })}</aside>
    </div>
    <div className="info-cta"><h2>Find your next favourite outfit</h2><div><Link href="/products" className="lh-pill">Shop the collection <ArrowRight size={16}/></Link><Link href="/appointment" className="pd-btn-sm">Book a fitting</Link></div></div>
  </div>;
}
