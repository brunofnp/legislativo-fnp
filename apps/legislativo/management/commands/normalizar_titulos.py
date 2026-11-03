"""Corrige proposições cujo `titulo` ficou com a ementa/assunto no lugar do
número oficial ("Tipo Número/Ano"), e remove duplicatas de proposições que já
existem com o número correto.

Origem: 5 registros (pks ~316-320 em produção) entraram manualmente com título
descritivo e sem link. Números confirmados na fonte oficial (Câmara/Senado):

  descritivo                                          -> oficial
  "PEC da Segurança"                                  -> PEC 18/2025   (duplicata)
  "Altera o art. 159 ... Fundo de Participação ..."   -> PEC 29/2017
  "Desobriga os Municípios com até 65.000 ..."        -> PLP 74/2026
  "Legitimidade para Entidades ... (art. 103, ADC/ADI)" -> PEC 253/2016 (duplicata)
  "Institui o Programa Nacional de Municípios Int..." -> PL 3645/2026

Idempotente: casa o registro pelo título descritivo; depois de corrigido o
título vira o número, então uma segunda execução não encontra mais nada.
Rodar: python manage.py normalizar_titulos [--dry-run]
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.proposicoes.models import Proposicao

# Registros únicos: renomear o título para o número oficial e preencher o link.
RENOMEAR = [
    {
        'match': {'titulo__startswith': 'Altera o art. 159 da Constituição Federal para disciplinar a distribuição'},
        'titulo': 'PEC 29/2017',
        'casa': 'senado',
        'link': 'https://www25.senado.leg.br/web/atividade/materias/-/materia/130672',
    },
    {
        'match': {'titulo__startswith': 'Desobriga os Municípios com até 65.000'},
        'titulo': 'PLP 74/2026',
        'casa': 'camara',
        'link': 'https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao=2611313',
    },
    {
        'match': {'titulo__startswith': 'Institui o Programa Nacional de Municípios Inteligentes'},
        'titulo': 'PL 3645/2026',
        'casa': 'senado',
        'link': 'https://www25.senado.leg.br/web/atividade/materias/-/materia/175127',
    },
]

# Duplicatas: já existe o registro correto com número; remover o descritivo,
# preservando eventuais comentários/anexos (movidos para o registro correto).
DEDUP = [
    {'match': {'titulo__icontains': 'PEC da Segurança'}, 'twin': 'PEC 18/2025'},
    {'match': {'titulo__icontains': 'Legitimidade para Entidades de representação municipais'}, 'twin': 'PEC 253/2016'},
]


class Command(BaseCommand):
    help = 'Corrige títulos descritivos (sem número) e remove duplicatas das proposições.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Só mostra o que faria, sem gravar.')

    def handle(self, *args, **options):
        dry = options['dry_run']
        with transaction.atomic():
            for regra in RENOMEAR:
                self._renomear(regra, dry)
            for regra in DEDUP:
                self._dedup(regra, dry)
            if dry:
                self.stdout.write(self.style.WARNING('DRY-RUN: nada gravado.'))
                transaction.set_rollback(True)

    def _mover_conteudo(self, origem, destino, dry):
        """Move comentários e anexos do registro removido para o correto."""
        coment = origem.comentarios.count()
        anexos = origem.anexos.count()
        if not dry:
            origem.comentarios.update(proposicao=destino)
            origem.anexos.update(proposicao=destino)
        if coment or anexos:
            self.stdout.write(f'    movidos p/ {destino.titulo}: {coment} comentário(s), {anexos} anexo(s)')

    def _renomear(self, regra, dry):
        qs = Proposicao.objects.filter(**regra['match'])
        for p in qs:
            twin = Proposicao.objects.filter(titulo=regra['titulo']).exclude(pk=p.pk).first()
            if twin:
                # Já existe o número: trata como duplicata (não cria 2 iguais).
                self.stdout.write(f'• #{p.pk} "{p.titulo[:50]}…" já existe como {regra["titulo"]} (#{twin.pk}) — mesclando')
                self._mover_conteudo(p, twin, dry)
                if not dry:
                    p.delete()
                continue
            self.stdout.write(f'• #{p.pk} "{p.titulo[:50]}…" -> {regra["titulo"]} ({regra["casa"]})')
            if not dry:
                p.titulo = regra['titulo']
                p.casa = regra['casa']
                p.link = regra['link']
                p.save(update_fields=['titulo', 'casa', 'link'])

    def _dedup(self, regra, dry):
        qs = Proposicao.objects.filter(**regra['match'])
        twin = Proposicao.objects.filter(titulo=regra['twin']).first()
        for p in qs:
            if twin and twin.pk == p.pk:
                continue
            if not twin:
                # Sem o registro correto na base: em vez de apagar, só renomeia
                # para não perder o item (fica com o número certo).
                self.stdout.write(f'• #{p.pk} "{p.titulo[:50]}…" -> {regra["twin"]} (sem duplicata; renomeando)')
                if not dry:
                    p.titulo = regra['twin']
                    p.save(update_fields=['titulo'])
                continue
            self.stdout.write(f'• #{p.pk} "{p.titulo[:50]}…" é duplicata de {regra["twin"]} (#{twin.pk}) — removendo')
            self._mover_conteudo(p, twin, dry)
            if not dry:
                p.delete()
