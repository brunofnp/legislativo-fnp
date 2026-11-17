"""Deriva o "na pauta" da agenda oficial da Câmara.

O campo ``pauta`` das proposições era só manual (``Pauta: Sim`` na planilha),
então o filtro ``?filtro=pauta`` mostrava o que alguém digitou, não a Ordem do
Dia real. Este comando lê a agenda oficial (sessões DELIBERATIVAS do Plenário e
das comissões, de hoje até ``--dias`` à frente) e torna o ``pauta`` das
proposições da **Câmara** autoritativo: marca quem entrou na pauta, desmarca
quem saiu. Quando muda, dispara o alerta (sino + e-mail) para quem segue.

As proposições do **Senado** (e qualquer uma sem ``idProposicao`` no link) não
são tocadas — continuam com a pauta manual até a v2 (agenda do Senado, quando a
API de Dados Abertos estabilizar).

Segurança: se a leitura da agenda falhar (rede/API fora), o comando NÃO altera
nada — uma falha não pode esvaziar a pauta do painel.

Modos:
  (padrão)   marca/desmarca e alerta os seguidores das que mudaram
  --quiet    aplica SEM alertar (use no primeiro baseline)
  --dry-run  só mostra o que mudaria
  --dias N   janela da agenda em dias (padrão 7)
"""
from __future__ import annotations

import re

from django.core.management.base import BaseCommand

from apps.proposicoes import fontes
from apps.proposicoes.models import Proposicao

ID_CAMARA = re.compile(r'idProposicao=(\d+)')


class Command(BaseCommand):
    help = 'Deriva o campo "pauta" das proposições da Câmara a partir da agenda oficial (Ordem do Dia).'

    def add_arguments(self, parser):
        parser.add_argument('--dias', type=int, default=7,
                            help='Janela da agenda, em dias a partir de hoje (padrão 7).')
        parser.add_argument('--dry-run', action='store_true', dest='dry_run',
                            help='Não grava; apenas mostra o que mudaria.')
        parser.add_argument('--quiet', action='store_true', dest='quiet',
                            help='Aplica sem disparar alerta (sino/e-mail) — use no primeiro baseline.')

    def handle(self, *args, **options):
        dias = options['dias']
        dry_run = options['dry_run']
        quiet = options['quiet']

        em_pauta = fontes.pauta_camara(dias=dias)
        if em_pauta is None:
            self.stderr.write(self.style.WARNING(
                'Não consegui ler a agenda oficial da Câmara; nada foi alterado.'
            ))
            return

        marcadas = desmarcadas = 0
        for prop in Proposicao.objects.publicadas().order_by('pk'):
            m = ID_CAMARA.search(prop.link or '')
            if not m:
                continue  # Senado / sem id: pauta manual, não toca
            deveria = m.group(1) in em_pauta
            if prop.pauta == deveria:
                continue

            if dry_run:
                self.stdout.write(f'[dry-run] {prop.titulo}: pauta {prop.pauta} -> {deveria}')
            elif quiet:
                Proposicao.objects.filter(pk=prop.pk).update(pauta=deveria)
            else:
                prop.pauta = deveria
                prop.save()  # dispara o alerta aos seguidores (pauta está em CAMPOS_ALERTA)

            if deveria:
                marcadas += 1
            else:
                desmarcadas += 1

        modo = 'dry-run' if dry_run else ('quiet' if quiet else 'normal')
        self.stdout.write(self.style.SUCCESS(
            f'[{modo}] {len(em_pauta)} proposição(ões) na pauta oficial da Câmara; '
            f'{marcadas} marcada(s), {desmarcadas} desmarcada(s) no painel.'
        ))
