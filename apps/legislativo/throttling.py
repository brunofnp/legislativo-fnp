"""Rate limiting simples para os formulários públicos (comentário e
participação), sem depender de pacote externo — usa o cache padrão do Django
(LocMemCache), suficiente para a escala atual (1 processo). Se o app crescer
para múltiplos workers/servidores, trocar para um backend de cache
compartilhado (ex.: Redis) resolve sem mudar esta função."""

from django.core.cache import cache


def _client_identifier(request):
    """Sessão + IP, não só IP: atrás do Nginx em produção, várias pessoas
    podem aparecer com o mesmo IP se X-Forwarded-For não estiver configurado,
    então a sessão evita que uma trave a outra."""
    if not request.session.session_key:
        request.session.save()
    ip = request.META.get('REMOTE_ADDR', '')
    return f'{request.session.session_key}:{ip}'


def rate_limited(key_prefix, request, limit, window_seconds):
    """Retorna True se o limite já foi atingido nesta janela (deve bloquear o
    envio); caso contrário, conta essa tentativa e retorna False."""
    cache_key = f'ratelimit:{key_prefix}:{_client_identifier(request)}'
    count = cache.get(cache_key, 0)
    if count >= limit:
        return True
    cache.set(cache_key, count + 1, window_seconds)
    return False
