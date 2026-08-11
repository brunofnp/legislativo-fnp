from allauth.account.models import EmailAddress
from django.contrib import admin, messages
from django.contrib.admin.actions import delete_selected as django_delete_selected
from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.auth.admin import UserAdmin
from django.contrib.contenttypes.models import ContentType
from django.db.models import Exists, OuterRef
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html, format_html_join

from .models import Municipio, Perfil, TentativaLogin, Usuario


class PerfilInline(admin.StackedInline):
    model = Perfil
    can_delete = False
    extra = 0
    autocomplete_fields = ['municipio']


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    """Hierarquia de perfis (Root / Administrador FNP / Usuário) é gerenciada aqui via
    grupos e permissões nativas do Django — ver `python manage.py setup_roles`."""

    list_display = (
        'username', 'email', 'first_name', 'last_name', 'email_confirmado',
        'status_cadastro', 'exclusao_pendente', 'is_staff', 'is_superuser', 'is_active',
        'acoes_rapidas',
    )
    # UserAdmin.list_filter já inclui 'groups' -- não repetir aqui (duplicava o filtro).
    list_filter = UserAdmin.list_filter + ('perfil__status_aprovacao', 'perfil__exclusao_solicitada_em')
    inlines = [PerfilInline]
    actions = ['aprovar_cadastros', 'rejeitar_cadastros', 'aprovar_exclusoes', 'rejeitar_exclusoes']

    # Botões de ação rápida por linha (ver acoes_rapidas) reaproveitam o
    # form/checkboxes/CSRF já existentes da changelist via JS, em vez de
    # views/endpoints novos — aciona a mesma action registrada em
    # `actions` (inclusive a tela nativa de confirmação de exclusão).
    # js/admin_quick_actions.js agora carrega globalmente (ver
    # templates/admin/base_site.html), não só nesta página -- o modal de
    # Ajuda também precisa dele em todo o Admin.

    def get_queryset(self, request):
        email_verificado = EmailAddress.objects.filter(
            user=OuterRef('pk'), email__iexact=OuterRef('email'), verified=True,
        )
        return (
            super().get_queryset(request)
            .select_related('perfil')
            .annotate(_email_confirmado=Exists(email_verificado))
        )

    def _registrar_log(self, request, queryset, mensagem):
        """LogEntry nativo do Django Admin só é criado sozinho pra edição de
        1 objeto de cada vez (save_model) -- ações em massa via .update()
        (aprovar/rejeitar cadastro e exclusão) nunca passavam por aqui, então
        não ficava registrado quem aprovou/rejeitou o quê quando (auditoria
        de segurança, 2026-08-11)."""
        content_type_id = ContentType.objects.get_for_model(Usuario).pk
        for usuario in queryset:
            LogEntry.objects.log_action(
                user_id=request.user.pk,
                content_type_id=content_type_id,
                object_id=usuario.pk,
                object_repr=str(usuario),
                action_flag=CHANGE,
                change_message=mensagem,
            )

    def response_change(self, request, obj):
        """Botões extras na página do próprio usuário (ver
        templates/admin/usuarios/usuario/submit_line.html) para aprovar/
        rejeitar cadastro e exclusão sem precisar voltar pra listagem e usar
        a ação em massa."""
        if '_aprovar_cadastro' in request.POST:
            Perfil.objects.filter(usuario=obj).update(status_aprovacao=Perfil.APROVADO)
            self._registrar_log(request, [obj], 'Cadastro aprovado.')
            self.message_user(request, 'Cadastro aprovado.')
            return HttpResponseRedirect(request.path)
        if '_rejeitar_cadastro' in request.POST:
            Perfil.objects.filter(usuario=obj).update(status_aprovacao=Perfil.REJEITADO)
            self._registrar_log(request, [obj], 'Cadastro rejeitado.')
            self.message_user(request, 'Cadastro rejeitado.')
            return HttpResponseRedirect(request.path)
        if '_rejeitar_exclusao' in request.POST:
            Perfil.objects.filter(usuario=obj).update(exclusao_solicitada_em=None)
            self._registrar_log(request, [obj], 'Solicitação de exclusão rejeitada.')
            self.message_user(request, 'Solicitação de exclusão rejeitada.')
            return HttpResponseRedirect(request.path)
        if '_aprovar_exclusao' in request.POST:
            perfil = getattr(obj, 'perfil', None)
            if not perfil or not perfil.exclusao_solicitada_em:
                self.message_user(request, 'Este usuário não tem exclusão solicitada.', level=messages.WARNING)
                return HttpResponseRedirect(request.path)
            nome = str(obj)
            obj.delete()
            self.message_user(request, f'Conta de {nome} excluída.')
            return HttpResponseRedirect(reverse('admin:usuarios_usuario_changelist'))
        return super().response_change(request, obj)

    @admin.display(description='Cadastro', ordering='perfil__status_aprovacao')
    def status_cadastro(self, obj):
        perfil = getattr(obj, 'perfil', None)
        return perfil.get_status_aprovacao_display() if perfil else '—'

    @admin.display(description='Exclusão solicitada', boolean=True, ordering='perfil__exclusao_solicitada_em')
    def exclusao_pendente(self, obj):
        perfil = getattr(obj, 'perfil', None)
        return bool(perfil and perfil.exclusao_solicitada_em)

    @admin.display(description='E-mail confirmado', boolean=True, ordering='_email_confirmado')
    def email_confirmado(self, obj):
        """Cadastro por e-mail/senha não exige confirmar o e-mail antes de
        navegar (ACCOUNT_EMAIL_VERIFICATION='optional', ver settings.py) --
        alguém pode se cadastrar usando o e-mail de outra pessoa sem provar
        que é dono dele. Como a aprovação de cadastro já é uma revisão
        humana (CadastroPendenteMiddleware), essa coluna dá ao Root/
        Administrador FNP o sinal que falta pra recusar um cadastro
        suspeito antes de aprovar (auditoria de segurança, 2026-08-11)."""
        return bool(getattr(obj, '_email_confirmado', False))

    @admin.display(description='Ações rápidas')
    def acoes_rapidas(self, obj):
        perfil = getattr(obj, 'perfil', None)
        botoes = []
        if perfil and perfil.status_aprovacao == Perfil.PENDENTE:
            botoes.append(('aprovar_cadastros', 'Aprovar cadastro', 'ok'))
            botoes.append(('rejeitar_cadastros', 'Rejeitar cadastro', 'danger'))
        if perfil and perfil.exclusao_solicitada_em:
            botoes.append(('aprovar_exclusoes', 'Aprovar exclusão', 'danger'))
            botoes.append(('rejeitar_exclusoes', 'Manter conta', 'ok'))
        if not botoes:
            return '—'
        return format_html(
            '<div class="fnp-quick-actions">{}</div>',
            format_html_join(
                '',
                '<button type="button" class="fnp-quick-action fnp-quick-action--{}" '
                'data-fnp-action="{}" data-fnp-pk="{}">{}</button>',
                ((estilo, acao, obj.pk, label) for acao, label, estilo in botoes),
            ),
        )

    @admin.action(description='Aprovar cadastros selecionados')
    def aprovar_cadastros(self, request, queryset):
        atualizados = Perfil.objects.filter(usuario__in=queryset).update(status_aprovacao=Perfil.APROVADO)
        self._registrar_log(request, queryset, 'Cadastro aprovado (ação em massa).')
        self.message_user(request, f'{atualizados} cadastro(s) aprovado(s).')

    @admin.action(description='Rejeitar cadastros selecionados')
    def rejeitar_cadastros(self, request, queryset):
        atualizados = Perfil.objects.filter(usuario__in=queryset).update(status_aprovacao=Perfil.REJEITADO)
        self._registrar_log(request, queryset, 'Cadastro rejeitado (ação em massa).')
        self.message_user(request, f'{atualizados} cadastro(s) rejeitado(s).')

    @admin.action(description='Aprovar exclusão solicitada (exclui a conta)')
    def aprovar_exclusoes(self, request, queryset):
        alvo = queryset.filter(perfil__exclusao_solicitada_em__isnull=False)
        ignorados = queryset.count() - alvo.count()
        if ignorados:
            self.message_user(
                request,
                f'{ignorados} usuário(s) ignorado(s) por não ter exclusão solicitada.',
                level=messages.WARNING,
            )
        if not alvo:
            return None
        # Reaproveita a ação nativa "Excluir selecionados" (mesma tela de
        # confirmação com o resumo de objetos relacionados que serão apagados
        # em cascata) em vez de excluir direto sem confirmação.
        return django_delete_selected(self, request, alvo)

    @admin.action(description='Rejeitar solicitação de exclusão (mantém a conta)')
    def rejeitar_exclusoes(self, request, queryset):
        atualizados = Perfil.objects.filter(
            usuario__in=queryset, exclusao_solicitada_em__isnull=False,
        ).update(exclusao_solicitada_em=None)
        self._registrar_log(request, queryset, 'Solicitação de exclusão rejeitada (ação em massa).')
        self.message_user(request, f'{atualizados} solicitação(ões) de exclusão rejeitada(s).')


@admin.register(Municipio)
class MunicipioAdmin(admin.ModelAdmin):
    list_display = ('nome', 'uf', 'prefeito')
    list_filter = ('uf',)
    search_fields = ('nome', 'uf', 'prefeito')


@admin.register(TentativaLogin)
class TentativaLoginAdmin(admin.ModelAdmin):
    """Log de auditoria -- só leitura, nunca criado/editado à mão (ver
    signals.registrar_login_sucesso/falha)."""

    list_display = ('criado_em', 'email', 'usuario', 'sucesso', 'ip')
    list_filter = ('sucesso',)
    search_fields = ('email', 'ip')
    date_hierarchy = 'criado_em'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
