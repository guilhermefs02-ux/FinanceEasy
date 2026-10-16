"""Categorização automática de transações importadas (UC04 e UC05).

Ordem de classificação:
1. Regras específicas por descrição.
2. Hugging Face para despesas sem regra específica.
3. Melhor sugestão disponível, identificada como baixa confiança,
   quando não houver evidência suficiente.

As categorias sugeridas respeitam as categorias padrão existentes
no banco de dados. Não se presume a finalidade de transferências
apenas pelo banco ou carteira digital utilizados.
"""

from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


CATEGORIA_OUTROS = "Outros"
CATEGORIA_ALIMENTACAO = "Alimentação/Supermercado"
CATEGORIA_MORADIA = "Moradia/Casa"
CATEGORIA_TRANSPORTE = "Transporte"
CATEGORIA_EDUCACAO = "Educação"
CATEGORIA_LAZER = "Lazer"
CATEGORIA_ASSINATURAS = "Assinaturas"

CATEGORIAS_DESPESA_PADRAO = [
    CATEGORIA_ALIMENTACAO,
    CATEGORIA_MORADIA,
    CATEGORIA_TRANSPORTE,
    CATEGORIA_EDUCACAO,
    CATEGORIA_LAZER,
    CATEGORIA_ASSINATURAS,
    CATEGORIA_OUTROS,
]

CATEGORIAS_RECEITA_PADRAO = [
    "Salário",
    "Bicos/Extras",
    "Venda de Usados",
    "Benefício",
    "Outros",
]


# Regras para despesas.
REGRAS_PALAVRA_CHAVE = [
    (
        r"\bIFOOD\b|\bRAPPI\b|\bPIZZARIA\b|\bRESTAURANTE\b|"
        r"\bLANCHONETE\b|\bPADARIA\b|\bACOUGUE\b|\bHORTIFRUTI\b|"
        r"\bSUPERMERCADO\b|\bMERCADO\s+CARDOSO\b|\bMERCADINHO\b|"
        r"\bBURGER\s?KING\b|\bMCDONALD|\bHABIBS\b|"
        r"\bLANCHES\b|\bCONFEITARIA\b|\bPASTELARIA\b",
        CATEGORIA_ALIMENTACAO,
    ),
    (
        r"\bUBER\b|\b99\s?POP\b|\b99APP\b|\b99TAXI\b|"
        r"\bPOSTO\b|\bCOMBUSTIVEL\b|\bGASOLINA\b|\bDIESEL\b|"
        r"\bESTACIONAMENTO\b|\bPEDAGIO\b|\bBILHETE\s?UNICO\b|"
        r"\bSEM\s?PARAR\b|\bVELOE\b",
        CATEGORIA_TRANSPORTE,
    ),
    (
        r"\bNETFLIX\b|\bSPOTIFY\b|\bDISNEY\s?\+?\b|\bHBO\b|"
        r"\bMAX\b|\bAMAZON\s?PRIME\b|\bYOUTUBE\s?PREMIUM\b|"
        r"\bDEEZER\b|\bPARAMOUNT\b|\bGLOBOPLAY\b|"
        r"\bAPPLE\s?MUSIC\b|\bGOOGLE\s?ONE\b",
        CATEGORIA_ASSINATURAS,
    ),
    (
        r"\bSABESP\b|\bENEL\b|\bELETROPAULO\b|\bCPFL\b|"
        r"\bCEMIG\b|\bLIGHT\b|\bCOPEL\b|\bCOMGAS\b|"
        r"\bSANEPAR\b|\bSANEAMENTO\b|\bCIA\s?SANEAMEN\b|"
        r"\bWORLD\s?FIBRA\b|\bTELECOM\b|\bVIVO\b|\bCLARO\b|"
        r"\bTIM\b|\bOI\s?FIBRA\b|\bINTERNET\b|\bALUGUEL\b|"
        r"\bCONDOMINIO\b|\bIPTU\b|\bENERGIA\s?ELETRICA\b|"
        r"\bAGUA\s?E\s?ESGOTO\b|\bGAS\s?ENCANADO\b|"
        r"\bSANEAGO\b|\bEMASA\b",
        CATEGORIA_MORADIA,
    ),
    (
        r"\bFACULDADE\b|\bESCOLA\b|\bCURSO\b|\bUDEMY\b|"
        r"\bALURA\b|\bLIVRARIA\b|\bMENSALIDADE\s?ESCOLAR\b|"
        r"\bMATERIAL\s?ESCOLAR\b|\bIDIOMAS\b",
        CATEGORIA_EDUCACAO,
    ),
    (
        r"\bCINEMA\b|\bINGRESSO\b|\bSHOW\b|\bSTEAM\b|"
        r"\bPLAYSTATION\b|\bXBOX\b|\bNINTENDO\b|"
        r"\bPARQUE\s?DE\s?DIVERSAO\b|\bBOLICHE\b",
        CATEGORIA_LAZER,
    ),
    # Não há categoria específica de saúde no cadastro padrão.
    (
        r"\bFARMACIA\b|\bDROGARIA\b|\bDROGASIL\b|\bPACHECO\b|"
        r"\bCLINICA\b|\bHOSPITAL\b|\bLABORATORIO\b|"
        r"\bDENTISTA\b|\bODONTOLOG\b",
        CATEGORIA_OUTROS,
    ),
]


