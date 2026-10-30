import {AuthForm} from '@/components/auth';import {get} from '@/lib/server';import {Site} from '@/lib/types';
export const metadata={title:'Create an Account',robots:{index:false,follow:false}};
export default async function Page(){const site=await get<Site>('site/');return <AuthForm register whatsappReady={site.whatsapp_ready}/>}
