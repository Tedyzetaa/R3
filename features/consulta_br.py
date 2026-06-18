"""
CONSULTA BR — Módulo de Consultas de Dados Públicos
R2 Tactical OS — features/consulta_br.py

Consolida o toolkit Puxar-Dados (CPF, CNPJ, CEP, BIN) em funções
que retornam strings formatadas para o Telegram.

APIs utilizadas:
  CEP  → ViaCEP          (https://viacep.com.br)
  CNPJ → ReceitaWS       (https://www.receitaws.com.br)
  CPF  → MTE/GOV         (portal público — pode ficar instável)
  BIN  → Binlist.io      (https://binlist.io)
"""

import re
import base64
import requests

TIMEOUT = 12  # segundos por request


# ══════════════════════════════════════════════════════════════════════════════
# CEP — ViaCEP
# ══════════════════════════════════════════════════════════════════════════════

def consultar_cep(cep: str) -> str:
    """Consulta endereço completo de um CEP via ViaCEP."""
    cep = re.sub(r"\D", "", cep)
    if len(cep) != 8:
        return "❌ CEP inválido. Informe exatamente 8 dígitos (sem traço)."

    try:
        r = requests.get(
            f"https://viacep.com.br/ws/{cep}/json/", timeout=TIMEOUT
        )
        d = r.json()

        if "erro" in d:
            return f"❌ CEP `{cep}` não encontrado na base dos Correios."

        complemento = d.get("complemento") or "—"
        return (
            f"📮 *CONSULTA CEP — R2*\n\n"
            f"CEP: `{d.get('cep', cep)}`\n"
            f"📍 Logradouro: {d.get('logradouro', 'N/A')}\n"
            f"   Complemento: {complemento}\n"
            f"   Bairro: {d.get('bairro', 'N/A')}\n"
            f"🏙️ Cidade: {d.get('localidade', 'N/A')} — {d.get('uf', 'N/A')}\n\n"
            f"IBGE: `{d.get('ibge', 'N/A')}` | "
            f"GIA: `{d.get('gia', 'N/A')}` | "
            f"DDD: `{d.get('ddd', 'N/A')}` | "
            f"SIAFI: `{d.get('siafi', 'N/A')}`"
        )

    except requests.Timeout:
        return "❌ Timeout ao consultar ViaCEP. Tente novamente."
    except Exception as e:
        return f"❌ Erro na consulta CEP: {e}"


# ══════════════════════════════════════════════════════════════════════════════
# CNPJ — ReceitaWS
# ══════════════════════════════════════════════════════════════════════════════

def consultar_cnpj(cnpj: str) -> str:
    """Consulta empresa pelo CNPJ via ReceitaWS (Receita Federal)."""
    cnpj = re.sub(r"\D", "", cnpj)
    if len(cnpj) != 14:
        return "❌ CNPJ inválido. Informe 14 dígitos (sem pontos, barra ou traço)."

    try:
        r = requests.get(
            f"https://www.receitaws.com.br/v1/cnpj/{cnpj}", timeout=TIMEOUT
        )
        d = r.json()

        if d.get("status") == "ERROR":
            return f"❌ {d.get('message', 'CNPJ não encontrado.')}"

        # Atividades secundárias (máx 3 + contagem)
        ativ_sec = d.get("atividades_secundarias", [])
        if ativ_sec:
            itens = [f"  • {a.get('text', '')}" for a in ativ_sec[:3]]
            ativ_str = "\n" + "\n".join(itens)
            if len(ativ_sec) > 3:
                ativ_str += f"\n  _(+{len(ativ_sec) - 3} mais)_"
        else:
            ativ_str = " N/A"

        fantasia = d.get("fantasia") or "—"
        email    = d.get("email")    or "N/A"
        efr      = d.get("efr")      or "—"

        return (
            f"🏢 *CONSULTA CNPJ — R2*\n\n"
            f"CNPJ: `{d.get('cnpj', cnpj)}`\n"
            f"📛 Razão Social: {d.get('nome', 'N/A')}\n"
            f"   Fantasia: {fantasia}\n"
            f"📊 Situação: *{d.get('situacao', 'N/A')}* "
            f"({d.get('motivo_situacao', 'N/A')}) — {d.get('data_situacao', 'N/A')}\n"
            f"🏷️ Tipo: {d.get('tipo', 'N/A')} | Porte: {d.get('porte', 'N/A')}\n"
            f"⚖️ Natureza: {d.get('natureza_juridica', 'N/A')}\n"
            f"📅 Abertura: {d.get('abertura', 'N/A')}\n"
            f"💰 Capital Social: R$ {d.get('capital_social', 'N/A')}\n\n"
            f"📍 {d.get('logradouro', '')}, {d.get('numero', '')}"
            f"{' — ' + d.get('complemento') if d.get('complemento') else ''}\n"
            f"   {d.get('bairro', '')} — {d.get('municipio', '')} / {d.get('uf', '')}\n"
            f"   CEP: `{d.get('cep', 'N/A')}`\n\n"
            f"📞 {d.get('telefone', 'N/A')} | ✉️ {email}\n"
            f"🔧 Atividade Principal: {d.get('atividade_principal', [{}])[0].get('text', 'N/A')}\n"
            f"📂 Atividades Secundárias:{ativ_str}\n\n"
            f"🏛️ EFR: {efr}\n"
            f"⏱️ Atualizado: {d.get('ultima_atualizacao', 'N/A')}"
        )

    except requests.Timeout:
        return "❌ Timeout ao consultar ReceitaWS. Tente novamente."
    except Exception as e:
        return f"❌ Erro na consulta CNPJ: {e}"


