# Projeto: Automação eplus.huawei.com — Partner Deal Registration

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
  - Comando para abrir o Chrome (Windows):
    `chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\eplus_profile"`
  - O browser NUNCA é fechado pelo script (é a janela logada do usuário).
- Site é lento → timeout padrão de 30s.

## Fluxo (6 blocos)
0. Conectar à sessão já logada (CDP)
1. Buscar parceiro (Advanced Search → Partner Company → Query)
2. Ler contadores de status + filtrar Approved
3. Contar/coletar as POs aprovadas
4. Abrir e ler cada PO (uma por vez, mesma aba)
5. IA: resumo + contato do owner — **PLACEHOLDER, fase futura**
6. Saída: PDF primeiro, dashboard como evolução

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

## Estado atual
- `eplus_automation.py` tem os **blocos 1 a 4 preenchidos** e compilando.
- A **extração da tela de detalhe (Parte 2)** ainda é TODO — depende dos
  seletores do "DR Details" (a inspecionar com o agente de navegador).
- Bloco 5 (IA) e bloco 6 (saída) são placeholders.

## Campos a extrair na tela DR Details (Parte 2)
Project Name, DR No, Submitted Partner, Submitted by, Submitted Date,
Approval Date, Estimated Order Date, Estimated Amount, Approver, Expired Date,
Public Tender, e **Project Background** (texto livre com CNPJ, contato do owner,
escopo, concorrente, orçamento — é daqui que a IA vai extrair o contato).
Suspeita: os campos são pares rótulo+valor com padrão consistente → extrair
todos de uma vez pelo padrão, em vez de um seletor por campo.

## TODOs imediatos
1. Testar a Parte 1 no site real (buscar, filtrar, contar).
2. Confirmar `voltar_para_lista()`: botão "DR List" vs `go_back()`.
3. Trocar o `wait_for_load_state` pós-abertura por esperar um seletor real do
   DR Details.
4. Rodar prompt da Parte 2 no agente de navegador para obter os seletores do
   detalhe e preencher `extrair_dados_po()`.

## Preferências do usuário (Gabriel)
- Respostas objetivas e diretas.
- Estrutura modular, código comentado quando pedir.