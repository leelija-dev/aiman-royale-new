"""Copy the policy pages (text only) from the live site into Admin → Pages and publish them.

    python manage.py import_live_pages --dry-run     # show what would be imported
    python manage.py import_live_pages               # save + publish
    python manage.py import_live_pages --overwrite   # replace pages that already have text

Finds the pages from the live footer links ("Privacy", "Terms", "Return/Refund",
"Shipping/Delivery"), falling back to common URLs. Run it on a machine that can reach
aimanroyale.com. Images, scripts and styling are dropped; headings, paragraphs and
lists are kept.
"""
import re
import urllib.error
import urllib.parse
import urllib.request

from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand

from shop.models import Page
from shop.richtext import clean_html

# slug on this site -> (title, words that identify the footer link, fallback paths on the live site)
PAGES = {
    'privacy': ('Privacy Policy', ['privacy'], ['/privacy-policy']),
    'terms': ('Terms & Conditions', ['terms', 'condition'], ['/terms-condition', '/terms-and-conditions', '/terms']),
    'returns': ('Return & Refund Policy', ['return', 'refund'], ['/return-policy', '/refund-policy', '/return-refund-policy', '/return-and-refund-policy', '/returns']),
    'shipping': ('Shipping & Delivery Policy', ['shipping', 'delivery'], ['/shipping-policy', '/shipping', '/delivery-policy', '/shipping-and-delivery']),
}
DROP = ['script', 'style', 'noscript', 'header', 'footer', 'nav', 'form', 'svg', 'img', 'picture', 'video', 'iframe', 'button', 'aside']


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'AimanRoyale-ContentImport/1.0', 'Accept': 'text/html'})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode(r.headers.get_content_charset() or 'utf-8', 'replace')


def text_len(el):
    return sum(len(b.get_text(' ', strip=True)) for b in el.find_all(['p', 'li', 'h2', 'h3', 'h4', 'h5']))


def main_content(page_html):
    """The block holding the page's text (menus, footer and images removed), as clean HTML."""
    soup = BeautifulSoup(page_html, 'html.parser')
    for t in soup(DROP):
        t.decompose()
    el = soup.find('main') or soup.body or soup
    # Walk down while one child still holds almost all of the text.
    while True:
        total = text_len(el)
        kids = [k for k in el.find_all(recursive=False) if getattr(k, 'name', None)]
        inner = max(kids, key=text_len, default=None)
        if inner is None or total == 0 or text_len(inner) < total * .9:
            break
        el = inner
    for h1 in el.find_all('h1'):
        h1.decompose()  # our page shows its own title
    return clean_html(str(el))


class Command(BaseCommand):
    help = 'Import Privacy, Terms, Return & Refund and Shipping pages (text only) from the live site.'

    def add_arguments(self, parser):
        parser.add_argument('--base', default='https://aimanroyale.com')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--overwrite', action='store_true')

    def handle(self, *args, **o):
        base = o['base'].rstrip('/')
        try:
            home = BeautifulSoup(fetch(base + '/'), 'html.parser')
        except (urllib.error.URLError, OSError) as e:
            self.stderr.write(f'Could not open {base}: {e}')
            return
        links = [(a.get_text(' ', strip=True).lower(), urllib.parse.urljoin(base + '/', a['href'])) for a in home.find_all('a', href=True)]
        found = {}
        for slug, (title, words, fallbacks) in PAGES.items():
            urls = [u for text, u in links if u.startswith(base) and any(w in text for w in words)]
            if slug == 'returns':  # don't mistake the privacy page for the refund policy
                urls = [u for u in urls if 'privacy' not in u]
            urls += [base + p for p in fallbacks]
            for url in dict.fromkeys(urls):
                try:
                    body = main_content(fetch(url))
                except (urllib.error.URLError, OSError):
                    continue
                if len(re.sub('<[^>]+>', '', body)) > 300:
                    found[slug] = (title, url, body)
                    break
        if 'shipping' not in found and 'returns' in found:
            # The live site keeps delivery details in its return policy: use that for "View delivery & return details".
            found['shipping'] = ('Delivery & Returns', found['returns'][1], found['returns'][2])
        for slug, (title, url, body) in found.items():
            words = len(re.sub('<[^>]+>', ' ', body).split())
            page = Page.objects.filter(slug=slug).first()
            if page and page.published and page.body.strip() and not o['overwrite']:
                self.stdout.write(f'skip  /info/{slug} (already has text; use --overwrite)')
                continue
            self.stdout.write(f'{"would import" if o["dry_run"] else "import"}  /info/{slug}  ← {url}  ({words} words)')
            if not o['dry_run']:
                Page.objects.update_or_create(slug=slug, defaults={'title': title, 'body': body, 'published': True})
        for slug in PAGES:
            if slug not in found:
                self.stdout.write(self.style.WARNING(f'not found  /info/{slug} — add the text in Admin → Pages and tick Published.'))
