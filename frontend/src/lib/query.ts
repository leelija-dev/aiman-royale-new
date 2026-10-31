// Shared by server pages and client components (no 'use client').
export type Query = Record<string, string | string[] | undefined>;
export const OCCASIONS = ['Haldi', 'Wedding', 'Party', 'Festive'];
export const list = (v: Query[string]) => (Array.isArray(v) ? v : v ? [v] : []);
export function toParams(q: Query) {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(q)) for (const x of list(v)) p.append(k, x);
  return p;
}
