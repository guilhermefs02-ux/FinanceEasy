import json
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from decimal import Decimal, InvalidOperation
from collections import defaultdict

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction as db_transaction
from django.db.models import Sum
from django.db.models.functions import TruncYear
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from core.services.budget_alerts import verificar_limite_categoria
from debts.models import Debt

from .forms import (
    CategoryBudgetForm,
    CategoryForm,
    DespesaForm,
    ImportUploadForm,
    LoteDespesaFormSet,
    LoteReceitaFormSet,
    LoteRecorrenciaFormSet,
    ReceitaForm,
    RecurringBillForm,
)
from .models import (
    Category,
    CategoryBudget,
    ImportBatch,
    RecurringBill,
    RecurringBillPayment,
    Transaction,
)
from .services.categorizer import sugerir_categoria
from .services.import_parser import (
    ExtratoInvalidoError,
    formato_por_extensao,
    parse_extrato,
)
from .services.recurrency import gerar_parcelas_futuras
from .services.recurring_bills import gerar_vencimentos_contas_fixas


def _data_efetiva_pagamento(pagamento):
    """Obtém a data real do pagamento ou usa o vencimento como alternativa."""
    if pagamento.pago_em:
        if timezone.is_aware(pagamento.pago_em):
            return timezone.localtime(pagamento.pago_em).date()
        return pagamento.pago_em.date()

    return pagamento.data_vencimento


def _regularizar_pagamentos_contas_fixas(usuario):
    """
    Regulariza pagamentos antigos sem gerar despesas duplicadas.

    Atualiza transações que já estejam vinculadas ao pagamento.
    Quando não houver vínculo, procura um lançamento com os mesmos
    dados específicos da despesa de conta fixa antes de criar outro.
    """
    regularizadas = 0

    pagamentos_ids = list(
        RecurringBillPayment.objects.filter(
            conta__usuario=usuario,
            status=RecurringBillPayment.Status.PAGO,
        ).values_list("pk", flat=True)
    )

    for pagamento_id in pagamentos_ids:
        with db_transaction.atomic():
            pagamento = (
                RecurringBillPayment.objects.select_for_update()
                .select_related("conta", "conta__categoria")
                .filter(
                    pk=pagamento_id,
                    conta__usuario=usuario,
                    status=RecurringBillPayment.Status.PAGO,
                )
                .first()
            )

            if pagamento is None:
                continue

            conta = pagamento.conta
            data_pagamento = _data_efetiva_pagamento(pagamento)
            descricao = f"Pagamento: {conta.nome_servico}"

            transacao = None

            if pagamento.transacao_id:
                transacao = Transaction.objects.filter(
                    pk=pagamento.transacao_id,
                    usuario=usuario,
                ).first()

            if transacao is None:
                transacao = (
                    Transaction.objects.filter(
                        usuario=usuario,
                        tipo=Transaction.Tipo.DESPESA,
                        valor=pagamento.valor,
                        data=data_pagamento,
                        categoria=conta.categoria,
                        descricao=descricao,
                        origem=Transaction.Origem.MANUAL,
                        status=Transaction.Status.CONFIRMADA,
                        tipo_recorrencia=Transaction.TipoRecorrencia.FIXA,
                        pagamentos_contas_fixas__isnull=True,
                    )
                    .order_by("criado_em")
                    .first()
                )

            if transacao is None:
                transacao = Transaction.objects.create(
                    usuario=usuario,
                    tipo=Transaction.Tipo.DESPESA,
                    valor=pagamento.valor,
                    data=data_pagamento,
                    categoria=conta.categoria,
                    descricao=descricao,
                    origem=Transaction.Origem.MANUAL,
                    status=Transaction.Status.CONFIRMADA,
                    tipo_recorrencia=Transaction.TipoRecorrencia.FIXA,
                )
                regularizadas += 1
            else:
                campos = {
                    "tipo": Transaction.Tipo.DESPESA,
                    "valor": pagamento.valor,
                    "data": data_pagamento,
                    "categoria": conta.categoria,
                    "descricao": descricao,
                    "origem": Transaction.Origem.MANUAL,
                    "status": Transaction.Status.CONFIRMADA,
                    "tipo_recorrencia": Transaction.TipoRecorrencia.FIXA,
                }

                alterada = False

                for campo, valor in campos.items():
                    valor_atual = (
                        getattr(transacao, f"{campo}_id")
                        if campo == "categoria"
                        else getattr(transacao, campo)
                    )

                    valor_novo = valor.pk if campo == "categoria" else valor

                    if valor_atual != valor_novo:
                        setattr(transacao, campo, valor)
                        alterada = True

                if alterada:
                    transacao.save()

            if pagamento.transacao_id != transacao.pk:
                pagamento.transacao = transacao
                pagamento.save(update_fields=["transacao"])

    return regularizadas


@login_required
def registrar_receita(request):
    if request.method == "POST":
        form = ReceitaForm(request.POST, user=request.user)
        if form.is_valid():
            transacao = form.save(commit=False)
            transacao.usuario = request.user
            transacao.origem = Transaction.Origem.MANUAL
            transacao.status = Transaction.Status.CONFIRMADA
            transacao.save()

            if transacao.tipo_recorrencia in [
                Transaction.TipoRecorrencia.PARCELADA,
                Transaction.TipoRecorrencia.FIXA,
            ]:
                gerar_parcelas_futuras(
                    transacao_base=transacao,
                    quantidade_parcelas=transacao.total_parcelas,
                )

            messages.success(
                request,
                f"Receita de R$ {transacao.valor} registrada.",
            )
            return redirect("dashboard:painel")
    else:
        form = ReceitaForm(user=request.user)

    return render(
        request,
        "transactions/registrar_receita.html",
        {"form": form},
    )


