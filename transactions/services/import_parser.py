"""Leitura de extratos bancários e faturas — UC04.

Suporta os três formatos pedidos na arquitetura: OFX (padrão bancário
universal, o mais confiável), CSV (heurística de cabeçalho) e PDF
(extração de texto best-effort, já que o layout varia por banco).

Todas as funções devolvem uma lista de dicts:
    {"data": date, "descricao": str, "valor": Decimal}
onde valor positivo = entrada/receita e valor negativo = saída/despesa,
exatamente como no extrato bancário original (UC04, passo 6).
"""

from __future__ import annotations

import csv
import io
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation


class ExtratoInvalidoError(Exception):
    """FE01 — arquivo corrompido ou formato não reconhecido."""


# Termos de saldo e resumos de conta comuns a serem ignorados na importação
TERMOS_IGNORAR_SALDO = [
    "SALDO DO DIA", "SALDO ANTERIOR", "SALDO FINAL", "SALDO INICIAL",
    "SDO DO DIA", "SDO ANTERIOR", "SALDO DISPONIVEL", "SALDO ATUAL",
    "RESGATE AUTOMATICO", "SDO CONTA", "SALDO EM CONTA", "TOTAL DO DIA",
    "SALDO TOTAL", "SALDO CONSOLIDADO", "SALDO BASE", "SALDO REMUNERADO"
]

def _eh_linha_de_saldo(descricao: str) -> bool:
    """Retorna True se a descrição for apenas uma linha de saldo ou resumo."""
    desc_upper = (descricao or "").upper().strip()
    return any(termo in desc_upper for termo in TERMOS_IGNORAR_SALDO)


def _parse_valor_brl(texto: str) -> Decimal:
    texto = texto.strip().replace("R$", "").strip()
    negativo = texto.startswith("-") or texto.startswith("(")
    texto = texto.lstrip("-").strip("()").strip()
    # formatos: 1.234,56  |  1234.56  |  1234,56
    if "," in texto and "." in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif "," in texto:
        texto = texto.replace(",", ".")
    try:
        valor = Decimal(texto)
    except InvalidOperation:
        raise ExtratoInvalidoError(f"Valor monetário inválido: {texto!r}")
    return -valor if negativo else valor


def parse_ofx(arquivo) -> list[dict]:
    try:
        from ofxparse import OfxParser
    except ImportError as exc:  # pragma: no cover
        raise ExtratoInvalidoError("Suporte a OFX não instalado.") from exc

    try:
        conteudo = arquivo.read()
        if isinstance(conteudo, bytes):
            buffer = io.BytesIO(conteudo)
        else:
            buffer = io.StringIO(conteudo)
        ofx = OfxParser.parse(buffer)
    except Exception as exc:
        raise ExtratoInvalidoError(
            "Não conseguimos ler este arquivo. Certifique-se de exportar o "
            "extrato no formato OFX diretamente do aplicativo do seu banco."
        ) from exc

    transacoes = []
    contas = ofx.accounts if hasattr(ofx, "accounts") else [ofx.account]
    for conta in contas:
        for t in conta.statement.transactions:
            descricao = (t.memo or t.payee or "").strip()
            if _eh_linha_de_saldo(descricao):
                continue
            transacoes.append(
                {
                    "data": t.date.date() if hasattr(t.date, "date") else t.date,
                    "descricao": descricao,
                    "valor": Decimal(str(t.amount)),
                }
            )
    if not transacoes:
        raise ExtratoInvalidoError(
            "Não encontramos nenhuma movimentação neste arquivo OFX."
        )
    return transacoes


COLUNAS_DATA = ["data", "date", "dt"]
COLUNAS_DESCRICAO = ["descricao", "descrição", "historico", "histórico", "description", "memo", "lancamento", "lançamento"]
COLUNAS_VALOR = ["valor", "value", "amount", "vlr"]

FORMATOS_DATA = ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"]


def _parse_data_flex(texto: str):
    texto = texto.strip()
    for fmt in FORMATOS_DATA:
        try:
            return datetime.strptime(texto, fmt).date()
        except ValueError:
            continue
    raise ExtratoInvalidoError(f"Data inválida no arquivo: {texto!r}")


