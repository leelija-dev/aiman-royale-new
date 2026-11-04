'use client';
import Link from 'next/link';
import {useCallback, useEffect, useState} from 'react';
import {useSearchParams} from 'next/navigation';
import {Check, PackageCheck, RefreshCw, Truck, MapPin, CircleAlert, Box, Home, ClipboardCheck} from 'lucide-react';
import {api, err} from '@/lib/client';

type Tracking = {order: string; awb: string; status: string; courier_status: string; destination: string; stage: number; stages: string[];
  events: {time: string; status: string; detail: string; location: string}[]; updated: string | null; cancelled: boolean};
const ICONS = [ClipboardCheck, Box, Truck, MapPin, Home];
const when = (t: string) => { const d = new Date(t); return isNaN(+d) ? t : d.toLocaleString('en-IN', {day: 'numeric', month: 'short', year: 'numeric', hour: 'numeric', minute: '2-digit'}); };

export function TrackOrder() {
  const params = useSearchParams();
  const [order, setOrder] = useState(params.get('order') || ''), [awb, setAwb] = useState(params.get('awb') || '');
  const [query, setQuery] = useState<{order?: string; awb?: string} | null>(params.get('order') ? {order: params.get('order')!} : params.get('awb') ? {awb: params.get('awb')!} : null);
  const [data, setData] = useState<Tracking | null>(null), [error, setError] = useState(''), [busy, setBusy] = useState(false);

  const load = useCallback(async (q: {order?: string; awb?: string}) => {
    setBusy(true);
    try { setData(await api<Tracking>(`track/?${new URLSearchParams(q as Record<string, string>)}`)); setError(''); }
    catch (e) { const m = err(e); setError(m); setData(null); }
    finally { setBusy(false); }
  }, []);
  useEffect(() => {
    if (!query) return;
    load(query);
    const t = setInterval(() => load(query), 30000); // auto-update every 30 seconds
    return () => clearInterval(t);
  }, [query, load]);

  const done = data && (data.stage >= 4 || data.cancelled);
  return <section className="tk-page">
    <div className="tk-card">
      <h1>Track Your Order</h1><p>Enter your Order ID or Waybill number to track your shipment</p>
      <div className="tk-forms">
        <form onSubmit={e => { e.preventDefault(); if (order.trim()) { setAwb(''); setQuery({order: order.trim()}); } }}>
          <label>Order ID<input value={order} onChange={e => setOrder(e.target.value)} placeholder="e.g. F327BD04"/></label><button className="tk-btn" disabled={busy}>Track</button></form>
        <form onSubmit={e => { e.preventDefault(); if (awb.trim()) { setOrder(''); setQuery({awb: awb.trim()}); } }}>
          <label>Waybill / AWB<input value={awb} onChange={e => setAwb(e.target.value)} placeholder="e.g. 85529910000173" inputMode="numeric"/></label><button className="tk-btn" disabled={busy}>Track</button></form>
      </div>
    </div>

    {error && <div className="tk-card"><p className="pd-err"><CircleAlert size={16}/>{error}{/sign in/i.test(error) && <> <Link href={`/login?next=${encodeURIComponent(`/track?order=${order}`)}`}>Sign in</Link></>}</p></div>}

    {data && <div className="tk-card">
      {!done && <p className="tk-live"><RefreshCw size={14}/> Auto-updating every 30 seconds…</p>}
      <div className="tk-head"><div><h2>Shipment Tracking</h2>
        <p>{data.order && <>Order: <strong>#{data.order}</strong> · </>}AWB: <strong>{data.awb || 'Not booked yet'}</strong></p>
        {data.destination && <p>Destination: <strong>{data.destination}</strong></p>}</div>
        <span className={`tk-status${data.cancelled ? ' bad' : data.stage >= 4 ? ' ok' : ''}`}><PackageCheck size={15}/> {data.cancelled ? 'Cancelled' : data.courier_status || (data.stage >= 0 ? data.stages[data.stage] : data.status)}</span></div>
      {!data.cancelled && <ol className="tk-steps">{data.stages.map((s, i) => { const I = ICONS[i] || Check; return <li key={s} className={i <= data.stage ? 'done' : ''}><span>{i <= data.stage ? <Check size={15}/> : <I size={15}/>}</span>{s}</li>; })}</ol>}
      <h3>Tracking Events</h3>
      {data.events.length ? <ol className="tk-events">{data.events.map((e, i) => <li key={i} className={i === 0 ? 'latest' : ''}><strong>{e.status}</strong>{e.location && <span> · {e.location}</span>}
        {e.detail && <p>{e.detail}</p>}<small>{when(e.time)}</small></li>)}</ol>
        : <p className="tk-empty">{data.awb ? 'No tracking events yet. Updates appear once Delhivery picks up your parcel.' : 'Your parcel is being prepared. Tracking starts once it is booked with Delhivery.'}</p>}
      {data.updated && <p className="tk-updated">Last checked {when(data.updated)}</p>}
    </div>}
  </section>;
}