@login_required
def lote_receitas(request):
    """Lançamento manual de várias receitas de uma vez."""
    if request.method == "POST":
        formset = LoteReceitaFormSet(
            request.POST,
            form_kwargs={"user": request.user},
        )

        if formset.is_valid():
            criadas = 0

            with db_transaction.atomic():
                for linha in formset:
                    dados = linha.cleaned_data
                    if not dados:
                        continue

                    Transaction.objects.create(
                        usuario=request.user,
                        tipo=Transaction.Tipo.RECEITA,
                        valor=dados["valor"],
                        categoria=dados["categoria"],
                        data=dados["data"],
                        descricao=dados.get("descricao", ""),
                        origem=Transaction.Origem.MANUAL,
                        status=Transaction.Status.CONFIRMADA,
                    )
                    criadas += 1

            if criadas == 0:
                messages.warning(
                    request,
                    "Nenhuma linha foi preenchida — nada foi lançado.",
                )
            else:
                messages.success(
                    request,
                    f"{criadas} receita(s) registradas de uma vez. "
                    "Seu saldo já foi atualizado.",
                )
                return redirect("dashboard:painel")
    else:
        formset = LoteReceitaFormSet(
            form_kwargs={"user": request.user},
        )

    return render(
        request,
        "transactions/lote.html",
        {"formset": formset, "tipo": "receita"},
    )


@login_required
def registrar_despesa(request):
    if request.method == "POST":
        form = DespesaForm(request.POST, user=request.user)

        if form.is_valid():
            transacao = form.save(commit=False)
            transacao.usuario = request.user
            transacao.origem = Transaction.Origem.MANUAL
            transacao.status = Transaction.Status.CONFIRMADA
            transacao.save()

            if transacao.tipo_recorrencia in [
                Transaction.TipoRecorrencia.PARCELADA,
                Transaction.TipoRecorrencia.FIXA,
            ]:
                gerar_parcelas_futuras(
                    transacao_base=transacao,
                    quantidade_parcelas=transacao.total_parcelas,
                )

            alerta = verificar_limite_categoria(
                request.user,
                transacao.categoria,
            )

            messages.success(
                request,
                f"Despesa de R$ {transacao.valor} registrada.",
            )

            if alerta:
                messages.warning(request, alerta["mensagem"])

            return redirect("dashboard:painel")
    else:
        form = DespesaForm(user=request.user)

    return render(
        request,
        "transactions/registrar_despesa.html",
        {"form": form},
    )


@login_required
def lote_despesas(request):
    """Lançamento manual de várias despesas de uma vez."""
    if request.method == "POST":
        formset = LoteDespesaFormSet(
            request.POST,
            form_kwargs={"user": request.user},
        )

        if formset.is_valid():
            criadas = 0
            alertas = []

            with db_transaction.atomic():
                for linha in formset:
                    dados = linha.cleaned_data
                    if not dados:
                        continue

                    transacao = Transaction.objects.create(
                        usuario=request.user,
                        tipo=Transaction.Tipo.DESPESA,
                        valor=dados["valor"],
                        categoria=dados["categoria"],
                        forma_pagamento=dados.get("forma_pagamento", ""),
                        data=dados["data"],
                        descricao=dados.get("descricao", ""),
                        origem=Transaction.Origem.MANUAL,
                        status=Transaction.Status.CONFIRMADA,
                    )

                    criadas += 1

                    alerta = verificar_limite_categoria(
                        request.user,
                        transacao.categoria,
                    )

                    if alerta:
                        alertas.append(alerta["mensagem"])

            if criadas == 0:
                messages.warning(
                    request,
                    "Nenhuma linha foi preenchida — nada foi lançado.",
                )
            else:
                messages.success(
                    request,
                    f"{criadas} despesa(s) registradas de uma vez.",
                )

                for mensagem in alertas:
                    messages.warning(request, mensagem)

                return redirect("dashboard:painel")
    else:
        formset = LoteDespesaFormSet(
            form_kwargs={"user": request.user},
        )

    return render(
        request,
        "transactions/lote.html",
        {"formset": formset, "tipo": "despesa"},
    )


