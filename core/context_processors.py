from calendar import monthrange
from datetime import timedelta

from django.db.models import F
from django.utils import timezone


def privacy_mode(request):
    """Expõe o estado do Modo Privacidade para todos os templates."""
    return {
        "privacy_mode_on": request.session.get(
            "privacy_mode_on",
            False,
        )
    }


def _data_vencimento(ano, mes, dia):
    """Ajusta o vencimento para o último dia do mês, se necessário."""
    ultimo_dia = monthrange(ano, mes)[1]
    return timezone.datetime(ano, mes, min(dia, ultimo_dia)).date()


def _contar_avisos_usuario(user, dias_janela=7):
    """Conta os avisos sem criar ou modificar ocorrências financeiras."""
    hoje = timezone.localdate()
    limite = hoje + timedelta(days=dias_janela)

    vencidos = 0
    a_vencer = 0
    pagamentos_processados = set()

    contas = user.recorrencias.all().prefetch_related("pagamentos")

    for conta in contas:
        # Ocorrências antigas pendentes, inclusive de contas inativas.
        pagamentos_antigos = conta.pagamentos.filter(
            status="pendente",
            data_vencimento__lt=hoje,
        ).order_by("data_vencimento")

        for pagamento in pagamentos_antigos:
            if pagamento.pk not in pagamentos_processados:
                pagamentos_processados.add(pagamento.pk)
                vencidos += 1

        if not conta.ativo:
            continue

        if conta.periodicidade == "anual":
            mes = conta.mes_vencimento
            if not mes:
                continue
        else:
            mes = hoje.month

        vencimento = _data_vencimento(
            hoje.year,
            mes,
            conta.dia_vencimento,
        )

        if vencimento > limite:
            continue

        pagamento = conta.pagamentos.filter(
            data_vencimento=vencimento,
        ).first()

        if pagamento is not None:
            if pagamento.status == "pago":
                continue

            if pagamento.pk in pagamentos_processados:
                continue

            pagamentos_processados.add(pagamento.pk)

        if vencimento < hoje:
            vencidos += 1
        else:
            a_vencer += 1

    dividas = (
        user.dividas.filter(
            quitada=False,
            parcelas_pagas__lt=F("total_parcelas"),
        )
        .prefetch_related("pagamentos")
    )

    for divida in dividas:
        if divida.parcelas_restantes <= 0:
            continue

        vencimento = _data_vencimento(
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
            continue

        pagamento_no_mes = divida.pagamentos.filter(
            data_pagamento__year=hoje.year,
            data_pagamento__month=hoje.month,
        ).exists()

        if pagamento_no_mes:
            continue

        if vencimento < hoje:
            vencidos += 1
        elif vencimento <= limite:
            a_vencer += 1

    return {
        "total_avisos": vencidos + a_vencer,
        "total_avisos_vencidos": vencidos,
        "total_avisos_a_vencer": a_vencer,
    }


def notificacoes(request):
    """Disponibiliza o sino e os contadores da Central de Avisos."""
    contexto = {
        "notificacoes_recentes": [],
        "total_notificacoes_nao_lidas": 0,
        "total_avisos": 0,
        "total_avisos_vencidos": 0,
        "total_avisos_a_vencer": 0,
    }

    if not request.user.is_authenticated:
        return contexto

    notificacoes_usuario = request.user.notificacoes.all().order_by(
        "-criada_em"
    )

    contexto.update({
        "notificacoes_recentes": notificacoes_usuario[:5],
        "total_notificacoes_nao_lidas": (
            notificacoes_usuario.filter(lida=False).count()
        ),
    })

    contexto.update(_contar_avisos_usuario(request.user))

    return contexto
