# ADR 0003 — Segurança: auditorias, hardening e postura atual

- **Status:** Implementado, revisado múltiplas vezes; pendências reais em
  aberto (ver seção final).
- **Contexto temporal:** primeira rodada crítica em 2026-08-06 (junto do
  upgrade Django 4.2→5.2), pentest completo de 48 itens em 2026-08-11
  (relatório → correção → revarredura no mesmo dia), ajustes pontuais
  desde então.

Este documento consolida **todo o trabalho de segurança** feito no
projeto: por que a plataforma foi tratada como alvo plausível de ataque, o
que foi auditado, o que foi corrigido, o que foi uma decisão consciente
(não um bug) e o que ainda está pendente. `CLAUDE.md` tem uma seção
permanente "Postura de segurança" com o resumo do estado atual — este ADR
é o registro completo, com o raciocínio por trás de cada item.

---

## Contexto

O Painel Legislativo FNP é um fórum de discussão política pública, com
cadastro aberto, comentários visíveis a qualquer visitante e dados de
estratégia institucional da FNP (mérito de proposições). Isso o torna um
**alvo plausível** de spam, cadastro fraudulento, scraping abusivo e
tentativa de acesso não autorizado ao Admin — não um sistema interno de
baixo risco. As auditorias partiram dessa premissa, com o usuário
explicitamente pedindo avaliação "como pentester sênior" na rodada mais
completa (2026-08-11).

**Limitação de escopo constante**: o Claude Code nunca teve acesso SSH ao
droplet nem ao painel da DigitalOcean — toda auditoria de infraestrutura
(firewall, SSH, banco) foi feita por *leitura de código* primeiro,
marcada explicitamente como "não verificável daqui", e só confirmada
depois via comandos conduzidos pelo usuário por SSH.

---

## Cronologia das auditorias

### 2026-08-06 — Primeira rodada, junto do upgrade Django

**Crítico:**

- **Django 4.2 sem patch de segurança desde 2026-04-07** (confirmado na
  fonte oficial) — upgrade em 3 etapas até 5.2 LTS (suporte até
  abril/2028), exigindo também upgrade do `django-allauth` (0.60→65.19,
  única versão compatível) e renomeação de várias settings do allauth.
- **`DEBUG`/`SECRET_KEY` com fallback inseguro** — `DEBUG` tinha default
  `'True'` (deveria falhar fechado); `SECRET_KEY` caía pra uma string
  conhecida de tutorial se a env var sumisse. Agora `DEBUG` default é
  `False`, e produção sem `SECRET_KEY` derruba o boot em vez de rodar
  insegura.

**Alto/Médio, todos fechados na mesma sessão:**

