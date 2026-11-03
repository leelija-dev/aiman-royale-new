"""Small allow-list HTML cleaner for content edited in admin or imported from the old site.

Keeps headings, paragraphs, lists, bold/italic, line breaks and plain links; drops everything
else (scripts, styles, event handlers, inline styles, iframes). Plain text without tags is
turned into paragraphs (blank line = new paragraph)."""
import html
import re
from html.parser import HTMLParser

ALLOWED = {'p', 'h2', 'h3', 'h4', 'ul', 'ol', 'li', 'strong', 'b', 'em', 'i', 'br', 'a'}
RENAME = {'h1': 'h2', 'h5': 'h4', 'h6': 'h4'}
DROP_WITH_CONTENT = {'script', 'style', 'iframe', 'object', 'embed', 'noscript', 'template', 'svg', 'button', 'form', 'select', 'textarea', 'picture', 'video', 'audio', 'figure', 'canvas'}
VOID = {'br'}


class _Cleaner(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.stack, self.skip = [], [], 0

    def handle_starttag(self, tag, attrs):
        if tag in DROP_WITH_CONTENT:
            self.skip += 1
            return
        if self.skip:
            return
        tag = RENAME.get(tag, tag)
        if tag not in ALLOWED:
            return
        if tag == 'p' and 'p' in self.stack:  # no nested paragraphs
            return
        attr = ''
        if tag == 'a':
            href = dict(attrs).get('href') or ''
            if re.match(r'^(https?://|/|mailto:|tel:)', href.strip(), re.I):
                attr = f' href="{html.escape(href.strip(), quote=True)}"'
                if href.strip().lower().startswith('http'):
                    attr += ' rel="noopener" target="_blank"'
        self.out.append(f'<{tag}{attr}>')
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in DROP_WITH_CONTENT:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return
        tag = RENAME.get(tag, tag)
        if tag in self.stack:
            while self.stack:
                t = self.stack.pop()
                self.out.append(f'</{t}>')
                if t == tag:
                    break

    def handle_data(self, data):
        if not self.skip:
            self.out.append(html.escape(data, quote=False))


def clean_html(value: str) -> str:
    value = (value or '').strip()
    if not value:
        return ''
    if not re.search(r'<[a-zA-Z/][^>]*>', value):
        paras = [p.strip() for p in re.split(r'\n\s*\n', value) if p.strip()]
        return ''.join(f'<p>{html.escape(p).replace(chr(10), "<br>")}</p>' for p in paras)
    c = _Cleaner()
    c.feed(value)
    c.close()
    out = ''.join(c.out) + ''.join(f'</{t}>' for t in reversed(c.stack))
    out = re.sub(r'<(p|li|h2|h3|h4|strong|em|b|i)>\s*</\1>', '', out)  # empty tags
    out = re.sub(r'\s{2,}', ' ', out)
    return out.strip()
