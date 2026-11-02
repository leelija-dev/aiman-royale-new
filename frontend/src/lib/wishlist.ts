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

function load(force = false) {
  if (!force && (ids || loading)) return loading || Promise.resolve();
  loading = api<Product[]>('wishlist/')
    .then(list => { ids = new Set(list.map(p => p.id)); signedIn = true; })
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
    if (!signedIn) return 'login' as const;
    const removing = !!ids?.has(productId);
    try {
      await api('wishlist/', removing ? 'DELETE' : 'POST', {product: productId});
    } catch {
      await load(true);
      if (!signedIn) return 'login' as const;
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
