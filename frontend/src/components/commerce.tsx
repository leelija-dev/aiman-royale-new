'use client';
import Link from 'next/link';import Image from 'next/image';import {useEffect,useState} from 'react';import {useRouter} from 'next/navigation';import {ArrowRight,ShoppingBag,Trash2,ShieldCheck,LockKeyhole,CheckCircle2} from 'lucide-react';import {api,err,bagChanged} from '@/lib/client';import {Bag,Site,Order,Product,User,money,photo} from '@/lib/types';
export function PaymentReturn(){const [order,setOrder]=useState<Order|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(true);
 async function verify(){setBusy(true);setError('');try{const id=new URLSearchParams(window.location.search).get('order');if(!id)throw Error('Missing order reference.');setOrder(await api<Order>('payments/verify/','POST',{order:id}));}catch(e){setError(err(e));}finally{setBusy(false);}}
 useEffect(()=>{void verify();},[]);
 const paid=order&&['paid','processing','shipped','delivered'].includes(order.status);
 return <section className="section empty"><p className="eyebrow">AIMAN ROYALE · CASHFREE</p><h1>{busy?'Checking your payment…':paid?'Your payment is confirmed.':'Your payment status'}</h1>{order&&<p>Order {order.id.slice(0,8).toUpperCase()} · {order.status.replaceAll('_',' ')} · {money(order.total)}</p>}{!busy&&!paid&&<p>If your bank has charged you, please do not pay again while verification is pending.</p>}<p role="status">{error}</p><div className="center"><button className="button outline" disabled={busy} onClick={verify}>Check Again</button> <Link className="button" href="/account/orders">View My Orders / Sign In</Link></div></section>;
}
