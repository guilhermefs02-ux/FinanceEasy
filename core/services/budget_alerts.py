"""UC06 — Disparar Alerta Preventivo de Limite de Categoria.

Chamado sempre que uma despesa é confirmada (lançamento manual — UC03 —
ou aprovação em lote da conciliação — UC05). Quando o total do mês na
categoria atinge 80% do teto definido pelo usuário, gera um card de aviso
amigável e uma notificação (para o sino do topo).
"""

from __future__ import annotations

from datetime import date

from django.db.models import Sum

from core.models import Notification

LIMIAR_ALERTA = 0.8


def _dias_restantes_no_ciclo(hoje: date) -> int:
    if hoje.month == 12:
        proximo_mes = date(hoje.year + 1, 1, 1)
    else:
        proximo_mes = date(hoje.year, hoje.month + 1, 1)
    return (proximo_mes - hoje).days


def verificar_limite_categoria(user, categoria):
    """Retorna um dict com o aviso (ou None se não há teto ou não atingiu
    80%) e, como efeito colateral, garante que exista uma notificação
    deduplicada por usuário+categoria+mês."""
    from transactions.models import CategoryBudget, Transaction

    try:
        orcamento = CategoryBudget.objects.get(usuario=user, categoria=categoria)
    except CategoryBudget.DoesNotExist:
        return None

    hoje = date.today()
    total_mes = (
        Transaction.objects.filter(
            usuario=user,
            categoria=categoria,
            tipo=Transaction.Tipo.DESPESA,
            status=Transaction.Status.CONFIRMADA,
            data__year=hoje.year,
            data__month=hoje.month,
        ).aggregate(total=Sum("valor"))["total"]
        or 0
    )

    if orcamento.teto_mensal <= 0:
        return None

    percentual = float(total_mes) / float(orcamento.teto_mensal)
    if percentual < LIMIAR_ALERTA:
        return None

    dias_restantes = _dias_restantes_no_ciclo(hoje)
    percentual_exibicao = min(round(percentual * 100), 999)
    mensagem = (
        f"Aviso amigável: os seus gastos em {categoria.nome} atingiram "
        f"{percentual_exibicao}% do planejado para o mês. Ainda faltam "
        f"{dias_restantes} dias para o fim do ciclo."
    )

    chave = f"orcamento:{categoria.pk}:{hoje.year}-{hoje.month:02d}"
    Notification.objects.get_or_create(
        usuario=user,
        chave_deduplicacao=chave,
        defaults={"mensagem": mensagem, "nivel": Notification.Nivel.ALERTA},
    )

    return {
        "categoria": categoria,
        "percentual": percentual_exibicao,
        "dias_restantes": dias_restantes,
        "mensagem": mensagem,
        "total_mes": total_mes,
        "teto_mensal": orcamento.teto_mensal,
    }
