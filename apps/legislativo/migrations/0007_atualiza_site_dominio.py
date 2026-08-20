# django.contrib.sites cria o Site (pk=SITE_ID, ver settings.py) com
# domain='example.com'/name='example.com' por padrão -- nunca tinha sido
# atualizado. django-allauth usa esses dois campos pra montar o texto de
# TODOS os e-mails transacionais (confirmação de cadastro, redefinição de
# senha, etc.): "[example.com] E-mail de redefinição de senha", "Olá da
# example.com!" -- achado real, reportado pelo usuário num e-mail de
# redefinição de senha de verdade. O link em si (password_reset_url) já
# usava o domínio certo (vem do host da requisição, não daqui) -- só o
# texto de marca institucional estava errado.
#
# update_or_create (não .filter().update()) de propósito: num banco novo
# (ex.: banco de teste, recriado do zero a cada execução), a linha do
# Site só é criada por um sinal post_migrate do próprio Django DEPOIS que
# todas as migrations terminam -- .filter(pk=1).update(...) não acha
# nenhuma linha nesse momento e não faz nada, silenciosamente (achado
# rodando os testes: passava num banco dev já existente, falhava no
# banco de teste recriado do zero).
from django.db import migrations


def atualizar_site(apps, schema_editor):
    Site = apps.get_model('sites', 'Site')
    Site.objects.update_or_create(
        pk=1,
        defaults={'domain': 'legislativo.fnp.org.br', 'name': 'Painel Legislativo FNP'},
    )


def reverter_site(apps, schema_editor):
    Site = apps.get_model('sites', 'Site')
    Site.objects.filter(pk=1).update(domain='example.com', name='example.com')


class Migration(migrations.Migration):

    dependencies = [
        ('legislativo', '0006_remove_comentario_autor_remove_comentario_parent_and_more'),
        ('sites', '0002_alter_domain_unique'),
    ]

    operations = [
        migrations.RunPython(atualizar_site, reverter_site),
    ]
