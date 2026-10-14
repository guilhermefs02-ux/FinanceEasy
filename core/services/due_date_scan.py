"""UC14 — Varredura diária automática de vencimentos.

Roda todo dia às 08h00 (management command `varredura_vencimentos`, veja
core/management/commands/) e também de forma preguiçosa no primeiro
acesso do dia de cada usuário (core/middleware.py), gerando avisos
preventivos sem tom acusatório para contas fixas (RecurringBill) e
parcelas de dívidas (Debt) que vencem em D+5, D+2 ou hoje (D=0).
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta

from core.models import Notification

DIAS_DE_AVISO = (5, 2, 0)


def _proxima_data_vencimento(dia_vencimento: int, referencia: date) -> date:
    """Encontra a próxima ocorrência (neste mês ou no próximo) do dia de
    vencimento informado, lidando com meses mais curtos (ex.: dia 31 em
    fevereiro cai no último dia do mês)."""
    ano, mes = referencia.year, referencia.month
    for _ in range(2):
        ultimo_dia_mes = calendar.monthrange(ano, mes)[1]
        dia = min(dia_vencimento, ultimo_dia_mes)
        candidata = date(ano, mes, dia)
        if candidata >= referencia:
            return candidata
        mes += 1
        if mes > 12:
            mes = 1
            ano += 1
    return candidata  # fallback, não deve acontecer


def _mensagem_conta(nome: str, valor, dias_restantes: int) -> str:
    valor_fmt = f"R$ {valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    if dias_restantes == 0:
        return f"Hoje vence a sua conta de {nome} ({valor_fmt}). Se já pagou, pode ignorar este aviso."
    if dias_restantes == 2:
        return f"Sua conta de {nome} ({valor_fmt}) vence depois de amanhã. Que tal conferir sua folga de segurança?"
    return f"Sua conta de {nome} ({valor_fmt}) vence em {dias_restantes} dias. Ainda dá tempo de se planejar."


def _mensagem_divida(divida) -> str:
    valor_fmt = f"R$ {divida.valor_parcela:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    dias = (_proxima_data_vencimento(divida.dia_vencimento, date.today()) - date.today()).days
    if dias == 0:
        return (
            f"Hoje vence a sua parcela de {divida.credor} ({valor_fmt}). "
            "Se já pagou, confirme no app para manter seu saldo certinho."
        )
    if dias == 2:
        return f"A parcela de {divida.credor} ({valor_fmt}) vence depois de amanhã."
    return f"A parcela de {divida.credor} ({valor_fmt}) vence em {dias} dias."


def run_scan_for_user(user) -> int:
    """Executa a varredura para um único usuário. Retorna quantas
    notificações novas foram criadas."""
    hoje = date.today()
    criadas = 0

    contas = user.recorrencias.filter(ativo=True)
    for conta in contas:
        vencimento = _proxima_data_vencimento(conta.dia_vencimento, hoje)
        dias_restantes = (vencimento - hoje).days
        if dias_restantes not in DIAS_DE_AVISO:
            continue
        chave = f"conta:{conta.pk}:{vencimento.isoformat()}"
        _, criado = Notification.objects.get_or_create(
            usuario=user,
            chave_deduplicacao=chave,
            defaults={
                "mensagem": _mensagem_conta(conta.nome_servico, conta.valor, dias_restantes),
                "nivel": Notification.Nivel.URGENTE if dias_restantes == 0 else Notification.Nivel.ALERTA,
            },
        )
        criadas += int(criado)

    dividas = user.dividas.filter(quitada=False)
    for divida in dividas:
        vencimento = _proxima_data_vencimento(divida.dia_vencimento, hoje)
        dias_restantes = (vencimento - hoje).days
        if dias_restantes not in DIAS_DE_AVISO:
            continue
        chave = f"divida:{divida.pk}:{vencimento.isoformat()}"
        _, criado = Notification.objects.get_or_create(
            usuario=user,
            chave_deduplicacao=chave,
            defaults={
                "mensagem": _mensagem_divida(divida),
                "nivel": Notification.Nivel.URGENTE if dias_restantes == 0 else Notification.Nivel.ALERTA,
            },
        )
        criadas += int(criado)

    return criadas


def run_scan_for_all_users() -> int:
    """Usado pelo management command (agendador do SO, 08h00)."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    total = 0
    for user in User.objects.filter(is_active=True):
        total += run_scan_for_user(user)
    return total
