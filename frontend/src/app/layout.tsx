import type {Metadata} from 'next';
import {Header,Footer} from '@/components/chrome';
import {get,origin} from '@/lib/server';
import type {Site} from '@/lib/types';
import './globals.css';
export const dynamic='force-dynamic';
export const metadata:Metadata={metadataBase:new URL(origin),title:{default:'Aiman Royale | Designer Ethnic Wear for Women',template:'%s | Aiman Royale'},description:'Discover designer salwar suits, lehengas, palazzo sets and Indo-western styles. Book a personal fitting or styling appointment with Aiman Royale.',openGraph:{siteName:'Aiman Royale',locale:'en_IN',type:'website'},robots:{index:true,follow:true}};
export default async function RootLayout({children}:{children:React.ReactNode}){let site:Site;try{site=await get<Site>('site/');}catch{site={name:'Aiman Royale',announcement:'Thoughtfully designed. Beautifully you.',hero_title:'Shop Luxury',hero_description:'',hero_image:'/images/hero.webp',phone:'',email:'',address:'',cod_enabled:false,payment_ready:false,whatsapp_ready:false,collections:[]};}return <html lang="en-IN"><body><a className="skip-link" href="#main">Skip to content</a><Header site={site}/><main id="main">{children}</main><Footer site={site}/></body></html>;}
