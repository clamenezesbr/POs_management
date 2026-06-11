"""
================================================================================
 AUTOMACAO eplus.huawei.com - Partner Deal Registration
================================================================================
 LOGIN: este script NAO faz login. Abra o Chrome em modo debug, conecte a VPN
 e faca o SSO manualmente; o Playwright se pluga nessa sessao.

 PASSO A PASSO:
   1. Execute launch_chrome.bat  (abre o Chrome com debug port)
   2. Conecte a VPN
   3. Faca o SSO manualmente no Chrome aberto
   4. Execute rodar.bat (ou: python main.py)
   5. Digite o nome do parceiro quando solicitado

 DEPENDENCIAS:
   pip install playwright
   playwright install chromium
================================================================================
"""

import re

from playwright.sync_api import sync_playwright, expect

BASE_URL = "https://eplus.huawei.com/web/eplus/#/dr?~l_registration_phurx4=%2Fdeal_registration_list"
CDP_ENDPOINT = "http://localhost:9222"
TIMEOUT = 30000  # 30s - o site e lento


# =============================================================================
# BLOCO 0 - Conectar a sessao ja logada
# =============================================================================
def conectar_navegador(playwright):
    print(f"[0] Conectando ao Chrome em {CDP_ENDPOINT} ...")
    try:
        browser = playwright.chromium.connect_over_cdp(CDP_ENDPOINT)
    except Exception as e:
        raise SystemExit(
            f"\n[ERRO] Nao foi possivel conectar ao Chrome.\n"
            f"  Verifique se o launch_chrome.bat foi executado antes da VPN.\n"
            f"  Detalhe: {e}"
        )
    context = browser.contexts[0]
    page = context.pages[0] if context.pages else context.new_page()
    page.set_default_timeout(TIMEOUT)
    if "deal_registration_list" not in page.url:
        print("[0] Navegando para a listagem de Deal Registrations ...")
        page.goto(BASE_URL)
    print("[0] Conectado com sucesso.")
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
    print(f"[1] Buscando parceiro: '{nome_parceiro}' ...")
    adv = page.get_by_role("button", name="Advanced Search")
    if adv.count() > 0 and adv.is_visible():
        adv.click()

    campo = _campo_por_rotulo(page, "Partner Company")
    campo.click()
    campo.fill(nome_parceiro)

    page.get_by_role("button", name="Query").click()
    page.wait_for_load_state("networkidle")
    # Tenta aguardar o grid, mas nao falha se nao houver resultados (Vue nao renderiza grid vazio)
    try:
        page.locator('[role="grid"]').wait_for(state='visible', timeout=10000)
    except Exception:
        pass
    print("[1] Busca concluida.")


# =============================================================================
# BLOCO 2 - Ler contadores de status e filtrar Approved
# =============================================================================
STATUS_LABELS = ["Approving", "Approved", "Rejected", "Closed-Won",
                 "Closed", "Invalid", "Expired", "All"]


def ler_status(page) -> dict:
    """
    Le os cards do topo. Sobe ate 4 niveis a partir do rotulo para achar
    um ancestral cujo filho direto seja um numero puro — robusto a qualquer
    nivel de nesting (count pode estar em div.top, enquanto label esta em div.bottom).
    """
    js = """(labels) => {
        const out = {};
        for (const name of labels) {
            const xp = document.evaluate(
                "//*[normalize-space(text())='" + name + "']",
                document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null
            );
            let found = false;
            for (let i = 0; i < xp.snapshotLength; i++) {
                const label = xp.snapshotItem(i);
                let ancestor = label.parentElement;
                for (let d = 0; d < 4 && ancestor; d++, ancestor = ancestor.parentElement) {
                    const numEl = [...ancestor.children].find(
                        c => /^\\d+$/.test((c.innerText || c.textContent || '').trim())
                    );
                    if (numEl) {
                        out[name] = (numEl.innerText || numEl.textContent).trim();
                        found = true;
                        break;
                    }
                }
                if (found) break;
            }
            if (!found) out[name] = null;
        }
        return out;
    }"""
    return page.evaluate(js, STATUS_LABELS)