# ══════════════════════════════════════════════════════════════════════════════
# CPF — Portal MTE/GOV
# ══════════════════════════════════════════════════════════════════════════════

def consultar_cpf(cpf: str) -> str:
    """
    Consulta CPF via portal público MTE.
    ATENÇÃO: fonte governamental instável — pode retornar vazio.
    """
    cpf = re.sub(r"\D", "", cpf)
    if len(cpf) != 11:
        return "❌ CPF inválido. Informe 11 dígitos (sem pontos ou traço)."

    endpoint = base64.b64decode(
        b"aHR0cDovL3d3dy5qdXZlbnR1ZGV3ZWIubXRlLmdvdi5ici9wbnBlcGVzcXVpc2FzLmFzcA=="
    ).decode("ascii")

    headers = {
        "Content-Type": (
            "text/xml, application/x-www-form-urlencoded;"
            "charset=ISO-8859-1, text/xml; charset=ISO-8859-1"
        ),
        "Cookie": (
            "ASPSESSIONIDSCCRRTSA=NGOIJMMDEIMAPDACNIEDFBID; "
            "FGTServer=2A56DE837DA99704910F47A454B42D1A8CCF150E0874FDE491A399A5EF5657"
            "BC0CF03A1EEB1C685B4C118A83F971F6198A78"
        ),
        "Host": "www.juventudeweb.mte.gov.br",
    }

    try:
        r = requests.post(
            endpoint,
            headers=headers,
            data=f"acao=consultar%20cpf&cpf={cpf}&nocache=0.7636039437638835",
            timeout=TIMEOUT,
        )
        t = r.text

        def _ex(pattern):
            m = re.search(pattern, t)
            return m.group(1).strip() if m else None

        nome   = _ex(r'NOPESSOAFISICA="(.*?)"')
        nasc   = _ex(r'DTNASCIMENTO="(.*?)"')
        mae    = _ex(r'NOMAE="(.*?)"')
        logr   = _ex(r'NOLOGRADOURO="(.*?)"')
        nr     = _ex(r'NRLOGRADOURO="(.*?)"')
        compl  = _ex(r'DSCOMPLEMENTO="(.*?)"')
        bairro = _ex(r'NOBAIRRO="(.*?)"')
        cidade = _ex(r'NOMUNICIPIO="(.*?)"')
        uf     = _ex(r'SGUF="(.*?)"')
        cep_r  = _ex(r'NRCEP="(.*?)"')
        nr_cpf = _ex(r'NRCPF="(.*?)"')

        if not nome:
            return (
                "⚠️ CPF não encontrado ou fonte indisponível.\n\n"
                "_Nota: o portal MTE é uma fonte pública e pode estar "
                "offline ou com dados desatualizados._"
            )

        endereco_parts = [
            f"{logr.title()}, {nr}" if logr and nr else logr or "",
            compl.title()           if compl          else "",
            bairro.title()          if bairro         else "",
        ]
        endereco = " | ".join(p for p in endereco_parts if p)

        return (
            f"🪪 *CONSULTA CPF — R2*\n\n"
            f"CPF: `{nr_cpf or cpf}`\n"
            f"👤 Nome: {nome.title()}\n"
            f"🎂 Nascimento: {nasc or 'N/A'}\n"
            f"👩 Mãe: {mae.title() if mae else 'N/A'}\n\n"
            f"📍 {endereco or 'Endereço não disponível'}\n"
            f"   {cidade.title() if cidade else 'N/A'} — {uf or 'N/A'}\n"
            f"   CEP: `{cep_r or 'N/A'}`\n\n"
            f"⚠️ _Fonte: Portal Juventude Web / MTE (dados públicos)_"
        )

    except requests.Timeout:
        return "❌ Timeout ao consultar fonte CPF. Tente novamente."
    except Exception as e:
        return f"❌ Erro na consulta CPF: {e}"


# ══════════════════════════════════════════════════════════════════════════════
# BIN — Binlist.io
# ══════════════════════════════════════════════════════════════════════════════

def consultar_bin(bin_num: str) -> str:
    """Consulta informações de BIN de cartão via Binlist.io."""
    bin_num = re.sub(r"\D", "", bin_num)
    if len(bin_num) < 6:
        return "❌ BIN inválido. Informe ao menos 6 dígitos."

    try:
        r = requests.get(
            f"https://binlist.io/lookup/{bin_num}/", timeout=TIMEOUT
        )
        d = r.json()

        if not d.get("success"):
            return "❌ BIN não encontrado ou inválido."

        banco  = d.get("bank", {})
        pais   = d.get("country", {})
        numero = d.get("number", {})
        scheme = (d.get("scheme") or "N/A").upper()
        tipo   = (d.get("type")   or "N/A").upper()

        return (
            f"💳 *CONSULTA BIN — R2*\n\n"
            f"BIN: `{numero.get('iin', bin_num)}`\n"
            f"🏦 Banco: {banco.get('name', 'N/A')}\n"
            f"🔖 Bandeira: {scheme}\n"
            f"📂 Categoria: {d.get('category', 'N/A')}\n"
            f"💳 Tipo: {tipo}\n"
            f"🌍 País: {pais.get('name', 'N/A')} ({pais.get('alpha2', '')})\n"
            f"📞 Tel. Banco: {banco.get('phone', 'N/A')}\n"
            f"🌐 URL: {banco.get('url', 'N/A')}"
        )

    except requests.Timeout:
        return "❌ Timeout ao consultar Binlist. Tente novamente."
    except Exception as e:
        return f"❌ Erro na consulta BIN: {e}"