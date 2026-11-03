"""Copy each category's long description from the live site into Collection.details.

    python manage.py import_live_descriptions --dry-run       # show what would be saved
    python manage.py import_live_descriptions                 # save (skips categories that already have details)
    python manage.py import_live_descriptions --overwrite     # replace existing details too
    python manage.py import_live_descriptions --slug salwar-kameez --slug gown
    python manage.py import_live_descriptions --home          # homepage 'About the brand' text (Read more block)

The live page for each collection is https://aimanroyale.com/collections/<slug> (change with --base).
The description block is found automatically: it is the text block that holds the "Read more" /
"Show less" toggle (or, failing that, the largest block of paragraphs outside the menu, product grid
and footer). Nothing is saved unless at least 150 characters of text are found.
"""
import re
import urllib.error
import urllib.request

from bs4 import BeautifulSoup, NavigableString
from django.core.management.base import BaseCommand

from shop.models import Collection, HomeSection
from shop.richtext import clean_html

TOGGLE = re.compile(r'^\s*(read\s*more|show\s*less|read\s*less|show\s*more|view\s*more|view\s*less|see\s*more|see\s*less)\s*[.…»›>+\-]*\s*$', re.I)
NOISE = ['script', 'style', 'noscript', 'svg', 'header', 'nav', 'footer', 'form', 'iframe', 'template', 'select', 'input']
MIN_CHARS = 150


def text_len(el):
    return len(' '.join(el.get_text(' ', strip=True).split()))


def looks_like_products(el):
    txt = el.get_text(' ', strip=True)
    return txt.count('₹') + txt.count('Rs.') >= 3 or len(el.select('img')) >= 4


def find_block(soup):
    """Return the element that holds the long description, or None."""
    for tag in NOISE:
        for el in soup.find_all(tag):
            el.decompose()
    # 1) Elements whose own text is just a 'Read more' / 'Show less' toggle.
    toggles = [el for el in soup.find_all(['a', 'button', 'span', 'div', 'p', 'label'])
               if el.get_text(strip=True) and TOGGLE.match(el.get_text(' ', strip=True)) and not el.find(['p', 'h1', 'h2', 'h3'])]
    best = None
    for t in toggles:
        node = t.parent
        while node is not None and node.name not in ('body', '[document]'):
            if text_len(node) - len(t.get_text(strip=True)) >= MIN_CHARS:
                if not looks_like_products(node) and (best is None or text_len(node) > text_len(best)):
                    best = node
                break
            node = node.parent
    if best is not None:
        return best
    # 2) Fallback: the container with the most paragraph text that is not a product grid.
    candidates = []
    for el in soup.find_all(['section', 'article', 'div']):
        paras = el.find_all('p', recursive=True)
        words = sum(text_len(p) for p in paras)
        if words >= MIN_CHARS and not looks_like_products(el):
            candidates.append((words, -len(list(el.descendants)), el))
    if not candidates:
        return None
    candidates.sort(key=lambda c: (c[0], c[1]), reverse=True)
    return candidates[0][2]


def extract(html_text):
    """Description HTML (cleaned) from a full page, or ''."""
    soup = BeautifulSoup(html_text, 'html.parser')
    block = find_block(soup)
    if block is None:
        return ''
    # Remove the toggles themselves.
    for el in block.find_all(['a', 'button', 'span', 'div', 'p', 'label']):
        if el.get_text(strip=True) and TOGGLE.match(el.get_text(' ', strip=True)) and not el.find(['p', 'h1', 'h2', 'h3']):
            el.decompose()
    # Text only: drop images and media.
    for el in block.find_all(['img', 'picture', 'figure', 'video', 'audio', 'iframe', 'canvas']):
        el.decompose()
    # Remove a shortened teaser ('...'/'…' ending) shown before the full text.
    full_len = text_len(block)
    for el in block.find_all(['p', 'div', 'span']):
        if el.find(['p', 'h1', 'h2', 'h3', 'ul', 'ol', 'div']):
            continue
        t = ' '.join(el.get_text(' ', strip=True).split())
        if t.endswith(('...', '…')) and len(t) < min(400, full_len * 0.6):
            el.decompose()
    # Wrapper boxes: plain-text boxes become paragraphs, boxes holding other blocks are unwrapped.
    BLOCKS = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'div', 'section', 'article', 'table']
    for el in reversed(block.find_all(['div', 'section', 'article'])):
        if el.find(BLOCKS):
            el.unwrap()
        elif el.get_text(strip=True):
            el.name = 'p'
            el.attrs = {}
        else:
            el.decompose()
    # Bare text directly inside the block becomes paragraphs.
    for child in list(block.children):
        if isinstance(child, NavigableString) and child.strip():
            p = soup.new_tag('p')
            p.string = child.strip()
            child.replace_with(p)
    return clean_html(block.decode_contents())