def filtrar_approved(page):
    """
    Clica no card 'Approved' do topo para filtrar a tabela.
    Usa JS para identificar o card correto (irmao numerico), evitando
    clicar no 'Approved' do dropdown DR Status do formulario.
    """
    print("[2] Filtrando por status Approved ...")
    found = page.evaluate("""() => {
        const xp = document.evaluate(
            "//*[normalize-space(text())='Approved']",
            document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null
        );
        for (let i = 0; i < xp.snapshotLength; i++) {
            const label = xp.snapshotItem(i);
            let ancestor = label.parentElement;
            for (let d = 0; d < 4 && ancestor; d++, ancestor = ancestor.parentElement) {
                const numEl = [...ancestor.children].find(
                    c => /^\\d+$/.test((c.innerText || c.textContent || '').trim())
                );
                if (numEl) {
                    ancestor.click();
                    return true;
                }
            }
        }
        return false;
    }""")
    if not found:
        raise RuntimeError("Card 'Approved' nao encontrado na barra de status.")
    page.wait_for_load_state("networkidle")
    try:
        page.locator('[role="grid"]').wait_for(state='visible', timeout=10000)
    except Exception:
        pass  # 0 POs aprovadas — grid nao renderiza
    print("[2] Filtro aplicado.")


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
    # Aguarda o container da tela DR Details aparecer (mais confiavel que networkidle)
    page.locator('#aui-collapse-content-54912283').wait_for(state='visible')


# --- helpers para extrair contato do owner a partir do Project Background -----

def _extrair_email(texto: str) -> str | None:
    m = re.search(r'[\w.+-]+@[\w-]+\.[a-z]{2,}', texto, re.IGNORECASE)
    return m.group() if m else None


def _extrair_telefone(texto: str) -> str | None:
    # Formatos brasileiros: (11) 99999-9999 | +55 11 99999-9999 | 11999999999
    m = re.search(r'(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{2}\)?[\s-]?)[\d\s-]{8,10}', texto)
    if not m:
        return None
    candidato = m.group().strip()
    # Descarta se for CNPJ (14 digitos sem formatacao de telefone)
    apenas_digitos = re.sub(r'\D', '', candidato)
    if len(apenas_digitos) == 14:
        return None
    return candidato if len(apenas_digitos) >= 8 else None


def _extrair_nome_owner(texto: str) -> str | None:
    # Procura linha com padrao "Gerente|Contato|Responsavel|Owner: <nome>"
    # onde o nome vem antes do email/telefone
    patterns = [
        r'(?:Gerente|Contato|Responsável|Owner|Representante)[^:\n]*:\s*([^@\n\(]+)',
        r'Nome[^:\n]*:\s*([^\n@]+)',
    ]
    for pat in patterns:
        m = re.search(pat, texto, re.IGNORECASE)
        if m:
            nome = m.group(1).strip().rstrip(',;/ ')
            # Rejeita se nao tiver espaco: provavelmente e um username, nao um nome real
            if nome and ' ' in nome:
                return nome
    return None


def extrair_dados_po(page) -> dict:
    """Extrai todos os campos da tela DR Details via JS no container #aui-collapse-content-54912283."""
    js = r"""() => {
        const C = document.querySelector('#aui-collapse-content-54912283');
        if (!C) return null;
        const children = Array.from(C.children);

        function getField(labelText) {
            const label = children.find(el => el.innerText.trim() === labelText);
            return label ? (label.nextElementSibling?.innerText.trim() ?? null) : null;
        }

        // Project Background: texto livre em varios nos apos o rotulo
        function getBackground() {
            const idx = children.findIndex(el => el.innerText.trim() === 'Project Background');
            if (idx === -1) return null;
            return children.slice(idx + 1)
                .map(n => n.innerText.trim())
                .filter(Boolean)
                .join('\n');
        }

        return {
            project_name:          getField('Project Name'),
            dr_no:                 getField('DR. No.'),
            submitted_partner:     getField('Submitted Partner'),
            submitted_by:          getField('Submitted by'),
            submitted_date:        getField('Submited Date'),
            approval_date:         getField('Approval Date'),
            estimated_order_date:  getField('Estimated Order Date'),
            estimated_amount:      getField('Estimated Amount'),
            approver:              getField('Approver'),
            expired_date:          getField('Expired Date'),
            public_tender:         getField('Public Tender'),
            project_background:    getBackground(),
        };
    }"""

    dados = page.evaluate(js) or {}
    bg = dados.get("project_background") or ""
    dados["owner_email"] = _extrair_email(bg)
    dados["owner_telefone"] = _extrair_telefone(bg)
    dados["owner_nome"] = _extrair_nome_owner(bg)
    return dados


