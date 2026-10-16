from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import F, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from goals.models import Goal
from transactions.models import RecurringBillPayment, Transaction

from .services.hgbrasil import obter_dados_financeiros


MESES = [
    {"numero": 1, "nome": "Janeiro"},
    {"numero": 2, "nome": "Fevereiro"},
    {"numero": 3, "nome": "Março"},
    {"numero": 4, "nome": "Abril"},
    {"numero": 5, "nome": "Maio"},
    {"numero": 6, "nome": "Junho"},
    {"numero": 7, "nome": "Julho"},
    {"numero": 8, "nome": "Agosto"},
    {"numero": 9, "nome": "Setembro"},
    {"numero": 10, "nome": "Outubro"},
    {"numero": 11, "nome": "Novembro"},
    {"numero": 12, "nome": "Dezembro"},
]


def _inicio_fim_mes(referencia: date):
    inicio = referencia.replace(day=1)

    if referencia.month == 12:
        fim = date(referencia.year + 1, 1, 1) - timedelta(days=1)
    else:
        fim = date(
            referencia.year,
            referencia.month + 1,
            1,
        ) - timedelta(days=1)

    return inicio, fim


def _data_valida_vencimento(ano, mes, dia):
    """Ajusta o vencimento para o último dia do mês, quando necessário."""
    ultimo_dia = monthrange(ano, mes)[1]
    return date(ano, mes, min(dia, ultimo_dia))


def _vencimento_referencia_conta(conta, hoje):
    """Retorna o vencimento da competência atual da conta recorrente."""
    if conta.periodicidade == "anual":
        mes = conta.mes_vencimento

        if not mes:
            return None

        return _data_valida_vencimento(
            hoje.year,
            mes,
            conta.dia_vencimento,
        )

    return _data_valida_vencimento(
        hoje.year,
        hoje.month,
        conta.dia_vencimento,
    )


def _vencimento_referencia_divida(divida, hoje):
    """
    Retorna o vencimento da dívida na competência atual.

    Como o modelo Debt não armazena o vencimento individual de cada
    parcela, utiliza o dia de vencimento cadastrado e o histórico
    de pagamentos como referência.
    """
    if divida.quitada or divida.parcelas_restantes <= 0:
        return None

    vencimento = _data_valida_vencimento(
        hoje.year,
        hoje.month,
        divida.dia_vencimento,
    )

    criada_em = timezone.localtime(divida.criado_em).date()

    if (
        criada_em.year == hoje.year
        and criada_em.month == hoje.month
        and criada_em > vencimento
        and divida.parcelas_pagas == 0
    ):
        return None

    pagamento_no_mes = divida.pagamentos.filter(
        data_pagamento__year=hoje.year,
        data_pagamento__month=hoje.month,
    ).exists()

    if pagamento_no_mes:
        return None

    return vencimento


def _central_de_avisos(user, dias_janela=7):
    """
    Centraliza os avisos de contas recorrentes e dívidas em aberto.
    """
    hoje = timezone.localdate()
    limite = hoje + timedelta(days=dias_janela)

    avisos_vencidos = []
    avisos_a_vencer = []

    # Contas recorrentes mensais e anuais.
    for conta in user.recorrencias.filter(ativo=True):
        vencimento = _vencimento_referencia_conta(conta, hoje)

        if vencimento is None:
            continue

        pagamento, _ = conta.pagamentos.get_or_create(
            data_vencimento=vencimento,
            defaults={
                "valor": conta.valor,
                "status": "pendente",
            },
        )

        if pagamento.status == "pago":
            continue

        item = {
            "tipo": "conta",
            "periodicidade": conta.periodicidade,
            "nome": conta.nome_servico,
            "valor": pagamento.valor,
            "vencimento": vencimento,
            "categoria": conta.categoria,
            "conta": conta,
            "pagamento": pagamento,
        }

        if vencimento < hoje:
            avisos_vencidos.append(item)
        elif vencimento <= limite:
            avisos_a_vencer.append(item)

    # Dívidas com parcelas restantes.
    dividas = (
        user.dividas.filter(
            quitada=False,
            parcelas_pagas__lt=F("total_parcelas"),
        )
        .prefetch_related("pagamentos")
    )

    for divida in dividas:
        vencimento = _vencimento_referencia_divida(divida, hoje)

        if vencimento is None:
            continue

        item = {
            "tipo": "divida",
            "periodicidade": "parcela",
            "nome": divida.credor,
            "valor": divida.valor_parcela,
            "vencimento": vencimento,
            "categoria": None,
            "conta": None,
            "pagamento": None,
            "divida": divida,
        }

        if vencimento < hoje:
            avisos_vencidos.append(item)
        elif vencimento <= limite:
            avisos_a_vencer.append(item)

    avisos_vencidos.sort(key=lambda item: item["vencimento"])
    avisos_a_vencer.sort(key=lambda item: item["vencimento"])

    return {
        "vencidos": avisos_vencidos,
        "a_vencer": avisos_a_vencer,
        "total_vencidos": len(avisos_vencidos),
        "total_a_vencer": len(avisos_a_vencer),
        "total_avisos": len(avisos_vencidos) + len(avisos_a_vencer),
    }