@login_required
def importar_extrato(request):
    """UC04 — Importar Extrato Bancário e Fatura."""
    if request.method == "POST":
        form = ImportUploadForm(
            request.POST,
            request.FILES,
            user=request.user,
        )

        if form.is_valid():
            arquivo = form.cleaned_data["arquivo"]

            limite_bytes = getattr(
                settings,
                "MAX_UPLOAD_SIZE_BYTES",
                10 * 1024 * 1024,
            )

            if arquivo.size > limite_bytes:
                limite_mb = limite_bytes / (1024 * 1024)

                messages.error(
                    request,
                    f"O arquivo selecionado é muito grande. "
                    f"O limite para importação é de {limite_mb:g} MB. "
                    "Exporte novamente o extrato em um arquivo menor.",
                )

                return render(
                    request,
                    "transactions/importar_extrato.html",
                    {"form": form},
                )

            tipo_conta = form.cleaned_data["tipo_conta"]
            cartao_divida = form.cleaned_data.get("cartao_divida")
            formato = formato_por_extensao(arquivo.name)

            if not formato:
                messages.error(
                    request,
                    "Não conseguimos ler este arquivo. "
                    "Certifique-se de exportar o extrato no formato "
                    "OFX ou CSV diretamente do aplicativo do seu banco.",
                )

                return render(
                    request,
                    "transactions/importar_extrato.html",
                    {"form": form},
                )

            try:
                linhas = parse_extrato(arquivo, formato)
            except ExtratoInvalidoError as exc:
                messages.error(request, str(exc))

                return render(
                    request,
                    "transactions/importar_extrato.html",
                    {"form": form},
                )

            batch = ImportBatch.objects.create(
                usuario=request.user,
                arquivo_nome=arquivo.name,
                formato=formato,
                tipo_conta=tipo_conta,
                cartao_divida=cartao_divida,
                total_linhas=len(linhas),
            )

            novas, duplicadas = 0, 0

            for linha in linhas:
                valor = linha["valor"]

                tipo = (
                    Transaction.Tipo.RECEITA
                    if valor >= 0
                    else Transaction.Tipo.DESPESA
                )

                valor_abs = abs(valor)
                descricao_banco = linha["descricao"]

                hash_dedup = Transaction.calcular_hash(
                    request.user.id,
                    linha["data"],
                    valor_abs,
                    descricao_banco,
                )

                if Transaction.objects.filter(
                    usuario=request.user,
                    hash_dedup=hash_dedup,
                ).exists():
                    duplicadas += 1
                    continue

                sugestao = sugerir_categoria(
                    descricao_banco,
                    tipo,
                )

                categorias_usuario = Category.objects.para_usuario(
                    request.user,
                    tipo,
                )

                categoria = categorias_usuario.filter(
                    nome__iexact=sugestao.nome_categoria,
                ).first()

                if categoria is None:
                    categoria = categorias_usuario.filter(
                        nome="Outros",
                    ).first()

                Transaction.objects.create(
                    usuario=request.user,
                    tipo=tipo,
                    valor=valor_abs,
                    data=linha["data"],
                    categoria=categoria,
                    descricao=descricao_banco,
                    descricao_origem_banco=descricao_banco,
                    origem=Transaction.Origem.IMPORTADO,
                    status=Transaction.Status.PENDENTE,
                    import_batch=batch,
                    categoria_sugerida_confianca=sugestao.confianca,
                    hash_dedup=hash_dedup,
                    debito_fatura_cartao=(
                        cartao_divida
                        if tipo_conta == ImportBatch.TipoConta.FATURA_CARTAO
                        else None
                    ),
                )

                novas += 1

            batch.total_novas = novas
            batch.total_duplicadas = duplicadas
            batch.save()

            if novas == 0:
                messages.info(
                    request,
                    "Todas as transações deste extrato já foram "
                    "importadas anteriormente. Nenhum novo gasto "
                    "foi adicionado.",
                )

                batch.concluido = True
                batch.save()

                return redirect("transactions:extrato")

            return redirect(
                "transactions:conciliar",
                batch_id=batch.pk,
            )
    else:
        form = ImportUploadForm(user=request.user)

    return render(
        request,
        "transactions/importar_extrato.html",
        {"form": form},
    )


@login_required
def conciliar(request, batch_id):
    """UC05 — Categorizar Transações em Lote e Conciliação."""
    batch = get_object_or_404(
        ImportBatch,
        pk=batch_id,
        usuario=request.user,
    )

    pendentes = batch.transacoes.filter(
        status=Transaction.Status.PENDENTE,
    ).select_related("categoria")

    if request.method == "POST":
        categorias_despesa = {
            c.pk: c
            for c in Category.objects.para_usuario(
                request.user,
                Category.Tipo.DESPESA,
            )
        }

        categorias_receita = {
            c.pk: c
            for c in Category.objects.para_usuario(
                request.user,
                Category.Tipo.RECEITA,
            )
        }

        with db_transaction.atomic():
            aprovadas = 0
            categorias_tocadas = set()

            for transacao in pendentes:
                incluir = (
                    request.POST.get(f"incluir_{transacao.pk}") == "on"
                )

                if not incluir:
                    transacao.delete()
                    continue

                categoria_id = request.POST.get(
                    f"categoria_{transacao.pk}",
                )

                if categoria_id:
                    mapa = (
                        categorias_receita
                        if transacao.tipo == Transaction.Tipo.RECEITA
                        else categorias_despesa
                    )

                    try:
                        nova_categoria = mapa.get(int(categoria_id))
                    except (ValueError, TypeError):
                        nova_categoria = None

                    if nova_categoria:
                        transacao.categoria = nova_categoria

                transacao.status = Transaction.Status.CONFIRMADA
                transacao.save()
                aprovadas += 1

                if (
                    transacao.tipo == Transaction.Tipo.DESPESA
                    and transacao.categoria_id
                ):
                    categorias_tocadas.add(transacao.categoria_id)

            batch.concluido = True
            batch.save()

        segundos_estimados = max(round(aprovadas / 6), 1)

        messages.success(
            request,
            f"Pronto! {aprovadas} transações importadas em "
            f"{segundos_estimados} segundos. "
            "O seu extrato e a sua folga financeira estão "
            "100% atualizados.",
        )

        for categoria_id in categorias_tocadas:
            categoria = Category.objects.filter(
                pk=categoria_id,
            ).first()

            if categoria:
                alerta = verificar_limite_categoria(
                    request.user,
                    categoria,
                )

                if alerta:
                    messages.warning(request, alerta["mensagem"])

        sugestoes_dividas = _sugerir_baixas_de_divida(
            request.user,
            batch,
        )

        for sugestao in sugestoes_dividas:
            messages.info(request, sugestao)

        return redirect("transactions:extrato")

    despesa_categorias = Category.objects.para_usuario(
        request.user,
        Category.Tipo.DESPESA,
    )

    receita_categorias = Category.objects.para_usuario(
        request.user,
        Category.Tipo.RECEITA,
    )

    return render(
        request,
        "transactions/conciliar.html",
        {
            "batch": batch,
            "pendentes": pendentes,
            "despesa_categorias": despesa_categorias,
            "receita_categorias": receita_categorias,
        },
    )


