# "Na pauta" v2 — cobertura do Senado (2026-11-18)

## Problema
A v1 do `atualizar_pauta` só derivava a pauta da **Câmara** (agenda de eventos).
Matérias do **Senado** na Ordem do Dia ficavam invisíveis ao filtro
`?filtro=pauta`. Caso concreto: **PLP 299/2026** (ajuste fiscal — altera a LC
200/2023), oficialmente "INCLUÍDA EM ORDEM DO DIA" no Plenário do Senado, mas o
painel mostrava "Pauta: Não". O sinal já estava no próprio `status_tramitacao`,
mas `is_on_pauta` só olhava o campo manual.

## Decisão
Estender a derivação para as duas Casas, cada uma pelo melhor sinal oficial:
- **Câmara**: mantém `fontes.pauta_camara` (agenda de eventos deliberativos).
- **Senado**: novo `fontes.buscar_status_senado(cod)` lê a situação atual por
  `codigoMateria` (do link `/materia/NNNN`) e marca `na_pauta=True` quando a
  situação contém **"ordem do dia"**.

Critério **estrito**: "ordem do dia" presente **e** "aguardando" ausente —
conta só quem FOI incluída na Ordem do Dia (ex.: "INCLUÍDA EM ORDEM DO DIA").
Não contam: "pronta para pauta/deliberação" (pronta, mas não pautada) e
"AGUARDANDO INCLUSÃO ORDEM DO DIA…" (esperando ser pautada). Sem a exclusão de
"aguardando", a substring "ordem do dia" dava falso positivo (casos reais
18/11/2026: PL 4146/2020 e PL 5473/2025). O card passou a exibir **"NA ORDEM DO
DIA"** no lugar de "PAUTA", deixando o critério explícito.

## Segurança
- Agenda da Câmara indisponível (`pauta_camara` → None): as proposições da
  Câmara ficam intocadas (não esvazia a pauta); o Senado ainda é processado.
- Leitura do Senado falha para uma matéria (`buscar_status_senado` → None):
  aquela matéria fica intocada.

## Fora de escopo
- Agenda do Senado por evento (hoje usamos a situação por matéria, que já
  resolve o caso). O endpoint `materia/situacaoatual` está em descontinuação;
  quando sair, migrar para `/processo/{idProcesso}`.

## Testes
`BuscarStatusSenadoTest` (ordem do dia → na pauta; pronta p/ deliberação → não)
e `AtualizarPautaTest` reescrito (Câmara mantida + Senado: marca/desmarca,
falha não altera, agenda da Câmara falha ainda processa Senado, alerta, quiet,
dry-run). Smoke test real 18/11/2026: PLP 299/2026 → na_pauta=True.
