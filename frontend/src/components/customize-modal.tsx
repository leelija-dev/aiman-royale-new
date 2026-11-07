'use client';
import {useEffect, useMemo, useRef, useState} from 'react';
import {X, Ruler, Send} from 'lucide-react';
import type {Product} from '@/lib/types';
import {money} from '@/lib/types';

export type CustomPayload = {variant: number; qty: number; m: Record<string, string>; options: Record<string, string>};

const MAIN = [['bust', 'Bust'], ['waist', 'Waist'], ['hip', 'Hip'], ['armhole', 'Armhole']] as const;
const EXTRA = [['shoulder', 'Shoulder'], ['height', 'Height'], ['sleeve', 'Sleeve Length'], ['top_length', 'Top Length'], ['bottom_length', 'Bottom Length'], ['blouse_length', 'Blouse Length']] as const;

function Toggle({on, set, label}: {on: boolean; set: (v: boolean) => void; label: string}) {
  return <label className="cz-toggle"><span>{label}</span><button type="button" role="switch" aria-checked={on} className={on ? 'on' : ''} onClick={() => set(!on)}><i/></button><em>{on ? 'Yes' : 'No'}</em></label>;
}

/** "Customize" popup: choose a base size, enter measurements and design changes, then send a custom request.
 *  Our team confirms the price; the customer pays from My Account → Custom Requests. */