@login_required
def cancelar_importacao(request, batch_id):
    """Cancela o lote pendente e apaga os lançamentos não confirmados."""
    batch = get_object_or_404(
        ImportBatch,
        pk=batch_id,
        usuario=request.user,
    )

    if request.method == "POST":
        batch.transacoes.filter(
            status=Transaction.Status.PENDENTE,
        ).delete()

        batch.delete()

        messages.info(
            request,
            "Importação de extrato cancelada e lançamentos descartados.",
        )

        return redirect("transactions:extrato")

    return redirect(
        "transactions:conciliar",
        batch_id=batch.pk,
    )


def _sugerir_baixas_de_divida(user, batch):
    """Sugere baixas de parcelas de dívidas com base no extrato."""
    sugestoes = []

    dividas_ativas = list(
        Debt.objects.filter(
            usuario=user,
            quitada=False,
        )
    )

    if not dividas_ativas:
        return sugestoes

    transacoes = batch.transacoes.filter(
        status=Transaction.Status.CONFIRMADA,
        tipo=Transaction.Tipo.DESPESA,
    )

    for transacao in transacoes:
        descricao = (
            transacao.descricao_origem_banco or ""
        ).upper()

        for divida in dividas_ativas:
            if divida.credor.upper() in descricao:
                sugestoes.append(
                    f"Notamos um pagamento para \"{divida.credor}\" "
                    "no seu extrato — quer marcar a parcela como paga "
                    "em Dívidas?"
                )
                break

    return sugestoes


@login_required
def extrato(request):
    """UC09 — Extrato consolidado, filtros e navegação temporal."""
    hoje = timezone.localdate()

    try:
        mes_atual = int(request.GET.get("mes", hoje.month))
        ano_atual = int(request.GET.get("ano", hoje.year))
    except (ValueError, TypeError):
        mes_atual, ano_atual = hoje.month, hoje.year

    if not 1 <= mes_atual <= 12:
        mes_atual = hoje.month

    if not 1900 <= ano_atual <= 2100:
        ano_atual = hoje.year

    periodo = request.GET.get("periodo", "mensal")
    if periodo not in {"diario", "semanal", "mensal", "anual"}:
        periodo = "mensal"

    tipo = request.GET.get("tipo", "")
    if tipo not in (
        Transaction.Tipo.RECEITA,
        Transaction.Tipo.DESPESA,
        "",
    ):
        tipo = ""

    categoria_id = request.GET.get("categoria", "").strip()

    primeiro_dia_mes = date(ano_atual, mes_atual, 1)

    if mes_atual == 12:
        primeiro_dia_mes_seguinte = date(ano_atual + 1, 1, 1)
    else:
        primeiro_dia_mes_seguinte = date(ano_atual, mes_atual + 1, 1)

    ultimo_dia_mes = primeiro_dia_mes_seguinte - timedelta(days=1)

    if periodo == "diario":
        data_inicio = hoje
        data_fim = hoje
    elif periodo == "semanal":
        data_inicio = hoje - timedelta(days=hoje.weekday())
        data_fim = data_inicio + timedelta(days=6)
    elif periodo == "anual":
        data_inicio = date(ano_atual, 1, 1)
        data_fim = date(ano_atual, 12, 31)
    else:
        data_inicio = primeiro_dia_mes
        data_fim = ultimo_dia_mes

    qs = Transaction.objects.filter(
        usuario=request.user,
        data__range=(data_inicio, data_fim),
    ).select_related("categoria")

    if tipo:
        qs = qs.filter(tipo=tipo)

    if tipo == Transaction.Tipo.RECEITA:
        categorias_filtro = Category.objects.para_usuario(
            request.user,
            Category.Tipo.RECEITA,
        )
    elif tipo == Transaction.Tipo.DESPESA:
        categorias_filtro = Category.objects.para_usuario(
            request.user,
            Category.Tipo.DESPESA,
        )
    else:
        categorias_filtro = Category.objects.para_usuario(request.user)

    if categoria_id:
        if categoria_id.isdigit():
            categoria_valida = categorias_filtro.filter(
                pk=int(categoria_id),
            ).exists()

            if categoria_valida:
                qs = qs.filter(categoria_id=int(categoria_id))
            else:
                categoria_id = ""
        else:
            categoria_id = ""

    if mes_atual == 1:
        mes_anterior = 12
        ano_anterior = ano_atual - 1
    else:
        mes_anterior = mes_atual - 1
        ano_anterior = ano_atual

    despesas_mes_atual = (
        Transaction.objects.filter(
            usuario=request.user,
            tipo=Transaction.Tipo.DESPESA,
            status=Transaction.Status.CONFIRMADA,
            data__gte=primeiro_dia_mes,
            data__lt=primeiro_dia_mes_seguinte,
        ).aggregate(total=Sum("valor"))["total"]
        or Decimal("0.00")
    )

    inicio_mes_anterior = date(ano_anterior, mes_anterior, 1)

    if mes_anterior == 12:
        inicio_mes_seguinte_ao_anterior = date(ano_anterior + 1, 1, 1)
    else:
        inicio_mes_seguinte_ao_anterior = date(
            ano_anterior,
            mes_anterior + 1,
            1,
        )

    despesas_mes_anterior = (
        Transaction.objects.filter(
            usuario=request.user,
            tipo=Transaction.Tipo.DESPESA,
            status=Transaction.Status.CONFIRMADA,
            data__gte=inicio_mes_anterior,
            data__lt=inicio_mes_seguinte_ao_anterior,
        ).aggregate(total=Sum("valor"))["total"]
        or Decimal("0.00")
    )

    if despesas_mes_anterior > 0:
        variacao_percentual = round(
            float(
                (despesas_mes_atual - despesas_mes_anterior)
                / despesas_mes_anterior
                * 100
            )
        )
    elif despesas_mes_atual > 0:
        variacao_percentual = 100
    else:
        variacao_percentual = None

    categorias_despesa = Category.objects.para_usuario(
        request.user,
        Category.Tipo.DESPESA,
    )
    categorias_receita = Category.objects.para_usuario(
        request.user,
        Category.Tipo.RECEITA,
    )

    lista_meses = [
        (1, "Janeiro"),
        (2, "Fevereiro"),
        (3, "Março"),
        (4, "Abril"),
        (5, "Maio"),
        (6, "Junho"),
        (7, "Julho"),
        (8, "Agosto"),
        (9, "Setembro"),
        (10, "Outubro"),
        (11, "Novembro"),
        (12, "Dezembro"),
    ]

    anos_disponiveis = list(
        range(
            min(hoje.year - 3, ano_atual - 1),
            max(hoje.year + 5, ano_atual + 1) + 1,
        )
    )

    if periodo == "diario":
        descricao_periodo = "Hoje"
    elif periodo == "semanal":
        descricao_periodo = "Esta semana"
    elif periodo == "anual":
        descricao_periodo = f"Ano de {ano_atual}"
    else:
        descricao_periodo = f"{mes_atual:02d}/{ano_atual}"

    return render(
        request,
        "transactions/extrato.html",
        {
            "transacoes": qs.order_by("-data", "-criado_em"),
            "categorias_despesa": categorias_despesa,
            "categorias_receita": categorias_receita,
            "categorias_filtro": categorias_filtro,
            "filtro_categoria": categoria_id,
            "filtro_tipo": tipo,
            "filtro_periodo": periodo,
            "descricao_periodo": descricao_periodo,
            "data_inicio": data_inicio,
            "data_fim": data_fim,
            "mes_atual": mes_atual,
            "ano_atual": ano_atual,
            "lista_meses": lista_meses,
            "anos_disponiveis": anos_disponiveis,
            "despesas_mes_atual": despesas_mes_atual,
            "despesas_mes_anterior": despesas_mes_anterior,
            "variacao_percentual": variacao_percentual,
        },
    )


