@login_required
def editar_colchao(request):
    """Edita somente o valor-alvo da meta principal."""

    colchao, criado = Goal.objects.get_or_create(
        usuario=request.user,
        is_colchao_padrao=True,
        defaults={
            "nome": "Colchão para Imprevistos",
            "valor_alvo": Decimal("150.00"),
        },
    )

    if request.method == "POST":
        form = GoalForm(
            request.POST,
            instance=colchao,
        )
    else:
        form = GoalForm(instance=colchao)

    # O nome não é editável na meta principal.
    # Portanto, não pode ser obrigatório no formulário.
    form.fields["nome"].required = False

    if request.method == "POST":
        if form.is_valid():
            objetivo = form.save(commit=False)

            # Preserva o nome fixo da meta principal.
            objetivo.nome = "Colchão para Imprevistos"
            objetivo.save()

            messages.success(
                request,
                "Valor-alvo do Colchão para Imprevistos atualizado!",
            )

            return redirect("goals:lista")

        logger.warning(
            "Erro ao editar o Colchão para Imprevistos: %s",
            form.errors,
        )

        messages.error(
            request,
            "Não foi possível salvar. Confira os erros exibidos no formulário.",
        )

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
