'use client';
function message(value:unknown):string {if(typeof value==='string')return value;if(Array.isArray(value))return value.map(message).join(' ');if(value&&typeof value==='object')return Object.entries(value).map(([k,v])=>`${k==='error'||k==='detail'||k==='non_field_errors'?'':`${k}: `}${message(v)}`).join(' ');return 'Something went wrong. Please try again.';}
export async function api<T=Record<string,unknown>>(path:string,method='GET',body?:unknown):Promise<T>{
 let csrf=''; if(method!=='GET'){const r=await fetch('/api/csrf/',{credentials:'same-origin',cache:'no-store'});if(!r.ok)throw Error('Unable to start a secure session. Please refresh.');csrf=(await r.json()).csrfToken;}
 const r=await fetch(`/api/${path}`,{method,credentials:'same-origin',cache:'no-store',headers:{'Content-Type':'application/json',...(csrf?{'X-CSRFToken':csrf}:{})},...(body!==undefined?{body:JSON.stringify(body)}:{})});
 const data=await r.json().catch(()=>({error:'Service unavailable. Please try again.'}));if(!r.ok)throw Error(message(data));return data;
}
export const err=(e:unknown)=>e instanceof Error?e.message:'Please try again.';
export function bagChanged(){window.dispatchEvent(new Event('bag-changed'));}
