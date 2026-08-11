"""Rate limiting simples para os formulários públicos (comentário e
participação), sem depender de pacote externo — usa o cache padrão do Django
(LocMemCache), suficiente para a escala atual (1 processo). Se o app crescer
para múltiplos workers/servidores, trocar para um backend de cache
compartilhado (ex.: Redis) resolve sem mudar esta função."""

from django.core.cache import cache


def _client_ip(request):
    """Em produção o Gunicorn só é alcançado via Nginx (porta do container
    presa em 127.0.0.1, ver docker-compose.yml) -- sem ler X-Forwarded-For,
    REMOTE_ADDR é sempre o IP do próprio Nginx pra qualquer visitante,
    zerando na prática o componente de IP do rate limit (auditoria de
    segurança, 2026-08-11). Nginx é o único ponto de entrada confiável
    (deploy/nginx-legislativo.conf: proxy_set_header X-Forwarded-For
    $proxy_add_x_forwarded_for), então o valor confiável é sempre o ÚLTIMO
    da lista (o que o próprio Nginx anexou) -- um cliente malicioso pode
    mandar um X-Forwarded-For falso, mas só entra ANTES do valor real que o
    Nginx acrescenta, nunca depois."""
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded_for:
        return forwarded_for.split(',')[-1].strip()
    return request.META.get('REMOTE_ADDR', '')


def _client_identifier(request):
    """Sessão + IP, não só IP: uma sessão evita que um IP compartilhado
    (rede corporativa/CGNAT) trave todo mundo atrás dele por um só abusar."""
    if not request.session.session_key:
        request.session.save()
    return f'{request.session.session_key}:{_client_ip(request)}'


def rate_limited(key_prefix, request, limit, window_seconds):
    """Retorna True se o limite já foi atingido nesta janela (deve bloquear o
    envio); caso contrário, conta essa tentativa e retorna False."""
    cache_key = f'ratelimit:{key_prefix}:{_client_identifier(request)}'
    count = cache.get(cache_key, 0)
    if count >= limit:
        return True
    cache.set(cache_key, count + 1, window_seconds)
    return False
