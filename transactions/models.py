from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import redirect, render

from goals.models import Goal
from transactions.models import RecurringBill, Transaction

from .services.hgbrasil import obter_dados_financeiros


def _inicio_fim_mes(referencia: date):
    inicio = referencia.replace(day=1)

    if referencia.month == 12:
        fim = date(referencia.year + 1, 1, 1) - timedelta(days=1)
    else:
        fim = date(referencia.year, referencia.month + 1, 1) - timedelta(days=1)

    return inicio, fim


def _data_valida_vencimento(ano, mes, dia):
    """Ajusta o dia para o último dia do mês quando necessário."""
    if mes == 12:
        primeiro_dia_mes_seguinte = date(ano + 1, 1, 1)
    else:
        primeiro_dia_mes_seguinte = date(ano, mes + 1, 1)

    ultimo_dia = (primeiro_dia_mes_seguinte - timedelta(days=1)).day
    return date(ano, mes, min(dia, ultimo_dia))


def _proximo_vencimento_conta(conta, hoje):
    """Calcula a próxima data de vencimento de uma conta fixa."""
    if conta.periodicidade == RecurringBill.Periodicidade.ANUAL:
        mes = conta.mes_vencimento

        # Não inventa um vencimento para contas anuais sem mês cadastrado.
        if not mes:
            return None

        vencimento = _data_valida_vencimento(
            hoje.year,
            mes,
            conta.dia_vencimento,
        )

        if vencimento < hoje:
            vencimento = _data_valida_vencimento(
                hoje.year + 1,
                mes,
                conta.dia_vencimento,
            )

        return vencimento

    vencimento = _data_valida_vencimento(
        hoje.year,
        hoje.month,
        conta.dia_vencimento,
    )

    if vencimento < hoje:
        if hoje.month == 12:
            ano_seguinte, mes_seguinte = hoje.year + 1, 1
        else:
            ano_seguinte, mes_seguinte = hoje.year, hoje.month + 1

        vencimento = _data_valida_vencimento(
            ano_seguinte,
            mes_seguinte,
            conta.dia_vencimento,
        )

    return vencimento


def _proximas_contas(user, dias_janela=7):
    """Busca contas fixas e parcelas de dívidas próximas do vencimento."""
    hoje = date.today()
    limite = hoje + timedelta(days=dias_janela)
    itens = []

    for conta in user.recorrencias.filter(ativo=True):
        vencimento = _proximo_vencimento_conta(conta, hoje)

        if vencimento is None or not hoje <= vencimento <= limite:
            continue

        # A conta anual deve exibir o valor integral do vencimento.
        # A mensal exibe o valor mensal cadastrado.
        valor_vencimento = conta.valor

        itens.append(
            {
                "tipo": "conta",
                "nome": conta.nome_servico,
                "valor": valor_vencimento,
                "vencimento": vencimento,
                "categoria": conta.categoria,
            }
        )

    # Mantém o cálculo de vencimentos das dívidas separado das contas fixas.
    from core.services.due_date_scan import _proxima_data_vencimento

    for divida in user.dividas.filter(quitada=False):
        vencimento = _proxima_data_vencimento(
            divida.dia_vencimento,
            hoje,
        )

        if hoje <= vencimento <= limite:
            itens.append(
                {
                    "tipo": "divida",
                    "nome": divida.credor,
                    "valor": divida.valor_parcela,
                    "vencimento": vencimento,
                    "categoria": None,
                }
            )

    itens.sort(key=lambda item: item["vencimento"])
    return itens


