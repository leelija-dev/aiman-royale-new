import {Mail, MapPin, Phone, Clock} from 'lucide-react';
import {get} from '@/lib/server';
import type {Site} from '@/lib/types';
import {ContactForm} from '@/components/contact-form';

export const metadata = {title: 'Contact Us', description: 'Contact Aiman Royale — call, WhatsApp, email or send us a message.', alternates: {canonical: '/info/contact'}};

// Phone, email and address come from admin → Site settings → Contact.
export default async function Contact() {
  const s = await get<Site>('site/').catch(() => null);
  const phone = s?.phone || '', digits = phone.replace(/\D/g, '');
  return <div className="info-page contact">
    <div className="info-head"><p className="eyebrow">We’re here to help</p><h1>Contact Us</h1><p>Questions about sizing, an order or a custom outfit? Reach us any way you like — our fashion experts reply quickly.</p></div>
    <div className="ct-grid">
      <div className="ct-cards">
        {phone && <a className="ct-card" href={`tel:${phone.replace(/\s/g, '')}`}><Phone size={20}/><div><strong>Call us</strong><span>{phone}</span></div></a>}
        {digits && <a className="ct-card" href={`https://wa.me/${digits}`} target="_blank" rel="noopener noreferrer"><svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden><path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2Zm4.5 12.1c-.2-.1-1.5-.7-1.7-.8-.2-.1-.4-.1-.6.1l-.8 1c-.1.2-.3.2-.5.1a6.7 6.7 0 0 1-3.3-2.9c-.3-.4.3-.4.8-1.4.1-.2 0-.3 0-.4l-.8-1.8c-.2-.5-.4-.4-.6-.4h-.5a1 1 0 0 0-.7.3 3 3 0 0 0-.9 2.2c0 1.3.9 2.5 1.1 2.7.1.2 1.9 2.9 4.5 4 1.7.7 2.3.8 3.2.6.5-.1 1.5-.6 1.7-1.2.2-.6.2-1.1.2-1.2-.1-.1-.3-.2-.5-.3Z"/></svg><div><strong>WhatsApp</strong><span>Chat with our team</span></div></a>}
        {s?.email && <a className="ct-card" href={`mailto:${s.email}`}><Mail size={20}/><div><strong>Email us</strong><span>{s.email}</span></div></a>}
        {s?.address && <div className="ct-card"><MapPin size={20}/><div><strong>Visit our studio</strong><span>{s.address}</span></div></div>}
        <div className="ct-card"><Clock size={20}/><div><strong>Fittings by appointment</strong><span><a href="/appointment">Book a time that suits you</a></span></div></div>
      </div>
      <ContactForm/>
    </div>
    {s?.address && <iframe className="ct-map" title="Map to Aiman Royale" loading="lazy" referrerPolicy="no-referrer-when-downgrade"
      src={`https://www.google.com/maps?q=${encodeURIComponent(s.address)}&output=embed`}/>}
  </div>;
}
