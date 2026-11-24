"""Atualiza o campo ``apensada_a`` das proposições da Câmara.

Lê o último despacho de apense/desapense da ficha oficial (``fontes.
buscar_apensacao_camara``) e grava a principal a que a matéria está apensada
(ex.: "PEC 231/2019"), ou limpa o campo quando foi desapensada.

Conservador por princípio: quando a fonte é indeterminada (``None`` — sem
despacho de apense/desapense ou principal não identificável), NÃO toca no
campo, pra não sobrescrever a curadoria da coordenação com um palpite. Só
grava em detecção positiva: uma principal clara ("X") ou desapensação
explícita ("").

Só Câmara (o despacho de apensação vem da ficha da Câmara). ``apensada_a`` não
está em CAMPOS_ALERTA; a gravação é silenciosa (``.update()``), sem alerta.

Modos:
  (padrão)   grava as mudanças detectadas
  --dry-run  só mostra o que mudaria
  --limit N  processa no máximo N proposições da Câmara
"""
from __future__ import annotations

import re

from django.core.management.base import BaseCommand

from apps.proposicoes import fontes
from apps.proposicoes.models import Proposicao

ID_CAMARA = re.compile(r'idProposicao=(\d+)')


class Command(BaseCommand):
    help = 'Atualiza o campo apensada_a das proposições da Câmara pelo último despacho de apense/desapense.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', dest='dry_run',
                            help='Não grava; apenas mostra o que mudaria.')
        parser.add_argument('--limit', type=int, default=0,
                            help='Processa no máximo N proposições da Câmara (0 = todas).')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']

        alteradas = indeterminadas = fora_camara = 0
        processadas = 0
        for prop in Proposicao.objects.publicadas().order_by('pk'):
            m = ID_CAMARA.search(prop.link or '')
            if not m:
                fora_camara += 1
                continue
            if limit and processadas >= limit:
                break
            processadas += 1

            resultado = fontes.buscar_apensacao_camara(m.group(1), prop.titulo)
            if resultado is None:
                indeterminadas += 1
                continue  # indeterminado: não toca (preserva curadoria)

            if resultado == (prop.apensada_a or ''):
                continue  # já está correto

            if dry_run:
                antes = prop.apensada_a or '(autônoma)'
                depois = resultado or '(autônoma)'
                self.stdout.write(f'[dry-run] {prop.titulo}: {antes} -> {depois}')
            else:
                Proposicao.objects.filter(pk=prop.pk).update(apensada_a=resultado)
            alteradas += 1

        modo = 'dry-run' if dry_run else 'normal'
        self.stdout.write(self.style.SUCCESS(
            f'[{modo}] {alteradas} alterada(s), {indeterminadas} indeterminada(s) '
            f'(não tocadas), {fora_camara} fora da Câmara.'
        ))