@login_required
def editar_transacao(request, pk):
    transacao = get_object_or_404(
        Transaction,
        pk=pk,
        usuario=request.user,
    )

    FormClasse = (
        ReceitaForm
        if transacao.tipo == Transaction.Tipo.RECEITA
        else DespesaForm
    )

    if request.method == "POST":
        form = FormClasse(
            request.POST,
            instance=transacao,
            user=request.user,
        )

        if form.is_valid():
            form.save()
            messages.success(request, "Lançamento atualizado.")
            return redirect("transactions:extrato")
    else:
        form = FormClasse(
            instance=transacao,
            user=request.user,
        )

    return render(
        request,
        "transactions/editar_transacao.html",
        {"form": form, "transacao": transacao},
    )


@login_required
def excluir_transacao(request, pk):
    transacao = get_object_or_404(
        Transaction,
        pk=pk,
        usuario=request.user,
    )

    if request.method == "POST":
        transacao.delete()
        messages.success(request, "Lançamento excluído.")

    return redirect("transactions:extrato")


@login_required
def assinaturas(request):
    """UC07 — Gerenciar contas fixas e assinaturas recorrentes."""
    regularizadas = _regularizar_pagamentos_contas_fixas(request.user)
    gerar_vencimentos_contas_fixas(request.user)

    if regularizadas:
        messages.success(
            request,
            f"{regularizadas} despesa(s) de conta(s) fixa(s) "
            "antiga(s) foram recuperadas e vinculadas ao extrato.",
        )

    if request.method == "POST":
        form = RecurringBillForm(
            request.POST,
            user=request.user,
        )

        if form.is_valid():
            recorrencia = form.save(commit=False)
            recorrencia.usuario = request.user

            if (
                recorrencia.periodicidade
                == RecurringBill.Periodicidade.MENSAL
            ):
                recorrencia.mes_vencimento = None

            recorrencia.save()

            messages.success(
                request,
                f"{recorrencia.nome_servico} adicionada às suas recorrências.",
            )

            return redirect("transactions:assinaturas")
    else:
        form = RecurringBillForm(user=request.user)

    itens = request.user.recorrencias.filter(ativo=True)
    total_mensal = sum(i.valor_mensalizado for i in itens)
    total_anual = sum(i.valor_anualizado for i in itens)

    return render(
        request,
        "transactions/assinaturas.html",
        {
            "form": form,
            "itens": itens,
            "total_mensal": total_mensal,
            "total_anual": total_anual,
        },
    )


