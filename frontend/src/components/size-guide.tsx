'use client';
import Image from 'next/image';
import {useEffect, useRef, useState} from 'react';
import {X, FileDown} from 'lucide-react';
import {api} from '@/lib/client';

type Row = {size: string; alt: string; bust: number; waist: number; hip: number; armhole: number; uk: string};
type Guide = {rows: Row[]; steps: {title: string; text: string; image: string}[]; note: string; pdf: string};
type Unit = 'in' | 'cm';
const COLS = ['bust', 'waist', 'hip', 'armhole'] as const;
const UNIT_KEY = 'ar-size-unit';

/** Opens the Size Guide popup from anywhere: window.dispatchEvent(new Event('open-size-guide')). */
export const openSizeGuide = () => window.dispatchEvent(new Event('open-size-guide'));

const fmt = (inches: number, unit: Unit) => unit === 'in'
  ? inches.toLocaleString('en-IN', {minimumFractionDigits: 0, maximumFractionDigits: 2})
  : `${(Math.round(inches * 2.54 * 10) / 10).toLocaleString('en-IN', {maximumFractionDigits: 1})} cm`;

/** Simple dress-form diagram used when a step has no photo uploaded. */
function Diagram({title}: {title: string}) {
  const t = title.toLowerCase();
  const y = t.includes('waist') ? 118 : t.includes('hip') ? 160 : t.includes('arm') ? 62 : 86;
  const arm = t.includes('arm');
  return <svg viewBox="0 0 240 230" className="sg-diagram" aria-hidden>
    <rect width="240" height="230" fill="#f4eee9"/>
    <path d="M120 22c-12 0-20 9-20 20 0 6 2 10 5 14l-28 8c-10 3-15 12-14 22l4 40c2 14 10 18 10 30l-6 70h98l-6-70c0-12 8-16 10-30l4-40c1-10-4-19-14-22l-28-8c3-4 5-8 5-14 0-11-8-20-20-20Z" fill="#1f5b46"/>
    <path d="M100 60c10 8 30 8 40 0" stroke="#d8c28c" strokeWidth="3" fill="none"/>
    {arm ? <ellipse cx="80" cy="76" rx="9" ry="20" fill="none" stroke="#f2c230" strokeWidth="5"/>
      : <path d={`M66 ${y}q54 14 108 0`} stroke="#f2c230" strokeWidth="6" fill="none"/>}
    {!arm && <path d={`M84 ${y + 2}h72`} stroke="#2fb7ff" strokeWidth="3" markerStart="url(#a)" markerEnd="url(#b)"/>}
    <defs><marker id="a" viewBox="0 0 10 10" refX="1" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M10 0L0 5l10 5z" fill="#2fb7ff"/></marker>
      <marker id="b" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0 0l10 5-10 5z" fill="#2fb7ff"/></marker></defs>
    <text x="120" y={arm ? 120 : y + 26} textAnchor="middle" fontFamily="Arial" fontWeight="700" fontStyle="italic" fontSize="15" fill="#fff">{title.split(' ')[0].toUpperCase()}</text>
  </svg>;
}

