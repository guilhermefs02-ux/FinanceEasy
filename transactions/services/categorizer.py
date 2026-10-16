"""Categorização automática de transações importadas (UC04, passo 7 e UC05).

Ordem de classificação:
1. Regras específicas por descrição, sem chamadas externas.
2. Hugging Face para despesas sem indicadores de transferência genérica.
3. Categoria "Outros" quando não houver evidência suficiente.

Importante:
- Não inferir a finalidade de uma transferência apenas pelo banco ou carteira
  digital utilizada.
- Evitar classificar transferências entre contas como compras.
- Reconhecer contas de consumo e serviços recorrentes.
- Respeitar as categorias cadastradas no sistema.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


# Regras específicas para despesas.
# A descrição é normalizada antes da comparação: acentos são removidos
# e o texto é convertido para maiúsculas.
REGRAS_PALAVRA_CHAVE = [
    # Alimentação e delivery
    (
        r"\bIFOOD\b|\bRAPPI\b|\bPIZZARIA\b|\bRESTAURANTE\b|"
        r"\bLANCHONETE\b|\bPADARIA\b|\bACOUGUE\b|\bHORTIFRUTI\b|"
        r"\bSUPERMERCADO\b|\bMERCADO\s+CARDOSO\b|\bMERCADINHO\b|"
        r"\bBURGER\s?KING\b|\bMCDONALD",
        "Alimentação/Supermercado",
    ),

    # Transporte
    (
        r"\bUBER\b|\b99\s?POP\b|\b99APP\b|\b99TAXI\b|"
        r"\bPOSTO\b|\bCOMBUSTIVEL\b|\bESTACIONAMENTO\b|"
        r"\bPEDAGIO\b|\bBILHETE\s?UNICO\b",
        "Transporte",
    ),

    # Assinaturas e entretenimento digital
    (
        r"\bNETFLIX\b|\bSPOTIFY\b|\bDISNEY\s?\+?\b|\bHBO\b|"
        r"\bAMAZON\s?PRIME\b|\bYOUTUBE\s?PREMIUM\b|\bDEEZER\b|"
        r"\bPARAMOUNT\b",
        "Assinaturas",
    ),

    # Moradia, água, energia, gás e internet
    (
        r"\bSABESP\b|\bENEL\b|\bELETROPAULO\b|\bCPFL\b|"
        r"\bCEMIG\b|\bLIGHT\b|\bCOPEL\b|\bCOMGAS\b|"
        r"\bSANEPAR\b|\bSANEAMENTO\b|\bCIA\s?SANEAMEN\b|"
        r"\bWORLD\s?FIBRA\b|\bTELECOM\b|\bVIVO\b|\bCLARO\b|"
        r"\bTIM\b|\bOI\s?FIBRA\b|\bINTERNET\b|\bALUGUEL\b|"
        r"\bCONDOMINIO\b|\bIPTU\b",
        "Moradia/Casa",
    ),

    # Saúde
    (
        r"\bFARMACIA\b|\bDROGARIA\b|\bDROGASIL\b|\bPACHECO\b|"
        r"\bCLINICA\s?MEDICA\b|\bHOSPITAL\b|\bLABORATORIO\b|"
        r"\bDENTISTA\b|\bODONTOLOG",
        "Outros",
    ),

    # Educação
    (
        r"\bFACULDADE\b|\bESCOLA\b|\bCURSO\b|\bUDEMY\b|"
        r"\bALURA\b|\bLIVRARIA\b",
        "Educação",
    ),

    # Lazer
    (
        r"\bCINEMA\b|\bINGRESSO\b|\bSHOW\b|\bSTEAM\b|"
        r"\bPLAYSTATION\b|\bXBOX\b",
        "Lazer",
    ),
]


# Receitas identificáveis pela descrição.
# Recebimentos por Pix sem contexto suficiente continuam em "Outros".
REGRAS_RECEITA = [
    (
        r"\bSALARIO\b|\bFOLHA\s?DE\s?PAGAMENTO\b|"
        r"\bPGTO\s?SAL\b|\bPAGAMENTO\s?DE\s?SALARIO\b",
        "Salário",
    ),
]


# Descrições que não revelam a finalidade real da movimentação.
# Nesses casos, não enviamos o texto ao modelo para tentar adivinhar
# uma categoria com base apenas no nome de um banco ou carteira.
PADROES_TRANSFERENCIA_GENERICA = [
    r"\bTRANSFERENCIA\s+(?:ENVIADA|RECEBIDA)\b",
    r"\bTRANSFERENCIA\s+RECEBIDA\b",
    r"\bPIX\s+(?:ENVIADO|RECEBIDO)\b",
    r"\bTED\s+(?:ENVIADA|RECEBIDA)\b",
    r"\bDOC\s+(?:ENVIADO|RECEBIDO)\b",
    r"\bPAGAMENTO\s+DE\s+FATURA\b",
]

# Pagamentos de boletos sem identificação suficiente do beneficiário
# também não devem ser classificados por tentativa.
PADROES_BOLETO_GENERICO = [
    r"\bPAGAMENTO\s+DE\s+BOLETO\b",
    r"\bBOLETO\s+PAGO\b",
]


@dataclass
class SugestaoCategoria:
    nome_categoria: str
    confianca: str  # "alta" ou "baixa"
    origem: str  # "regra" | "huggingface" | "padrao"


def _normalizar(texto: str) -> str:
    """Remove acentos e padroniza o texto para comparação."""
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(caractere)
    )
    return texto.upper()


def _corresponde_a_algum_padrao(
    descricao_normalizada: str,
    padroes: list[str],
) -> bool:
    return any(
        re.search(padrao, descricao_normalizada)
        for padrao in padroes
    )


def _por_regras(
    descricao: str,
    tipo: str,
) -> SugestaoCategoria | None:
    descricao_normalizada = _normalizar(descricao)

    regras = (
        REGRAS_RECEITA
        if tipo == "receita"
        else REGRAS_PALAVRA_CHAVE
    )

    for padrao, categoria in regras:
        if re.search(padrao, descricao_normalizada):
            return SugestaoCategoria(
                nome_categoria=categoria,
                confianca="alta",
                origem="regra",
            )

    return None


def _categorias_despesa_labels() -> list[str]:
    """Obtém apenas categorias de despesa existentes no banco."""
    from transactions.models import Category

    return list(
        Category.objects.filter(tipo="despesa").values_list(
            "nome",
            flat=True,
        )
    ) or ["Outros"]


def _por_huggingface(descricao: str) -> SugestaoCategoria | None:
    token = getattr(settings, "HUGGINGFACE_API_TOKEN", "")

    if not token or not descricao:
        return None

    cache_key = f"hf_categoria:{_normalizar(descricao).lower()}"
    cached = cache.get(cache_key)

    if cached:
        return SugestaoCategoria(**cached)

    try:
        from huggingface_hub import InferenceClient

        client = InferenceClient(token=token)
        labels = _categorias_despesa_labels()

        resultado = client.zero_shot_classification(
            descricao,
            candidate_labels=labels,
            model=getattr(
                settings,
                "HUGGINGFACE_ZERO_SHOT_MODEL",
                "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli",
            ),
        )

        melhor = resultado[0] if resultado else None

        if not melhor:
            return None

        score = float(
            melhor.score
            if hasattr(melhor, "score")
            else melhor["score"]
        )
        label = (
            melhor.label
            if hasattr(melhor, "label")
            else melhor["label"]
        )

        # Uma previsão pouco segura não deve ser apresentada como certa.
        confianca = "alta" if score >= 0.70 else "baixa"

        sugestao = SugestaoCategoria(
            nome_categoria=label,
            confianca=confianca,
            origem="huggingface",
        )

        cache.set(
            cache_key,
            sugestao.__dict__,
            timeout=60 * 60 * 24 * 7,
        )

        return sugestao

    except Exception:
        logger.exception(
            "Falha ao classificar transação via Hugging Face Inference API"
        )
        return None


def sugerir_categoria(
    descricao: str,
    tipo: str = "despesa",
) -> SugestaoCategoria:
    """Sugere uma categoria para a transação importada."""

    descricao_normalizada = _normalizar(descricao)

    # Primeiro, aplicar regras com identificação explícita do comerciante
    # ou serviço. Ex.: iFood, Uber, Sanepar e Eletropaulo.
    sugestao = _por_regras(descricao, tipo)

    if sugestao:
        return sugestao

    # Transferências genéricas não revelam onde o dinheiro foi gasto.
    # O mesmo vale para pagamentos de fatura, que podem quitar compras
    # já registradas em outras transações.
    if _corresponde_a_algum_padrao(
        descricao_normalizada,
        PADROES_TRANSFERENCIA_GENERICA,
    ):
        return SugestaoCategoria(
            nome_categoria="Outros",
            confianca="baixa",
            origem="padrao",
        )

    if _corresponde_a_algum_padrao(
        descricao_normalizada,
        PADROES_BOLETO_GENERICO,
    ):
        return SugestaoCategoria(
            nome_categoria="Outros",
            confianca="baixa",
            origem="padrao",
        )

    # A IA só é utilizada para despesas sem regra específica.
    if tipo == "despesa":
        sugestao = _por_huggingface(descricao)

        if sugestao:
            return sugestao

    return SugestaoCategoria(
        nome_categoria="Outros",
        confianca="baixa",
        origem="padrao",
    )
