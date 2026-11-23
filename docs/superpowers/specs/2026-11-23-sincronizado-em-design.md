# A1 — "Fonte conferida em DD/MM" (sincronizado_em) — 2026-11-23

## Problema
O painel não mostrava quando o dado foi conferido na fonte oficial. O usuário
não tinha como saber se "Aguardando parecer" é de hoje ou de 2021 — faltava
transparência sobre a atualidade do histórico. O campo `atualizado_em`
(auto_now) não serve: muda a cada save, inclusive edição editorial.

## Decisão
Campo dedicado `Proposicao.sincronizado_em` (DateTimeField, nulo), tocado
**apenas** quando um comando consulta a fonte oficial:
- `atualizar_tramitacao` (ficha da Câmara) — grava a data a cada consulta
  bem-sucedida, **mesmo quando a movimentação não mudou** (é justamente o que
  dá a garantia de "foi conferido hoje").
- `atualizar_pauta` (agenda da Câmara / situação do Senado) — idem, grava a
  data em toda proposição cuja fonte foi lida com sucesso.

`sincronizado_em` não está em `CAMPOS_ALERTA`, então tocá-lo nunca dispara
alerta. No caso "consultou mas nada mudou", usa-se `.update()` (sem save → sem
signal). Falha de leitura da fonte **não** grava a data (nulo = não conferido).

## Exibição
- Card: rodapé discreto "Fonte conferida em DD/MM/AAAA" (ou "Conferência
  automática pendente" quando nulo).
- Detalhe: bloco "Última consulta à fonte oficial" com data e hora.

## Fora de escopo
Recalcular status/aprovada na mesma passada (isso é o A2). Aqui só a data da
consulta.

## Testes
`AtualizarTramitacaoTest`: grava ao consultar, grava mesmo sem mudança, não
grava sem dados. `AtualizarPautaTest`: grava mesmo sem mudar a pauta, dry-run
não grava. Suíte cheia: 226 testes OK.
