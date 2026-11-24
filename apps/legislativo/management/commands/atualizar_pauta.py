"""Deriva o "na pauta" das fontes oficiais, nas duas Casas.

O campo ``pauta`` era só manual (``Pauta: Sim`` na planilha), então o filtro
``?filtro=pauta`` mostrava o que alguém digitou, não a Ordem do Dia real. Este
comando torna o ``pauta`` autoritativo a partir das fontes oficiais:

- **Câmara**: lê a agenda oficial (sessões DELIBERATIVAS do Plenário e das
  comissões, de hoje até ``--dias`` à frente) — ``fontes.pauta_camara``.
- **Senado**: lê a situação atual de cada matéria (por ``codigoMateria`` do
  link) e considera na pauta quando a situação indica **ordem do dia** (ex.:
  "INCLUÍDA EM ORDEM DO DIA") — ``fontes.buscar_status_senado``.

Marca quem entrou na pauta e desmarca quem saiu; quando muda, dispara o alerta
(sino + e-mail) para quem segue. Proposições sem id reconhecível no link ficam
com a pauta manual.

Segurança: se a agenda da Câmara falhar, as proposições da Câmara ficam
intocadas (uma falha não pode esvaziar a pauta); idem para cada matéria do
Senado cuja leitura falhar.

Modos:
  (padrão)   marca/desmarca e alerta os seguidores das que mudaram
  --quiet    aplica SEM alertar (use no primeiro baseline)
  --dry-run  só mostra o que mudaria
  --dias N   janela da agenda da Câmara em dias (padrão 7)
"""
from __future__ import annotations

import re

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.proposicoes import fontes
from apps.proposicoes.models import Proposicao

ID_CAMARA = re.compile(r'idProposicao=(\d+)')
ID_SENADO = re.compile(r'/materia/(\d+)')


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

        em_pauta_camara = fontes.pauta_camara(dias=dias)
        if em_pauta_camara is None:
            self.stderr.write(self.style.WARNING(
                'Não consegui ler a agenda da Câmara; as proposições da Câmara ficam intocadas nesta rodada.'
            ))

        agora = timezone.now()
        marcadas = desmarcadas = sem_leitura_senado = 0
        for prop in Proposicao.objects.publicadas().order_by('pk'):
            link = prop.link or ''
            mcam = ID_CAMARA.search(link)
            msen = ID_SENADO.search(link)

            if mcam:
                if em_pauta_camara is None:
                    continue  # agenda indisponível: não mexe nas da Câmara
                deveria = mcam.group(1) in em_pauta_camara
            elif msen:
                dados = fontes.buscar_status_senado(msen.group(1))
                if dados is None:
                    sem_leitura_senado += 1
                    continue  # leitura falhou: não mexe nesta matéria
                deveria = dados['na_pauta']
            else:
                continue  # sem id reconhecível: pauta manual

            # Chegou aqui = a fonte oficial foi consultada com sucesso para esta
            # proposição. Registra a data da consulta (sincronizado_em não está
            # em CAMPOS_ALERTA, então nunca dispara alerta).
            if prop.pauta == deveria:
                if not dry_run:
                    Proposicao.objects.filter(pk=prop.pk).update(sincronizado_em=agora)
                continue

            if dry_run:
                self.stdout.write(f'[dry-run] {prop.titulo}: pauta {prop.pauta} -> {deveria}')
            elif quiet:
                Proposicao.objects.filter(pk=prop.pk).update(pauta=deveria, sincronizado_em=agora)
            else:
                prop.pauta = deveria
                prop.sincronizado_em = agora
                prop.save()  # dispara o alerta aos seguidores (pauta está em CAMPOS_ALERTA)

            if deveria:
                marcadas += 1
            else:
                desmarcadas += 1

        modo = 'dry-run' if dry_run else ('quiet' if quiet else 'normal')
        camara_info = (
            'agenda da Câmara indisponível'
            if em_pauta_camara is None
            else f'{len(em_pauta_camara)} na pauta oficial da Câmara'
        )
        self.stdout.write(self.style.SUCCESS(
            f'[{modo}] {camara_info}; {marcadas} marcada(s), {desmarcadas} desmarcada(s); '
            f'{sem_leitura_senado} matéria(s) do Senado sem leitura.'
        ))
