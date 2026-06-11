"""
================================================================================
 AUTOMACAO eplus.huawei.com - Partner Deal Registration  (PARTE 1)
================================================================================
 Cobre os blocos 1 a 4: buscar parceiro, filtrar Approved, coletar e abrir
 cada PO. A extracao detalhada dos campos (Parte 2) e a IA (bloco 5) ficam
 como TODO ate validarmos os seletores da tela de detalhe.

 LOGIN: este script NAO faz login. Abra o Chrome em modo debug, conecte a VPN
 e faca o SSO manualmente; o Playwright se pluga nessa sessao.
   chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\\eplus_profile"

 DEPENDENCIAS:
   pip install playwright
   playwright install chromium

 ----------------------------------------------------------------------------
 NOTAS DE ARQUITETURA (a partir dos seletores reais inspecionados):
  - Botoes: localizados por TEXTO (nao ha classe unica confiavel).
  - Campos: NAO ha label ligado por for/id -> ancoramos pelo texto do rotulo
    e descemos para o input vizinho.
  - Tabela: e um GRID VIRTUAL do Vue (role="grid"), NAO uma <table>.
  - Links das POs: NAO sao <a href>. Sao spans com click do Vue Router.
    => Nao da para coletar URLs. Abrimos por INDICE de linha e, apos voltar,
       RECAPTURAMOS a tabela (os elementos antigos ficam "stale").
 ----------------------------------------------------------------------------
"""

from playwright.sync_api import sync_playwright, expect

BASE_URL = "https://eplus.huawei.com/web/eplus/#/dr?~l_registration_phurx4=%2Fdeal_registration_list"
CDP_ENDPOINT = "http://localhost:9222"
TIMEOUT = 30000  # 30s - o site e lento


# =============================================================================
# BLOCO 0 - Conectar a sessao ja logada
# =============================================================================
def conectar_navegador(playwright):
    browser = playwright.chromium.connect_over_cdp(CDP_ENDPOINT)
    context = browser.contexts[0]
    page = context.pages[0] if context.pages else context.new_page()
    page.set_default_timeout(TIMEOUT)
    # Garante que estamos na listagem (se a SPA ja estiver aberta, nao recarrega a toa)
    if "deal_registration_list" not in page.url:
        page.goto(BASE_URL)
    return browser, page


# --- helper: localizar o input vizinho a um rotulo de texto -------------------
def _campo_por_rotulo(page, texto_rotulo: str):
    """
    Acha o input cujo rotulo (texto) e 'texto_rotulo', subindo ate o container
    da linha do formulario e descendo para o .aui-input__inner.
    Confirmado pelo agente: nao ha for/id; a relacao e por proximidade no DOM.
    """
    xpath = (
        f"xpath=//*[normalize-space(text())='{texto_rotulo}']"
        f"/ancestor::*[.//input][1]//input[contains(@class,'aui-input__inner')]"
    )
    return page.locator(xpath).first


# =============================================================================
# BLOCO 1 - Buscar parceiro
# =============================================================================
def buscar_parceiro(page, nome_parceiro: str):
    # Abre o painel "Advanced Search" (se ainda nao estiver aberto)
    adv = page.get_by_role("button", name="Advanced Search")
    if adv.count() > 0 and adv.is_visible():
        adv.click()

    # Preenche o campo "Partner Company" (ancorado pelo rotulo)
    campo = _campo_por_rotulo(page, "Partner Company")
    campo.click()
    campo.fill(nome_parceiro)

    # Dispara a busca
    page.get_by_role("button", name="Query").click()
    page.wait_for_load_state("networkidle")


# =============================================================================
# BLOCO 2 - Ler contadores de status e filtrar Approved
# =============================================================================
STATUS_LABELS = ["Approving", "Approved", "Rejected", "Closed-Won",
                 "Closed", "Invalid", "Expired", "All"]


def ler_status(page) -> dict:
    """
    Le os cards do topo. O numero fica no irmao anterior ao rotulo (confirmado
    pelo agente). Fazemos via JS no contexto da pagina, mais confiavel que
    adivinhar a hierarquia de divs.
    """
    js = """(labels) => {
        const out = {};
        for (const name of labels) {
            const label = [...document.querySelectorAll('*')].find(el =>
                el.children.length === 0 &&
                el.textContent.trim() === name &&
                el.getBoundingClientRect().top < 220);
            out[name] = label ? (label.previousElementSibling?.textContent.trim() ?? null) : null;
        }
        return out;
    }"""
    return page.evaluate(js, STATUS_LABELS)


