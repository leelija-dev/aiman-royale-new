import {get, origin} from '@/lib/server';
import type {Site} from '@/lib/types';

// llms.txt (https://llmstxt.org): a short Markdown guide to the store for AI assistants and agents.
export const revalidate = 3600;

export async function GET() {
  let site: Site | null = null;
  try { site = await get<Site>('site/'); } catch {}
  const name = site?.name || 'Aiman Royale';
  const cols = (site?.collections || []).map(c => `- [${c.name}](${origin}/collections/${c.slug})`);
  const body = [
    `# ${name}`,
    '',
    `> ${site?.hero_description || 'Designer Indian ethnic wear for women: salwar kameez, anarkali suits, sharara and gharara sets, gowns and bridal wear, in standard sizes or made to your measurements.'}`,
    '',
    'Prices are in Indian rupees (INR) and include taxes. Most styles can be bought Stitched (standard sizes) or with Custom Measurements.',
    '',
    '## Shop',
    `- [All products](${origin}/products): every style, with filters for category, occasion, colour, size and price`,
    ...cols,
    '',
    '## Help',
    `- [Size guide](${origin}/info/size-guide)`,
    `- [Book a fitting appointment](${origin}/appointment)`,
    `- [Track an order](${origin}/track)`,
    `- [Contact us](${origin}/info/contact)${site?.phone ? ` · WhatsApp/phone ${site.phone}` : ''}${site?.email ? ` · ${site.email}` : ''}`,
    `- [About ${name}](${origin}/info/about)`,
    '',
    '## Optional',
    `- [Sitemap](${origin}/sitemap.xml)`,
    '',
  ].join('\n');
  return new Response(body, {headers: {'Content-Type': 'text/markdown; charset=utf-8', 'Cache-Control': 'public, max-age=3600'}});
}
