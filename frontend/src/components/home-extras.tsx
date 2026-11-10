'use client';
import Image from 'next/image';
import Link from 'next/link';
import {useEffect, useRef, useState} from 'react';
import {ChevronLeft, ChevronRight, ArrowRight, FileDown} from 'lucide-react';
import {openSizeGuide} from '@/components/size-guide';

/* ---------- Promo banner carousel ---------- */
type Slide = {title: string; image: string; href: string; caption: string};
export function PromoCarousel({slides}: {slides: Slide[]}) {
  const [i, setI] = useState(0), [paused, setPaused] = useState(false);
  const n = slides.length;
  useEffect(() => {
    if (paused || n < 2 || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const t = setInterval(() => setI(x => (x + 1) % n), 5000);
    return () => clearInterval(t);
  }, [paused, n]);
  return <section className="pc" aria-roledescription="carousel" aria-label="Featured offers" onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)} onFocus={() => setPaused(true)} onBlur={() => setPaused(false)}>
    <div className="pc-track" style={{transform: `translateX(-${i * 100}%)`}}>
      {slides.map((s, k) => <Link key={s.title + k} href={s.href} className="pc-slide" aria-roledescription="slide" aria-label={`${k + 1} of ${n}: ${s.title}`} aria-hidden={k !== i} tabIndex={k === i ? 0 : -1}>
        <Image src={s.image} alt="" fill sizes="100vw" priority={k === 0}/>
        <div className="pc-copy"><h3>{s.title}</h3>{s.caption && <span>{s.caption} <ArrowRight size={16}/></span>}</div>
      </Link>)}
    </div>
    {n > 1 && <>
      <button type="button" className="pc-arrow prev" aria-label="Previous banner" onClick={() => setI((i - 1 + n) % n)}><ChevronLeft size={22}/></button>
      <button type="button" className="pc-arrow next" aria-label="Next banner" onClick={() => setI((i + 1) % n)}><ChevronRight size={22}/></button>
      <div className="pc-dots">{slides.map((s, k) => <button key={k} type="button" aria-label={`Show banner ${k + 1}`} aria-current={k === i} className={k === i ? 'on' : ''} onClick={() => setI(k)}/>)}</div>
    </>}
  </section>;
}

/* ---------- Horizontal scroller with arrows (product rows, tiles) ---------- */
export function Scroller({children, label}: {children: React.ReactNode; label?: string}) {
  const ref = useRef<HTMLDivElement>(null);
  const [edges, setEdges] = useState({start: true, end: false});
  const update = () => { const el = ref.current; if (!el) return; setEdges({start: el.scrollLeft < 8, end: el.scrollLeft + el.clientWidth >= el.scrollWidth - 8}); };
  useEffect(() => { update(); const el = ref.current; el?.addEventListener('scroll', update, {passive: true}); window.addEventListener('resize', update); return () => { el?.removeEventListener('scroll', update); window.removeEventListener('resize', update); }; }, []);
  const go = (dir: number) => { const el = ref.current; if (el) el.scrollBy({left: dir * el.clientWidth * 0.85, behavior: 'smooth'}); };
  return <div className="hs" role="region" aria-label={label ? `${label} (scrollable)` : 'Scrollable list'}>
    {!edges.start && <button type="button" className="hs-arrow prev" aria-label="Scroll left" onClick={() => go(-1)}><ChevronLeft size={20}/></button>}
    <div ref={ref} className="hs-track">{children}</div>
    {!edges.end && <button type="button" className="hs-arrow next" aria-label="Scroll right" onClick={() => go(1)}><ChevronRight size={20}/></button>}
  </div>;
}

/* ---------- Size guide section ---------- */
export type SizeGuideData = {rows: {size: string; alt: string; bust: number; waist: number; hip: number; armhole: number; uk: string}[]; steps: {title: string; text: string; image: string}[]; note: string; pdf: string};
const COLS = ['bust', 'waist', 'hip', 'armhole'] as const;
export function HomeSizeGuide({title, guide}: {title: string; guide: SizeGuideData}) {
  const [unit, setUnit] = useState<'in' | 'cm'>('in');
  const fmt = (v: number) => unit === 'in' ? v.toLocaleString('en-IN', {maximumFractionDigits: 2}) : `${(Math.round(v * 25.4) / 10).toLocaleString('en-IN', {maximumFractionDigits: 1})} cm`;
  return <section className="hsg" aria-labelledby="hsg-title">
    <div className="hsg-head"><h2 id="hsg-title">{title}</h2>
      <div className="sg-unit" role="group" aria-label="Units">{(['in', 'cm'] as const).map(u => <button key={u} type="button" aria-pressed={unit === u} className={unit === u ? 'on' : ''} onClick={() => setUnit(u)}>{u === 'in' ? 'Inches' : 'cm'}</button>)}</div></div>
    <div className="hsg-body">
      <div className="sg-table-wrap"><table className="hsg-table"><thead><tr><th>SIZE</th><th>Bust</th><th>Waist</th><th>Hip</th><th>Armhole</th><th>UK Size</th></tr></thead>
        <tbody>{guide.rows.map(r => <tr key={r.size}><th scope="row">{r.alt ? `${r.size} (${r.alt})` : r.size}</th>{COLS.map(c => <td key={c}>{fmt(r[c])}</td>)}<td>{r.uk}</td></tr>)}</tbody></table></div>
      <ol className="hsg-steps">{guide.steps.map((s, k) => <li key={s.title + k}><span>{k + 1}</span><div><strong>{s.title}</strong>{s.text && <p>{s.text}</p>}</div></li>)}</ol>
    </div>
    <div className="hsg-foot"><p>{guide.note}</p>
      {guide.pdf ? <a href={guide.pdf} download target="_blank" rel="noopener"><FileDown size={18}/> Download Size Chart (PDF)</a>
        : <button type="button" onClick={openSizeGuide}><FileDown size={18}/> Download Size Chart (PDF)</button>}</div>
  </section>;
}