def filtrar_approved(page):
    """
    Clica no card 'Approved' do topo (o agente confirmou que isso filtra a
    tabela). Usamos o rotulo de texto e clicamos no elemento pai (o card).
    """
    card = page.locator(
        "xpath=//*[normalize-space(text())='Approved']/.."
    ).first
    card.click()
    page.wait_for_load_state("networkidle")


# =============================================================================
# BLOCO 3 - Contar as POs aprovadas (grid virtual do Vue)
# =============================================================================
def contar_linhas(page) -> int:
    """Numero de linhas de DADOS no grid (exclui cabecalho)."""
    js = """() => [...document.querySelectorAll('[role="row"]')]
              .filter(r => r.querySelector('[role="gridcell"]')).length"""
    return page.evaluate(js)


def _indice_coluna(page, nome_coluna: str) -> int:
    """Indice da coluna pelo texto do columnheader (ex: 'Project Name')."""
    js = """(nome) => {
        const hs = [...document.querySelectorAll('[role="columnheader"]')];
        return hs.findIndex(h => h.textContent.trim() === nome);
    }"""
    return page.evaluate(js, nome_coluna)


# =============================================================================
# BLOCO 4 - Abrir e ler cada PO (por INDICE, recapturando a cada volta)
# =============================================================================
def abrir_po_por_indice(page, idx_linha: int, idx_col_projeto: int):
    """
    Clica no link (span) da coluna Project Name da linha 'idx_linha'.
    Nao usamos href: e click do Vue Router. Por isso abrimos por indice.
    """
    linha = page.locator('[role="row"]').filter(
        has=page.locator('[role="gridcell"]')
    ).nth(idx_linha)
    celula = linha.locator('[role="gridcell"]').nth(idx_col_projeto)
    celula.locator('span, a').first.click()
    page.wait_for_load_state("networkidle")
    # TODO (Parte 2): trocar por expect(seletor da tela DR Details).to_be_visible()


def extrair_dados_po(page) -> dict:
    """[PARTE 2 - a preencher com os seletores da tela DR Details]"""
    dados = {
        "project_name": None, "dr_no": None, "submitted_partner": None,
        "submitted_by": None, "submitted_date": None, "approval_date": None,
        "estimated_order_date": None, "estimated_amount": None, "approver": None,
        "expired_date": None, "public_tender": None, "project_background": None,
        "owner_nome": None, "owner_email": None, "owner_telefone": None,
    }
    # TODO (Parte 2)
    return dados


def voltar_para_lista(page):
    """Volta da tela de detalhe para a listagem (a tabela sera recriada)."""
    dr_list = page.get_by_role("button", name="DR List")
    if dr_list.count() > 0:
        dr_list.click()
    else:
        page.go_back()
    page.wait_for_load_state("networkidle")


def processar_todas_pos(page) -> list:
    """Loop por INDICE: abre linha i, extrai, volta, recaptura na proxima."""
    resultados = []
    idx_col = _indice_coluna(page, "Project Name")
    total = contar_linhas(page)
    for i in range(total):
        abrir_po_por_indice(page, i, idx_col)
        resultados.append(extrair_dados_po(page))
        voltar_para_lista(page)
    return resultados


# =============================================================================
# BLOCO 5 - IA (placeholder) e BLOCO 6 - Saida
# =============================================================================
def gerar_resumo_ia(dados_po: dict) -> str:
    return "[resumo gerado pela IA - a implementar]"  # TODO (futuro)


def gerar_saida(resultados: list, nome_parceiro: str):
    pass  # TODO: PDF / dashboard


# =============================================================================
# ORQUESTRADOR
# =============================================================================
def main(nome_parceiro: str):
    with sync_playwright() as p:
        browser, page = conectar_navegador(p)
        try:
            buscar_parceiro(page, nome_parceiro)
            print("Contadores:", ler_status(page))
            filtrar_approved(page)
            print(f"{contar_linhas(page)} POs aprovadas encontradas.")
            resultados = processar_todas_pos(page)
            for d in resultados:
                d["resumo"] = gerar_resumo_ia(d)
            gerar_saida(resultados, nome_parceiro)
        finally:
            pass  # NAO fechar: e a SUA janela logada


if __name__ == "__main__":
    parceiro = input("Nome do parceiro: ").strip()
    main(parceiro)