@login_required
def painel(request):
    hoje = date.today()
    inicio_mes, fim_mes = _inicio_fim_mes(hoje)

    transacoes_mes = Transaction.objects.filter(
        usuario=request.user,
        status=Transaction.Status.CONFIRMADA,
        data__range=[inicio_mes, fim_mes],
    )

    total_receitas = (
        transacoes_mes.filter(
            tipo=Transaction.Tipo.RECEITA,
        ).aggregate(total=Sum("valor"))["total"]
        or Decimal("0")
    )

    total_despesas = (
        transacoes_mes.filter(
            tipo=Transaction.Tipo.DESPESA,
        ).aggregate(total=Sum("valor"))["total"]
        or Decimal("0")
    )

    receitas_confirmadas = (
        Transaction.objects.filter(
            usuario=request.user,
            status=Transaction.Status.CONFIRMADA,
            tipo=Transaction.Tipo.RECEITA,
        ).aggregate(total=Sum("valor"))["total"]
        or Decimal("0")
    )

    despesas_confirmadas = (
        Transaction.objects.filter(
            usuario=request.user,
            status=Transaction.Status.CONFIRMADA,
            tipo=Transaction.Tipo.DESPESA,
        ).aggregate(total=Sum("valor"))["total"]
        or Decimal("0")
    )

    saldo_disponivel = receitas_confirmadas - despesas_confirmadas

    proximas_contas = _proximas_contas(
        request.user,
        dias_janela=7,
    )

    total_a_vencer_7_dias = sum(
        (item["valor"] for item in proximas_contas),
        start=Decimal("0"),
    )

    sobra_segura = saldo_disponivel - total_a_vencer_7_dias

    top_categorias = (
        transacoes_mes.filter(
            tipo=Transaction.Tipo.DESPESA,
        )
        .values(
            "categoria__nome",
            "categoria__cor",
            "categoria__icone",
        )
        .annotate(total=Sum("valor"))
        .order_by("-total")[:3]
    )

    maior_categoria_total = max(
        (categoria["total"] for categoria in top_categorias),
        default=Decimal("0"),
    )

    dados_hgbrasil = obter_dados_financeiros()

    colchao = Goal.objects.filter(
        usuario=request.user,
        is_colchao_padrao=True,
    ).first()

    objetivos = list(
        Goal.objects.filter(
            usuario=request.user,
        ).order_by(
            "-is_colchao_padrao",
            "criado_em",
        )
    )

    total_acumulado_objetivos = Decimal("0")

    for objetivo in objetivos:
        acumulado = objetivo.valor_acumulado

        objetivo.valor_restante = max(
            objetivo.valor_alvo - acumulado,
            Decimal("0"),
        )

        objetivo._acumulado_ordem = acumulado
        total_acumulado_objetivos += acumulado

    objetivos.sort(
        key=lambda objetivo: (
            not objetivo.is_colchao_padrao,
            -objetivo._acumulado_ordem,
            objetivo.criado_em,
        )
    )

    receitas_detalhes = Transaction.objects.filter(
        usuario=request.user,
        tipo=Transaction.Tipo.RECEITA,
        data__range=[inicio_mes, fim_mes],
        status=Transaction.Status.CONFIRMADA,
    ).order_by("-data")

    despesas_detalhes = Transaction.objects.filter(
        usuario=request.user,
        tipo=Transaction.Tipo.DESPESA,
        data__range=[inicio_mes, fim_mes],
        status=Transaction.Status.CONFIRMADA,
    ).order_by("-data")

    contexto = {
        "total_receitas": total_receitas,
        "total_despesas": total_despesas,
        "saldo_disponivel": saldo_disponivel,
        "sobra_segura": sobra_segura,
        "proximas_contas": proximas_contas,
        "top_categorias": top_categorias,
        "maior_categoria_total": maior_categoria_total,
        "hgbrasil": dados_hgbrasil,
        "colchao": colchao,
        "objetivos": objetivos,
        "total_acumulado_objetivos": total_acumulado_objetivos,
        "mes_referencia": hoje,
        "receitas_detalhes": receitas_detalhes,
        "despesas_detalhes": despesas_detalhes,
    }

    return render(
        request,
        "dashboard/painel.html",
        contexto,
    )


@login_required
def alternar_privacidade(request):
    """FA01 — Modo Privacidade ('Olho Fechado'), RNF13."""
    if request.method == "POST":
        atual = request.session.get("privacy_mode_on", False)
        request.session["privacy_mode_on"] = not atual

    proximo = request.META.get("HTTP_REFERER") or "dashboard:painel"
    return redirect(proximo)


@login_required
def marcar_notificacoes_lidas(request):
    if request.method == "POST":
        request.user.notificacoes.filter(lida=False).update(lida=True)

    proximo = request.META.get("HTTP_REFERER") or "dashboard:painel"
    return redirect(proximo)
