"""UC14 — Varredura diária automática de vencimentos.

Gera notificações para contas fixas e dívidas:
- 5 dias antes do vencimento;
- 2 dias antes do vencimento;
- no dia do vencimento;
- após o vencimento, enquanto a obrigação continuar pendente.

A rotina pode ser executada pelo comando varredura_vencimentos
ou pelo middleware no primeiro acesso autenticado do dia.
"""

from __future__ import annotations

import calendar
from datetime import date

from django.db.models import F
from django.utils import timezone

from core.models import Notification


DIAS_DE_AVISO = (5, 2, 0)


def _data_vencimento(ano: int, mes: int, dia: int) -> date:
    """Ajusta o dia para o último dia do mês quando necessário."""
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    return date(ano, mes, min(dia, ultimo_dia))


def _vencimento_conta(conta, referencia: date) -> date | None:
    """Calcula o vencimento da ocorrência atual da conta recorrente."""
    if conta.periodicidade == "anual":
        if not conta.mes_vencimento:
            return None

        mes = conta.mes_vencimento
    else:
        mes = referencia.month

    return _data_vencimento(
        referencia.year,
        mes,
        conta.dia_vencimento,
    )


def _vencimento_mes_atual(dia_vencimento: int, referencia: date) -> date:
    """Calcula o vencimento da dívida na competência atual."""
    return _data_vencimento(
        referencia.year,
        referencia.month,
        dia_vencimento,
    )


def _formatar_valor(valor) -> str:
    """Formata valores monetários no padrão brasileiro."""
    return (
        f"R$ {valor:,.2f}"
        .replace(",", "_")
        .replace(".", ",")
        .replace("_", ".")
    )


def _mensagem_conta(nome: str, valor, vencimento: date, dias_restantes: int) -> str:
    """Cria a mensagem correspondente à situação da conta fixa."""
    valor_fmt = _formatar_valor(valor)

    if dias_restantes < 0:
        return (
            f"A conta de {nome} ({valor_fmt}) venceu em "
            f"{vencimento:%d/%m/%Y} e continua pendente. "
            "Confira a situação do pagamento."
        )

    if dias_restantes == 0:
        return (
            f"Hoje vence a sua conta de {nome} ({valor_fmt}). "
            "Se já pagou, confira se o pagamento foi registrado."
        )

    if dias_restantes == 2:
        return (
            f"Sua conta de {nome} ({valor_fmt}) vence "
            "depois de amanhã. Confira seu planejamento financeiro."
        )

    return (
        f"Sua conta de {nome} ({valor_fmt}) vence em "
        f"{dias_restantes} dias. Ainda dá tempo de se planejar."
    )


def _mensagem_divida(divida, vencimento: date, dias_restantes: int) -> str:
    """Cria a mensagem correspondente à situação da dívida."""
    valor_fmt = _formatar_valor(divida.valor_parcela)

    if dias_restantes < 0:
        return (
            f"A parcela de {divida.credor} ({valor_fmt}) venceu em "
            f"{vencimento:%d/%m/%Y} e pode estar em atraso. "
            "Confira a situação do pagamento."
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


def _atualizar_notificacao_existente(
    notificacao: Notification,
    mensagem: str,
    nivel: str,
    dias_restantes: int,
) -> None:
    """Atualiza o texto e reabre o aviso quando ele passa a estar atrasado."""
    if notificacao.mensagem == mensagem and notificacao.nivel == nivel:
        return

    mensagem_anterior = notificacao.mensagem.lower()
    estava_vencida = "venceu em" in mensagem_anterior

    notificacao.mensagem = mensagem
    notificacao.nivel = nivel

    campos_atualizados = ["mensagem", "nivel"]

    # Reabre o aviso somente na transição para atraso.
    if dias_restantes < 0 and not estava_vencida:
        notificacao.lida = False
        campos_atualizados.append("lida")

    notificacao.save(update_fields=campos_atualizados)


def _registrar_aviso_conta(
    user,
    conta,
    vencimento: date,
    dias_restantes: int,
) -> bool:
    """Cria ou atualiza o aviso de uma ocorrência de conta fixa."""
    chave = f"conta:{conta.pk}:{vencimento.isoformat()}"

    mensagem = _mensagem_conta(
        conta.nome_servico,
        conta.valor,
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

    if not criada:
        _atualizar_notificacao_existente(
            notificacao,
            mensagem,
            nivel,
            dias_restantes,
        )

    return criada


def _pagamento_divida_no_mes(divida, referencia: date) -> bool:
    """Verifica se existe pagamento da dívida no mês de referência."""
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
    """Cria ou atualiza o aviso da dívida sem duplicar a mesma ocorrência."""
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

    if not criada:
        _atualizar_notificacao_existente(
            notificacao,
            mensagem,
            nivel,
            dias_restantes,
        )

    return criada


def run_scan_for_user(user) -> int:
    """Executa a varredura de um usuário e retorna as notificações novas."""
    hoje = timezone.localdate()
    criadas = 0

    # ---------------------------------------------------------
    # CONTAS FIXAS
    # Utiliza o mesmo registro de ocorrência da Central de Avisos.
    # ---------------------------------------------------------
    contas = user.recorrencias.filter(ativo=True)

    for conta in contas:
        vencimento = _vencimento_conta(conta, hoje)

        if vencimento is None:
            continue

        pagamento, _ = conta.pagamentos.get_or_create(
            data_vencimento=vencimento,
            defaults={
                "valor": conta.valor,
                "status": "pendente",
            },
        )

        # Contas já pagas não devem gerar notificações.
        if pagamento.status == "pago":
            continue

        dias_restantes = (vencimento - hoje).days

        # Avisos preventivos nos dias definidos e avisos após o vencimento.
        if dias_restantes >= 0 and dias_restantes not in DIAS_DE_AVISO:
            continue

        criada = _registrar_aviso_conta(
            user,
            conta,
            vencimento,
            dias_restantes,
        )

        criadas += int(criada)

    # ---------------------------------------------------------
    # DÍVIDAS
    # O modelo atual não armazena uma data individual para cada
    # parcela; por isso, utiliza o dia cadastrado como referência.
    # ---------------------------------------------------------
    dividas = (
        user.dividas.filter(
            quitada=False,
            parcelas_pagas__lt=F("total_parcelas"),
        )
        .prefetch_related("pagamentos")
    )

    for divida in dividas:
        vencimento = _vencimento_mes_atual(
            divida.dia_vencimento,
            hoje,
        )

        dias_restantes = (vencimento - hoje).days

        criada_em = timezone.localtime(divida.criado_em).date()

        # Não considerar atrasada uma dívida cadastrada depois
        # do vencimento do mês, se nenhuma parcela foi paga.
        if (
            criada_em.year == hoje.year
            and criada_em.month == hoje.month
            and criada_em > vencimento
            and divida.parcelas_pagas == 0
        ):
            continue

        # Mantém a mesma regra já utilizada pela Central de Avisos.
        if _pagamento_divida_no_mes(divida, hoje):
            continue

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
