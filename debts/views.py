from datetime import date
from dateutil.relativedelta import relativedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from transactions.models import Category, Transaction
from .forms import DebtForm, PagamentoParcelaForm
from .models import Debt


import uuid
from datetime import date
from dateutil.relativedelta import relativedelta

# ... mantendo as outras importações ...

def _gerar_transacoes_futuras_divida(divida, user):
    """Gera parcelas pendentes na tabela Transaction para compor extratos futuros,
    atribuindo grupo_recorrencia_id para agrupamento no painel de futuros.
    """
    categoria = Category.objects.filter(nome="Dívidas/Empréstimos", tipo="despesa").first()
    if not categoria:
        categoria = Category.objects.filter(tipo="despesa").first()

    hoje = date.today()
    parcela_inicio = divida.parcelas_pagas + 1
    total = divida.total_parcelas

    # Gera um UUID para agrupar todas as parcelas dessa divida
    grupo_id = uuid.uuid4()

    # Descrição padronizada sem 'Parcela X/Y' para permitir o agrupamento correto
    descricao_padrao = f"{divida.credor} ({divida.get_categoria_passivo_display()})"

    for p in range(parcela_inicio, total + 1):
        offset_meses = p - parcela_inicio
        data_base = hoje + relativedelta(months=offset_meses)
        try:
            data_vencimento = data_base.replace(day=min(divida.dia_vencimento, 28))
        except ValueError:
            data_vencimento = data_base

        Transaction.objects.create(
            usuario=user,
            tipo=Transaction.Tipo.DESPESA,
            valor=divida.valor_parcela,
            data=data_vencimento,
            categoria=categoria,
            descricao=descricao_padrao,
            origem=Transaction.Origem.MANUAL,
            status=Transaction.Status.PENDENTE,
            tipo_recorrencia=Transaction.TipoRecorrencia.PARCELADA,
            parcela_atual=p,
            total_parcelas=total,
            grupo_recorrencia_id=grupo_id,
        )


@login_required
def lista_dividas(request):
    """UC10 — dívidas ordenadas priorizando juros altos no topo do plano de quitação."""
    dividas = request.user.dividas.filter(quitada=False)
    dividas_ordenadas = sorted(dividas, key=lambda d: (not d.eh_juros_alto, d.dia_vencimento))
    quitadas = request.user.dividas.filter(quitada=True)

    saldo_total_devedor = sum(d.saldo_total_devedor for d in dividas)

    return render(
        request,
        "debts/lista.html",
        {
            "dividas": dividas_ordenadas,
            "quitadas": quitadas,
            "saldo_total_devedor": saldo_total_devedor,
        },
    )


@login_required
def nova_divida(request):
    if request.method == "POST":
        form = DebtForm(request.POST)
        if form.is_valid():
            divida = form.save(commit=False)
            divida.usuario = request.user
            divida.save()

            # --- INTEGRAÇÃO COM EXTRATO FUTURO ---
            _gerar_transacoes_futuras_divida(divida, request.user)

            messages.success(request, f"Dívida com {divida.credor} cadastrada e integradas ao extrato futuro!")
            return redirect("debts:lista")
    else:
        form = DebtForm()
    return render(request, "debts/form.html", {"form": form})


@login_required
def editar_divida(request, pk):
    divida = get_object_or_404(Debt, pk=pk, usuario=request.user)
    if request.method == "POST":
        form = DebtForm(request.POST, instance=divida)
        if form.is_valid():
            form.save()
            messages.success(request, "Dívida atualizada com sucesso.")
            return redirect("debts:lista")
    else:
        form = DebtForm(instance=divida)
    return render(request, "debts/form.html", {"form": form, "divida": divida})


@login_required
def excluir_divida(request, pk):
    divida = get_object_or_404(Debt, pk=pk, usuario=request.user)
    if request.method == "POST":
        credor = divida.credor
        divida.delete()
        messages.success(request, f"Dívida com {credor} removida.")
        return redirect("debts:lista")
    return render(request, "debts/confirmar_exclusao.html", {"divida": divida})


@login_required
def pagar_parcela(request, pk):
    """UC11 — Liquidar Parcela com abatimento no saldo devedor e confirmação no extrato."""
    divida = get_object_or_404(Debt, pk=pk, usuario=request.user)

    if request.method == "POST":
        form = PagamentoParcelaForm(request.POST)
        if form.is_valid():
            debita = form.cleaned_data["debita_saldo_mes"]
            parcela_num = divida.parcelas_pagas + 1
            pagamento = divida.registrar_pagamento_parcela(debita_saldo_mes=debita)

            if pagamento and debita:
                # Tenta localizar a transação pendente existente no extrato futuro
                descricao_busca = f"{divida.credor} ({divida.get_categoria_passivo_display()})"
                transacao_existente = Transaction.objects.filter(
                    usuario=request.user,
                descricao=descricao_busca,
                parcela_atual=parcela_num,
                status=Transaction.Status.PENDENTE,
            ).first()

                if transacao_existente:
                    transacao_existente.status = Transaction.Status.CONFIRMADA
                    transacao_existente.data = date.today()
                    transacao_existente.save()
                    pagamento.transacao = transacao_existente
                else:
                    categoria = Category.objects.filter(nome="Dívidas/Empréstimos", tipo="despesa").first()
                    if not categoria:
                        categoria = Category.objects.filter(tipo="despesa").first()

                    transacao = Transaction.objects.create(
                        usuario=request.user,
                        tipo=Transaction.Tipo.DESPESA,
                        valor=pagamento.valor,
                        data=date.today(),
                        categoria=categoria,
                        descricao=descricao_busca,
                        origem=Transaction.Origem.MANUAL,
                        status=Transaction.Status.CONFIRMADA,
                    )
                    pagamento.transacao = transacao

                pagamento.save()

            if pagamento:
                if divida.quitada:
                    messages.success(
                        request,
                        f"Parabéns! Você quitou a dívida com {divida.credor}!",
                    )
                else:
                    messages.success(
                        request,
                        "Parcela paga e extrato atualizado!",
                    )
            return redirect("debts:lista")

    return redirect("debts:lista")

@login_required
def fatura_cartao(request, pk):
    """Exibe o detalhamento da fatura aberta do cartão de crédito."""
    cartao = get_object_or_404(
        Debt, 
        pk=pk, 
        usuario=request.user, 
        categoria_passivo=Debt.CategoriaPassivo.CARTAO_CREDITO
    )
    
    # Transações vinculadas a este cartão
    transacoes = Transaction.objects.filter(
        usuario=request.user,
        debito_fatura_cartao=cartao
    ).order_by("data")

    total_fatura = sum(t.valor for t in transacoes if t.status == Transaction.Status.PENDENTE)

    return render(
        request,
        "debts/fatura.html",
        {
            "cartao": cartao,
            "transacoes": transacoes,
            "total_fatura": total_fatura,
        },
    )