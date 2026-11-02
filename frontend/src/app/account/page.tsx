import {Suspense} from 'react';
import {AccountPage} from '@/components/account';

export const metadata = {title: 'My Account', robots: {index: false, follow: false}};

export default function Page() {
  return <Suspense fallback={<section className="ac-page"><p className="ac-loading">Loading your account…</p></section>}><AccountPage/></Suspense>;
}
