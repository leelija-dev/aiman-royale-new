import {Suspense} from 'react';
import {TrackOrder} from '@/components/track';

export const metadata = {title: 'Track Your Order', description: 'Track your Aiman Royale order with your order ID or Delhivery waybill (AWB) number.', alternates: {canonical: '/track'}};

export default function Page() {
  return <Suspense fallback={<section className="tk-page"><p>Loading…</p></section>}><TrackOrder/></Suspense>;
}
