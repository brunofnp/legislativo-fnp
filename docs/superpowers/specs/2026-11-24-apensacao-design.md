# B — Apensação ("Apensada à …") — 2026-11-24

## Problema
Proposições que tramitam **apensadas** apareciam no painel como autônomas
(ex.: PEC 27/2023, apensada à PEC 231/2019).

## Investigação da fonte
A apensação **não** está num campo estruturado confiável: `statusProposicao.
uriPropPrincipal` veio nulo para a PEC 27/2023. O sinal fica no **despacho das
tramitações** da Câmara ("Apense-se … à PEC-231/2019" / "Desapense-se …"), que
ainda **alterna** no tempo (a PEC 27/2023 foi desapensada e reapensada em
5/11/2025). Logo, detecção exige ler o último despacho de apense/desapense.

## Decisão
1. Campo `Proposicao.apensada_a` (CharField), **editável no admin** — a
   coordenação sempre pode definir/corrigir a principal.
2. `fontes.apensacao_de_tramitacoes` (puro, testável) + `buscar_apensacao_
   camara`: olham o ÚLTIMO despacho de apense/desapense.
   - **Direção importa**: "Apense-se [a X] à/ao Y" → a principal é a ÚLTIMA
     referência (Y); X (ou o título implícito) é a apensada. Se o próprio
     título for a principal (Y), retorna `None` (não está apensada) — o mesmo
     despacho aparece na ficha das duas.
   - Retorno: `'X'` (principal), `''` (desapensada), `None` (indeterminado).
3. `atualizar_apensacao` (comando, só Câmara): grava **só em detecção
   positiva**. `None` não toca no campo — preserva a curadoria, nunca
   sobrescreve com palpite. `apensada_a` fora de CAMPOS_ALERTA (gravação
   silenciosa).

## Exibição
Card: selo "APENSADA" + linha "Tramita apensada à **X**". Detalhe: bloco
"Apensação" ("Apensada à X" / "Tramita de forma autônoma").

## Limitações
Só Câmara (o despacho vem da ficha da Câmara). Formas raras de despacho (três+
proposições na mesma frase) podem não ser cobertas — por isso o campo é
curável no admin, e o automático nunca apaga uma curadoria por indecisão.

## Verificação
`ApensacaoParserTest` (forma curta/longa, desapense, último evento, sem
despacho, self=principal, PL vs PLP) e `AtualizarApensacaoTest` (grava, não
toca indeterminado, limpa desapense, dry-run, pula Senado). Smoke real 24/11:
PEC 27/2023 → "PEC 231/2019"; PEC 231/2019 → None. 251 testes OK.

## Nota de integração
Empilhado sobre A3 (migração 0012). Merge em ordem: #18 → #19 → #20 → #21.