export function SizeGuide() {
  const [open, setOpen] = useState(false), [data, setData] = useState<Guide | null>(null), [error, setError] = useState('');
  const [unit, setUnit] = useState<Unit>('in'), [std, setStd] = useState(true), [alt, setAlt] = useState(true);
  const closeBtn = useRef<HTMLButtonElement>(null), lastFocus = useRef<Element | null>(null);

  useEffect(() => {
    try { const u = localStorage.getItem(UNIT_KEY); if (u === 'cm' || u === 'in') setUnit(u); } catch {}
    const show = () => { lastFocus.current = document.activeElement; setOpen(true); };
    // Any link to the size guide page opens the popup instead (the page stays as a fallback without JavaScript).
    const onClick = (e: MouseEvent) => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const a = (e.target as Element).closest?.('a[href]') as HTMLAnchorElement | null;
      if (!a || a.target === '_blank') return;
      const url = new URL(a.href, location.href);
      if (url.origin === location.origin && url.pathname === '/info/size-guide') { e.preventDefault(); show(); }
    };
    document.addEventListener('click', onClick, true);
    window.addEventListener('open-size-guide', show);
    return () => { document.removeEventListener('click', onClick, true); window.removeEventListener('open-size-guide', show); };
  }, []);

  useEffect(() => {
    if (!open) return;
    if (!data) api<Guide>('size-guide/').then(setData).catch(() => setError('The size guide could not be loaded. Please try again.'));
    closeBtn.current?.focus();
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') close(); };
    window.addEventListener('keydown', esc);
    const overflow = document.body.style.overflow; document.body.style.overflow = 'hidden';
    return () => { window.removeEventListener('keydown', esc); document.body.style.overflow = overflow; };
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  function close() { setOpen(false); (lastFocus.current as HTMLElement | null)?.focus?.(); }
  function pickUnit(u: Unit) { setUnit(u); try { localStorage.setItem(UNIT_KEY, u); } catch {} }
  const label = (r: Row) => std && alt && r.alt ? `${r.size} (${r.alt})` : alt && r.alt ? r.alt : r.size;

  /** Printable copy of the chart in the current unit; the browser's print dialog saves it as PDF. */
  function printPdf() {
    if (!data) return;
    const w = window.open('', '_blank'); if (!w) return;
    const esc = (t: string) => t.replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]!));
    const rows = data.rows.map(r => `<tr><th>${esc(label(r))}</th>${COLS.map(c => `<td>${fmt(r[c], unit)}</td>`).join('')}<td>${esc(r.uk)}</td></tr>`).join('');
    w.document.write(`<!doctype html><title>Aiman Royale Size Chart</title><style>body{font:14px Poppins,Arial,sans-serif;margin:30px;color:#222}h1{font:600 26px Poppins,Arial,sans-serif;color:#a10000;margin:0 0 4px}table{border-collapse:collapse;width:100%;margin:18px 0}th,td{border:1px solid #ddd;padding:10px;text-align:center}thead th{background:#f5f2ee}p{color:#555}</style>
      <h1>Aiman Royale — Size Chart</h1><p>Body measurements in ${unit === 'in' ? 'inches' : 'centimetres'}.</p>
      <table><thead><tr><th>Size</th><th>Bust</th><th>Waist</th><th>Hip</th><th>Armhole</th><th>UK Size</th></tr></thead><tbody>${rows}</tbody></table><p>${esc(data.note)}</p>`);
    w.document.close(); w.focus(); setTimeout(() => w.print(), 300);
  }

  if (!open) return null;
  return <div className="sg-overlay" onClick={e => { if (e.target === e.currentTarget) close(); }}>
    <div className="sg" role="dialog" aria-modal="true" aria-labelledby="sg-title">
      <header className="sg-head"><h2 id="sg-title">Size Guide</h2>
        <div className="sg-unit" role="group" aria-label="Units">{(['in', 'cm'] as Unit[]).map(u => <button key={u} type="button" aria-pressed={unit === u} className={unit === u ? 'on' : ''} onClick={() => pickUnit(u)}>{u === 'in' ? 'Inches' : 'cm'}</button>)}</div>
        <button type="button" ref={closeBtn} className="sg-close" aria-label="Close size guide" onClick={close}><X size={22}/></button></header>
      {!data ? <p className="sg-loading">{error || 'Loading size guide…'}</p> : <>
        <div className="sg-body">
          <div className="sg-chart"><h3>Size Guide</h3>
            <div className="sg-table-wrap"><table><thead><tr><th>SIZE</th><th>Bust</th><th>Waist</th><th>Hip</th><th>Armhole</th><th>UK Size</th></tr></thead>
              <tbody>{data.rows.map(r => <tr key={r.size}><th scope="row">{label(r)}</th>{COLS.map(c => <td key={c}>{fmt(r[c], unit)}</td>)}<td>{r.uk}</td></tr>)}</tbody></table></div>
            <div className="sg-toggles"><label><input type="checkbox" checked={std} onChange={e => { if (e.target.checked || alt) setStd(e.target.checked); }}/> Standard sizes</label>
              <label><input type="checkbox" checked={alt} onChange={e => { if (e.target.checked || std) setAlt(e.target.checked); }}/> Alternate sizes</label></div>
          </div>
          <div className="sg-how"><h3>How to Measure Yourself</h3>
            {data.steps.map((s, i) => <section key={s.title + i} className="sg-step"><h4><span>{i + 1}</span>{s.title}</h4>
              <div className="sg-step-img">{s.image ? <Image src={s.image} alt={s.title} fill sizes="320px"/> : <Diagram title={s.title}/>}</div>
              {s.text && <p>{s.text}</p>}</section>)}</div>
        </div>
        <footer className="sg-foot"><p>{data.note}</p>
          {data.pdf ? <a href={data.pdf} download target="_blank" rel="noopener"><FileDown size={18}/> Download Size Chart (PDF)</a>
            : <button type="button" onClick={printPdf}><FileDown size={18}/> Download Size Chart (PDF)</button>}</footer>
      </>}
    </div>
  </div>;
}
