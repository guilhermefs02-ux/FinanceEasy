"""Cliente da API HG Brasil Finance (https://hgbrasil.com/finance/).

Usado na página inicial após o login. Consulta cotações, bolsas e taxas
financeiras, mantendo os resultados em cache para reduzir requisições.

O cache é configurado por HGBRASIL_CACHE_TTL_SECONDS e usa 300 segundos
(cinco minutos) como padrão.
"""

from __future__ import annotations

import logging

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

CACHE_KEY = "hgbrasil_finance_data"

MOEDAS_DESEJADAS = {
    "USD": "Dólar americano",
    "EUR": "Euro",
    "GBP": "Libra esterlina",
    "ARS": "Peso argentino",
}


def _dados_indisponiveis(motivo: str) -> dict:
    """Monta uma resposta segura quando a consulta não está disponível."""
    return {
        "disponivel": False,
        "motivo_indisponivel": motivo,
        "moedas": [],
        "bolsas": [],
        "taxas": {},
        "atualizado_em": None,
    }


def obter_dados_financeiros() -> dict:
    """Retorna cotações e indicadores financeiros para o dashboard.

    Estrutura retornada:
        {
            "disponivel": bool,
            "motivo_indisponivel": str | None,
            "moedas": [
                {
                    "nome": str,
                    "codigo": str,
                    "compra": float | None,
                    "venda": float | None,
                    "variacao": float | None,
                }
            ],
            "bolsas": [{"nome": str, "pontos": float, "variacao": float}],
            "taxas": {"selic": float, "cdi": float},
            "atualizado_em": str | None,
        }

    Nunca propaga exceções para a página do dashboard.
    """
    cached = cache.get(CACHE_KEY)
    if cached is not None:
        return cached

    api_key = getattr(settings, "HGBRASIL_API_KEY", "")
    if not api_key:
        return _dados_indisponiveis(
            "As cotações estão indisponíveis no momento. "
            "Verifique a configuração da integração HG Brasil."
        )

    try:
        resposta = requests.get(
            settings.HGBRASIL_API_URL,
            params={"key": api_key},
            timeout=6,
        )
        resposta.raise_for_status()
        bruto = resposta.json()

        if not isinstance(bruto, dict):
            raise ValueError("Resposta inválida da API HG Brasil.")

        resultados = bruto.get("results") or {}
        if not isinstance(resultados, dict):
            raise ValueError("Formato de resultados inválido.")

        # Seleciona apenas as quatro moedas desejadas, na ordem definida.
        currencies = resultados.get("currencies") or {}
        moedas = []

        for codigo, nome in MOEDAS_DESEJADAS.items():
            dados = currencies.get(codigo)

            if not isinstance(dados, dict):
                continue

            moedas.append(
                {
                    "codigo": codigo,
                    "nome": nome,
                    "compra": dados.get("buy"),
                    "venda": dados.get("sell"),
                    "variacao": dados.get("variation"),
                }
            )

        # Mantém a seleção de bolsas disponível no código original.
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

        # Extrai as taxas Selic e CDI.
        taxas_raw = resultados.get("taxes") or []
        taxas = {}

        for item in taxas_raw:
            if not isinstance(item, dict):
                continue

            nome_taxa = (item.get("name") or "").lower()

            if "selic" in nome_taxa:
                taxas["selic"] = item.get("value")
            elif "cdi" in nome_taxa:
                taxas["cdi"] = item.get("value")

        dados_finais = {
            "disponivel": True,
            "motivo_indisponivel": None,
            "moedas": moedas,
            "bolsas": bolsas[:4],
            "taxas": taxas,
            "atualizado_em": (
                resultados.get("last_updated")
                or bruto.get("execution_time")
            ),
        }

        tempo_cache = getattr(
            settings,
            "HGBRASIL_CACHE_TTL_SECONDS",
            300,
        )

        cache.set(
            CACHE_KEY,
            dados_finais,
            timeout=tempo_cache,
        )

        return dados_finais

    except Exception:
        logger.exception("Falha ao consultar a API HG Brasil Finance")
        return _dados_indisponiveis(
            "Não conseguimos buscar as cotações agora. "
            "Tente novamente em instantes."
        )
