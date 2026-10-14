"""Categorização automática de transações importadas (UC04, passo 7 e
UC05). Duas camadas, da mais barata para a mais cara:

1. **Regras por palavra-chave** — cobre os exemplos citados no caso de uso
   (IFOOD/PADARIA, POSTO/UBER, NETFLIX/SPOTIFY, SABESP/ENEL, ...) com
   confiança "alta" e sem nenhuma chamada de rede.
2. **Hugging Face Inference API** (zero-shot-classification) — usada
   apenas quando nenhuma regra bate. Chamada de biblioteca real ao
   ecossistema Hugging Face (`huggingface_hub`), conforme pedido na
   arquitetura. Exige um token gratuito em HUGGINGFACE_API_TOKEN (veja
   README.md); sem token, ou se a chamada falhar, cai para "Outros" com
   confiança baixa — o usuário sempre consegue reclassificar na tela de
   conciliação (UC05).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# (padrão regex sobre a descrição em maiúsculas) -> nome da categoria de despesa
REGRAS_PALAVRA_CHAVE = [
    (r"\bIFOOD\b|\bRAPPI\b|\bPADARIA\b|\bMERCADO\b|\bSUPERMERCADO\b|\bACOUGUE\b|\bHORTIFRUTI\b", "Alimentação/Supermercado"),
    (r"\bRESTAURANTE\b|\bLANCHONETE\b|\bPIZZARIA\b|\bBURGER\b|\bMCDONALD|\bBURGER\s?KING", "Alimentação/Supermercado"),
    (r"\bPOSTO\b|\bUBER\b|\b99\s?POP\b|\b99APP\b|\bCOMBUSTIVEL\b|\bESTACIONAMENTO\b|\bPEDAGIO\b|\bBILHETE\s?UNICO\b", "Transporte"),
    (r"\bNETFLIX\b|\bSPOTIFY\b|\bDISNEY\b|\bHBO\b|\bAMAZON\s?PRIME\b|\bYOUTUBE\s?PREMIUM\b|\bDEEZER\b|\bPARAMOUNT\b", "Assinaturas"),
    (r"\bSABESP\b|\bENEL\b|\bCPFL\b|\bCEMIG\b|\bLIGHT\b|\bCOPEL\b|\bCOMGAS\b|\bALUGUEL\b|\bCONDOMINIO\b|\bIPTU\b", "Moradia/Casa"),
    (r"\bFARMACIA\b|\bDROGARIA\b|\bDROGASIL\b|\bPACHECO\b", "Outros"),
    (r"\bFACULDADE\b|\bESCOLA\b|\bCURSO\b|\bUDEMY\b|\bALURA\b|\bLIVRARIA\b", "Educação"),
    (r"\bCINEMA\b|\bINGRESSO\b|\bSHOW\b|\bSTEAM\b|\bPLAYSTATION\b|\bXBOX\b", "Lazer"),
]

# Origens de receita reconhecidas em extratos (UC04, o sistema também
# pré-categoriza valores positivos).
REGRAS_RECEITA = [
    (r"\bSALARIO\b|\bFOLHA\s?DE\s?PAGAMENTO\b|\bPGTO\s?SAL", "Salário"),
    (r"\bPIX\s?RECEBIDO\b|\bTED\s?RECEBID", "Outros"),
]


@dataclass
class SugestaoCategoria:
    nome_categoria: str
    confianca: str  # "alta" ou "baixa"
    origem: str  # "regra" | "huggingface" | "padrao"


def _por_regras(descricao: str, tipo: str) -> SugestaoCategoria | None:
    descricao_upper = (descricao or "").upper()
    regras = REGRAS_RECEITA if tipo == "receita" else REGRAS_PALAVRA_CHAVE
    for padrao, categoria in regras:
        if re.search(padrao, descricao_upper):
            return SugestaoCategoria(categoria, "alta", "regra")
    return None


def _categorias_despesa_labels():
    from transactions.models import Category

    return list(
        Category.objects.filter(tipo="despesa").values_list("nome", flat=True)
    ) or ["Outros"]


def _por_huggingface(descricao: str) -> SugestaoCategoria | None:
    token = getattr(settings, "HUGGINGFACE_API_TOKEN", "")
    if not token or not descricao:
        return None

    cache_key = f"hf_categoria:{descricao.strip().lower()}"
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
            model=getattr(settings, "HUGGINGFACE_ZERO_SHOT_MODEL", None),
        )
        # huggingface_hub retorna uma lista de objetos {label, score} ordenada
        melhor = resultado[0] if resultado else None
        if not melhor:
            return None

        score = float(melhor.score if hasattr(melhor, "score") else melhor["score"])
        label = melhor.label if hasattr(melhor, "label") else melhor["label"]
        confianca = "alta" if score >= 0.55 else "baixa"
        sugestao = SugestaoCategoria(label, confianca, "huggingface")
        cache.set(cache_key, sugestao.__dict__, timeout=60 * 60 * 24 * 7)
        return sugestao
    except Exception:
        logger.exception("Falha ao classificar transação via Hugging Face Inference API")
        return None


def sugerir_categoria(descricao: str, tipo: str = "despesa") -> SugestaoCategoria:
    """Ponto de entrada usado pelo importador (UC04/UC05)."""
    sugestao = _por_regras(descricao, tipo)
    if sugestao:
        return sugestao

    if tipo == "despesa":
        sugestao = _por_huggingface(descricao)
        if sugestao:
            return sugestao

    return SugestaoCategoria("Outros", "baixa", "padrao")
