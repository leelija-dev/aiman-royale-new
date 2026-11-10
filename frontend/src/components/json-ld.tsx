/** Custom JSON-LD schema blocks entered in admin. */
export function JsonLd({items}: {items?: unknown[] | null}) {
  if (!items?.length) return null;
  return <>{items.map((x, i) => <script key={i} type="application/ld+json" dangerouslySetInnerHTML={{__html: JSON.stringify(x).replace(/</g, '\\u003c')}}/>)}</>;
}
