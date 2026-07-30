from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.legislativo.models import (
    Comentario,
    EdicaoMeritoHistorico,
    Macrotema,
    Noticia,
    Participacao,
    Proposicao,
    Tema,
    Usuario,
)

ROOT_EMAIL_PADRAO = 'bruno.marra@fnp.org.br'

ROOT_GROUP_NAME = 'Root'
ADMINISTRADOR_GROUP_NAME = 'Administrador FNP'
USUARIO_GROUP_NAME = 'Usuário'

# Root não recebe permissões explícitas: is_superuser já ignora toda checagem de permissão.
ADMINISTRADOR_PERMISSOES = {
    Proposicao: ['view', 'change'],
    Comentario: ['view', 'change'],
    Macrotema: ['view', 'add', 'change'],
    Tema: ['view', 'add', 'change'],
    Noticia: ['view', 'add', 'change'],
    Participacao: ['view'],
    EdicaoMeritoHistorico: ['view'],
}


class Command(BaseCommand):
    help = (
        'Cria/sincroniza os grupos de hierarquia (Root, Administrador FNP, Usuário) '
        'e promove o e-mail informado a superusuário (root). Idempotente.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--root-email',
            default=ROOT_EMAIL_PADRAO,
            help=f'E-mail a promover a Root. Padrão: {ROOT_EMAIL_PADRAO}',
        )

    def handle(self, *args, **options):
        with transaction.atomic():
            root_group, _ = Group.objects.get_or_create(name=ROOT_GROUP_NAME)

            admin_group, _ = Group.objects.get_or_create(name=ADMINISTRADOR_GROUP_NAME)
            admin_perms = []
            for model, acoes in ADMINISTRADOR_PERMISSOES.items():
                content_type = ContentType.objects.get_for_model(model)
                codenames = [f'{acao}_{model._meta.model_name}' for acao in acoes]
                admin_perms += list(Permission.objects.filter(content_type=content_type, codename__in=codenames))
            admin_group.permissions.set(admin_perms)

            Group.objects.get_or_create(name=USUARIO_GROUP_NAME)

        self.stdout.write(self.style.SUCCESS(
            f'Grupos sincronizados: {ROOT_GROUP_NAME}, {ADMINISTRADOR_GROUP_NAME} '
            f'({len(admin_perms)} permissões), {USUARIO_GROUP_NAME}.'
        ))

        email = options['root_email']
        try:
            usuario = Usuario.objects.get(email__iexact=email)
        except Usuario.DoesNotExist:
            self.stdout.write(self.style.WARNING(
                f'Usuário com e-mail {email} ainda não existe. '
                'Rode este comando novamente depois que a pessoa fizer o primeiro login/cadastro.'
            ))
            return

        usuario.is_staff = True
        usuario.is_superuser = True
        usuario.save(update_fields=['is_staff', 'is_superuser'])
        usuario.groups.add(root_group)
        usuario.groups.remove(*Group.objects.filter(name=USUARIO_GROUP_NAME))
        self.stdout.write(self.style.SUCCESS(f'{email} promovido a Root (superusuário).'))