def voltar_para_lista(page):
    """Volta da tela de detalhe para a listagem (a tabela sera recriada)."""
    dr_list = page.get_by_role("button", name="DR List")
    if dr_list.count() > 0:
        dr_list.click()
    else:
        page.go_back()
    page.locator('[role="grid"]').wait_for(state='visible')


def processar_todas_pos(page) -> list:
    """Loop por INDICE: abre linha i, extrai, volta, recaptura na proxima."""
    resultados = []
    idx_col = _indice_coluna(page, "Project Name")
    total = contar_linhas(page)
    print(f"[4] Processando {total} PO(s) aprovada(s) ...")
    for i in range(total):
        print(f"[4] PO {i + 1}/{total} ...")
        try:
            abrir_po_por_indice(page, i, idx_col)
            dados = extrair_dados_po(page)
            resultados.append(dados)
            print(f"    DR No: {dados.get('dr_no')} | Projeto: {dados.get('project_name')}")
        except Exception as e:
            print(f"    [AVISO] Falha ao processar PO {i + 1}: {e}")
            resultados.append({"erro": str(e), "indice": i})
        finally:
            voltar_para_lista(page)
    return resultados


# =============================================================================
# BLOCO 5 - IA (placeholder) e BLOCO 6 - Saida
# =============================================================================
def gerar_resumo_ia(dados_po: dict) -> str:
    return "[resumo gerado pela IA - a implementar]"  # TODO (futuro)


def gerar_saida(resultados: list, nome_parceiro: str):
    """Imprime os dados extraidos no console. PDF / dashboard: fase futura."""
    separador = "=" * 72
    print(f"\n{separador}")
    print(f"  RESULTADO — {nome_parceiro}  ({len(resultados)} PO(s) aprovada(s))")
    print(separador)
    for i, d in enumerate(resultados, 1):
        if "erro" in d:
            print(f"\n[PO {i}] ERRO: {d['erro']}")
            continue
        print(f"\n[PO {i}] {d.get('dr_no', 'N/A')}")
        print(f"  Projeto:          {d.get('project_name')}")
        print(f"  Parceiro:         {d.get('submitted_partner')}")
        print(f"  Submetido por:    {d.get('submitted_by')}")
        print(f"  Data submissao:   {d.get('submitted_date')}")
        print(f"  Aprovado em:      {d.get('approval_date')}")
        print(f"  Expira em:        {d.get('expired_date')}")
        print(f"  Valor estimado:   {d.get('estimated_amount')}")
        print(f"  Data pedido est.: {d.get('estimated_order_date')}")
        print(f"  Aprovador:        {d.get('approver')}")
        print(f"  Licitacao publ.:  {d.get('public_tender')}")
        print(f"  --- Contato owner ---")
        print(f"  Nome:             {d.get('owner_nome')}")
        print(f"  Email:            {d.get('owner_email')}")
        print(f"  Telefone:         {d.get('owner_telefone')}")
        bg = d.get("project_background") or ""
        if bg:
            print(f"  --- Project Background ---")
            for linha in bg.splitlines():
                print(f"    {linha}")
        print(f"  Resumo IA:        {d.get('resumo')}")
    print(f"\n{separador}\n")


# =============================================================================
# ORQUESTRADOR
# =============================================================================
def main(nome_parceiro: str):
    with sync_playwright() as p:
        browser, page = conectar_navegador(p)
        try:
            buscar_parceiro(page, nome_parceiro)
            contadores = ler_status(page)
            print(f"[2] Contadores de status: {contadores}")
            filtrar_approved(page)
            total = contar_linhas(page)
            print(f"[3] {total} PO(s) aprovada(s) encontrada(s).")
            if total == 0:
                print("Nenhuma PO aprovada para este parceiro. Encerrando.")
                return
            resultados = processar_todas_pos(page)
            for d in resultados:
                d["resumo"] = gerar_resumo_ia(d)
            gerar_saida(resultados, nome_parceiro)
        finally:
            pass  # NAO fechar: e a SUA janela logada


if __name__ == "__main__":
    parceiro = input("Nome do parceiro: ").strip()
    if not parceiro:
        raise SystemExit("[ERRO] Nome do parceiro nao pode ser vazio.")
    main(parceiro)