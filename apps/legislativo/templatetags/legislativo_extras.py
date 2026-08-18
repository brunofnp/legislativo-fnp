from urllib.parse import urlparse

from django import template

register = template.Library()


@register.filter
def dominio(url):
    """Extrai o domínio de uma URL para exibir como badge de fonte (ex.:
    'https://www.folhavitoria.com.br/x' -> 'FOLHAVITORIA.COM.BR')."""
    if not url:
        return ''
    netloc = urlparse(url).netloc
    if netloc.startswith('www.'):
        netloc = netloc[len('www.'):]
    return netloc.upper()
