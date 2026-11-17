# "Na pauta" a partir da agenda oficial + fix do Senado — design (2026-11-16)

## Problema
`?filtro=pauta` filtra o booleano `pauta`, que só era setado no ingest por
`is_on_pauta` (= `Pauta == "Sim"` na planilha). Era 100% manual e congelado: o
atualizador de tramitação refresca a última movimentação mas não mexe no
`pauta`. Resultado: o filtro não reflete a Ordem do Dia real.

Em paralelo, `fontes.buscar_senado` achava a matéria mas não extraía o texto da
situação (procurava `descricaoSituacao`; o `/processo` traz `situacaoAtual`),
devolvendo sempre "Em tramitação".

## Decisão
1. **`fontes.pauta_camara(dias=7)`** lê a agenda oficial da Câmara (`/eventos`
   das sessões DELIBERATIVAS de hoje até `dias`, + `/eventos/{id}/pauta`) e
   devolve o conjunto de `idProposicao` na pauta. Devolve `None` em falha de
   rede (sinal de "não altere nada").
2. **Comando `atualizar_pauta`** torna o `pauta` das proposições da **Câmara**
   autoritativo a partir desse conjunto: marca quem entrou, desmarca quem saiu,
   e dispara o alerta aos seguidores (pauta está em `CAMPOS_ALERTA`). `--quiet`
   (baseline silencioso), `--dry-run`, `--dias N`.
3. **Fix `buscar_senado`**: ler `situacaoAtual` do `/processo`.

## Segurança
Se `pauta_camara` devolver `None` (falha), o comando aborta sem alterar nada —
uma falha de API não pode esvaziar a pauta do painel. Teste cobre isso.

## Escopo / fora de escopo
- Câmara: Plenário **e** comissões deliberativas (evita desmarcar item que está
  só em pauta de comissão).
- Senado e proposições sem `idProposicao` no link: **não tocadas** (pauta
  manual até a v2, quando a agenda do Senado entrar — API em migração).
- Baseline silencioso no primeiro disparo; depois cron diário em modo normal
  (aí sim alerta "entrou na pauta").

## Testes
`AtualizarPautaTest` (7 casos, `pauta_camara` mockada): marca, desmarca,
Senado intacto, **falha→não altera nada**, alerta ao entrar, `--quiet` não
alerta, `--dry-run` não grava. `BuscarSenadoTest`: extrai `situacaoAtual`.
Smoke test real em 16/11/2026: situação do Senado e `pauta_camara` ao vivo.
