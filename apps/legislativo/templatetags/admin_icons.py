from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# Um ícone por "função" (app ou model) do Admin, no mesmo estilo de traço usado
# no resto da plataforma (viewBox 24x24, stroke, sem preenchimento).
_ICON_PATHS = {
    'dashboard': '<rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/>',
    'shield': '<path d="M12 2 3 6v6c0 5 3.8 9 9 10 5.2-1 9-5 9-10V6z"/>',
    'message-circle': '<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8z"/>',
    'message-square': '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
    'bell': '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>',
    'mail': '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m2 7 10 6 10-6"/>',
    'share': '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="M8.6 13.5 15.4 17.5M15.4 6.5 8.6 10.5"/>',
    'grid': '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/>',
    'link': '<path d="M10 13a5 5 0 0 0 7.5.5l2-2a5 5 0 0 0-7-7l-1 1"/><path d="M14 11a5 5 0 0 0-7.5-.5l-2 2a5 5 0 0 0 7 7l1-1"/>',
    'key': '<circle cx="7.5" cy="15.5" r="5.5"/><path d="m21 2-9.6 9.6M15.5 7.5 18 10l3-3-2.5-2.5"/>',
    'file-text': '<path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5z"/><path d="M14.5 2v5.5H20"/><path d="M9 13h6M9 17h6M9 9h1"/>',
    'clock': '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    'folder': '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    'newspaper': '<path d="M4 4h13a2 2 0 0 1 2 2v13a1 1 0 0 1-1 1H6a2 2 0 0 1-2-2z"/><path d="M4 4v14a2 2 0 0 1-2 2"/><path d="M9 8h6M9 12h6M9 16h4"/>',
    'tag': '<path d="M20.59 13.41 11 3.83A2 2 0 0 0 9.59 3.24L3 3v6.59a2 2 0 0 0 .59 1.41l9.59 9.59a2 2 0 0 0 2.82 0l6.59-6.59a2 2 0 0 0 0-2.82Z"/><circle cx="7.5" cy="7.5" r="1"/>',
    'building': '<path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z"/><path d="M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2"/><path d="M10 6h4M10 10h4M10 14h4M10 18h4"/>',
    'globe': '<circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>',
    'user': '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.6-7 8-7s8 3 8 7"/>',
    'users': '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    'ban': '<circle cx="12" cy="12" r="10"/><path d="m4.9 4.9 14.2 14.2"/>',
    'flag': '<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><path d="M4 22V15"/>',
    'dot': '<circle cx="12" cy="12" r="3"/>',
    'download': '<path d="M12 3v12m0 0-4-4m4 4 4-4"/><path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/>',
    'home': '<path d="M3 11.5 12 4l9 7.5"/><path d="M5 10v9a1 1 0 0 0 1 1h4v-6h4v6h4a1 1 0 0 0 1-1v-9"/>',
    'help-circle': '<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><path d="M12 17h.01"/>',
}

# Ícone por app do Django Admin (usado no link direto, se o app só tiver um
# model, ou no cabeçalho do grupo recolhível, se tiver mais de um).
_APP_ICONS = {
    'auth': 'shield',
    'comentarios': 'message-circle',
    'account': 'mail',
    'socialaccount': 'share',
    'proposicoes': 'file-text',
    'sites': 'globe',
    'usuarios': 'users',
}

# Ícone por model (chave "app_label.object_name", minúsculo) — usado nos
# subitens de um grupo recolhível.
_MODEL_ICONS = {
    'auth.group': 'shield',
    'comentarios.comentario': 'message-square',
    'comentarios.notificacao': 'bell',
    'comentarios.participacao': 'users',
    'comentarios.palavraproibida': 'ban',
    'comentarios.denunciacomentario': 'flag',
    'account.emailaddress': 'mail',
    'socialaccount.socialapp': 'grid',
    'socialaccount.socialaccount': 'link',
    'socialaccount.socialtoken': 'key',
    'proposicoes.edicaomeritohistorico': 'clock',
    'proposicoes.macrotema': 'folder',
    'proposicoes.noticia': 'newspaper',
    'proposicoes.proposicao': 'file-text',
    'proposicoes.tema': 'tag',
    'sites.site': 'globe',
    'usuarios.municipio': 'building',
    'usuarios.usuario': 'user',
}

_SVG_WRAPPER = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{}</svg>'
)


def _svg(icon_name):
    return mark_safe(_SVG_WRAPPER.format(_ICON_PATHS.get(icon_name, _ICON_PATHS['dot'])))


@register.simple_tag
def icon(icon_name):
    return _svg(icon_name)


@register.simple_tag
def app_icon(app_label):
    return _svg(_APP_ICONS.get(app_label, 'grid'))


@register.simple_tag
def model_icon(app_label, object_name):
    key = f'{app_label}.{object_name}'.lower()
    return _svg(_MODEL_ICONS.get(key, _APP_ICONS.get(app_label, 'dot')))
