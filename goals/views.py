import logging
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import ContribuicaoForm, GoalForm
from .models import (
    Goal,
    GoalContribution,
    GoalWithdrawal,
    atualizar_objetivos_e_arquivar,
)

logger = logging.getLogger(__name__)


def obter_objetivos_ativos(usuario):
    """Atualiza os status e retorna os objetivos ainda ativos."""

    atualizar_objetivos_e_arquivar(usuario)

    return Goal.objects.filter(
        usuario=usuario,
        arquivado_em__isnull=True,
    )


@login_required
def lista_objetivos(request):
    """Exibe a reserva de emergência e os demais objetivos ativos."""

    objetivos_ativos = obter_objetivos_ativos(request.user)

    colchao = objetivos_ativos.filter(
        is_colchao_padrao=True
    ).first()

    if colchao is None:
        colchao = Goal.objects.create(
            usuario=request.user,
            nome="Colchão para Imprevistos",
            valor_alvo=Decimal("150.00"),
            is_colchao_padrao=True,
        )

    outros_objetivos = objetivos_ativos.filter(
        is_colchao_padrao=False
    ).order_by("-criado_em")

    form = GoalForm()

    if request.method == "POST":
        form = GoalForm(request.POST)

        if form.is_valid():
            objetivo = form.save(commit=False)
            objetivo.usuario = request.user
            objetivo.is_colchao_padrao = False
            objetivo.save()

            messages.success(
                request,
                f'O objetivo "{objetivo.nome}" foi criado com sucesso.',
            )
            return redirect("goals:lista")

        messages.error(
            request,
            "Confira os dados informados para criar um objetivo.",
        )

    atalhos = [
        {"valor": Decimal("5.00"), "rotulo": "R$ 5,00"},
        {"valor": Decimal("10.00"), "rotulo": "R$ 10,00"},
        {"valor": Decimal("20.00"), "rotulo": "R$ 20,00"},
    ]

    return render(
        request,
        "goals/lista.html",
        {
            "colchao": colchao,
            "outros_objetivos": outros_objetivos,
            "form": form,
            "atalhos": atalhos,
        },
    )


@login_required
@require_POST
def guardar_troco(request, pk):
    """Registra uma contribuição em um objetivo ativo."""

    atualizar_objetivos_e_arquivar(request.user)

    objetivo = get_object_or_404(
        Goal,
        pk=pk,
        usuario=request.user,
        arquivado_em__isnull=True,
    )

    if objetivo.concluido_em:
        messages.warning(
            request,
            "Este objetivo já foi concluído. Não é possível guardar "
            "mais dinheiro enquanto ele aguarda o arquivamento.",
        )
        return redirect("goals:lista")

    valor_atalho = request.POST.get("valor_atalho")
    valor = None

    if valor_atalho:
        try:
            valor = Decimal(valor_atalho.replace(",", "."))
        except (InvalidOperation, AttributeError):
            valor = None

        if valor is None or not valor.is_finite() or valor <= 0:
            messages.error(
                request,
                "Informe um valor válido para guardar.",
            )
            return redirect("goals:lista")
    else:
        form = ContribuicaoForm(request.POST)

        if not form.is_valid():
            messages.error(
                request,
                "Informe um valor válido, maior que zero.",
            )
            return redirect("goals:lista")

        valor = form.cleaned_data["valor"]

    try:
        with transaction.atomic():
            GoalContribution.objects.create(
                objetivo=objetivo,
                valor=valor,
            )

            objetivo.refresh_from_db()
            objetivo.atualizar_status_conclusao()
            objetivo.refresh_from_db()

        if objetivo.concluido_em:
            messages.success(
                request,
                f'Parabéns! Você concluiu o objetivo "{objetivo.nome}". '
                "Ele ficará disponível por mais 10 dias antes de ser "
                "arquivado.",
            )
        else:
            messages.success(
                request,
                f"Você guardou R$ {valor:.2f} no objetivo "
                f'"{objetivo.nome}".',
            )

    except Exception:
        logger.exception(
            "Erro ao registrar contribuição no objetivo %s",
            pk,
        )
        messages.error(
            request,
            "Não foi possível registrar o valor. Tente novamente.",
        )

    return redirect("goals:lista")


@login_required
@require_POST
def retirar_saldo(request, pk):
    """Registra uma retirada sem apagar o histórico de contribuições."""

    atualizar_objetivos_e_arquivar(request.user)

    with transaction.atomic():
        objetivo = get_object_or_404(
            Goal.objects.select_for_update(),
            pk=pk,
            usuario=request.user,
            arquivado_em__isnull=True,
        )

        if objetivo.concluido_em:
            messages.warning(
                request,
                "Este objetivo está concluído e não permite retiradas "
                "durante o período de espera para arquivamento.",
            )
            return redirect("goals:lista")

        valor_texto = request.POST.get("valor", "").strip()

        try:
            valor = Decimal(valor_texto.replace(",", "."))
        except (InvalidOperation, AttributeError):
            messages.error(
                request,
                "Informe um valor válido para retirar.",
            )
            return redirect("goals:lista")

        if not valor.is_finite() or valor <= 0:
            messages.error(
                request,
                "O valor da retirada precisa ser maior que zero.",
            )
            return redirect("goals:lista")

        objetivo.refresh_from_db()
        saldo_atual = objetivo.valor_acumulado

        if valor > saldo_atual:
            messages.error(
                request,
                f"Saldo insuficiente. O saldo disponível é "
                f"R$ {saldo_atual:.2f}.",
            )
            return redirect("goals:lista")

        GoalWithdrawal.objects.create(
            objetivo=objetivo,
            valor=valor,
        )

        objetivo.refresh_from_db()
        objetivo.atualizar_status_conclusao()
        objetivo.refresh_from_db()

    messages.success(
        request,
        f"Retirada de R$ {valor:.2f} registrada no objetivo "
        f'"{objetivo.nome}".',
    )

    return redirect("goals:lista")