# Regras para receitas identificáveis.
REGRAS_RECEITA = [
    (
        r"\bSALARIO\b|\bFOLHA\s?DE\s?PAGAMENTO\b|"
        r"\bPGTO\s?SAL\b|\bPAGAMENTO\s?DE\s?SALARIO\b|"
        r"\bCREDITO\s?SALARIAL\b|\bORDENADO\b",
        "Salário",
    ),
    (
        r"\bAPOSENTADORIA\b|\bPENSAO\s?INSS\b|\bINSS\s?BENEFICIO\b|"
        r"\bBENEFICIO\s?PREVIDENCIARIO\b|\bAUXILIO\b|"
        r"\bBOLSA\s?FAMILIA\b|\bBPC\b|\bLOAS\b",
        "Benefício",
    ),
    (
        r"\bFREELANCE\b|\bFREELA\b|\bSERVICO\s?PRESTADO\b|"
        r"\bTRABALHO\s?EXTRA\b|\bRENDA\s?EXTRA\b|"
        r"\bCOMISSAO\b|\bHONORARIOS\s?RECEBIDOS\b",
        "Bicos/Extras",
    ),
    (
        r"\bVENDA\s?DE\s?USADOS\b|\bVENDA\s?USADO\b|"
        r"\bVENDA\s?VEICULO\b|\bVENDA\s?MOVEIS\b",
        "Venda de Usados",
    ),
]


PADROES_TRANSFERENCIA_GENERICA = [
    r"\bTRANSFERENCIA\s+(?:ENVIADA|RECEBIDA)\b",
    r"\bTRANSFERENCIA\s+(?:ENTRE\s+CONTAS|PIX)\b",
    r"\bPIX\s+(?:ENVIADO|RECEBIDO)\b",
    r"\bTED\s+(?:ENVIADA|RECEBIDA)\b",
    r"\bDOC\s+(?:ENVIADO|RECEBIDO)\b",
    r"\bPAGAMENTO\s+DE\s+FATURA\b",
    r"\bLIQUIDACAO\s+DE\s+FATURA\b",
    r"\bPAGAMENTO\s+DE\s+CARTAO\b",
]

PADROES_BOLETO_GENERICO = [
    r"\bPAGAMENTO\s+DE\s+BOLETO\b",
    r"\bBOLETO\s+PAGO\b",
    r"\bPAGAMENTO\s+TITULO\b",
]


@dataclass
class SugestaoCategoria:
    nome_categoria: str
    confianca: str
    origem: str


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
    """Retorna categorias padrão de despesas existentes no banco."""
    from transactions.models import Category

    existentes = list(
        Category.objects.filter(
            tipo=Category.Tipo.DESPESA,
            usuario__isnull=True,
        ).values_list("nome", flat=True)
    )

    if not existentes:
        return CATEGORIAS_DESPESA_PADRAO.copy()

    permitidas = set(CATEGORIAS_DESPESA_PADRAO)
    labels = [nome for nome in existentes if nome in permitidas]

    return labels or [CATEGORIA_OUTROS]


def _por_huggingface(descricao: str) -> SugestaoCategoria | None:
    token = getattr(settings, "HUGGINGFACE_API_TOKEN", "")

    if not token or not descricao:
        return None

    labels = _categorias_despesa_labels()
    descricao_normalizada = _normalizar(descricao)
    cache_key = (
        "hf_categoria:v2:"
        + hashlib.sha256(
            (descricao_normalizada + "|" + "|".join(labels)).encode("utf-8")
        ).hexdigest()
    )

    cached = cache.get(cache_key)
    if cached:
        return SugestaoCategoria(**cached)

    try:
        from huggingface_hub import InferenceClient

        client = InferenceClient(token=token)
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

        if label not in labels:
            logger.warning(
                "Hugging Face retornou categoria fora da lista permitida: %s",
                label,
            )
            return None

        sugestao = SugestaoCategoria(
            nome_categoria=label,
            confianca="alta" if score >= 0.70 else "baixa",
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
    """Sugere uma categoria e indica quando precisa de revisão."""

    if tipo not in ("receita", "despesa"):
        tipo = "despesa"

    descricao_normalizada = _normalizar(descricao)

    # 1. Regras específicas têm prioridade.
    sugestao = _por_regras(descricao, tipo)
    if sugestao:
        return sugestao

    # 2. Transferências e pagamentos genéricos não revelam a finalidade.
    if _corresponde_a_algum_padrao(
        descricao_normalizada,
        PADROES_TRANSFERENCIA_GENERICA,
    ) or _corresponde_a_algum_padrao(
        descricao_normalizada,
        PADROES_BOLETO_GENERICO,
    ):
        return SugestaoCategoria(
            nome_categoria=CATEGORIA_OUTROS,
            confianca="baixa",
            origem="padrao",
        )

    # 3. A IA classifica despesas sem regra específica.
    if tipo == "despesa":
        sugestao = _por_huggingface(descricao)
        if sugestao:
            return sugestao

    return SugestaoCategoria(
        nome_categoria=CATEGORIA_OUTROS,
        confianca="baixa",
        origem="padrao",
    )
