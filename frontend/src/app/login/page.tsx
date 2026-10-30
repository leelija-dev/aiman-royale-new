import {AuthForm} from '@/components/auth';import {get} from '@/lib/server';import {Site} from '@/lib/types';
export const metadata={title:'Sign In',robots:{index:false,follow:false}};
export default async function Page(){const site=await get<Site>('site/');return <AuthForm whatsappReady={site.whatsapp_ready}/>}