@login_required
def lote_despesas_fixas(request):
    """Cadastro em lote de despesas fixas e recorrentes."""
    if request.method == "POST":
        formset = LoteRecorrenciaFormSet(
            request.POST,
            form_kwargs={"user": request.user},
        )

        if formset.is_valid():
            criadas = 0

            with db_transaction.atomic():
                for linha in formset:
                    dados = linha.cleaned_data

                    if not dados:
                        continue

                    periodicidade = dados["periodicidade"]
                    mes_vencimento = dados.get("mes_vencimento")

                    if periodicidade == RecurringBill.Periodicidade.MENSAL:
                        mes_vencimento = None

                    RecurringBill.objects.create(
                        usuario=request.user,
                        nome_servico=dados["nome_servico"],
                        categoria=dados["categoria"],
                        valor=dados["valor"],
                        periodicidade=periodicidade,
                        mes_vencimento=mes_vencimento,
                        dia_vencimento=dados["dia_vencimento"],
                    )

                    criadas += 1

            if criadas == 0:
                messages.warning(
                    request,
                    "Nenhuma linha foi preenchida — nada foi lançado.",
                )
            else:
                messages.success(
                    request,
                    f"{criadas} despesa(s) fixa(s) adicionadas de uma vez.",
                )

                return redirect("transactions:assinaturas")
    else:
        formset = LoteRecorrenciaFormSet(
            form_kwargs={"user": request.user},
        )

    return render(
        request,
        "transactions/lote_recorrencias.html",
        {"formset": formset},
    )


@login_required
def marcar_conta_fixa_paga(request, pagamento_id):
    """
    Marca uma conta fixa como paga e registra a despesa
    na data efetiva do pagamento.
    """
    if request.method != "POST":
        return redirect("transactions:assinaturas")

    with db_transaction.atomic():
        pagamento = get_object_or_404(
            RecurringBillPayment.objects.select_for_update().select_related(
                "conta",
                "conta__categoria",
            ),
            pk=pagamento_id,
            conta__usuario=request.user,
        )

        if pagamento.status == RecurringBillPayment.Status.PAGO:
            messages.info(
                request,
                "Este vencimento já está marcado como pago.",
            )
            return redirect("transactions:assinaturas")

        conta = pagamento.conta
        data_pagamento = timezone.localdate()

        transacao = None

        if pagamento.transacao_id:
            transacao = Transaction.objects.filter(
                pk=pagamento.transacao_id,
                usuario=request.user,
            ).first()

        if transacao:
            transacao.tipo = Transaction.Tipo.DESPESA
            transacao.valor = pagamento.valor
            transacao.data = data_pagamento
            transacao.categoria = conta.categoria
            transacao.descricao = f"Pagamento: {conta.nome_servico}"
            transacao.origem = Transaction.Origem.MANUAL
            transacao.status = Transaction.Status.CONFIRMADA
            transacao.tipo_recorrencia = Transaction.TipoRecorrencia.FIXA
            transacao.save()
        else:
            transacao = Transaction.objects.create(
                usuario=request.user,
                tipo=Transaction.Tipo.DESPESA,
                valor=pagamento.valor,
                data=data_pagamento,
                categoria=conta.categoria,
                descricao=f"Pagamento: {conta.nome_servico}",
                origem=Transaction.Origem.MANUAL,
                status=Transaction.Status.CONFIRMADA,
                tipo_recorrencia=Transaction.TipoRecorrencia.FIXA,
            )

        pagamento.transacao = transacao
        pagamento.status = RecurringBillPayment.Status.PAGO
        pagamento.pago_em = timezone.now()
        pagamento.save(
            update_fields=[
                "transacao",
                "status",
                "pago_em",
            ]
        )

    messages.success(
        request,
        (
            f"{conta.nome_servico} marcada como paga. "
            f"A despesa foi registrada no extrato em "
            f"{data_pagamento.strftime('%d/%m/%Y')}."
        ),
    )

    return redirect("transactions:assinaturas")


@login_required
def remover_assinatura(request, pk):
    recorrencia = get_object_or_404(
        RecurringBill,
        pk=pk,
        usuario=request.user,
    )

    if request.method == "POST":
        recorrencia.ativo = False
        recorrencia.save()

        messages.info(
            request,
            f"{recorrencia.nome_servico} removida das recorrências.",
        )

    return redirect("transactions:assinaturas")


@login_required
def orcamentos(request):
    """UC06 — Definir o teto mensal por categoria."""
    if request.method == "POST":
        form = CategoryBudgetForm(
            request.POST,
            user=request.user,
        )

        if form.is_valid():
            orcamento, _criado = CategoryBudget.objects.update_or_create(
                usuario=request.user,
                categoria=form.cleaned_data["categoria"],
                defaults={
                    "teto_mensal": form.cleaned_data["teto_mensal"],
                },
            )

            messages.success(
                request,
                f"Limite de {orcamento.categoria.nome} definido "
                f"em R$ {orcamento.teto_mensal}.",
            )

            return redirect("transactions:orcamentos")
    else:
        form = CategoryBudgetForm(user=request.user)

    orcamentos_atuais = (
        CategoryBudget.objects.filter(usuario=request.user)
        .select_related("categoria")
    )

    return render(
        request,
        "transactions/orcamentos.html",
        {
            "form": form,
            "orcamentos_atuais": orcamentos_atuais,
        },
    )


