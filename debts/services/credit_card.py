from datetime import date
from dateutil.relativedelta import relativedelta
from transactions.models import Transaction, Category


def calcular_data_fatura(data_compra, dia_fechamento, dia_vencimento):
    """
    Calcula a data exata de vencimento da fatura onde a compra deve ser alocada,
    considerando o dia de fechamento do cartão.
    """
    # Se a compra ocorreu no dia ou após o fechamento, vai para a fatura do próximo mês
    if data_compra.day >= dia_fechamento:
        data_fatura_base = data_compra + relativedelta(months=1)
    else:
        data_fatura_base = data_compra

    # Ajusta para o dia de vencimento do cartão
    try:
        data_vencimento = data_fatura_base.replace(day=min(dia_vencimento, 28))
    except ValueError:
        data_vencimento = data_fatura_base

    return data_vencimento


def processar_compra_cartao(divida_cartao, valor_parcela, quantidade_parcelas, data_compra, descricao, user):
    """
    Registra uma compra realizada no cartão de crédito, distribuindo as parcelas
    nas faturas futuras apropriadas com base na data de fechamento/vencimento.
    """
    dia_fechamento = max(divida_cartao.dia_vencimento - 7, 1)  # Estima fechamento 7 dias antes do vencimento
    dia_vencimento = divida_cartao.dia_vencimento

    categoria = Category.objects.filter(nome="Cartão de Crédito", tipo="despesa").first()
    if not categoria:
        categoria = Category.objects.filter(tipo="despesa").first()

    primeira_fatura = calcular_data_fatura(data_compra, dia_fechamento, dia_vencimento)

    for i in range(quantidade_parcelas):
        data_vencimento_parcela = primeira_fatura + relativedelta(months=i)
        
        Transaction.objects.create(
            usuario=user,
            tipo=Transaction.Tipo.DESPESA,
            valor=valor_parcela,
            data=data_vencimento_parcela,
            categoria=categoria,
            descricao=f"{descricao} ({i+1}/{quantidade_parcelas}) — {divida_cartao.credor}",
            origem=Transaction.Origem.MANUAL,
            status=Transaction.Status.PENDENTE,
            tipo_recorrencia=Transaction.TipoRecorrencia.PARCELADA if quantidade_parcelas > 1 else Transaction.TipoRecorrencia.UNICA,
            parcela_atual=i + 1,
            total_parcelas=quantidade_parcelas,
            debito_fatura_cartao=divida_cartao,
        )