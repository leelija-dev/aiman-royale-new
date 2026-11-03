import {Suspense} from 'react';
import {AccountPage} from '@/components/account';

export const metadata = {title: 'Order History', robots: {index: false, follow: false}};

export default function Page() {
  return <Suspense fallback={<section className="ac-page"><p className="ac-loading">Loading your orders…</p></section>}><AccountPage section="orders"/></Suspense>;
}
