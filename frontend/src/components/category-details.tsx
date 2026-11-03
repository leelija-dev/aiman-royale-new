'use client';
import {useEffect, useRef, useState} from 'react';
import {ChevronDown} from 'lucide-react';

/** Long category description: 3 lines with Read more. The full text is always in the page for search engines. */
export function CategoryDetails({html, bare = false}: {html: string; bare?: boolean}) {
  const [open, setOpen] = useState(false), [long, setLong] = useState(true);
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => { const el = box.current; if (el) setLong(el.scrollHeight > el.clientHeight + 4); }, [html]);
  const Tag = bare ? 'div' : 'section';
  return <Tag className={bare ? 'cd cd-bare' : 'cp-wrap cd'} aria-label={bare ? undefined : 'About this collection'}>
    <div ref={box} id="cd-text" className={open || !long ? 'cd-text open' : 'cd-text'} dangerouslySetInnerHTML={{__html: html}}/>
    {long && <button type="button" className="cd-toggle" aria-expanded={open} aria-controls="cd-text" onClick={() => setOpen(!open)}>
      {open ? 'Show less' : 'Read more'}<ChevronDown size={16} className={open ? 'flip' : ''}/></button>}
  </Tag>;
}
