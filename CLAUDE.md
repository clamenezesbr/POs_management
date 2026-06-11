# Projeto: Automação eplus.huawei.com — Partner Deal Registration

> **REGRA:** Atualizar este arquivo a cada alteração no código.

## Objetivo
Automatizar um processo manual feito várias vezes ao dia: dado o nome de um
parceiro, buscar suas POs (Deal Registrations), filtrar as **Approved**, abrir
cada uma, ler a página de detalhe e gerar um resumo com os dados do projeto e,
principalmente, o **contato do owner do parceiro**.

## Stack e decisões de arquitetura
- **Playwright (sync API)** em Python. Escolhido sobre Selenium por lidar melhor
  com sites pesados de AJAX e ter auto-wait nativo.
- **Login NÃO é automatizado.** O usuário abre o Chrome em modo debug, conecta a
  VPN e faz o SSO manualmente. O script se PLUGA nessa sessão já logada via
  `connect_over_cdp` em `http://localhost:9222`.
  - Usar `launch_chrome.bat` (já criado) para abrir o Chrome com os flags certos.
  - O browser NUNCA é fechado pelo script (é a janela logada do usuário).
- Site é lento → timeout padrão de 30s.
- Dependências: `pip install playwright` + `playwright install chromium` (já feito).

## Arquivos do projeto
| Arquivo | Descrição |
|---|---|
| `main.py` | Script principal — blocos 0 a 6 |
| `launch_chrome.bat` | Abre o Chrome com `--remote-debugging-port=9222` |
| `rodar.bat` | Executa `python main.py` com mensagem de pré-requisitos |
| `requirements.txt` | `playwright>=1.60.0` |

## Fluxo (6 blocos) — estado atual
| Bloco | Descrição | Status |
|---|---|---|
| 0 | Conectar à sessão CDP | ✅ Implementado |
| 1 | Buscar parceiro (Advanced Search → Partner Company → Query) | ✅ Implementado |
| 2 | Ler contadores de status + filtrar Approved | ✅ Implementado |
| 3 | Contar POs aprovadas (grid virtual Vue) | ✅ Implementado |
| 4 | Abrir e ler cada PO por índice | ✅ Implementado |
| 4b | Extrair campos da tela DR Details (`extrair_dados_po`) | ✅ Implementado |
| 5 | IA: resumo + contato do owner | 🔲 Placeholder |
| 6 | Saída: PDF / dashboard | 🔲 Console por enquanto |

## Descobertas CRÍTICAS sobre o site (de inspeção real do DOM)
O site usa framework **AUI / Element-UI (Vue)**. Implicações:
- **Classes são genéricas** (`aui-input__inner`, `aui-button--default` se repetem)
  → NÃO servem como seletor sozinhas.
- **Botões**: localizar por TEXTO. Playwright `get_by_role("button", name="...")`.
  - "Advanced Search", "Query" (é o `aui-button--primary`, único), "Reset".
- **Campos NÃO têm label ligado por for/id** → ancorar pelo TEXTO do rótulo e
  descer ao input vizinho (helper `_campo_por_rotulo` usa XPath).
- **DR Status** é dropdown CUSTOM (não `<select>` nativo): clicar no input
  readonly abre `.aui-select-dropdown__list`, depois clicar no item "Approved".
- **Tabela = GRID VIRTUAL do Vue** (`role="grid"`, não `<table>`). Linhas de
  dados = `[role="row"]` que contêm `[role="gridcell"]`.
- **Links das POs NÃO são `<a href>`** — são spans com click do Vue Router.
  → NÃO dá para coletar URLs. Abrir por ÍNDICE de linha e RECAPTURAR a tabela a
    cada volta (elementos antigos ficam "stale").
- Clicar no card "Approved" do topo filtra a tabela.

## Tela DR Details — estrutura do DOM (inspecionada)
Container raiz: `#aui-collapse-content-54912283` (tabpanel "Basic Information").

Padrão flat/linear: filhos diretos alternando rótulo → valor.
Extração via JS com `nextElementSibling` por texto do rótulo — robusto a
mudanças de ordem. Project Background é multi-nó (vários `<div>` irmãos após
o rótulo — capturar todos com `slice(bgLabelIdx + 1)`).

Campos mapeados: Project Name, DR No, Submitted Partner, Submitted by,
Submited Date (typo do sistema, um "t"), Approval Date, Estimated Order Date,
Estimated Amount, Approver, Expired Date, Public Tender, Project Background.

## ⚠️ Risco conhecido: ID dinâmico do container
`#aui-collapse-content-54912283` — o número `54912283` pode ser gerado
dinamicamente pelo Vue e **mudar entre sessões ou deploys do site**.

**Sintoma se quebrar:** `extrair_dados_po()` retorna todos os campos `None`.

**Como corrigir:** trocar o seletor por algo estável, ex:
```python
# Opção A: prefixo do id
page.locator('[id^="aui-collapse-content-"]').first

# Opção B: pelo tab ativo "Basic Information"
page.locator('[role="tabpanel"][aria-hidden="false"]')
```
Testar no site real e ajustar conforme necessário.

## Extração de contato do owner (Project Background)
O campo `project_background` é texto livre. Helpers de regex em `main.py`:
- `_extrair_email()` — regex padrão de email
- `_extrair_telefone()` — formatos BR; descarta CNPJ (14 dígitos)
- `_extrair_nome_owner()` — busca "Gerente|Contato|Responsável|Owner: <nome>"
  só aceita se tiver espaço no valor (filtra usernames de email)

Exemplo real observado:
```
"Gerente de Negócios (Cel/E-mail): jonatasmsouza@nereidas.com.br"
→ owner_email: "jonatasmsouza@nereidas.com.br"
→ owner_nome:  None  (sem nome explícito na linha)
```

## TODOs restantes
1. **Testar no site real** — validar blocos 1-4b com um parceiro real.
2. **Confirmar ID do container** `#aui-collapse-content-54912283` é estável;
   se não for, aplicar a correção acima.
3. **Confirmar `voltar_para_lista()`** — botão "DR List" vs `go_back()`.
4. **Bloco 5 (IA)** — integrar LLM para resumo + extração de contato do Background.
5. **Bloco 6 (saída)** — gerar PDF com os dados.

## Preferências do usuário (Gabriel)
- Respostas objetivas e diretas.
- Estrutura modular, código comentado quando pedir.
- Atualizar CLAUDE.md a cada alteração no código.
