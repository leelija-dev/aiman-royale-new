import Image from 'next/image';
import {get} from '@/lib/server';
import {ProductPage} from '@/lib/types';
import {Listing} from '@/components/catalogue';
export const metadata={title:'All Collections',alternates:{canonical:'/products'}};
export default async function Products({searchParams}:{searchParams:Promise<Record<string,string>>}){const q=await searchParams;const data=await get<ProductPage>(`products/?${new URLSearchParams(q)}`);return <><div className="breadcrumb">Home / Collections</div><section className="collection-hero"><div><p className="eyebrow">THE AIMAN ROYALE COLLECTION</p><h1>For every version<br/>of <em>beautiful you.</em></h1><p>Designer ethnic wear. Thoughtfully selected.<br/>Find the piece that tells your story.</p></div><div className="collection-hero-image"><Image src="/images/collection.webp" alt="The Aiman Royale collection" fill priority sizes="50vw"/></div></section><Listing data={data} query={q}/></>}
