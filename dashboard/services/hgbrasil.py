"""Cliente da API HG Brasil Finance (https://hgbrasil.com/finance/),
usada na página inicial após o login (UC08), conforme exigido pela
arquitetura do projeto.

Plano gratuito: 400 requisições/dia. Por isso o resultado fica em cache
por HGBRASIL_CACHE_TTL_SECONDS (15 minutos por padrão — mesmo intervalo
de atualização das cotações informado pela própria HG Brasil), evitando
estourar a cota mesmo com vários usuários abrindo o painel.
"""

from __future__ import annotations

import logging

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

CACHE_KEY = "hgbrasil_finance_data"


class HGBrasilIndisponivel(Exception):
    pass


def obter_dados_financeiros() -> dict:
    """Retorna um dict pronto para o template do dashboard:

        {
            "disponivel": bool,
            "motivo_indisponivel": str | None,
            "moedas": [{"nome", "codigo", "compra", "venda", "variacao"}],
            "bolsas": [{"nome", "pontos", "variacao"}],
            "taxas": {"selic": float, "cdi": float},
            "atualizado_em": str,
        }

    Nunca levanta exceção: se a chave não estiver configurada ou a API
    falhar, devolve disponivel=False com um motivo amigável, para o
    dashboard seguir funcionando normalmente (RNF06 — disponibilidade).
    """
    cached = cache.get(CACHE_KEY)
    if cached:
        return cached

    api_key = getattr(settings, "HGBRASIL_API_KEY", "")
    if not api_key:
        return {
            "disponivel": False,
            "motivo_indisponivel": (
                "Configure HGBRASIL_API_KEY no arquivo .env para ver cotações "
                "em tempo real aqui (veja o README.md)."
            ),
            "moedas": [],
            "bolsas": [],
            "taxas": {},
            "atualizado_em": None,
        }

    try:
        resposta = requests.get(
            settings.HGBRASIL_API_URL, params={"key": api_key}, timeout=6
        )
        resposta.raise_for_status()
        bruto = resposta.json()
        resultados = bruto.get("results", {})

        moedas = []
        for codigo, dados in (resultados.get("currencies") or {}).items():
            if not isinstance(dados, dict) or codigo.upper() in ["SOURCE", "BRL"]:
                continue
            moedas.append(
                {
                    "codigo": codigo,
                    "nome": dados.get("name", codigo),
                    "compra": dados.get("buy"),
                    "venda": dados.get("sell"),
                    "variacao": dados.get("variation"),
                }
            )

        bolsas = []
        for codigo, dados in (resultados.get("stocks") or {}).items():
            if not isinstance(dados, dict):
                continue
            bolsas.append(
                {
                    "codigo": codigo,
                    "nome": dados.get("name", codigo),
                    "pontos": dados.get("points"),
                    "variacao": dados.get("variation"),
                }
            )

        taxas_raw = resultados.get("taxes") or []
        taxas = {}
        for item in taxas_raw:
            if not isinstance(item, dict):
                continue
            nome = (item.get("name") or "").lower()
            if "selic" in nome:
                taxas["selic"] = item.get("value")
            elif "cdi" in nome:
                taxas["cdi"] = item.get("value")

        dados_finais = {
            "disponivel": True,
            "motivo_indisponivel": None,
            "moedas": moedas[:4],
            "bolsas": bolsas[:4],
            "taxas": taxas,
            "atualizado_em": resultados.get("last_updated") or bruto.get("execution_time"),
        }
        cache.set(CACHE_KEY, dados_finais, timeout=settings.HGBRASIL_CACHE_TTL_SECONDS)
        return dados_finais

    except Exception:
        logger.exception("Falha ao consultar a API HG Brasil Finance")
        return {
            "disponivel": False,
            "motivo_indisponivel": "Não conseguimos buscar as cotações agora. Tente novamente em instantes.",
            "moedas": [],
            "bolsas": [],
            "taxas": {},
            "atualizado_em": None,
        }