@login_required
def categorias(request):
    """Lista categorias padrão e próprias e permite criar novas."""
    if request.method == "POST":
        form = CategoryForm(
            request.POST,
            user=request.user,
        )

        if form.is_valid():
            categoria = form.save()

            messages.success(
                request,
                f'Categoria "{categoria.nome}" criada.',
            )

            return redirect("transactions:categorias")
    else:
        form = CategoryForm(user=request.user)

    minhas_despesa = Category.objects.filter(
        usuario=request.user,
        tipo=Category.Tipo.DESPESA,
    )

    minhas_receita = Category.objects.filter(
        usuario=request.user,
        tipo=Category.Tipo.RECEITA,
    )

    padrao_despesa = Category.objects.filter(
        usuario__isnull=True,
        tipo=Category.Tipo.DESPESA,
    )

    padrao_receita = Category.objects.filter(
        usuario__isnull=True,
        tipo=Category.Tipo.RECEITA,
    )

    return render(
        request,
        "transactions/categorias.html",
        {
            "form": form,
            "minhas_despesa": minhas_despesa,
            "minhas_receita": minhas_receita,
            "padrao_despesa": padrao_despesa,
            "padrao_receita": padrao_receita,
        },
    )


@login_required
def excluir_categoria(request, pk):
    categoria = get_object_or_404(
        Category,
        pk=pk,
        usuario=request.user,
    )

    if request.method == "POST":
        em_uso = (
            categoria.transacoes.exists()
            or categoria.recorrencias.exists()
            or categoria.orcamentos.exists()
        )

        if em_uso:
            messages.error(
                request,
                f'Não é possível excluir "{categoria.nome}" porque '
                "ela já está sendo usada em algum lançamento, "
                "assinatura ou orçamento.",
            )
        else:
            categoria.delete()
            messages.success(request, "Categoria excluída.")

    return redirect("transactions:categorias")


@login_required
def extrato_view(request):
    hoje = timezone.localdate()

    try:
        mes = int(request.GET.get("mes", hoje.month))
        ano = int(request.GET.get("ano", hoje.year))
    except (ValueError, TypeError):
        mes, ano = hoje.month, hoje.year

    if not 1 <= mes <= 12:
        mes = hoje.month

    transacoes = Transaction.objects.filter(
        usuario=request.user,
        data__month=mes,
        data__year=ano,
    ).order_by("data")

    context = {
        "transacoes": transacoes,
        "mes_atual": mes,
        "ano_atual": ano,
        "hoje": hoje,
    }

    return render(
        request,
        "transactions/extrato.html",
        context,
    )


@login_required
def lancamentos_futuros_view(request):
    """Exibe previsão agrupada por parcelamento e recorrência futura."""
    hoje = timezone.localdate()

    transacoes_futuras = Transaction.objects.filter(
        usuario=request.user,
        status=Transaction.Status.PENDENTE,
        data__gte=hoje,
    ).select_related("categoria").order_by("data")

    total_despesas_futuras = (
        transacoes_futuras.filter(
            tipo=Transaction.Tipo.DESPESA,
        ).aggregate(t=Sum("valor"))["t"]
        or Decimal("0.00")
    )

    total_receitas_futuras = (
        transacoes_futuras.filter(
            tipo=Transaction.Tipo.RECEITA,
        ).aggregate(t=Sum("valor"))["t"]
        or Decimal("0.00")
    )

    grupos_dict = defaultdict(list)
    itens_avulsos = []

    for transacao in transacoes_futuras:
        if transacao.grupo_recorrencia_id:
            grupos_dict[transacao.grupo_recorrencia_id].append(
                transacao,
            )
        else:
            itens_avulsos.append(transacao)

    agrupados = []

    for grupo_id, lista in grupos_dict.items():
        primeira = lista[0]
        ultima = lista[-1]
        qtd = len(lista)
        valor_unitario = primeira.valor
        valor_total_grupo = sum(item.valor for item in lista)

        agrupados.append(
            {
                "descricao": primeira.descricao or "Sem descrição",
                "categoria": primeira.categoria,
                "tipo": primeira.tipo,
                "qtd_restante": qtd,
                "total_parcelas": primeira.total_parcelas,
                "valor_unitario": valor_unitario,
                "valor_total_grupo": valor_total_grupo,
                "data_inicio": primeira.data,
                "data_fim": ultima.data,
                "exemplo_id": primeira.pk,
            }
        )

    return render(
        request,
        "transactions/lancamentos_futuros.html",
        {
            "agrupados": agrupados,
            "itens_avulsos": itens_avulsos,
            "total_despesas_futuras": total_despesas_futuras,
            "total_receitas_futuras": total_receitas_futuras,
        },
    )