class Command(BaseCommand):
    help = 'Copy category descriptions from the live site into Collection.details (see module docstring).'

    def add_arguments(self, parser):
        parser.add_argument('--base', default='https://aimanroyale.com', help='Live site address')
        parser.add_argument('--slug', action='append', help='Only these collection slugs (repeatable)')
        parser.add_argument('--dry-run', action='store_true', help='Show what would be saved; change nothing')
        parser.add_argument('--overwrite', action='store_true', help='Replace details that are already filled in')
        parser.add_argument('--home', action='store_true', help="Import the homepage 'About the brand' text instead of categories")

    def fetch(self, url):
        req = urllib.request.Request(url, headers={'User-Agent': 'AimanRoyale-ContentImport/1.0', 'Accept': 'text/html'})
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.read().decode(r.headers.get_content_charset() or 'utf-8', 'replace')

    def import_home(self, o):
        sec = HomeSection.objects.filter(kind='story').order_by('sort_order').first()
        if not sec:
            self.stdout.write(self.style.WARNING('No "Brand story" section on the homepage. Add one in admin first.'))
            return
        url = o['base'].rstrip('/') + '/'
        try:
            page = self.fetch(url)
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'✗ could not open {url} ({e})'))
            return
        details = extract(page)
        plain = ' '.join(re.sub(r'<[^>]+>', ' ', details).split())
        if len(plain) < MIN_CHARS:
            self.stdout.write(self.style.WARNING(f'✗ no Read more text found on {url}'))
            return
        # The section title is shown separately; drop a leading heading that repeats it.
        details = re.sub(r'^<h2>[^<]*resilience[^<]*</h2>', '', details, flags=re.I)
        preview = plain[:160] + ('…' if len(plain) > 160 else '')
        if o['dry_run']:
            self.stdout.write(f'✓ homepage: would save {len(plain)} characters — "{preview}"')
        else:
            sec.text = details
            sec.save(update_fields=['text'])
            self.stdout.write(self.style.SUCCESS(f'✓ homepage: saved {len(plain)} characters — "{preview}"'))

    def handle(self, *args, **o):
        if o['home']:
            return self.import_home(o)
        qs = Collection.objects.all().order_by('name')
        if o['slug']:
            qs = qs.filter(slug__in=o['slug'])
        saved = skipped = missing = 0
        for c in qs:
            if c.details and not o['overwrite']:
                self.stdout.write(f'· {c.slug}: already has details (use --overwrite to replace)')
                skipped += 1
                continue
            url = f"{o['base'].rstrip('/')}/collections/{c.slug}"
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'AimanRoyale-ContentImport/1.0', 'Accept': 'text/html'})
                with urllib.request.urlopen(req, timeout=25) as r:
                    page = r.read().decode(r.headers.get_content_charset() or 'utf-8', 'replace')
            except urllib.error.HTTPError as e:
                self.stdout.write(self.style.WARNING(f'✗ {c.slug}: live page returned {e.code} ({url})'))
                missing += 1
                continue
            except Exception as e:  # network, timeout
                self.stdout.write(self.style.WARNING(f'✗ {c.slug}: could not open {url} ({e})'))
                missing += 1
                continue
            details = extract(page)
            plain = re.sub(r'<[^>]+>', ' ', details)
            plain = ' '.join(plain.split())
            if len(plain) < MIN_CHARS:
                self.stdout.write(self.style.WARNING(f'✗ {c.slug}: no description found on {url}'))
                missing += 1
                continue
            preview = plain[:160] + ('…' if len(plain) > 160 else '')
            if o['dry_run']:
                self.stdout.write(f'✓ {c.slug}: would save {len(plain)} characters — "{preview}"')
            else:
                c.details = details
                c.save(update_fields=['details'])
                self.stdout.write(self.style.SUCCESS(f'✓ {c.slug}: saved {len(plain)} characters — "{preview}"'))
            saved += 1
        verb = 'would save' if o['dry_run'] else 'saved'
        self.stdout.write(f'\nDone: {saved} {verb}, {skipped} skipped (already filled), {missing} not found.')