/* ---------- Designer's perspective: photo with a quote card carousel ---------- */
type Note = {title: string; text: string; name: string; role: string};
export function NotesCarousel({badge, image, notes}: {badge: string; image: string; notes: Note[]}) {
  const [i, setI] = useState(0), n = notes.length, x = notes[i];
  const [role, extra] = (x.role || '').split('|').map(t => t.trim());
  return <section className="lh-notes" aria-roledescription="carousel" aria-label={badge}>
    <Image src={image} alt="" fill sizes="100vw"/>
    <div className="lh-notes-card">
      {badge && <small className="lh-badge solid">{badge}</small>}
      <div aria-live="polite"><h3>{x.title}</h3>{x.text && <blockquote>“{x.text}”</blockquote>}</div>
      <div className="lh-notes-foot">
        {n > 1 && <button type="button" aria-label="Previous note" onClick={() => setI((i - 1 + n) % n)}><ChevronLeft size={18}/></button>}
        <div className="lh-notes-by"><span>{(x.name || 'A').trim()[0]}</span><div><b>{x.name}</b>{role && <em>{role}</em>}{extra && <small>{extra}</small>}</div></div>
        {n > 1 && <button type="button" aria-label="Next note" onClick={() => setI((i + 1) % n)}><ChevronRight size={18}/></button>}
      </div>
      {n > 1 && <div className="pc-dots static">{notes.map((t, k) => <button key={k} type="button" aria-label={`Show note ${k + 1}`} aria-current={k === i} className={k === i ? 'on' : ''} onClick={() => setI(k)}/>)}</div>}
    </div>
  </section>;
}

/* ---------- Hero slider (slide 1 = hero section, more slides = its cards in admin) ---------- */
export type HeroSlide = {eyebrow: string; title: string; subtitle: string; button: {label: string; href: string} | null; image: string;
  mobile?: string; alt?: string; imageTitle?: string; href?: string};
export function HeroSlider({slides}: {slides: HeroSlide[]}) {
  const [i, setI] = useState(0), [paused, setPaused] = useState(false), n = slides.length;
  useEffect(() => {
    if (paused || n < 2 || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const t = setInterval(() => setI(x => (x + 1) % n), 6000);
    return () => clearInterval(t);
  }, [paused, n]);
  const lines = (t: string) => t.split('\n').flatMap((l, k) => k ? [<br key={k}/>, l] : [l]);
  return <section className="luxury-hero hero-slider" aria-roledescription="carousel" aria-label="Featured collections"
    onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)} onFocus={() => setPaused(true)} onBlur={() => setPaused(false)}>
    {!slides[0]?.title && <h1 className="sr-only">Aiman Royale – designer ethnic wear, salwar kameez, anarkali &amp; gowns</h1>}
    {slides.map((s, k) => {
      const title = s.title.replace(/\n/g, ' '), alt = s.alt || title || s.imageTitle || 'Aiman Royale collection';
      const href = s.href || s.button?.href, text = !!(s.title || s.eyebrow || s.subtitle);
      const body = <>
        <Image className={s.mobile ? 'hs-desk' : ''} src={s.image} alt={alt} title={s.imageTitle || undefined} fill priority={k === 0} sizes="100vw" quality={92}/>
        {s.mobile && <Image className="hs-mob" src={s.mobile} alt={alt} title={s.imageTitle || undefined} fill priority={k === 0} sizes="100vw" quality={92}/>}
        {text && <div className="hero-copy">{s.eyebrow && <p className="eyebrow">{s.eyebrow}</p>}{k === 0 ? <h1>{lines(s.title)}</h1> : <h2 className="hero-h">{lines(s.title)}</h2>}
          {s.subtitle && <p>{s.subtitle}</p>}{s.button && <span className="button">{s.button.label} <ArrowRight size={16}/></span>}</div>}
      </>;
      return <div key={k} className={`hero-slide${k === i ? ' on' : ''}`} aria-roledescription="slide" aria-label={`${k + 1} of ${n}`} aria-hidden={k !== i}>
        {href ? <Link href={href} className="hero-link" tabIndex={k === i ? 0 : -1} aria-label={text ? undefined : alt}>{body}</Link> : body}
      </div>;
    })}
    {n > 1 && <>
      <button type="button" className="pc-arrow prev" aria-label="Previous slide" onClick={() => setI((i - 1 + n) % n)}><ChevronLeft size={22}/></button>
      <button type="button" className="pc-arrow next" aria-label="Next slide" onClick={() => setI((i + 1) % n)}><ChevronRight size={22}/></button>
      <div className="pc-dots">{slides.map((_, k) => <button key={k} type="button" aria-label={`Show slide ${k + 1}`} aria-current={k === i} className={k === i ? 'on' : ''} onClick={() => setI(k)}/>)}</div>
    </>}
  </section>;
}