@login_required
@require_POST
def resetar_colchao(request):
    """Zera o saldo do colchão registrando uma retirada no histórico."""

    try:
        with transaction.atomic():
            colchao = get_object_or_404(
                Goal.objects.select_for_update(),
                usuario=request.user,
                is_colchao_padrao=True,
                arquivado_em__isnull=True,
            )

            saldo_atual = colchao.valor_acumulado

            if saldo_atual < Decimal("0.00"):
                messages.error(
                    request,
                    "O saldo do colchão está negativo. Confira as movimentações "
                    "antes de resetar a meta.",
                )
                return redirect("goals:lista")

            if saldo_atual == Decimal("0.00"):
                messages.info(
                    request,
                    "O colchão já está com saldo zerado.",
                )
                return redirect("goals:lista")

            GoalWithdrawal.objects.create(
                objetivo=colchao,
                valor=saldo_atual,
            )

            colchao.refresh_from_db()
            colchao.atualizar_status_conclusao()

        messages.success(
            request,
            f"Colchão resetado. A retirada de R$ {saldo_atual:.2f} "
            "foi registrada e o histórico anterior foi preservado.",
        )

    except Exception:
        logger.exception(
            "Erro ao resetar o colchão do usuário %s",
            request.user.pk,
        )
        messages.error(
            request,
            "Não foi possível resetar o colchão. Tente novamente.",
        )

    return redirect("goals:lista")


@login_required
def editar_colchao(request):
    """Permite alterar o valor-alvo da reserva de emergência."""

    objetivos_ativos = obter_objetivos_ativos(request.user)

    colchao = get_object_or_404(
        objetivos_ativos,
        is_colchao_padrao=True,
    )

    if request.method == "POST":
        form = GoalForm(request.POST, instance=colchao)

        if form.is_valid():
            colchao.valor_alvo = form.cleaned_data["valor_alvo"]
            colchao.nome = "Colchão para Imprevistos"
            colchao.save(update_fields=["valor_alvo", "nome"])
            colchao.atualizar_status_conclusao()

            messages.success(
                request,
                "O valor-alvo do colchão foi atualizado.",
            )
            return redirect("goals:lista")
    else:
        form = GoalForm(instance=colchao)

    return render(
        request,
        "goals/editar.html",
        {
            "form": form,
            "objetivo": colchao,
            "titulo": "Editar colchão para imprevistos",
        },
    )


@login_required
def editar_objetivo(request, pk):
    """Permite editar um objetivo secundário ativo."""

    atualizar_objetivos_e_arquivar(request.user)

    objetivo = get_object_or_404(
        Goal,
        pk=pk,
        usuario=request.user,
        is_colchao_padrao=False,
        arquivado_em__isnull=True,
    )

    if request.method == "POST":
        form = GoalForm(request.POST, instance=objetivo)

        if form.is_valid():
            form.save()
            objetivo.refresh_from_db()
            objetivo.atualizar_status_conclusao()

            messages.success(
                request,
                "Objetivo atualizado com sucesso.",
            )
            return redirect("goals:lista")
    else:
        form = GoalForm(instance=objetivo)

    return render(
        request,
        "goals/editar.html",
        {
            "form": form,
            "objetivo": objetivo,
            "titulo": "Editar objetivo",
        },
    )


@login_required
@require_POST
def excluir_objetivo(request, pk):
    """Exclui um objetivo secundário ativo."""

    objetivo = get_object_or_404(
        Goal,
        pk=pk,
        usuario=request.user,
        is_colchao_padrao=False,
        arquivado_em__isnull=True,
    )

    nome = objetivo.nome
    objetivo.delete()

    messages.success(
        request,
        f'O objetivo "{nome}" e suas movimentações foram excluídos.',
    )

    return redirect("goals:lista")


@login_required
def historico_objetivos(request):
    """Diagnóstico temporário da página de histórico."""

    logger.info("DIAGNÓSTICO HISTÓRICO: função iniciada")

    try:
        objetivos = list(
            Goal.objects.filter(
                usuario=request.user,
                arquivado_em__isnull=False,
            ).order_by("-arquivado_em")
        )

        logger.info(
            "DIAGNÓSTICO HISTÓRICO: consulta OK; quantidade=%s",
            len(objetivos),
        )

        resposta = render(
            request,
            "goals/historico.html",
            {"objetivos": objetivos},
        )

        logger.info(
            "DIAGNÓSTICO HISTÓRICO: template renderizado OK"
        )
        return resposta

    except Exception:
        logger.exception(
            "DIAGNÓSTICO HISTÓRICO: erro para usuário %s",
            request.user.pk,
        )
        raise
