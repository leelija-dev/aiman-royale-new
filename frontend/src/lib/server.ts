import 'server-only';
export async function get<T>(path:string):Promise<T>{
 const res=await fetch(`${process.env.INTERNAL_API_URL||'http://127.0.0.1:8000'}/api/${path}`,{headers:{'X-Forwarded-Proto':process.env.INTERNAL_REQUEST_SCHEME||'http'},cache:'no-store',signal:AbortSignal.timeout(10000)});
 if(!res.ok)throw new Error(res.status===404?'Not found':'The studio is temporarily unavailable. Please try again shortly.');
 return res.json();
}
export const origin=process.env.NEXT_PUBLIC_SITE_URL||'http://localhost:3000';