def parse_csv(arquivo) -> list[dict]:
    conteudo = arquivo.read()
    if isinstance(conteudo, bytes):
        for encoding in ("utf-8-sig", "latin-1"):
            try:
                conteudo = conteudo.decode(encoding)
                break
            except UnicodeDecodeError:
                continue

    amostra = conteudo[:2048]
    try:
        dialect = csv.Sniffer().sniff(amostra, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
        dialect.delimiter = ";" if amostra.count(";") > amostra.count(",") else ","

    leitor = csv.reader(io.StringIO(conteudo), dialect)
    linhas = [linha for linha in leitor if any(campo.strip() for campo in linha)]
    if not linhas:
        raise ExtratoInvalidoError("O arquivo CSV está vazio.")

    cabecalho = [c.strip().lower() for c in linhas[0]]
    idx_data = next((i for i, c in enumerate(cabecalho) if c in COLUNAS_DATA), None)
    idx_desc = next((i for i, c in enumerate(cabecalho) if c in COLUNAS_DESCRICAO), None)
    idx_valor = next((i for i, c in enumerate(cabecalho) if c in COLUNAS_VALOR), None)

    linhas_dados = linhas[1:]
    if idx_data is None or idx_valor is None:
        # Sem cabeçalho reconhecível: assume Data, Descrição, Valor (ordem comum)
        idx_data, idx_desc, idx_valor = 0, 1, 2
        linhas_dados = linhas

    transacoes = []
    for linha in linhas_dados:
        if len(linha) <= max(idx_data, idx_valor):
            continue

        descricao = linha[idx_desc].strip() if idx_desc is not None and idx_desc < len(linha) else ""
        if _eh_linha_de_saldo(descricao):
            continue

        try:
            data = _parse_data_flex(linha[idx_data])
            valor = _parse_valor_brl(linha[idx_valor])
        except ExtratoInvalidoError:
            continue

        transacoes.append({"data": data, "descricao": descricao, "valor": valor})

    if not transacoes:
        raise ExtratoInvalidoError(
            "Não conseguimos ler este arquivo. Certifique-se de exportar o "
            "extrato no formato CSV diretamente do aplicativo do seu banco."
        )
    return transacoes


LINHA_PDF_REGEX = re.compile(
    r"(?P<data>\d{2}/\d{2}/\d{4}|\d{2}/\d{2})\s+(?P<descricao>.+?)\s+(?P<valor>-?R?\$?\s?-?[\d.,]+)\s*$"
)


def parse_pdf(arquivo) -> list[dict]:
    try:
        import pdfplumber
    except ImportError as exc:  # pragma: no cover
        raise ExtratoInvalidoError("Suporte a PDF não instalado.") from exc

    transacoes = []
    try:
        with pdfplumber.open(arquivo) as pdf:
            for pagina in pdf.pages:
                texto = pagina.extract_text() or ""
                for linha in texto.splitlines():
                    m = LINHA_PDF_REGEX.search(linha.strip())
                    if not m:
                        continue
                    
                    descricao = m.group("descricao").strip()
                    if _eh_linha_de_saldo(descricao):
                        continue

                    data_texto = m.group("data")
                    if len(data_texto) == 5:  # dd/mm sem ano -> assume ano corrente
                        data_texto += f"/{datetime.now().year}"
                    try:
                        data = _parse_data_flex(data_texto)
                        valor = _parse_valor_brl(m.group("valor"))
                    except ExtratoInvalidoError:
                        continue
                    transacoes.append(
                        {"data": data, "descricao": descricao, "valor": valor}
                    )
    except Exception as exc:
        raise ExtratoInvalidoError(
            "Não conseguimos ler este arquivo. Certifique-se de exportar o "
            "extrato em PDF nativo (não digitalizado) diretamente do "
            "aplicativo do seu banco."
        ) from exc

    if not transacoes:
        raise ExtratoInvalidoError(
            "Não encontramos linhas de movimentação reconhecíveis neste PDF. "
            "Extratos em PDF variam muito entre bancos — se possível, "
            "prefira exportar em OFX ou CSV."
        )
    return transacoes


def parse_extrato(arquivo, formato: str) -> list[dict]:
    formato = (formato or "").lower()
    if formato == "ofx":
        return parse_ofx(arquivo)
    if formato == "csv":
        return parse_csv(arquivo)
    if formato == "pdf":
        return parse_pdf(arquivo)
    raise ExtratoInvalidoError("Formato de arquivo não suportado.")


def formato_por_extensao(nome_arquivo: str) -> str | None:
    nome = nome_arquivo.lower()
    if nome.endswith(".ofx"):
        return "ofx"
    if nome.endswith(".csv"):
        return "csv"
    if nome.endswith(".pdf"):
        return "pdf"
    return None