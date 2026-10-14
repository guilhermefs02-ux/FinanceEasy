```python
import logging
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

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
    """UC12 — Estabelecer Reserva de Segurança com Microvalores."""
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
    )

    if request.method == "POST":
        try:
            valor_atalho = request.POST.get("valor_atalho")

            if valor_atalho:
                valor = Decimal(valor_atalho)
            else:
                form = ContribuicaoForm(request.POST)

                if not form.is_valid():
                    messages.error(
                        request,
                        "Informe um valor válido para guardar.",
                    )
                    return redirect("goals:lista")

                valor = form.cleaned_data["valor"]

            if valor <= 0:
                messages.error(
                    request,
                    "O valor da contribuição deve ser maior que zero.",
                )
                return redirect("goals:lista")

            GoalContribution.objects.create(
                objetivo=objetivo,
                valor=valor,
            )

            objetivo.refresh_from_db()

            if (
                objetivo.percentual_concluido >= 100
                and not objetivo.concluido_em
            ):
                objetivo.concluido_em = timezone.now()
                objetivo.save(update_fields=["concluido_em"])

                messages.success(
                    request,
                    f'Você completou o objetivo "{objetivo.nome}"! '
                    "Seu esforço aos poucos valeu a pena. 🎉",
                )
            else:
                messages.success(
                    request,
                    f"+R$ {valor} guardado em "
                    f'"{objetivo.nome}". Cada trocado conta!',
                )

        except Exception:
            logger.exception(
                "Erro ao guardar contribuição do objetivo ID %s",
                pk,
            )
            raise

    return redirect("goals:lista")
```
