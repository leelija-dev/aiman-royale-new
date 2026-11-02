'use client';
import {useEffect, useState} from 'react';
import {BadgePercent, Check, X, Lock} from 'lucide-react';
import {api} from '@/lib/client';
import {money} from '@/lib/types';

type Coupon = {code: string; percent: number; minimum: string; description: string; expires_at: string | null; eligible: boolean; saving: string; short_by: string};

/**
 * Coupon area for the bag and checkout pages: a code box plus every available coupon
 * with what it saves on the current bag. One coupon can be applied at a time.
 */
export function SavingZone({applied, onApply, onRemove, refreshKey, message}: {
  applied: string; onApply: (code: string) => Promise<void> | void; onRemove: () => void; refreshKey?: unknown; message?: {ok: boolean; text: string} | null;
}) {
  const [list, setList] = useState<Coupon[] | null>(null), [code, setCode] = useState(''), [busy, setBusy] = useState('');
  useEffect(() => { api<Coupon[]>('coupons/').then(setList).catch(() => setList([])); }, [refreshKey]);
  async function apply(c: string) { const v = c.trim().toUpperCase(); if (!v) return; setBusy(v); try { await onApply(v); setCode(''); } finally { setBusy(''); } }

  return <section className="sz" aria-labelledby="sz-title">
    <h3 id="sz-title"><span className="sz-icon"><BadgePercent size={18}/></span>Saving Zone</h3>
    {applied ? <div className="sz-applied"><Check size={18}/><div><strong>{applied}</strong> applied{message?.ok && message.text.includes('save') ? <small>{message.text}</small> : null}</div>
      <button type="button" onClick={onRemove} aria-label={`Remove coupon ${applied}`}><X size={16}/> Remove</button></div>
      : <form className="sz-form" onSubmit={e => { e.preventDefault(); apply(code); }}>
        <input value={code} onChange={e => setCode(e.target.value)} placeholder="Enter coupon code" aria-label="Coupon code" autoCapitalize="characters"/>
        <button disabled={!code.trim() || !!busy}>{busy && busy === code.trim().toUpperCase() ? '…' : 'Apply'}</button></form>}
    {message && !message.ok && <p className="pd-err">{message.text}</p>}
    {list === null ? <p className="sz-empty">Loading offers…</p> : !list.length ? <p className="sz-empty">No coupon available right now</p> :
      <ul className="sz-list">{list.map(c => {
        const on = applied === c.code;
        return <li key={c.code} className={`sz-card${on ? ' on' : ''}${c.eligible ? '' : ' locked'}`}>
          <div className="sz-tag"><strong>{c.percent}%</strong><span>OFF</span></div>
          <div className="sz-info"><p className="sz-code">{c.code}</p>
            {c.description && <p className="sz-desc">{c.description}</p>}
            <p className={c.eligible ? 'sz-save' : 'sz-lock'}>{c.eligible ? `You save ${money(c.saving)}` : <><Lock size={13}/> Add {money(c.short_by)} more to unlock</>}</p>
            {Number(c.minimum) > 0 && <p className="sz-min">On orders above {money(c.minimum)}{c.expires_at ? ` · till ${new Date(c.expires_at).toLocaleDateString('en-IN', {day: 'numeric', month: 'short'})}` : ''}</p>}
          </div>
          {on ? <span className="sz-btn done"><Check size={15}/> Applied</span>
            : <button type="button" className="sz-btn" disabled={!c.eligible || !!busy} onClick={() => apply(c.code)}>{busy === c.code ? '…' : 'Apply'}</button>}
        </li>;
      })}</ul>}
  </section>;
}
