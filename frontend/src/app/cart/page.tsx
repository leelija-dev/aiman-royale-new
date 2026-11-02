import {get} from '@/lib/server';
import {Facets, ProductPage} from '@/lib/types';
import {BagPage} from '@/components/bag';

export const metadata = {title: 'Shopping Bag', robots: {index: false, follow: false}};

export default async function Page() {
  const [featured, facets] = await Promise.all([
    get<ProductPage>('products/?featured=1').catch(() => null),
    get<Facets>('facets/').catch(() => null),
  ]);
  const swatches = Object.fromEntries((facets?.colours || []).map(c => [c.name.toLowerCase(), c.hex]));
  return <BagPage suggestions={featured?.results || []} swatches={swatches}/>;
}
