"""Categorização automática de transações importadas (UC04 e UC05).

Prioridades:
1. Aplicar regras locais antes de consultar serviços externos.
2. Reutilizar categorias e cliente do Hugging Face.
3. Aproveitar o cache de classificações.
4. Limitar o tempo de espera da API externa.
5. Nunca presumir a finalidade de transferências genéricas.
"""

from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
from functools import lru_cache

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
    (
        r"\bFARMACIA\b|\bDROGARIA\b|\bDROGASIL\b|\bPACHECO\b|"
        r"\bCLINICA\b|\bHOSPITAL\b|\bLABORATORIO\b|"
        r"\bDENTISTA\b|\bODONTOLOG\b",
        CATEGORIA_OUTROS,
    ),
]

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


class SugestaoCategoria:
    def __init__(
        self,
        nome_categoria: str,
        confianca: str,
        origem: str,
    ):
        self.nome_categoria = nome_categoria
        self.confianca = confianca
        self.origem = origem

    def __repr__(self) -> str:
        return (
            f"SugestaoCategoria(nome_categoria={self.nome_categoria!r}, "
            f"confianca={self.confianca!r}, origem={self.origem!r})"
        )


def _normalizar(texto: str) -> str:
    """Remove acentos e padroniza o texto para comparação."""
    texto = unicodedata.normalize("NFKD", texto or "")
    return "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(caractere)
    ).upper()


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


@lru_cache(maxsize=1)
def _categorias_despesa_labels_cache() -> tuple[str, ...]:
    """Consulta e mantém em memória as categorias padrão existentes."""
    from transactions.models import Category

    existentes = list(
        Category.objects.filter(
            tipo=Category.Tipo.DESPESA,
            usuario__isnull=True,
        ).values_list("nome", flat=True)
    )

    if not existentes:
        return tuple(CATEGORIAS_DESPESA_PADRAO)

    permitidas = set(CATEGORIAS_DESPESA_PADRAO)
    labels = [nome for nome in existentes if nome in permitidas]

    return tuple(labels or [CATEGORIA_OUTROS])


def _categorias_despesa_labels() -> list[str]:
    """Retorna categorias sem repetir consultas ao banco."""
    try:
        return list(_categorias_despesa_labels_cache())
    except Exception:
        logger.exception("Não foi possível carregar categorias padrão.")
        return CATEGORIAS_DESPESA_PADRAO.copy()


@lru_cache(maxsize=4)
def _obter_cliente_huggingface(token: str, timeout: float):
    """Reutiliza o cliente da API em vez de recriá-lo por transação."""
    from huggingface_hub import InferenceClient

    return InferenceClient(token=token, timeout=timeout)


def _por_huggingface(descricao: str) -> SugestaoCategoria | None:
    token = getattr(settings, "HUGGINGFACE_API_TOKEN", "")

    if not token or not descricao:
        return None

    labels = _categorias_despesa_labels()
    descricao_normalizada = _normalizar(descricao)

    cache_key = (
        "hf_categoria:v3:"
        + hashlib.sha256(
            (
                descricao_normalizada
                + "|"
                + "|".join(labels)
            ).encode("utf-8")
        ).hexdigest()
    )

    cached = cache.get(cache_key)
    if cached:
        return SugestaoCategoria(**cached)

    timeout = float(
        getattr(settings, "HUGGINGFACE_TIMEOUT_SECONDS", 5)
    )
    timeout = max(1.0, min(timeout, 15.0))

    try:
        cliente = _obter_cliente_huggingface(token, timeout)

        resultado = cliente.zero_shot_classification(
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
            {
                "nome_categoria": sugestao.nome_categoria,
                "confianca": sugestao.confianca,
                "origem": sugestao.origem,
            },
            timeout=60 * 60 * 24 * 7,
        )

        return sugestao

    except Exception:
        logger.warning(
            "Falha ao classificar transação via Hugging Face. "
            "A importação continuará sem a classificação por IA.",
            exc_info=True,
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

    # 1. Regras locais: não precisam de chamadas externas.
    sugestao = _por_regras(descricao, tipo)
    if sugestao:
        return sugestao

    # 2. Transferências e pagamentos genéricos não revelam a finalidade.
    if (
        _corresponde_a_algum_padrao(
            descricao_normalizada,
            PADROES_TRANSFERENCIA_GENERICA,
        )
        or _corresponde_a_algum_padrao(
            descricao_normalizada,
            PADROES_BOLETO_GENERICO,
        )
    ):
        return SugestaoCategoria(
            nome_categoria=CATEGORIA_OUTROS,
            confianca="baixa",
            origem="padrao",
        )

    # 3. A IA é usada apenas para despesas sem regra específica.
    if tipo == "despesa":
        sugestao = _por_huggingface(descricao)
        if sugestao:
            return sugestao

    return SugestaoCategoria(
        nome_categoria=CATEGORIA_OUTROS,
        confianca="baixa",
        origem="padrao",
    )
