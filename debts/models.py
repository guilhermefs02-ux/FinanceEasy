from django.conf import settings
from django.db import models


class Debt(models.Model):
    """UC10 — dívidas, cartões e parcelamentos. Núcleo da persona
    "Equilibrista Sobrecarregado": este é o módulo prioritário do MVP."""

    class CategoriaPassivo(models.TextChoices):
        CARTAO_CREDITO = "cartao_credito", "Cartão de Crédito"
        CHEQUE_ESPECIAL = "cheque_especial", "Cheque Especial"
        EMPRESTIMO = "emprestimo", "Empréstimo Pessoal"
        CONSIGNADO = "consignado", "Consignado"
        FINANCIAMENTO = "financiamento", "Financiamento"
        CONTA_ATRASADA = "conta_atrasada", "Conta Atrasada"

    # Categorias com juros tipicamente altíssimos — priorizadas no topo do
    # plano de quitação (UC10, passo 5).
    CATEGORIAS_JUROS_ALTOS = {CategoriaPassivo.CHEQUE_ESPECIAL, CategoriaPassivo.CARTAO_CREDITO}

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dividas")
    credor = models.CharField("nome do credor", max_length=120)
    categoria_passivo = models.CharField(max_length=20, choices=CategoriaPassivo.choices)
    saldo_total_devedor = models.DecimalField(max_digits=12, decimal_places=2)
    total_parcelas = models.PositiveIntegerField(default=1)
    parcelas_pagas = models.PositiveIntegerField(default=0)
    valor_parcela = models.DecimalField(max_digits=10, decimal_places=2)
    dia_vencimento = models.PositiveSmallIntegerField(help_text="Dia do mês (1-31)")
    quitada = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["quitada", "dia_vencimento"]

    def __str__(self):
        return f"{self.credor} — {self.get_categoria_passivo_display()}"

    @property
    def eh_juros_alto(self):
        return self.categoria_passivo in self.CATEGORIAS_JUROS_ALTOS

    @property
    def parcelas_restantes(self):
        return max(self.total_parcelas - self.parcelas_pagas, 0)

    @property
    def percentual_quitado(self):
        if self.total_parcelas == 0:
            return 0
        return round(self.parcelas_pagas / self.total_parcelas * 100)

    def registrar_pagamento_parcela(self, debita_saldo_mes=True):
        """UC11 — marca uma parcela como paga e recalcula o saldo devedor."""
        if self.quitada or self.parcelas_restantes <= 0:
            return None

        pagamento = DebtPayment.objects.create(
            divida=self,
            valor=self.valor_parcela,
            numero_parcela=self.parcelas_pagas + 1,
            debitou_saldo_mes=debita_saldo_mes,
        )
        self.parcelas_pagas += 1
        self.saldo_total_devedor = max(self.saldo_total_devedor - self.valor_parcela, 0)
        if self.parcelas_restantes == 0 or self.saldo_total_devedor <= 0:
            self.quitada = True
        self.save()
        return pagamento


class DebtPayment(models.Model):
    """Histórico de parcelas liquidadas (UC11)."""

    divida = models.ForeignKey(Debt, on_delete=models.CASCADE, related_name="pagamentos")
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    numero_parcela = models.PositiveIntegerField()
    data_pagamento = models.DateTimeField(auto_now_add=True)
    debitou_saldo_mes = models.BooleanField(default=True)
    transacao = models.OneToOneField(
        "transactions.Transaction", null=True, blank=True, on_delete=models.SET_NULL, related_name="pagamento_divida"
    )

    class Meta:
        ordering = ["-data_pagamento"]

    def __str__(self):
        return f"Parcela {self.numero_parcela} de {self.divida.credor} — R$ {self.valor}"
