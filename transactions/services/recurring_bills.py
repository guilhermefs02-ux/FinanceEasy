import calendar
from datetime import date

from django.db import transaction

from transactions.models import RecurringBill, RecurringBillPayment


def _data_vencimento(ano: int, mes: int, dia: int) -> date:
    """Ajusta o dia ao último dia válido do mês."""
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    return date(ano, mes, min(dia, ultimo_dia))


@transaction.atomic
def gerar_vencimentos_contas_fixas(usuario, hoje: date | None = None) -> int:
    """
    Gera vencimentos futuros para as contas fixas ativas do usuário.

    Contas mensais: mantém até 12 ocorrências futuras.
    Contas anuais: mantém até 2 ocorrências futuras.
    Vencimentos existentes são preservados, sem duplicação.
    """
    hoje = hoje or date.today()
    criados = 0

    contas = (
        RecurringBill.objects
        .filter(usuario=usuario, ativo=True)
        .select_related("categoria")
    )

    for conta in contas:
        if conta.periodicidade == RecurringBill.Periodicidade.MENSAL:
            ano = hoje.year
            mes = hoje.month
            primeiro_vencimento = _data_vencimento(
                ano, mes, conta.dia_vencimento
            )

            if primeiro_vencimento < hoje:
                if mes == 12:
                    ano += 1
                    mes = 1
                else:
                    mes += 1

            quantidade = 12

            for _ in range(quantidade):
                vencimento = _data_vencimento(
                    ano, mes, conta.dia_vencimento
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
                ano, mes, conta.dia_vencimento
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
