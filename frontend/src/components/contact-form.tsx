'use client';
import {useState} from 'react';
import {Send, Check, CircleAlert} from 'lucide-react';
import {api, err} from '@/lib/client';

export function ContactForm() {
  const [busy, setBusy] = useState(false), [msg, setMsg] = useState<{ok: boolean; text: string} | null>(null);
  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault(); const form = e.currentTarget; setBusy(true); setMsg(null);
    try { const r = await api<{message: string}>('contact/', 'POST', Object.fromEntries(new FormData(form))); setMsg({ok: true, text: r.message}); form.reset(); }
    catch (e2) { setMsg({ok: false, text: err(e2)}); } finally { setBusy(false); }
  }
  return <form className="ct-form" onSubmit={submit}>
    <h2>Send us a message</h2>
    <div className="ct-row"><label>Your name<input name="name" required maxLength={100} autoComplete="name"/></label><label>Phone<input name="phone" type="tel" maxLength={20} autoComplete="tel"/></label></div>
    <label>Email<input name="email" type="email" required autoComplete="email"/></label>
    <label>Subject<input name="subject" maxLength={150} placeholder="Order, sizing, custom outfit…"/></label>
    <label>Message<textarea name="message" required minLength={10} rows={5}/></label>
    <button className="pd-btn pd-btn-bag" disabled={busy}><Send size={17}/>{busy ? 'Sending…' : 'Send message'}</button>
    {msg && <p className={msg.ok ? 'pd-ok' : 'pd-err'} role="status">{msg.ok ? <Check size={16}/> : <CircleAlert size={16}/>}{msg.text}</p>}
  </form>;
}
