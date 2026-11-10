import Link from 'next/link';
import {notFound} from 'next/navigation';
import {JsonLd} from '@/components/json-ld';
import {get} from '@/lib/server';

type P = {title: string; body: string; html: string; updated: string | null; schema?: unknown[]};

export async function generateMetadata({params}: {params: Promise<{slug: string}>}) {
  const {slug} = await params;
  try { const p = await get<P>(`pages/${slug}/`); return {title: p.title, alternates: {canonical: `/info/${slug}`}}; }
  catch { return {title: 'Store Information', robots: {index: false}}; }
}

const LINKS = [['shipping', 'Shipping & Delivery'], ['returns', 'Return & Refund Policy'], ['terms', 'Terms & Conditions'], ['privacy', 'Privacy Policy'], ['contact', 'Contact Us']];

// Policy pages: text from admin → Pages (imported from the live site with `manage.py import_live_pages`).
export default async function Page({params}: {params: Promise<{slug: string}>}) {
  const {slug} = await params;
  let p: P;
  try { p = await get<P>(`pages/${slug}/`); }
  catch (e) { if (e instanceof Error && e.message === 'Not found') notFound(); throw e; }
  return <div className="info-page policy">
    <JsonLd items={p.schema}/>
    <div className="info-head"><p className="eyebrow">Aiman Royale · Here to help</p><h1>{p.title}</h1>
      {p.updated && <p className="policy-updated">Last updated {new Date(p.updated).toLocaleDateString('en-IN', {day: 'numeric', month: 'long', year: 'numeric'})}</p>}</div>
    <div className="policy-grid">
      <nav className="policy-nav" aria-label="Store policies">{LINKS.map(([s, label]) => <Link key={s} href={`/info/${s}`} className={s === slug ? 'on' : ''}>{label}</Link>)}</nav>
      {p.html ? <article className="policy-body" dangerouslySetInnerHTML={{__html: p.html}}/>
        : <article className="policy-body">{p.body.split(/\n\s*\n/).map((b, i) => <p key={i} style={{whiteSpace: 'pre-line'}}>{b}</p>)}</article>}
    </div>
  </div>;
}
