import uuid
from dateutil.relativedelta import relativedelta
from transactions.models import Transaction


def gerar_parcelas_futuras(transacao_base, quantidade_parcelas=None):
    """Gera lançamentos futuros para transações PARCELADAS (com quantidade exata)

    ou projeta 36 meses futuros para transações FIXAS (Salário, Aluguel, etc).
    """
    grupo_id = uuid.uuid4()
    transacao_base.grupo_recorrencia_id = grupo_id

    # Se for FIXA, projetamos 36 meses (3 anos) para a frente e mantemos total_parcelas=1 (ou 36)
    if transacao_base.tipo_recorrencia == Transaction.TipoRecorrencia.FIXA:
        qtd_meses = 36
        transacao_base.total_parcelas = 1  # Evita atribuir None devido à restrição NOT NULL na BD
    else:
        qtd_meses = quantidade_parcelas or transacao_base.total_parcelas or 1
        transacao_base.total_parcelas = qtd_meses

    transacao_base.parcela_atual = 1
    transacao_base.save()

    data_original = transacao_base.data

    # Cria os registos para os meses subsequentes
    for i in range(2, qtd_meses + 1):
        nova_data = data_original + relativedelta(months=i - 1)

        Transaction.objects.create(
            usuario=transacao_base.usuario,
            descricao=transacao_base.descricao,
            valor=transacao_base.valor,
            data=nova_data,
            tipo=transacao_base.tipo,
            categoria=transacao_base.categoria,
            status=Transaction.Status.PENDENTE,
            origem=transacao_base.origem,
            tipo_recorrencia=transacao_base.tipo_recorrencia,
            parcela_atual=i if transacao_base.tipo_recorrencia == Transaction.TipoRecorrencia.PARCELADA else 1,
            total_parcelas=transacao_base.total_parcelas,
            grupo_recorrencia_id=grupo_id,
        )