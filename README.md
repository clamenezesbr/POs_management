# POs_management

Automação em Python para consultar **Deal Registrations** no portal `eplus.huawei.com`, filtrar registros com status **Approved**, abrir cada detalhe e extrair informações relevantes do projeto e do contato do owner do parceiro [1][2].

O fluxo foi pensado para uso interno com **Chrome em modo debug + VPN + SSO manual**, enquanto o script usa Playwright para se conectar à sessão já autenticada, sem automatizar login [2][3][4].

## Visão geral

O projeto busca reduzir um processo manual repetitivo: informar o nome de um parceiro, localizar seus registros no portal Huawei, filtrar os aprovados e consolidar os dados mais importantes diretamente no console [2][5].

Hoje, o script já cobre a conexão à sessão aberta no Chrome, a busca avançada por parceiro, a leitura dos contadores de status, o filtro em **Approved**, a navegação pelos itens da grade e a extração dos dados da tela de detalhes [2][5].

## Como funciona

1. Execute `launch_chrome.bat` para abrir o Google Chrome com `--remote-debugging-port=9222` e um perfil dedicado [3].
2. Conecte a VPN e faça o SSO manualmente na janela aberta do Chrome [2][3].
3. Execute `rodar.bat` ou `python main.py` [2][4].
4. Informe o nome do parceiro quando o script solicitar [2].
5. O script acessa a lista de deal registrations, aplica a busca, filtra `Approved`, abre cada PO encontrada e extrai os campos disponíveis da tela de detalhes [2][5].

## Estrutura do projeto

| Arquivo | Função |
|---|---|
| `main.py` | Script principal com conexão ao navegador, busca, filtragem, leitura da grid e extração dos detalhes [2]. |
| `launch_chrome.bat` | Abre o Chrome com porta de debug `9222` e perfil local dedicado [3]. |
| `rodar.bat` | Executa o fluxo principal com checagem visual dos pré-requisitos [4]. |
| `requirements.txt` | Dependência mínima do projeto: `playwright>=1.60.0` [2]. |
| `CLAUDE.md` | Documento de contexto técnico com decisões, riscos conhecidos e TODOs do projeto [5]. |

## Campos extraídos

Na tela **DR Details**, o script tenta capturar estes dados do registro [2][5]:

- `Project Name`
- `DR. No.`
- `Submitted Partner`
- `Submitted by`
- `Submited Date`
- `Approval Date`
- `Estimated Order Date`
- `Estimated Amount`
- `Approver`
- `Expired Date`
- `Public Tender`
- `Project Background`

Além disso, o texto de `Project Background` é processado com regex para tentar identificar [2][5]:

- Nome do owner
- E-mail do owner
- Telefone do owner

## Requisitos

Antes de rodar, o ambiente precisa ter [2][3][4]:

- Python instalado
- Google Chrome instalado no caminho padrão do Windows
- Acesso à VPN necessária para o portal
- SSO manual válido no portal `eplus.huawei.com`
- Playwright instalado
- Chromium do Playwright instalado

Instalação:

```bash
pip install -r requirements.txt
playwright install chromium
```

## Execução

Forma recomendada no Windows:

```bat
launch_chrome.bat
rodar.bat
```

Ou manualmente:

```bash
python main.py
```

Quando solicitado, informe o nome do parceiro exatamente como deseja pesquisar no campo **Partner Company** [2].

## Saída atual

A saída atual é impressa no console e inclui, para cada PO aprovada processada, dados cadastrais do registro, valor estimado, datas relevantes, aprovador, informações de contato detectadas e o conteúdo do **Project Background** [2].

O campo de resumo por IA já existe como ponto de extensão, mas hoje ainda retorna apenas um placeholder e não há geração de PDF ou dashboard final implementados [2][5].

## Limitações

- O login não é automatizado; depende de VPN e SSO manual feitos antes da execução [2][3][4].
- O script depende de o Chrome estar acessível em `http://localhost:9222` [2].
- A navegação usa uma grid virtual em Vue/AUI, então os elementos da tabela precisam ser recapturados a cada volta da tela de detalhes [5].
- Há um risco conhecido de o container de detalhes usar ID dinâmico, o que pode quebrar a extração se o portal mudar o DOM [5].
- A saída ainda não salva resultados em arquivo [5].

## Stack

- Python [1]
- Playwright Sync API [2][5]
- Google Chrome com Remote Debugging [2][3]
- Scripts `.bat` para operação no Windows [3][4]

## Próximos passos

Os próximos itens já mapeados no projeto são testar o fluxo com parceiros reais, validar o seletor do container de detalhes, revisar o retorno para a lista, integrar IA para resumo/extração complementar e gerar uma saída mais útil como PDF ou dashboard [5].