export function CustomizeModal({p, phone, colour, onClose, onSend, busy}: {p: Product; phone: string; colour: string; onClose: () => void; onSend: (d: CustomPayload) => void; busy: boolean}) {
  const sizes = useMemo(() => {
    const list = p.variants.filter(v => !colour || v.colour === colour);
    return (list.length ? list : p.variants).filter((v, i, a) => a.findIndex(x => x.size === v.size) === i);
  }, [p.variants, colour]);
  const [size, setSize] = useState<number>(0), [unit, setUnit] = useState<'in' | 'cm'>('in');
  const [m, setM] = useState<Record<string, string>>({}), [use, setUse] = useState<Record<string, boolean>>({});
  const [neck, setNeck] = useState(false), [back, setBack] = useState(false), [col, setCol] = useState(false);
  const [o, setO] = useState<Record<string, string>>({}), [error, setError] = useState('');
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', esc); document.body.style.overflow = 'hidden'; box.current?.focus();
    return () => { document.removeEventListener('keydown', esc); document.body.style.overflow = ''; };
  }, [onClose]);

  const measures = Object.fromEntries(Object.entries(m).filter(([k, v]) => v && (MAIN.some(([x]) => x === k) || use[k])));
  const options: Record<string, string> = {...(neck && o.neckline ? {neckline: o.neckline} : {}), ...(back && o.back ? {back: o.back} : {}), ...(col && o.colour ? {colour: o.colour} : {}), ...(o.extra ? {extra: o.extra} : {})};
  const count = Object.keys(measures).length + Object.keys(options).length;
  function submit() {
    setError('');
    if (!size) return setError('Choose the size you want customised.');
    if (!count) return setError('Enter at least one measurement or customisation.');
    const bad = Object.entries(measures).find(([, v]) => !(Number(v) > 0 && Number(v) <= 300));
    if (bad) return setError(`Check the ${bad[0].replace('_', ' ')} measurement.`);
    onSend({variant: size, qty: 1, m: {...measures, unit}, options});
  }
  const field = (k: string, label: string, optional = false) => <div key={k} className="cz-field">
    <label>{optional ? <input type="checkbox" checked={!!use[k]} onChange={e => setUse({...use, [k]: e.target.checked})}/> : null}{label}</label>
    <div className={`cz-num${optional && !use[k] ? ' off' : ''}`}><input type="number" inputMode="decimal" min={1} max={300} step={0.25} placeholder="Numeric input" value={m[k] || ''} disabled={optional && !use[k]}
      onChange={e => setM({...m, [k]: e.target.value})} aria-label={`${label} in ${unit === 'in' ? 'inches' : 'centimetres'}`}/><span>{unit}</span></div></div>;

  return <div className="pd-modal cz-wrap" role="dialog" aria-modal="true" aria-labelledby="cz-title" onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
    <div className="cz-box" ref={box} tabIndex={-1}>
      <header className="cz-head"><h2 id="cz-title">Customize</h2><button type="button" aria-label="Close" onClick={onClose}><X size={22}/></button></header>
      <div className="cz-body">
        <p className="cz-help">Need help customizing? Chat with our expert.</p>
        {phone && <a className="cz-chat" href={`https://wa.me/${phone.replace(/\D/g, '')}?text=${encodeURIComponent(`Hello Aiman Royale, I need help customizing ${p.name}.`)}`} target="_blank" rel="noopener noreferrer">
          <svg viewBox="0 0 24 24" width="17" height="17" fill="currentColor" aria-hidden><path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2Zm4.5 12.1c-.2-.1-1.5-.7-1.7-.8-.2-.1-.4-.1-.6.1l-.8 1c-.1.2-.3.2-.5.1a6.7 6.7 0 0 1-3.3-2.9c-.3-.4.3-.4.8-1.4.1-.2 0-.3 0-.4l-.8-1.8c-.2-.5-.4-.4-.6-.4h-.5a1 1 0 0 0-.7.3 3 3 0 0 0-.9 2.2c0 1.3.9 2.5 1.1 2.7.1.2 1.9 2.9 4.5 4 1.7.7 2.3.8 3.2.6.5-.1 1.5-.6 1.7-1.2.2-.6.2-1.1.2-1.2-.1-.1-.3-.2-.5-.3Z"/></svg>Chat With Us</a>}

        <h3>Choose a size to be customized:</h3>
        <div className="cz-sizes">{sizes.map(v => <button key={v.id} type="button" className={size === v.id ? 'on' : ''} aria-pressed={size === v.id} onClick={() => setSize(v.id)}><small>{money(p.price)}</small>{v.size}</button>)}</div>
        <p className="cz-note">Customized orders can take a minimum of 7 extra working days, along with customization charges (if applicable). Our team checks your request and confirms the final price before you pay.</p>

        <div className="cz-row"><h3>Enter your measurements below</h3>
          <div className="pd-unit cz-unit">{(['in', 'cm'] as const).map(u => <button type="button" key={u} className={unit === u ? 'on' : ''} aria-pressed={unit === u} onClick={() => setUnit(u)}>{u}</button>)}</div></div>
        <div className="cz-grid">{MAIN.map(([k, l]) => field(k, l))}</div>
        <p className="cz-sub">Other measurements (tick the ones you want to change)</p>
        <div className="cz-grid">{EXTRA.map(([k, l]) => field(k, l, true))}</div>

        <div className="cz-grid cz-design">
          <div><Toggle on={neck} set={setNeck} label="Neckline design change?"/><textarea disabled={!neck} rows={3} maxLength={500} placeholder="Please specify your neckline design change here" value={o.neckline || ''} onChange={e => setO({...o, neckline: e.target.value})}/></div>
          <div><Toggle on={back} set={setBack} label="Back design change?"/><textarea disabled={!back} rows={3} maxLength={500} placeholder="Please specify your back design change here" value={o.back || ''} onChange={e => setO({...o, back: e.target.value})}/></div>
        </div>
        <label className="cz-label">Additional customization requests here.<textarea rows={3} maxLength={500} placeholder="Please specify any additional customization requests here." value={o.extra || ''} onChange={e => setO({...o, extra: e.target.value})}/></label>
        <Toggle on={col} set={setCol} label="Do you want to change colour?"/>
        {col && <input className="cz-input" maxLength={120} placeholder={`Which colour would you like instead of ${colour || 'this colour'}?`} value={o.colour || ''} onChange={e => setO({...o, colour: e.target.value})}/>}
        {error && <p className="pd-err" role="alert">{error}</p>}
      </div>
      <footer className="cz-foot"><span><Ruler size={15}/> {count} customization{count === 1 ? '' : 's'} selected</span>
        <button type="button" className="pd-btn pd-btn-bag" disabled={busy} onClick={submit}><Send size={17}/>{busy ? 'Sending…' : 'Send Custom Request'}</button></footer>
    </div>
  </div>;
}
