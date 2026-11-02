// Shared by server pages and client components (no 'use client').
export type Query = Record<string, string | string[] | undefined>;
// Pictures used for occasions that have no image uploaded in admin.
export const OCCASION_FALLBACK: Record<string, string> = {haldi: '/images/green.webp', wedding: '/images/gharara.webp', party: '/images/purple.webp', festive: '/images/maroon.webp'};
export const occasionImage = (o: {slug: string; image: string}, i = 0) => o.image || OCCASION_FALLBACK[o.slug] || ['/images/rani.webp', '/images/wine.webp', '/images/pink.webp', '/images/navy.webp'][i % 4];
export const list = (v: Query[string]) => (Array.isArray(v) ? v : v ? [v] : []);
export function toParams(q: Query) {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(q)) for (const x of list(v)) p.append(k, x);
  return p;
}
