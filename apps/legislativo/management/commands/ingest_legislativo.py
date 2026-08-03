from __future__ import annotations

import json

from django.core.management.base import BaseCommand

from ...data_utils import (
    is_aprovada,
    is_on_pauta,
    is_parada,
    is_urgente,
    load_json_file,
    normalize_text,
    priority_from_text,
    slug_for_name,
    split_temas,
)
from apps.proposicoes.models import EdicaoMeritoHistorico, Macrotema, Noticia, Proposicao, Tema


class Command(BaseCommand):
    help = 'Importa proposições a partir de JSON gerado pelo Apps Script ou exportado da planilha.'

    def add_arguments(self, parser):
        parser.add_argument('source', type=str, help='Caminho para o arquivo JSON de importação')
        parser.add_argument('--dry-run', action='store_true', help='Não grava no banco, apenas valida o payload')

    def handle(self, *args, **options):
        source = options['source']
        dry_run = options['dry_run']
        records = load_json_file(source)
        self.stdout.write(f'Importando {len(records)} itens de {source}')

        for raw_record in records:
            titulo = normalize_text(raw_record.get('Proposição') or raw_record.get('Titulo') or raw_record.get('titulo'))
            if not titulo:
                self.stderr.write('Ignorando registro sem título.')
                continue

            casa = normalize_text(raw_record.get('Casa')).lower()
            if casa not in ('camara', 'câmara', 'senado'):
                casa = 'camara'
            if casa == 'câmara':
                casa = 'camara'

            tema_nomes = split_temas(raw_record.get('Tema'))
            macrotema = None
            macrotema_nome = normalize_text(raw_record.get('Macrotema') or raw_record.get('Tema Principal') or '')
            if macrotema_nome:
                macrotema, _ = Macrotema.objects.get_or_create(
                    nome=macrotema_nome,
                    defaults={'slug': slug_for_name(macrotema_nome), 'cor': '#1A4B8F'},
                )

            props = {
                'casa': casa,
                'status_tramitacao': normalize_text(raw_record.get('Status da Tramitação')),
                'local': normalize_text(raw_record.get('Local')),
                'pauta': is_on_pauta(raw_record),
                'urgente': is_urgente(raw_record),
                'aprovada': is_aprovada(raw_record),
                'parada': is_parada(raw_record),
                'prioridade_fnp': priority_from_text(raw_record.get('Prioridade FNP')),
                'macrotema': macrotema,
                'ementa_resumida': normalize_text(raw_record.get('Ementa Resumida')),
                'proximos_eventos': normalize_text(raw_record.get('Próximos Eventos/Ações Esperadas')),
                'interlocutores': normalize_text(raw_record.get('Interlocutores Estratégicos (Relatores, Lideranças, Técnicos)')),
                'ultima_movimentacao': normalize_text(raw_record.get('Última Movimentação')),
                'link': normalize_text(raw_record.get('Link')),
                'posicionamento_fnp': normalize_text(raw_record.get('Posicionamento da FNP')),
                'acoes_incidencia': normalize_text(raw_record.get('Ações de Incidência da FNP (realizadas e planejadas)')),
                'riscos_oportunidades': normalize_text(raw_record.get('Riscos e Oportunidades')),
            }

            if dry_run:
                self.stdout.write(f'[{titulo[:80]}] {props}')
                continue

            valores_anteriores = Proposicao.objects.filter(titulo=titulo).values(*Proposicao.CAMPOS_MERITO).first()

            proposicao, created = Proposicao.objects.update_or_create(
                titulo=titulo,
                defaults=props,
            )
            if created:
                self.stdout.write(f'Criada proposição: {titulo}')
            else:
                self.stdout.write(f'Atualizada proposição: {titulo}')
                if valores_anteriores:
                    EdicaoMeritoHistorico.objects.bulk_create([
                        EdicaoMeritoHistorico(
                            proposicao=proposicao,
                            autor=None,
                            campo=campo,
                            valor_anterior=valores_anteriores.get(campo, ''),
                            valor_novo=getattr(proposicao, campo),
                        )
                        for campo in Proposicao.CAMPOS_MERITO
                        if valores_anteriores.get(campo, '') != getattr(proposicao, campo)
                    ])

            temas_objs = []
            for nome in tema_nomes:
                tema_obj, _ = Tema.objects.get_or_create(
                    nome=nome,
                    defaults={'slug': slug_for_name(nome)},
                )
                temas_objs.append(tema_obj)
            proposicao.temas.set(temas_objs)

            noticias = raw_record.get('_noticias') or raw_record.get('noticias') or []
            if isinstance(noticias, str):
                try:
                    noticias = json.loads(noticias)
                except json.JSONDecodeError:
                    noticias = []
            if isinstance(noticias, dict):
                noticias = [noticias]

            for noticia in noticias:
                titulo_noticia = normalize_text(noticia.get('titulo') or noticia.get('title') or '')
                if not titulo_noticia:
                    continue
                Noticia.objects.update_or_create(
                    proposicao=proposicao,
                    titulo=titulo_noticia,
                    defaults={
                        'resumo': normalize_text(noticia.get('resumo') or noticia.get('description') or ''),
                        'url': normalize_text(noticia.get('link') or noticia.get('url') or ''),
                        'publicado_em': None,
                    },
                )
