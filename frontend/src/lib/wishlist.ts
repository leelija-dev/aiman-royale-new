'use client';
import {useEffect, useState} from 'react';
import {api} from '@/lib/client';
import type {Product} from '@/lib/types';

// One shared copy of the customer's wishlist for every heart on the page.
// null = not loaded yet; signedIn=false = visitor is not signed in.
let ids: Set<number> | null = null;
let signedIn = true;
let loading: Promise<void> | null = null;
const EVENT = 'wishlist-changed';
const PENDING = 'ar-pending-wish';

/** Login URL that brings the visitor back to this page afterwards. */
export const loginHere = () => `/login?next=${encodeURIComponent(window.location.pathname + window.location.search)}`;

function toast(text: string) {
  const el = document.createElement('div');
  el.className = 'ar-toast'; el.setAttribute('role', 'status'); el.textContent = text;
  document.body.appendChild(el);
  setTimeout(() => el.classList.add('out'), 2600); setTimeout(() => el.remove(), 3200);
}

/** After sign-in: save the style the visitor tried to wishlist while signed out. */
async function savePending() {
  let id = 0;
  try { id = Number(localStorage.getItem(PENDING)) || 0; localStorage.removeItem(PENDING); } catch {}
  if (!id || ids?.has(id)) return;
  try { await api('wishlist/', 'POST', {product: id}); ids!.add(id); toast('Added to your wishlist ♥'); } catch {}
}

function load(force = false) {
  if (!force && (ids || loading)) return loading || Promise.resolve();
  loading = api<Product[]>('wishlist/')
    .then(async list => { ids = new Set(list.map(p => p.id)); signedIn = true; await savePending(); })
    .catch(() => { ids = new Set(); signedIn = false; })
    .finally(() => { loading = null; window.dispatchEvent(new Event(EVENT)); });
  return loading;
}

/** Returns [isSaved, toggle]. toggle() resolves to 'login' when the visitor must sign in first. */
export function useWishlist(productId: number): [boolean, () => Promise<'added' | 'removed' | 'login'>] {
  const [saved, setSaved] = useState(false);
  useEffect(() => {
    const sync = () => setSaved(!!ids?.has(productId));
    // Re-check when the visitor was signed out earlier (they may have signed in since).
    sync(); load(!signedIn);
    window.addEventListener(EVENT, sync);
    return () => window.removeEventListener(EVENT, sync);
  }, [productId]);
  const toggle = async () => {
    // Wait for any load in progress so the click acts on the real, current wishlist.
    if (loading) await loading;
    if (!ids) await load();
    if (!signedIn) { try { localStorage.setItem(PENDING, String(productId)); } catch {} return 'login' as const; }
    const removing = !!ids?.has(productId);
    try {
      await api('wishlist/', removing ? 'DELETE' : 'POST', {product: productId});
    } catch {
      await load(true);
      if (!signedIn) { try { localStorage.setItem(PENDING, String(productId)); } catch {} return 'login' as const; }
      throw new Error('Could not update your wishlist. Please try again.');
    }
    if (removing) ids!.delete(productId); else ids!.add(productId);
    window.dispatchEvent(new Event(EVENT));
    return removing ? 'removed' as const : 'added' as const;
  };
  return [saved, toggle];
}

/** Number of saved styles, kept in sync with every heart on the page (0 when signed out). */
export function useWishlistCount() {
  const [n, setN] = useState(0);
  useEffect(() => {
    const sync = () => setN(ids?.size || 0);
    const refresh = () => { load(true); };
    sync(); load(!signedIn);
    window.addEventListener(EVENT, sync);
    window.addEventListener('bag-changed', refresh); // fired on sign in / sign out
    return () => { window.removeEventListener(EVENT, sync); window.removeEventListener('bag-changed', refresh); };
  }, []);
  return n;
}
