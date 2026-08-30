"""Авто-оглавление поста: добавляет якоря заголовкам h2-h4 и собирает TOC.

Работает на сервере (html.parser из stdlib) — без JS и без FOUC:
идемпотентно, id не дублируются, транслитерация русских заголовков.
"""
from html.parser import HTMLParser

from .translit import translit_slug

_HEADING_LEVELS = {'h2': 2, 'h3': 3, 'h4': 4}


def _render_starttag(tag: str, attrs: dict) -> str:
    if not attrs:
        return f'<{tag}>'
    attr_str = ''.join(f' {k}="{v}"' for k, v in attrs.items())
    return f'<{tag}{attr_str}>'


class _TOCBuilder(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []          # ('starttag', tag, attrs) или raw-строка
        self.toc: list[dict] = []
        self._used: set[str] = set()
        self._heading: dict | None = None

    def _unique_id(self, text: str) -> str:
        base = translit_slug(text) or 'section'
        slug = base
        i = 2
        while slug in self._used:
            slug = f'{base}-{i}'
            i += 1
        self._used.add(slug)
        return slug

    def handle_starttag(self, tag, attrs):
        if tag in _HEADING_LEVELS:
            attrs = dict(attrs)
            self._heading = {'level': _HEADING_LEVELS[tag], 'buf': [], 'attrs': attrs}
            self.parts.append(('starttag', tag, attrs))
        else:
            self.parts.append(self.get_starttag_text())

    def handle_startendtag(self, tag, attrs):
        self.parts.append(self.get_starttag_text())

    def handle_data(self, data):
        if self._heading is not None:
            self._heading['buf'].append(data)
        self.parts.append(data)

    def handle_endtag(self, tag):
        if self._heading is not None and tag in ('h2', 'h3', 'h4'):
            title = ' '.join(''.join(self._heading['buf']).split())
            hid = self._unique_id(title)
            self._heading['attrs']['id'] = hid
            self.toc.append({'level': self._heading['level'], 'id': hid, 'title': title})
            self._heading = None
        self.parts.append(f'</{tag}>')


def build_toc(content_html: str) -> tuple[list[dict], str]:
    """Возвращает (toc, html_с_якорями). toc — список {level, id, title}."""
    parser = _TOCBuilder()
    parser.feed(content_html or '')
    parser.close()

    html_parts = [
        _render_starttag(*part[1:]) if isinstance(part, tuple) else part
        for part in parser.parts
    ]
    return parser.toc, ''.join(html_parts)
