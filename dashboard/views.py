from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from goals.models import Goal
from transactions.models import RecurringBillPayment, Transaction

from .services.hgbrasil import obter_dados_financeiros


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


def _proximo_vencimento_conta(conta, hoje):
    """Calcula o próximo vencimento futuro de uma conta."""
    if conta.periodicidade == "anual":
        mes = conta.mes_vencimento

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
            ano_seguinte = hoje.year + 1
            mes_seguinte = 1
        else:
            ano_seguinte = hoje.year
            mes_seguinte = hoje.month + 1

        vencimento = _data_valida_vencimento(
            ano_seguinte,
            mes_seguinte,
            conta.dia_vencimento,
        )

    return vencimento


def _vencimento_referencia_conta(conta, hoje):
    """
    Retorna o vencimento da competência atual, mesmo se já tiver passado.
    """
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


def _central_de_avisos(user, dias_janela=7):
    """
    Monta a Central de Avisos com contas recorrentes e parcelas de dívidas.

    Cada conta recorrente possui um registro de pagamento por vencimento.
    O valor exibido é o valor integral da conta, inclusive nas anuais.
    """
    hoje = date.today()
    limite = hoje + timedelta(days=dias_janela)

    avisos_vencidos = []
    avisos_a_vencer = []

    # Contas fixas e assinaturas mensais ou anuais.
    for conta in user.recorrencias.filter(ativo=True):
        vencimento = _vencimento_referencia_conta(conta, hoje)

        if vencimento is None:
            continue

        # Cria o registro da ocorrência, se ainda não existir.
        # A restrição única do modelo impede duplicar o mesmo vencimento.
        pagamento, _ = conta.pagamentos.get_or_create(
            data_vencimento=vencimento,
            defaults={
                "valor": conta.valor,
                "status": "pendente",
            },
        )

        # Uma ocorrência paga não aparece como pendente.
        if pagamento.status == "pago":
            continue

        item = {
            "tipo": "conta",
            "periodicidade": conta.periodicidade,
            "nome": conta.nome_servico,
            "valor": conta.valor,
            "vencimento": vencimento,
            "categoria": conta.categoria,
            "conta": conta,
            "pagamento": pagamento,
        }

        if vencimento < hoje:
            avisos_vencidos.append(item)
        elif vencimento <= limite:
            avisos_a_vencer.append(item)

    # Dívidas e parcelas continuam sendo tratadas separadamente.
    from core.services.due_date_scan import _proxima_data_vencimento

    for divida in user.dividas.filter(quitada=False):
        vencimento = _proxima_data_vencimento(
            divida.dia_vencimento,
            hoje,
        )

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

    # Central de Avisos.
    central_avisos = _central_de_avisos(
        request.user,
        dias_janela=7,
    )

    # Apenas avisos futuros entram no cálculo da sobra segura.
    total_a_vencer_7_dias = sum(
        (
            item["valor"]
            for item in central_avisos["a_vencer"]
        ),
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
        "central_avisos": central_avisos,
        "avisos_vencidos": central_avisos["vencidos"],
        "avisos_a_vencer": central_avisos["a_vencer"],
        "total_vencidos": central_avisos["total_vencidos"],
        "total_a_vencer": central_avisos["total_a_vencer"],
        "total_avisos": central_avisos["total_avisos"],
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
@require_POST
def marcar_conta_paga(request, pagamento_id):
    """
    Marca como paga somente a ocorrência de vencimento selecionada.
    Não altera os vencimentos futuros da conta recorrente.
    """
    pagamento = get_object_or_404(
        RecurringBillPayment.objects.select_related("conta"),
        pk=pagamento_id,
        conta__usuario=request.user,
    )

    if pagamento.status != "pago":
        pagamento.status = "pago"
        pagamento.pago_em = timezone.now()
        pagamento.save(update_fields=["status", "pago_em"])

    return redirect("dashboard:painel")


@login_required
def alternar_privacidade(request):
    """Alterna o modo de privacidade do painel."""
    if request.method == "POST":
        atual = request.session.get("privacy_mode_on", False)
        request.session["privacy_mode_on"] = not atual

    proximo = (
        request.META.get("HTTP_REFERER")
        or "dashboard:painel"
    )

    return redirect(proximo)


@login_required
def marcar_notificacoes_lidas(request):
    if request.method == "POST":
        request.user.notificacoes.filter(lida=False).update(lida=True)

    proximo = (
        request.META.get("HTTP_REFERER")
        or "dashboard:painel"
    )

    return redirect(proximo)
