from django.contrib import admin
from django.contrib.admin.apps import AdminConfig


class FNPAdminSite(admin.AdminSite):
    site_header = 'Painel Root — Legislativo FNP'
    site_title = 'Legislativo FNP'
    index_title = 'Administração e hierarquia de acesso'
    index_template = 'admin/fnp_index.html'

    def index(self, request, extra_context=None):
        from django.db.models import Count, F, Q

        from apps.comentarios.models import Comentario
        from apps.proposicoes.models import Proposicao
        from apps.usuarios.models import Perfil, Usuario

        extra_context = extra_context or {}
        extra_context['fnp_dashboard'] = {
            'comentarios_pendentes': Comentario.objects.filter(status_moderacao='pendente').count(),
            'cadastros_pendentes': Perfil.objects.filter(status_aprovacao=Perfil.PENDENTE).count(),
            'exclusoes_pendentes': Perfil.objects.filter(exclusao_solicitada_em__isnull=False).count(),
            'proposicoes_urgentes': Proposicao.objects.filter(urgente=True).count(),
            'proposicoes_na_pauta': Proposicao.objects.filter(pauta=True).count(),
        }
        extra_context['fnp_usuarios'] = {
            'total': Usuario.objects.count(),
            'aprovados': Perfil.objects.filter(status_aprovacao=Perfil.APROVADO).count(),
        }
        extra_context['fnp_comentarios'] = {
            'aprovados': Comentario.objects.filter(status_moderacao='aprovado').count(),
            'rejeitados': Comentario.objects.filter(status_moderacao='rejeitado').count(),
            'denunciados': Comentario.objects.filter(denuncias__isnull=False).distinct().count(),
        }
        extra_context['fnp_top_engajamento'] = (
            Proposicao.objects.annotate(
                comentarios_count=Count(
                    'comentarios', distinct=True, filter=Q(comentarios__status_moderacao='aprovado')
                )
            )
            .annotate(relevancia=F('visualizacoes') + F('comentarios_count') * 5)
            .filter(Q(visualizacoes__gt=0) | Q(comentarios_count__gt=0))
            .order_by('-relevancia')[:5]
        )
        return super().index(request, extra_context)


class FNPAdminConfig(AdminConfig):
    default_site = 'apps.legislativo.admin_site.FNPAdminSite'
