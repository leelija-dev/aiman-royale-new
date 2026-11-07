'use client';
import Image from 'next/image';
import Link from 'next/link';
import {useEffect, useState} from 'react';
import {Card} from '@/components/collection-page';
import {money, type Product} from '@/lib/types';

type Seen = {slug: string; name: string; price: string; mrp: string; image: string};
const KEY = 'ar-recent';

/** Stores a product at the front of the "Recently Viewed" list (max 12). */
export function rememberViewed(p: Seen) {
  try {
    const list: Seen[] = JSON.parse(localStorage.getItem(KEY) || '[]');
    localStorage.setItem(KEY, JSON.stringify([p, ...list.filter(x => x.slug !== p.slug)].slice(0, 12)));
  } catch {}
}

export function RecentlyViewed({current}: {current: string}) {
  const [items, setItems] = useState<Seen[]>([]);
  useEffect(() => { try { setItems((JSON.parse(localStorage.getItem(KEY) || '[]') as Seen[]).filter(x => x.slug !== current && x.image)); } catch {} }, [current]);
  if (!items.length) return null;
  return <section className="az-section az-recent" aria-labelledby="az-recent-title">
    <h2 id="az-recent-title">Recently Viewed</h2>
    <div className="az-recent-row">{items.map(x => {
      const off = Number(x.mrp) > Number(x.price) ? Math.round((1 - Number(x.price) / Number(x.mrp)) * 100) : 0;
      return <Link key={x.slug} href={`/products/${x.slug}`} className="az-recent-card">
        <span><Image src={x.image} alt="" fill sizes="(max-width:700px) 40vw, 180px"/></span>
        <strong>Aiman Royale</strong><small>{x.name}</small>
        <em>{money(x.price)}{off > 0 && <> <del>{money(x.mrp)}</del> <b>{off}% OFF</b></>}</em>
      </Link>;
    })}</div>
  </section>;
}

/** "Similar Items" grid with quick filter chips (by collection / under a price). */
export function SimilarItems({items, hex = {}}: {items: Product[]; hex?: Record<string, string>}) {
  const cols = [...new Set(items.flatMap(p => p.collections.map(c => c.name)))].slice(0, 5);
  const [chip, setChip] = useState('All');
  if (!items.length) return null;
  const median = [...items].map(p => Number(p.price)).sort((a, b) => a - b)[Math.floor(items.length / 2)];
  const under = `Under ${money(Math.ceil(median / 500) * 500)}`;
  const chips = ['All', ...cols, ...(items.length > 3 ? [under] : [])];
  const shown = items.filter(p => chip === 'All' || (chip === under ? Number(p.price) <= Math.ceil(median / 500) * 500 : p.collections.some(c => c.name === chip)));
  return <section className="az-section" aria-labelledby="az-similar-title">
    <h2 id="az-similar-title">Similar Items</h2>
    {chips.length > 1 && <div className="cp-chips az-chips" role="group" aria-label="Filter similar items">{chips.map(c => <button key={c} type="button" aria-pressed={chip === c} className={chip === c ? 'on' : ''} onClick={() => setChip(c)}>{c}</button>)}</div>}
    <div className="cp-grid grid az-similar">{shown.map(p => <Card key={p.id} p={p} hex={hex}/>)}</div>
  </section>;
}
