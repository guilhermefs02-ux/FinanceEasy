import logging
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import ContribuicaoForm, GoalForm
from .models import Goal, GoalContribution

logger = logging.getLogger(__name__)

ATALHOS_MICROVALORES = [
    Decimal("5.00"),
    Decimal("10.00"),
    Decimal("20.00"),
]


@login_required
def lista_objetivos(request):
    colchao, criado = Goal.objects.get_or_create(
        usuario=request.user,
        is_colchao_padrao=True,
        defaults={
            "nome": "Colchão para Imprevistos",
            "valor_alvo": Decimal("150.00"),
        },
    )

    outros_objetivos = Goal.objects.filter(
        usuario=request.user,
        is_colchao_padrao=False,
        arquivado=False,
    )

    if request.method == "POST":
        form = GoalForm(request.POST)

        if form.is_valid():
            objetivo = form.save(commit=False)
            objetivo.usuario = request.user
            objetivo.save()

            messages.success(
                request,
                f'Objetivo "{objetivo.nome}" criado!',
            )
            return redirect("goals:lista")
    else:
        form = GoalForm()

    return render(
        request,
        "goals/lista.html",
        {
            "colchao": colchao,
            "outros_objetivos": outros_objetivos,
            "form": form,
            "atalhos": ATALHOS_MICROVALORES,
        },
    )


@login_required
def guardar_troco(request, pk):
    objetivo = get_object_or_404(
        Goal,
        pk=pk,
        usuario=request.user,
        arquivado=False,
    )

    if request.method == "POST":
        valor_atalho = request.POST.get("valor_atalho")

        if valor_atalho:
            try:
                valor = Decimal(
                    valor_atalho.strip().replace(",", ".")
                )

                if not valor.is_finite() or valor <= 0:
                    raise InvalidOperation("Valor inválido")

            except (InvalidOperation, ValueError, TypeError):
                logger.warning(
                    "Valor inválido recebido para o objetivo ID %s: %r",
                    pk,
                    valor_atalho,
                )
                messages.error(
                    request,
                    "Não foi possível interpretar o valor. Tente novamente.",
                )
                return redirect("goals:lista")
        else:
            form = ContribuicaoForm(request.POST)

            if not form.is_valid():
                messages.error(
                    request,
                    "Informe um valor válido para guardar.",
                )
                return redirect("goals:lista")

            valor = form.cleaned_data["valor"]

        try:
            GoalContribution.objects.create(
                objetivo=objetivo,
                valor=valor,
            )

            if (
                objetivo.percentual_concluido >= 100
                and not objetivo.concluido_em
            ):
                objetivo.concluido_em = timezone.now()
                objetivo.save()

                messages.success(
                    request,
                    f'Você completou o objetivo "{objetivo.nome}"! '
                    "Seu esforço aos poucos valeu a pena. 🎉",
                )
            else:
                messages.success(
                    request,
                    f'+R$ {valor} guardado em "{objetivo.nome}". '
                    "Cada trocado conta!",
                )

        except Exception:
            logger.exception(
                "Erro ao guardar contribuição do objetivo ID %s",
                pk,
            )
            raise

    return redirect("goals:lista")


@login_required
def editar_colchao(request):
    colchao, criado = Goal.objects.get_or_create(
        usuario=request.user,
        is_colchao_padrao=True,
        defaults={
            "nome": "Colchão para Imprevistos",
            "valor_alvo": Decimal("150.00"),
        },
    )

    if request.method == "POST":
        form = GoalForm(request.POST, instance=colchao)

        if form.is_valid():
            objetivo = form.save(commit=False)
            objetivo.nome = colchao.nome
            objetivo.save()

            messages.success(
                request,
                "Valor-alvo do Colchão para Imprevistos atualizado!",
            )
            return redirect("goals:lista")
    else:
        form = GoalForm(instance=colchao)

    return render(
        request,
        "goals/editar.html",
        {
            "form": form,
            "titulo": "Editar Colchão para Imprevistos",
            "objetivo": colchao,
            "editar_colchao": True,
        },
    )


@login_required
def editar_objetivo(request, pk):
    objetivo = get_object_or_404(
        Goal,
        pk=pk,
        usuario=request.user,
        is_colchao_padrao=False,
        arquivado=False,
    )

    if request.method == "POST":
        form = GoalForm(request.POST, instance=objetivo)

        if form.is_valid():
            form.save()

            messages.success(
                request,
                f'Objetivo "{objetivo.nome}" atualizado!',
            )
            return redirect("goals:lista")
    else:
        form = GoalForm(instance=objetivo)

    return render(
        request,
        "goals/editar.html",
        {
            "form": form,
            "titulo": "Editar objetivo",
            "objetivo": objetivo,
            "editar_colchao": False,
        },
    )


@login_required
@require_POST
def arquivar_objetivo(request, pk):
    objetivo = get_object_or_404(
        Goal,
        pk=pk,
        usuario=request.user,
        is_colchao_padrao=False,
        arquivado=False,
    )

    objetivo.arquivado = True
    objetivo.save(update_fields=["arquivado"])

    messages.success(
        request,
        f'Objetivo "{objetivo.nome}" arquivado. '
        "O histórico de contribuições foi preservado.",
    )

    return redirect("goals:lista")