@login_required
def comparativo_mensal(request):
    hoje = timezone.localdate().replace(day=1)

    meses_labels_6 = []
    receitas_data_6 = []
    despesas_data_6 = []

    for i in range(5, -1, -1):
        mes_ref = hoje - relativedelta(months=i)
        mes_fim = (
            mes_ref
            + relativedelta(months=1)
            - relativedelta(days=1)
        )

        meses_labels_6.append(mes_ref.strftime("%b/%Y"))

        tot_rec = (
            Transaction.objects.filter(
                usuario=request.user,
                tipo=Transaction.Tipo.RECEITA,
                data__range=[mes_ref, mes_fim],
                status=Transaction.Status.CONFIRMADA,
            ).aggregate(total=Sum("valor"))["total"]
            or 0
        )

        tot_desp = (
            Transaction.objects.filter(
                usuario=request.user,
                tipo=Transaction.Tipo.DESPESA,
                data__range=[mes_ref, mes_fim],
                status=Transaction.Status.CONFIRMADA,
            ).aggregate(total=Sum("valor"))["total"]
            or 0
        )

        receitas_data_6.append(float(tot_rec))
        despesas_data_6.append(float(tot_desp))

    meses_labels_12 = []
    receitas_data_12 = []
    despesas_data_12 = []

    for i in range(11, -1, -1):
        mes_ref = hoje - relativedelta(months=i)
        mes_fim = (
            mes_ref
            + relativedelta(months=1)
            - relativedelta(days=1)
        )

        meses_labels_12.append(mes_ref.strftime("%b/%y"))

        tot_rec_12 = (
            Transaction.objects.filter(
                usuario=request.user,
                tipo=Transaction.Tipo.RECEITA,
                data__range=[mes_ref, mes_fim],
                status=Transaction.Status.CONFIRMADA,
            ).aggregate(total=Sum("valor"))["total"]
            or 0
        )

        tot_desp_12 = (
            Transaction.objects.filter(
                usuario=request.user,
                tipo=Transaction.Tipo.DESPESA,
                data__range=[mes_ref, mes_fim],
                status=Transaction.Status.CONFIRMADA,
            ).aggregate(total=Sum("valor"))["total"]
            or 0
        )

        receitas_data_12.append(float(tot_rec_12))
        despesas_data_12.append(float(tot_desp_12))

    anos_qs = (
        Transaction.objects.filter(
            usuario=request.user,
            status=Transaction.Status.CONFIRMADA,
        )
        .annotate(ano=TruncYear("data"))
        .values("ano")
        .distinct()
        .order_by("ano")
    )

    anos_labels = []
    receitas_anos_data = []
    despesas_anos_data = []

    for item in anos_qs:
        ano_dt = item["ano"]

        if ano_dt:
            ano_str = str(ano_dt.year)
            anos_labels.append(ano_str)

            tot_rec_ano = (
                Transaction.objects.filter(
                    usuario=request.user,
                    tipo=Transaction.Tipo.RECEITA,
                    data__year=ano_dt.year,
                    status=Transaction.Status.CONFIRMADA,
                ).aggregate(total=Sum("valor"))["total"]
                or 0
            )

            tot_desp_ano = (
                Transaction.objects.filter(
                    usuario=request.user,
                    tipo=Transaction.Tipo.DESPESA,
                    data__year=ano_dt.year,
                    status=Transaction.Status.CONFIRMADA,
                ).aggregate(total=Sum("valor"))["total"]
                or 0
            )

            receitas_anos_data.append(float(tot_rec_ano))
            despesas_anos_data.append(float(tot_desp_ano))

    mes_atual_inicio = hoje
    mes_atual_fim = (
        hoje
        + relativedelta(months=1)
        - relativedelta(days=1)
    )

    gastos_categoria = (
        Transaction.objects.filter(
            usuario=request.user,
            tipo=Transaction.Tipo.DESPESA,
            data__range=[mes_atual_inicio, mes_atual_fim],
            status=Transaction.Status.CONFIRMADA,
        )
        .values("categoria__nome")
        .annotate(total=Sum("valor"))
        .order_by("-total")
    )

    cat_labels = [
        item["categoria__nome"] or "Outros"
        for item in gastos_categoria
    ]

    cat_data = [
        float(item["total"])
        for item in gastos_categoria
    ]

    context = {
        "meses_labels_json": json.dumps(meses_labels_6),
        "receitas_data_json": json.dumps(receitas_data_6),
        "despesas_data_json": json.dumps(despesas_data_6),
        "meses_labels_12_json": json.dumps(meses_labels_12),
        "receitas_data_12_json": json.dumps(receitas_data_12),
        "despesas_data_12_json": json.dumps(despesas_data_12),
        "anos_labels_json": json.dumps(anos_labels),
        "receitas_anos_data_json": json.dumps(receitas_anos_data),
        "despesas_anos_data_json": json.dumps(despesas_anos_data),
        "cat_labels_json": json.dumps(cat_labels),
        "cat_data_json": json.dumps(cat_data),
    }

    return render(
        request,
        "transactions/comparativo.html",
        context,
    )


@login_required
def reajustar_grupo_recorrente(request, grupo_id):
    """Reajusta parcelas futuras pertencentes ao mesmo grupo."""
    transacoes_futuras = Transaction.objects.filter(
        usuario=request.user,
        grupo_recorrencia_id=grupo_id,
        status=Transaction.Status.PENDENTE,
    )

    if request.method == "POST":
        novo_valor = request.POST.get("novo_valor")

        if novo_valor:
            try:
                valor_decimal = Decimal(novo_valor)
                if valor_decimal <= 0:
                    raise InvalidOperation
            except (InvalidOperation, ValueError):
                messages.error(request, "Informe um valor válido.")
            else:
                transacoes_futuras.update(valor=valor_decimal)

                messages.success(
                    request,
                    f"Todas as parcelas futuras foram reajustadas "
                    f"para R$ {valor_decimal}!",
                )

                return redirect("transactions:futuros")

    primeira = transacoes_futuras.first()

    return render(
        request,
        "transactions/reajustar_grupo.html",
        {
            "transacoes": transacoes_futuras,
            "item_base": primeira,
        },
    )
