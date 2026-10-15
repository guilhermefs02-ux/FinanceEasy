"""UC14 — Varredura diária automática de vencimentos.

Gera notificações preventivas para contas fixas e dívidas:
- 5 dias antes do vencimento;
- 2 dias antes do vencimento;
- no dia do vencimento;
- quando a parcela da dívida já está vencida.

A varredura pode ser executada pelo management command
varredura_vencimentos ou pelo middleware no primeiro acesso diário.
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta

from django.utils import timezone

from core.models import Notification


DIAS_DE_AVISO = (5, 2, 0)


def _proxima_data_vencimento(
    dia_vencimento: int,
    referencia: date,
) -> date:
    """Encontra o próximo vencimento, ajustando meses mais curtos."""
    ano = referencia.year
    mes = referencia.month

    for _ in range(2):
        ultimo_dia = calendar.monthrange(ano, mes)[1]
        dia = min(dia_vencimento, ultimo_dia)
        candidata = date(ano, mes, dia)

        if candidata >= referencia:
            return candidata

        mes += 1

        if mes > 12:
            mes = 1
            ano += 1

    return candidata


def _vencimento_mes_atual(
    dia_vencimento: int,
    referencia: date,
) -> date:
    """Calcula o vencimento da competência atual, inclusive se atrasado."""
    ultimo_dia = calendar.monthrange(
        referencia.year,
        referencia.month,
    )[1]

    dia = min(dia_vencimento, ultimo_dia)

    return date(
        referencia.year,
        referencia.month,
        dia,
    )


def _formatar_valor(valor) -> str:
    """Formata valores monetários no padrão brasileiro."""
    return (
        f"R$ {valor:,.2f}"
        .replace(",", "_")
        .replace(".", ",")
        .replace("_", ".")
    )


def _mensagem_conta(
    nome: str,
    valor,
    dias_restantes: int,
) -> str:
    valor_fmt = _formatar_valor(valor)

    if dias_restantes == 0:
        return (
            f"Hoje vence a sua conta de {nome} ({valor_fmt}). "
            "Se já pagou, pode ignorar este aviso."
        )

    if dias_restantes == 2:
        return (
            f"Sua conta de {nome} ({valor_fmt}) vence "
            "depois de amanhã. Que tal conferir sua folga de segurança?"
        )

    return (
        f"Sua conta de {nome} ({valor_fmt}) "
        f"vence em {dias_restantes} dias. Ainda dá tempo de se planejar."
    )


def _mensagem_divida(
    divida,
    vencimento: date,
    dias_restantes: int,
) -> str:
    """Monta a mensagem de acordo com a situação da parcela."""
    valor_fmt = _formatar_valor(divida.valor_parcela)

    if dias_restantes < 0:
        return (
            f"A parcela de {divida.credor} ({valor_fmt}) "
            f"venceu em {vencimento.strftime('%d/%m/%Y')} "
            "e pode estar em atraso. Confira a situação do pagamento."
        )

    if dias_restantes == 0:
        return (
            f"Hoje vence a sua parcela de {divida.credor} "
            f"({valor_fmt}). Confira o pagamento para manter "
            "seu saldo atualizado."
        )

    if dias_restantes == 2:
        return (
            f"A parcela de {divida.credor} ({valor_fmt}) "
            "vence depois de amanhã."
        )

    return (
        f"A parcela de {divida.credor} ({valor_fmt}) "
        f"vence em {dias_restantes} dias."
    )


def _pagamento_divida_no_mes(divida, referencia: date) -> bool:
    """Verifica se há pagamento registrado no mês de referência."""
    return divida.pagamentos.filter(
        data_pagamento__year=referencia.year,
        data_pagamento__month=referencia.month,
    ).exists()


def _registrar_aviso_divida(
    user,
    divida,
    vencimento: date,
    dias_restantes: int,
) -> bool:
    """
    Cria o aviso da dívida ou atualiza o aviso existente quando
    a parcela passa da situação preventiva para vencida.

    Retorna True somente quando uma nova notificação é criada.
    """
    chave = f"divida:{divida.pk}:{vencimento.isoformat()}"

    mensagem = _mensagem_divida(
        divida,
        vencimento,
        dias_restantes,
    )

    nivel = (
        Notification.Nivel.URGENTE
        if dias_restantes <= 0
        else Notification.Nivel.ALERTA
    )

    notificacao, criada = Notification.objects.get_or_create(
        usuario=user,
        chave_deduplicacao=chave,
        defaults={
            "mensagem": mensagem,
            "nivel": nivel,
        },
    )

    if criada:
        return True

    # Atualiza a mensagem antiga se a parcela passou a estar vencida.
    if notificacao.mensagem != mensagem:
        mensagem_anterior = notificacao.mensagem.lower()
        estava_vencida = "venceu em" in mensagem_anterior

        notificacao.mensagem = mensagem
        notificacao.nivel = nivel

        campos_atualizados = ["mensagem", "nivel"]

        # Se o aviso preventivo virou aviso de atraso, volta a aparecer
        # como não lido no sininho. Não o reabre diariamente.
        if dias_restantes < 0 and not estava_vencida:
            notificacao.lida = False
            campos_atualizados.append("lida")

        notificacao.save(update_fields=campos_atualizados)

    return False


def run_scan_for_user(user) -> int:
    """Executa a varredura de um usuário e retorna novas notificações."""
    hoje = timezone.localdate()
    criadas = 0

    # ---------------------------------------------------------
    # CONTAS FIXAS
    # Mantém o comportamento preventivo já existente.
    # ---------------------------------------------------------
    contas = user.recorrencias.filter(ativo=True)

    for conta in contas:
        vencimento = _proxima_data_vencimento(
            conta.dia_vencimento,
            hoje,
        )

        dias_restantes = (vencimento - hoje).days

        if dias_restantes not in DIAS_DE_AVISO:
            continue

        chave = f"conta:{conta.pk}:{vencimento.isoformat()}"

        _, criada = Notification.objects.get_or_create(
            usuario=user,
            chave_deduplicacao=chave,
            defaults={
                "mensagem": _mensagem_conta(
                    conta.nome_servico,
                    conta.valor,
                    dias_restantes,
                ),
                "nivel": (
                    Notification.Nivel.URGENTE
                    if dias_restantes == 0
                    else Notification.Nivel.ALERTA
                ),
            },
        )

        criadas += int(criada)

    # ---------------------------------------------------------
    # DÍVIDAS
    # Agora também verifica vencimentos que já passaram.
    # ---------------------------------------------------------
    dividas = user.dividas.filter(
        quitada=False,
        parcelas_pagas__lt=__import__(
            "django.db.models",
            fromlist=["F"],
        ).F("total_parcelas"),
    ).prefetch_related("pagamentos")

    for divida in dividas:
        vencimento = _vencimento_mes_atual(
            divida.dia_vencimento,
            hoje,
        )

        dias_restantes = (vencimento - hoje).days

        # Evita alertar como vencida uma dívida cadastrada depois
        # do vencimento deste mês, quando nenhuma parcela foi paga.
        criada_em = timezone.localtime(divida.criado_em).date()

        if (
            criada_em.year == hoje.year
            and criada_em.month == hoje.month
            and criada_em > vencimento
            and divida.parcelas_pagas == 0
        ):
            continue

        # Não avisa sobre a parcela deste mês se já houve pagamento
        # registrado no mês atual.
        if _pagamento_divida_no_mes(divida, hoje):
            continue

        # As parcelas atrasadas geram aviso independentemente
        # da quantidade de dias decorridos.
        if dias_restantes >= 0 and dias_restantes not in DIAS_DE_AVISO:
            continue

        criada = _registrar_aviso_divida(
            user,
            divida,
            vencimento,
            dias_restantes,
        )

        criadas += int(criada)

    return criadas


def run_scan_for_all_users() -> int:
    """Executa a varredura para todos os usuários ativos."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    total = 0

    for user in User.objects.filter(is_active=True):
        total += run_scan_for_user(user)

    return total
