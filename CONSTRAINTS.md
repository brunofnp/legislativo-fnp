# Constraints

Last reviewed: 2026-09-28 por brunofnp

Piso de qualidade do projeto. Agentes: leiam antes de escrever código e **não
enfraqueçam este arquivo para fazer uma mudança passar**. Apertar a régua pode
ser silencioso; afrouxar tem que ser pedido explícito e aparecer no commit.

## Piso (sempre vale, sem ferramenta extra)

- Não apagar, pular (`@skip`, `skipTest`, `expectedFailure`) nem esvaziar teste
  (tirar asserção) sem motivo escrito na mensagem de commit.
- Nenhuma supressão nova (`# noqa`, `# type: ignore`, `# nosec`) sem comentário
  explicando o porquê na mesma linha. Existentes e aceitas: `apps/usuarios/apps.py`
  (import de signals, F401) e `setup/settings.py` (import do CSP após config, E402).
- Nenhum stub não implementado (`raise NotImplementedError`, `except: pass`
  engolindo erro) entregue como pronto.
- Nenhum segredo no código ou no git — segredos só no `.env` do servidor.
- CSP continua sem `'unsafe-inline'` (ver ADR 0003).

## Aplicado com número

| Dimensão | Regra | Verificado por | Roda em |
|---|---|---|---|
| Testes | 100% da suíte passando | `pytest` | fim de tarefa, CI |
| Dependências | nenhuma vulnerabilidade conhecida | `pip-audit -r requirements.lock` | CI |

`pip-audit` é a opinião externa (base pública de vulnerabilidades); os testes
são da própria suíte.

## Medido, ainda não aplicado (trava: não pode piorar)

| Métrica | Hoje (2026-09-28) | Direção | Como medir |
|---|---|---|---|
| Testes | 134 passando | não pode cair sem motivo | `pytest -q` |
| Violações ruff | 448 (417 são E501) | não pode crescer | `ruff check . --statistics` |
| Cobertura | não medida | informativa — não virar meta | exigiria `pytest-cov`; só adicionar se pedido |

Por que cobertura é só informativa: projeto de 1 dev, diretriz de "testar
regra de negócio, não perseguir cobertura em código trivial" (`CLAUDE.md`).

## Acessibilidade — WCAG 2.1 AA (checklist, sem gate automático)

Não há ferramenta automática rodando (axe/Lighthouse exigem URL de preview,
que o projeto não tem). Enquanto isso, é checklist de revisão para toda
mudança de template/CSS/JS:

- skip links e `:focus-visible` funcionando em light e dark mode
- `prefers-reduced-motion` respeitado; nada que dependa só de hover
- ícones decorativos com `aria-hidden="true"`; campos com `<label>`
- contraste AA nos dois temas; alvo de toque confortável no mobile

## Exceções

| ID | Regra | Caminho | Motivo | Dono | Expira |
|---|---|---|---|---|---|
| — | — | — | — | — | — |
