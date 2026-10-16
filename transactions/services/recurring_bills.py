import calendar
from datetime import date

from django.db import transaction
from django.utils import timezone

from transactions.models import RecurringBill, RecurringBillPayment


def _data_vencimento(ano: int, mes: int, dia: int) -> date:
    """Ajusta o vencimento para o último dia válido do mês."""
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    return date(ano, mes, min(dia, ultimo_dia))


@transaction.atomic
def gerar_vencimentos_contas_fixas(usuario, hoje: date | None = None) -> int:
    """
    Cria os próximos vencimentos das contas fixas ativas.

    Contas mensais:
        Cria até 12 vencimentos futuros.

    Contas anuais:
        Cria até 2 vencimentos futuros, considerando o mês e o dia
        configurados para a conta.

    Vencimentos existentes são preservados para evitar duplicações.
    """
    hoje = hoje or timezone.localdate()
    criados = 0

    contas = RecurringBill.objects.filter(
        usuario=usuario,
        ativo=True,
    ).select_related("categoria")

    for conta in contas:
        if conta.periodicidade == RecurringBill.Periodicidade.MENSAL:
            ano = hoje.year
            mes = hoje.month

            primeiro_vencimento = _data_vencimento(
                ano,
                mes,
                conta.dia_vencimento,
            )

            if primeiro_vencimento < hoje:
                if mes == 12:
                    ano += 1
                    mes = 1
                else:
                    mes += 1

            for _ in range(12):
                vencimento = _data_vencimento(
                    ano,
                    mes,
                    conta.dia_vencimento,
                )

                _, criado = RecurringBillPayment.objects.get_or_create(
                    conta=conta,
                    data_vencimento=vencimento,
                    defaults={"valor": conta.valor},
                )

                if criado:
                    criados += 1

                if mes == 12:
                    ano += 1
                    mes = 1
                else:
                    mes += 1

        elif conta.periodicidade == RecurringBill.Periodicidade.ANUAL:
            mes = conta.mes_vencimento

            if not mes:
                continue

            ano = hoje.year

            primeiro_vencimento = _data_vencimento(
                ano,
                mes,
                conta.dia_vencimento,
            )

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
                    defaults={"valor": conta.valor},
                )

                if criado:
                    criados += 1

    return criados