def _contexto_avisos(user):
    """Monta os dados compartilhados pela Central de Avisos e pelo painel."""
    central_avisos = _central_de_avisos(user, dias_janela=7)

    return {
        "central_avisos": central_avisos,
        "avisos_vencidos": central_avisos["vencidos"],
        "avisos_a_vencer": central_avisos["a_vencer"],
        "total_vencidos": central_avisos["total_vencidos"],
        "total_a_vencer": central_avisos["total_a_vencer"],
        "total_avisos": central_avisos["total_avisos"],
    }


def _inteiro_get_valido(valor, padrao, minimo, maximo):
    """Converte um parâmetro GET em inteiro dentro dos limites permitidos."""
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        return padrao

    if minimo <= numero <= maximo:
        return numero

    return padrao


@login_required
def painel(request):
    hoje = timezone.localdate()

    mes_selecionado = _inteiro_get_valido(
        request.GET.get("mes"),
        hoje.month,
        1,
        12,
    )

    ano_selecionado = _inteiro_get_valido(
        request.GET.get("ano"),
        hoje.year,
        2000,
        2100,
    )

    mes_referencia = date(
        ano_selecionado,
        mes_selecionado,
        1,
    )

    inicio_mes, fim_mes = _inicio_fim_mes(mes_referencia)

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

    # Mantém os avisos no cálculo da sobra segura e nos indicadores do painel.
    dados_avisos = _contexto_avisos(request.user)
    avisos_a_vencer = dados_avisos["avisos_a_vencer"]

    total_a_vencer_7_dias = sum(
        (item["valor"] for item in avisos_a_vencer),
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
        (
            categoria["total"]
            for categoria in top_categorias
        ),
        default=Decimal("0"),
    )

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

    receitas_detalhes = transacoes_mes.filter(
        tipo=Transaction.Tipo.RECEITA,
    ).order_by("-data")

    despesas_detalhes = transacoes_mes.filter(
        tipo=Transaction.Tipo.DESPESA,
    ).order_by("-data")

    primeiro_ano_transacao = (
        Transaction.objects.filter(
            usuario=request.user,
        )
        .order_by("data")
        .values_list("data__year", flat=True)
        .first()
    )

    ano_inicial = min(
        primeiro_ano_transacao or hoje.year,
        hoje.year,
    )

    anos_disponiveis = list(
        range(ano_inicial, hoje.year + 1)
    )

    if ano_selecionado not in anos_disponiveis:
        anos_disponiveis.append(ano_selecionado)
        anos_disponiveis.sort()

    contexto = {
        "total_receitas": total_receitas,
        "total_despesas": total_despesas,
        "saldo_disponivel": saldo_disponivel,
        "sobra_segura": sobra_segura,
        **dados_avisos,
        "top_categorias": top_categorias,
        "maior_categoria_total": maior_categoria_total,
        "colchao": colchao,
        "objetivos": objetivos,
        "total_acumulado_objetivos": total_acumulado_objetivos,
        "mes_referencia": mes_referencia,
        "mes_selecionado": mes_selecionado,
        "ano_selecionado": ano_selecionado,
        "meses_disponiveis": MESES,
        "anos_disponiveis": anos_disponiveis,
        "receitas_detalhes": receitas_detalhes,
        "despesas_detalhes": despesas_detalhes,
    }

    return render(
        request,
        "dashboard/painel.html",
        contexto,
    )


@login_required
def avisos(request):
    """Exibe a Central de Avisos em uma página independente."""
    contexto = _contexto_avisos(request.user)
    contexto["privacy_mode_on"] = request.session.get(
        "privacy_mode_on",
        False,
    )

    return render(
        request,
        "dashboard/avisos.html",
        contexto,
    )


@login_required
def mercado(request):
    """Exibe indicadores financeiros em uma página independente."""
    dados_hgbrasil = obter_dados_financeiros()

    return render(
        request,
        "dashboard/mercado.html",
        {
            "hgbrasil": dados_hgbrasil,
        },
    )


@login_required
@require_POST
def marcar_conta_paga(request, pagamento_id):
    """Marca como paga somente a ocorrência selecionada."""
    pagamento = get_object_or_404(
        RecurringBillPayment.objects.select_related("conta"),
        pk=pagamento_id,
        conta__usuario=request.user,
    )

    if pagamento.status != "pago":
        pagamento.status = "pago"
        pagamento.pago_em = timezone.now()
        pagamento.save(update_fields=["status", "pago_em"])

    return redirect("dashboard:avisos")


@login_required
def alternar_privacidade(request):
    """Alterna o modo de privacidade do painel."""
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
