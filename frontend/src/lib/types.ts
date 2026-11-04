import type {MenuItem} from './menu';
export type QA={question:string;answer:string};
export type CategoryContent={eyebrow:string;tagline:string;seo_heading:string;seo_body:string;details?:string;faqs:QA[];guides:QA[];fitting:{title:string;text:string;button:string;steps:string[];image:string}};
export type Collection={id:number;name:string;slug:string;description:string;image:string;seo_title:string;seo_description:string;content?:CategoryContent};
export type Variant={id:number;sku:string;size:string;colour:string;stock:number};
export type Product={id:number;name:string;slug:string;description:string;care:string;fabric:string;fit?:string;includes?:string;occasions:string[];price:string;mrp:string;featured:boolean;custom_fit:boolean;images:{id:number;url:string;alt:string}[];variants:Variant[];collections:Collection[];seo_title:string;seo_description:string;updated_at:string;faqs?:{q:string;a:string}[]};
export type ProductPage={count:number;page:number;pages:number;results:Product[]};
export type Site={name:string;announcement:string;hero_title:string;hero_description:string;hero_image:string;phone:string;email:string;address:string;cod_enabled:boolean;payment_ready:boolean;whatsapp_ready:boolean;collections:Collection[];menu?:MenuItem[];occasions?:Occasion[];shop_page?:ShopPage;delivery_message?:string;social?:Record<string,string>;footer_tagline?:string;footer?:FooterData;calendly?:{url:string;primary:string;text:string;background:string}|null};
export type Occasion={name:string;slug:string;image:string;count?:number};
export type Facets={occasions:Occasion[];sizes:string[];colours:{name:string;hex:string;count:number}[];price:{min:number|string;max:number|string};count:number;price_ranges?:{value:string;label:string;count:number}[];collections?:{name:string;slug:string;count:number}[]};
export type ShopPage={eyebrow:string;title:string;text:string;image:string;heading:string;subheading:string;fitting:{title:string;text:string;note:string;image:string};trust:{title:string;text:string}[]};
export type CartItem={id:number;variant:Variant;product:Product;quantity:number;measurements:Record<string,string>};
export type Bag={items:CartItem[];subtotal:string};
export type User={id:number;name:string;email:string;phone:string|null;first_name?:string;last_name?:string;marketing_opt_in?:boolean;joined?:string};
export type Order={id:string;status:string;note?:string;pay_with?:string;subtotal:string;discount:string;shipping:string;total:string;gateway_order_id:string;tracking_url:string;awb?:string;courier_status?:string;tracking_events?:{time:string;status:string;detail:string;location:string}[];can_cancel?:boolean;cancelled_at?:string|null;cancel_reason?:string;created_at:string;items:{name:string;unit_price:string;quantity:number;size:string;colour:string;slug?:string;image?:string}[]};
/** ₹ in whole rupees (₹13,419.39 → ₹13,419) — the same amount the payment page charges. */
export const money=(n:string|number)=>new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:0}).format(Math.round(Number(n)));
export const photo=(p:Product)=>p.images[0]?.url||'/images/collection.webp';

/** Whole-number discount, rounded down so it is never overstated (e.g. 54.8% → 54%). */
export const discount=(p:{price:string|number;mrp:string|number})=>Number(p.mrp)>Number(p.price)?Math.floor((1-Number(p.price)/Number(p.mrp))*100):0;

export type FooterData={about:string;newsletter:{eyebrow:string;title:string;text:string};instagram:{handle:string;note:string;url:string;posts:{caption:string;image:string;href:string}[]};links:Record<string,{label:string;href:string}[]>;highlights:{title:string;text:string}[];services:{title:string;text:string;icon:string}[];payments:string[];delivery:string[];note:string};

export type PinInfo={checked:boolean;serviceable:boolean;cod:boolean;prepaid:boolean;city:string;state:string};
