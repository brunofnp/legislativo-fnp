from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from apps.comentarios.models import Comentario, DenunciaComentario, Notificacao, Participacao

from .models import Usuario


def _dados_engajamento_usuario(usuario):
    """Dados de cadastro + interações do usuário na plataforma, no formato
    consumido pelo banco externo de engajamento (ver item 8 do pedido do
    usuário em 2026-08-07). Participação é casada por e-mail porque
    Participacao não tem FK pra Usuario (formulário público, também
    preenchido por quem nunca criou conta)."""
    perfil = getattr(usuario, 'perfil', None)
    comentarios = Comentario.objects.filter(autor=usuario).select_related('proposicao')
    participacoes = Participacao.objects.filter(email__iexact=usuario.email)
    denuncias_feitas = DenunciaComentario.objects.filter(denunciante=usuario)
    notificacoes = Notificacao.objects.filter(destinatario=usuario)

    return {
        'cadastro': {
            'id': usuario.id,
            'email': usuario.email,
            'nome': usuario.get_full_name(),
            'data_cadastro': usuario.date_joined.isoformat(),
            'ultimo_login': usuario.last_login.isoformat() if usuario.last_login else None,
            'is_staff': usuario.is_staff,
            'is_superuser': usuario.is_superuser,
            'grupos': list(usuario.groups.values_list('name', flat=True)),
            'municipio': str(perfil.municipio) if perfil and perfil.municipio else None,
            'uf': perfil.municipio.uf if perfil and perfil.municipio else '',
            'setor_responsavel': perfil.setor_responsavel if perfil else '',
            'cargo': perfil.cargo if perfil else '',
            'telefone': perfil.telefone if perfil else '',
            'status_aprovacao': perfil.status_aprovacao if perfil else None,
            'exclusao_solicitada_em': (
                perfil.exclusao_solicitada_em.isoformat() if perfil and perfil.exclusao_solicitada_em else None
            ),
        },
        'interacoes': {
            'comentarios': [
                {
                    'proposicao': c.proposicao.titulo,
                    'texto': c.texto,
                    'status_moderacao': c.status_moderacao,
                    'criado_em': c.criado_em.isoformat(),
                }
                for c in comentarios
            ],
            'participacoes': [
                {
                    'tipo': p.tipo,
                    'proposicao': p.proposicao,
                    'mensagem': p.mensagem,
                    'criado_em': p.criado_em.isoformat(),
                }
                for p in participacoes
            ],
        },
        'resumo_engajamento': {
            'total_comentarios': comentarios.count(),
            'comentarios_aprovados': comentarios.filter(status_moderacao='aprovado').count(),
            'total_participacoes': participacoes.count(),
            'total_denuncias_feitas': denuncias_feitas.count(),
            'notificacoes_recebidas': notificacoes.count(),
            'dias_desde_cadastro': (timezone.now() - usuario.date_joined).days,
        },
    }


def exportar_dados_view(request):
    """Exportação de dados de cadastro + engajamento pra Root, um usuário
    específico ou em massa -- alimenta um banco externo de pontuação de
    engajamento, fora deste sistema. Só Root (is_superuser): dados de
    interação de todo mundo é PII sensível, diferente da exportação
    individual de LGPD (exportar_meus_dados, cada um só a própria)."""
    if not request.user.is_superuser:
        raise PermissionDenied

    usuarios = Usuario.objects.select_related('perfil', 'perfil__municipio').order_by('email')

    if request.method == 'POST':
        modo = request.POST.get('modo')
        if modo == 'usuario':
            usuario_id = request.POST.get('usuario_id')
            alvo = usuarios.filter(pk=usuario_id)
            if not alvo.exists():
                return render(
                    request,
                    'admin/exportar_dados.html',
                    {**admin.site.each_context(request), 'title': 'Exportar dados de engajamento',
                     'usuarios': usuarios, 'erro': 'Selecione um usuário válido.'},
                )
            nome_arquivo = f'engajamento-usuario-{usuario_id}'
        else:
            alvo = usuarios
            nome_arquivo = 'engajamento-usuarios-em-massa'

        payload = {
            'gerado_em': timezone.now().isoformat(),
            'gerado_por': request.user.email,
            'total_usuarios': alvo.count(),
            'usuarios': [_dados_engajamento_usuario(u) for u in alvo],
        }
        response = JsonResponse(payload, json_dumps_params={'ensure_ascii': False, 'indent': 2})
        response['Content-Disposition'] = (
            f'attachment; filename="{nome_arquivo}-{timezone.now():%Y%m%d-%H%M}.json"'
        )
        return response

    context = {
        **admin.site.each_context(request),
        'title': 'Exportar dados de engajamento',
        'usuarios': usuarios,
    }
    return render(request, 'admin/exportar_dados.html', context)
