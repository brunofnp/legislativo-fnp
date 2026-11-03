# Monitoramento interno por área — design

Data: 2026-11-03

## Contexto

O monitoramento legislativo tem três escopos (desenho original da coordenação):
público (painel aberto), **individual** (seguir/alerta — já no ar) e **interno por
área** (este documento). O interno nunca tinha sido construído; é o maior bloco
porque exige estruturar áreas e papéis, que não existiam no sistema (só havia
`Perfil.setor_responsavel` em texto livre e `is_staff`).

## Decisões (confirmadas com o usuário)

1. **Área:** cada pessoa escolhe a sua no `/perfil/`. Coordenador/gerente são
   marcados pela coordenação no Django Admin (papel não é autoeditável).
2. **Visibilidade:** todo o time da FNP (Legislativo) vê o interno de **todas** as
   áreas. Não aparece no painel público (usuários externos — prefeitos, indicados,
   parlamentares — não acessam).
3. **Entrada:** qualquer pessoa da área adiciona/remove proposições do
   monitoramento **da própria área**, sem aprovação. (Virar público é que passa
   pela Ingrid — fora do escopo deste bloco.)

## Modelo de dados

- `usuarios.AreaFNP`: `nome`, `slug`, `ordem`, `ativo`. Semeado com as 9 áreas de
  nível coordenação/gerência do organograma (28/07/2026); admin pode refinar.
- `usuarios.Perfil.area` (FK → AreaFNP, SET_NULL) e `Perfil.papel_area`
  (colaborador/coordenador/gerente, default colaborador).
- `proposicoes.MonitoramentoInterno`: `area`, `proposicao`, `adicionado_por`,
  `criado_em`. Único por (área, proposição). Só proposições publicadas entram.

## Regras

- **Ver o monitoramento interno:** `eh_equipe_fnp(user)` = Equipe FNP ou aprovador
  (is_staff). Exclui o público externo.
- **Adicionar/remover de uma área:** membro daquela área (a própria área do
  perfil). Uma pessoa pertence a uma área; edita só a dela, vê todas.
- **Papel (coordenador/gerente):** armazenado e exibido; sem efeito funcional
  neste bloco (reservado para fluxos futuros de aprovação/gestão por área).
- Curar/monitorar **não** dispara alerta aos seguidores (fora de `CAMPOS_ALERTA`).

## UI

- `/perfil/`: seletor de **Área da FNP** (só para equipe) + papel read-only.
- Menu lateral: **Monitoramento interno** (só equipe).
- Página da proposição: botão **monitorar na área** (ícone de olho), para equipe
  com área definida — espelha os botões favoritar/seguir.
- `/monitoramento-interno/`: uma seção por área (ordem do organograma), com os
  cards; a própria área vem marcada ("Minha área") e com botão de remover por
  card. Adicionar é pela página da proposição.

## Fora de escopo (futuro)

- Papéis com efeito funcional (coordenador/gerente aprovando inclusão pública).
- Fluxo de "pedir para virar público" (área → Ingrid → Adam/Ricardo).
- Monitoramento interno de proposições ainda não publicadas.

## Testes

Cobertura: toggle adiciona/remove na própria área; edita só a própria área; sem
área não cria; exige equipe (público → 403); só proposição publicada; página
visível à equipe e mostra todas as áreas; bloqueada ao público; perfil salva a
área.
