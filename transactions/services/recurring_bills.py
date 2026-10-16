import calendar
from datetime import date

from django.db import transaction
from django.utils import timezone

from transactions.models import RecurringBill, RecurringBillPayment


def _data_vencimento(ano: int, mes: int, dia: int) -> date:
    """Ajusta o vencimento para o último dia válido do mês."""
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    return date(ano, mes, min(dia, ultimo_dia))


def _proximo_mes(ano: int, mes: int) -> tuple[int, int]:
    """Retorna o ano e o mês seguintes."""
    if mes == 12:
        return ano + 1, 1

    return ano, mes + 1


@transaction.atomic
def gerar_vencimentos_contas_fixas(
    usuario,
    hoje: date | None = None,
) -> int:
    """
    Gera os próximos vencimentos das contas fixas ativas.

    Contas mensais:
        Mantém até 12 vencimentos a partir do próximo vencimento
        ainda não vencido, incluindo o dia atual quando aplicável.

    Contas anuais:
        Mantém até 2 vencimentos anuais a partir do próximo
        vencimento ainda não vencido.

    Vencimentos existentes são preservados, inclusive os que já
    foram pagos, para evitar duplicações e perda do histórico.
    """
    hoje = hoje or timezone.localdate()
    criados = 0

    contas = (
        RecurringBill.objects.filter(
            usuario=usuario,
            ativo=True,
        )
        .select_related("categoria")
        .order_by("pk")
    )

    for conta in contas:
        if conta.periodicidade == RecurringBill.Periodicidade.MENSAL:
            ano = hoje.year
            mes = hoje.month

            primeiro_vencimento = _data_vencimento(
                ano,
                mes,
                conta.dia_vencimento,
            )

            # Se o vencimento deste mês já passou, começa no mês seguinte.
            if primeiro_vencimento < hoje:
                ano, mes = _proximo_mes(ano, mes)

            for _ in range(12):
                vencimento = _data_vencimento(
                    ano,
                    mes,
                    conta.dia_vencimento,
                )

                _, criado = RecurringBillPayment.objects.get_or_create(
                    conta=conta,
                    data_vencimento=vencimento,
                    defaults={
                        "valor": conta.valor,
                    },
                )

                if criado:
                    criados += 1

                ano, mes = _proximo_mes(ano, mes)

        elif conta.periodicidade == RecurringBill.Periodicidade.ANUAL:
            mes = conta.mes_vencimento

            if not mes or not 1 <= mes <= 12:
                continue

            ano = hoje.year

            primeiro_vencimento = _data_vencimento(
                ano,
                mes,
                conta.dia_vencimento,
            )

            # Se o vencimento anual já passou, começa no próximo ano.
            if primeiro_vencimento < hoje:
                ano += 1

            for deslocamento in range(2):
                vencimento = _data_vencimento(
                    ano + deslocamento,
                    mes,
                    conta.dia_vencimento,
                )

                _, criado = RecurringBillPayment.objects.get_or_create(
                    conta=conta,
                    data_vencimento=vencimento,
                    defaults={
                        "valor": conta.valor,
                    },
                )

                if criado:
                    criados += 1

    return criados
