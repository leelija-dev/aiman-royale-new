import 'server-only';
import {createHash} from 'node:crypto';

// Requests from this server to Django carry a token so they are not counted against the per-visitor
// API limit (every page render and link prefetch comes from this one server IP; without the token a
// handful of visitors used up the limit and pages showed "A little pause").
// Uses INTERNAL_API_TOKEN, or is derived from DJANGO_SECRET_KEY (the same .env is given to both containers).
const secret = process.env.INTERNAL_API_TOKEN || process.env.DJANGO_SECRET_KEY || '';
const token = !secret ? '' : process.env.INTERNAL_API_TOKEN ? secret : createHash('sha256').update('aiman-internal:' + secret).digest('hex');

// Header, menu and footer data (site/) is read on every page and prefetch: keep it for 60 seconds.
const SHORT_CACHE = new Set(['site/']);

export async function get<T>(path:string):Promise<T>{
 const res=await fetch(`${process.env.INTERNAL_API_URL||'http://127.0.0.1:8000'}/api/${path}`,{
  headers:{'X-Forwarded-Proto':process.env.INTERNAL_REQUEST_SCHEME||'http',...(token?{'X-Internal-Token':token}:{})},
  ...(SHORT_CACHE.has(path)?{next:{revalidate:60}}:{cache:'no-store' as const}),
  signal:AbortSignal.timeout(10000)});
 if(!res.ok)throw new Error(res.status===404?'Not found':'The studio is temporarily unavailable. Please try again shortly.');
 return res.json();
}
export const origin=process.env.NEXT_PUBLIC_SITE_URL||'http://localhost:3000';