- Rate limit de login por IP explícito (`ACCOUNT_RATE_LIMITS`).
- 2FA obrigatório pra staff implementado (`MFAObrigatorioStaffMiddleware`)
  — **depois desativado a pedido do usuário no mesmo dia** (ver "Decisões
  conscientes" abaixo); continua disponível como opcional.
- `SECURE_REFERRER_POLICY`, `CSRF_TRUSTED_ORIGINS` explícitos.
- Limite de upload de foto de perfil (5MB), validado nos dois lados
  (`Perfil.foto` + Nginx).
- `ACCOUNT_EMAIL_VERIFICATION`: `'none'` → `'optional'`.
- Content-Security-Policy (`django-csp`) com `script-src` estrito (nonce
  automático).
- Lockfile com hash (`requirements.lock`) + `pip-audit` no CI a cada
  push/PR.
- CAPTCHA no cadastro (`django-recaptcha`, desligado até as chaves serem
  preenchidas).
- **Achado extra do `pip-audit`**: Pillow 10.4.0 tinha 24 vulnerabilidades
  conhecidas — atualizado pra série 12.x.

Também integrado nesta sessão: monitoramento de erro via Sentry (desligado
por padrão até `SENTRY_DSN` ser preenchido — ativado de fato só em
2026-08-11) e confirmação de que o backup do `fnp-database` estava ativo
(7 dias de retenção, point-in-time recovery).

### 2026-08-07 — CSP sem `'unsafe-inline'`

`style-src` do CSP removeu `'unsafe-inline'` depois de eliminar os 6
últimos usos de `style="..."` inline no projeto (4 redundantes removidos,
2 chips de cor dinâmica migrados pra `element.style.setProperty()` via
JS, que o CSP não restringe).

### 2026-08-11 — Pentest completo de 48 itens

A pedido explícito do usuário ("aja como pentester sênior... varredura de
segurança completa"), processo em 3 fases: relatório primeiro (48 itens,
categorias A-L, por leitura de código), aprovação do usuário, depois
correção — nunca corrigir antes de reportar.

**Achado crítico rebaixado depois de investigar a fundo** (não descartado
sem checar): `SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT` parecia à
primeira vista permitir "roubo de conta" via cadastro com e-mail de
terceiro — investigando o código-fonte do próprio `allauth`
(`wipe_password`), confirmado que a biblioteca já mitiga esse cenário
exato (apaga a senha do cadastro fraudulento se o e-mail não estava
verificado). Risco residual real, menor: a janela entre aprovação de um
cadastro suspeito e a vítima logar via Google. Fix: coluna "E-mail
confirmado" no `UsuarioAdmin`, visível onde Root já aprova cadastros —
dá o sinal sem exigir `ACCOUNT_EMAIL_VERIFICATION='mandatory'` (que
travaria cadastro sem `EMAIL_BACKEND` real, ver Pendências).

**Riscos corrigidos:**

- Comentário podia ser encaixado como resposta em *outra* proposição via
  POST manual (`ComentarioForm` não restringia o queryset de `parent` à
  proposição atual) — achado só por leitura de código.
- Aprovação/rejeição em massa de cadastro/exclusão não gerava
  `LogEntry` (só `.update()`, nunca passa pelo log automático do Admin)
  — sem rastro de quem aprovou o quê. Fix: `LogEntry` explícito.
- Senha mínima só o default do Django (8 caracteres) — `min_length=10`
  explícito, sem exigir símbolo/maiúscula (orientação atual do
  NIST/OWASP: comprimento > regras de complexidade).
- Sessão sem expiração explícita (caía no default de 2 semanas) —
  `SESSION_COOKIE_AGE` de 7 dias, explícito.
- Denúncia de comentário sem rate limit — adicionado, mesmo padrão de
  comentário/participação.
- **Rate limit dos formulários públicos praticamente sem componente de
  IP de verdade** — `REMOTE_ADDR` sempre era o IP do próprio Nginx (o
  Gunicorn só é alcançado via proxy reverso), sem nada traduzindo
  `X-Forwarded-For`. Fix: lê o **último** valor da lista (o que o Nginx
  de fato anexou, não um valor forjável pelo cliente).

Depois da correção: **revarredura completa dos 48 itens de novo**, item a
item contra o código real (não só memória da sessão) — 41 ✅, 1 decisão
consciente já tomada, 6 com nuance (2 pendências antigas confirmadas sem
mudança, 1 achado novo não corrigido por depender de decisão do usuário,
1 item de infraestrutura ainda não conferido no painel, 1 corrigido —
novo model `TentativaLogin`, log de auditoria de login somente-leitura no
Admin — 1 pendência antiga confirmada).

Na sequência, mesma sessão: **Cloud Firewall da DigitalOcean confirmado**
(camada separada do `ufw` local, mesma política — só 22/80/443), e
**Sentry ativado de fato** — e usado imediatamente pra achar um bug real
rodando em produção (`DisallowedHost` no healthcheck do Docker, corrigido
no mesmo dia).

**Checklist de infraestrutura por SSH** (itens que a Fase 1 tinha marcado
"não verificável daqui"): `PasswordAuthentication no` confirmado (login
só por chave — reduz bastante a gravidade de `PermitRootLogin yes` ainda
ligado, baixa prioridade), `fail2ban` ativo (349 banimentos históricos),
`ufw` só libera 22/80/443, Trusted Sources do `fnp-database` confirmado
restrito (só o droplet + 1 IP fixo, nunca "Allow all"), volume `media/`
corrigido de `root:root` pra `1000:1000` (mesmo risco do incidente
original de `staticfiles/`).

---

## Decisões conscientes (não são achados de segurança)

- **2FA deixou de ser obrigatório pra staff** — foi implementado e
  ativado em 2026-08-06, **desativado no mesmo dia a pedido do
  usuário**. Continua disponível como opcional em `/contas/2fa/`; a
  classe `MFAObrigatorioStaffMiddleware` segue em
  `apps/usuarios/middleware.py`, é só reativar a linha comentada em
  `MIDDLEWARE` se a decisão for revista.
- **Cluster Postgres compartilhado entre todos os sistemas da FNP** —
  parecia um achado (role `legislativo` consegue `CONNECT` em outros
  bancos do cluster), mas o usuário confirmou que é **arquitetura
  intencional**: os sistemas da FNP devem conversar entre si. Não é mais
  pendência.
- **Admin em `/admin/` sem allowlist de IP** — informacional, aceito
  dado o resto das defesas (2FA opcional, aprovação de cadastro, rate
  limit).
- **Client Secret do Google exposto numa captura de tela antiga** — em
  uma sessão o usuário decidiu inicialmente aceitar o risco (app ainda
  em modo "teste" no Google Cloud Console); **depois voltou atrás na
  mesma sessão** e pediu a rotação de verdade — feita e validada (login
  Google confirmado funcionando em produção com o secret novo). Falta só
  desativar o secret antigo no Google Cloud Console (ver Pendências).

---

## Incidentes de exposição de credencial e resposta

Duas vezes nesta sessão de segurança, uma credencial apareceu em texto
puro numa captura de tela ou terminal colado no chat — ambas tratadas
como incidente real, não ignoradas:

1. Senha do `doadmin` do `fnp-database` exposta por captura de tela numa
   sessão anterior → rotacionada e validada.
2. A **mesma** senha do `doadmin`, já rotacionada, apareceu de novo em
   texto puro num terminal colado no chat **desta** sessão → rotacionada
   **de novo**, desta vez sem colar a senha nova no chat.
3. Print do `.env` de produção no `nano` expôs `SECRET_KEY`, a senha da
   role `legislativo` (dentro do `DATABASE_URL`) e o `GOOGLE_CLIENT_SECRET`
   — usuário optou por terminar o Sentry primeiro; **rotação desses três
   ainda pendente** (ver Pendências).

**Lição registrada e válida daqui pra frente**: o cluster é compartilhado
com outros sistemas da FNP, então qualquer credencial exposta em
sessão de terminal/chat — de qualquer role, não só `doadmin` — merece
rotação. Cuidado ao colar comandos com senha visível.

---

## Postura atual — resumo rápido

| Área | Estado |
|---|---|
| Framework | Django 5.2 LTS (suporte até abril/2028), `django-allauth` 65.x |
| `DEBUG`/`SECRET_KEY` | Fail-closed — produção sem `SECRET_KEY` não sobe |
| HTTPS/HSTS | `SECURE_SSL_REDIRECT`, HSTS 1 ano + subdomínios + preload, cookies `Secure` (só com `DEBUG=False`) |
| CSP | Ativo, `script-src` com nonce, sem `'unsafe-inline'` em nenhuma diretiva |
| Rate limit | Formulários públicos (comentário/participação/denúncia) + login (allauth nativo), IP real via `X-Forwarded-For` |
| Senha | Mínimo 10 caracteres, sem regra de complexidade adicional |
| Sessão | Expira em 7 dias (`SESSION_COOKIE_AGE`) |
| 2FA | Disponível, **opcional** (não obrigatório pra staff, decisão consciente) |
| Dependências | `requirements.lock` com hash, `pip-audit` no CI |
| Monitoramento | Sentry ativo em produção |
| Log de auditoria | `TentativaLogin` (login) + `LogEntry` explícito em aprovação/rejeição de cadastro/exclusão |
| Infraestrutura | Cloud Firewall + `ufw` (só 22/80/443), SSH key-only, `fail2ban` ativo, Trusted Sources do banco restrito |
| CI | `pip-audit` a cada push/PR |

---

## Pendências de segurança em aberto

Ver também a seção "Pendências e próximos passos" em `CLAUDE.md` para o
estado mais atualizado — lista aqui é a fotografia de quando este ADR foi
escrito:

- **Rotacionar `SECRET_KEY`, senha da role `legislativo` e
  `GOOGLE_CLIENT_SECRET`** — os três apareceram em texto puro num print
  do `.env` de produção; ainda não rotacionados.
- **Desativar/excluir o Client Secret antigo do Google OAuth** (criado
  2026-08-04) no Google Cloud Console — o novo já está validado em
  produção, mas o antigo continua uma credencial ativa em paralelo.
- **Decidir se `acoes_incidencia`/`riscos_oportunidades` deveriam exigir
  login** — hoje aparecem pra qualquer visitante anônimo em
  `proposicao_detail.html` (`posicionamento_fnp` continua fazendo
  sentido público). Achado da revarredura, decisão do usuário antes de
  qualquer mudança de código.
- **`EMAIL_BACKEND` de produção sem provedor real configurado** —
  bloqueia o caminho mais robusto pro achado da fusão de conta
  (`ACCOUNT_EMAIL_VERIFICATION='mandatory'`) e a entrega de fato dos
  e-mails que o app já dispara (confirmação de conta, aviso de cadastro
  pendente).
- **Atualizações de SO + Docker pendentes com reboot** — adiado de
  propósito (droplet compartilhado com outros sistemas da FNP), precisa
  de janela combinada.
- `PermitRootLogin yes` ainda ligado — baixa prioridade dado
  `PasswordAuthentication no` (só chave SSH).
- Droplet `fnp-web` sem backup próprio (só o `fnp-database` tem).
- `RECAPTCHA_PUBLIC_KEY`/`RECAPTCHA_PRIVATE_KEY` não preenchidas — CAPTCHA
  implementado mas desligado até a conta ser criada.
