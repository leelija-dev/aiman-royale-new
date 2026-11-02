import {get} from '@/lib/server';
import {Site} from '@/lib/types';
import {CheckoutPage} from '@/components/checkout';

export const metadata = {title: 'Secure Checkout', robots: {index: false, follow: false}};

export default async function Page() {
  return <CheckoutPage site={await get<Site>('site/')}/>;
}
