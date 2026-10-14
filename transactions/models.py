import hashlib

from django.conf import settings
from django.db import models


class CategoryQuerySet(models.QuerySet):
    def para_usuario(self, user, tipo=None):
        """Categorias padrão (globais) + as pessoais deste usuário."""
        qs = self.filter(models.Q(usuario__isnull=True) | models.Q(usuario=user))
        if tipo:
            qs = qs.filter(tipo=tipo)
        return qs


class Category(models.Model):
    """Categorias de receita/despesa (RF04-RF10). Os registros padrão
    (``usuario=None``) são criados pela migração de dados (veja
    transactions/migrations) e ficam disponíveis para todos os usuários.
    Um usuário também pode criar categorias próprias (``usuario`` preenchido),
    visíveis só para ele, além das padrão.
    """

    class Tipo(models.TextChoices):
        RECEITA = "receita", "Receita"
        DESPESA = "despesa", "Despesa"

    nome = models.CharField(max_length=60)
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    icone = models.CharField(
        max_length=40, default="bi-tag", help_text="Classe do Bootstrap Icons"
    )
    cor = models.CharField(max_length=20, default="#6c63ff")
    is_padrao = models.BooleanField(default=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="categorias_personalizadas",
        help_text="Em branco = categoria padrão (todos veem). Preenchido = categoria pessoal, só deste usuário.",
    )

    objects = CategoryQuerySet.as_manager()

    class Meta:
        verbose_name_plural = "categorias"
        ordering = ["tipo", "nome"]
        unique_together = ["nome", "tipo", "usuario"]

    def __str__(self):
        return self.nome


class CategoryBudget(models.Model):
    """UC06 — teto mensal definido pelo usuário para uma categoria de despesa."""

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orcamentos")
    categoria = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="orcamentos")
    teto_mensal = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ["usuario", "categoria"]

    def __str__(self):
        return f"{self.categoria} até R$ {self.teto_mensal}/mês"


class ImportBatch(models.Model):
    """UC04 — um upload de extrato/fatura."""

    class Formato(models.TextChoices):
        OFX = "ofx", "OFX"
        CSV = "csv", "CSV"
        PDF = "pdf", "PDF"

    class TipoConta(models.TextChoices):
        CORRENTE = "corrente", "Conta corrente"
        FATURA_CARTAO = "fatura_cartao", "Fatura de cartão de crédito"

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="importacoes")
    arquivo_nome = models.CharField(max_length=255)
    formato = models.CharField(max_length=5, choices=Formato.choices)
    tipo_conta = models.CharField(max_length=15, choices=TipoConta.choices, default=TipoConta.CORRENTE)
    cartao_divida = models.ForeignKey(
        "debts.Debt", null=True, blank=True, on_delete=models.SET_NULL, related_name="importacoes"
    )
    importado_em = models.DateTimeField(auto_now_add=True)
    total_linhas = models.PositiveIntegerField(default=0)
    total_novas = models.PositiveIntegerField(default=0)
    total_duplicadas = models.PositiveIntegerField(default=0)
    concluido = models.BooleanField(default=False)

    class Meta:
        ordering = ["-importado_em"]

    def __str__(self):
        return f"{self.arquivo_nome} ({self.get_formato_display()})"


class Transaction(models.Model):
    """RF04/RF05 — receitas e despesas, manuais ou importadas (UC02, UC03,
    UC04, UC05)."""

    class Tipo(models.TextChoices):
        RECEITA = "receita", "Receita"
        DESPESA = "despesa", "Despesa"

    class FormaPagamento(models.TextChoices):
        DINHEIRO = "dinheiro", "Dinheiro"
        PIX = "pix", "PIX"
        DEBITO = "debito", "Débito"
        CREDITO = "credito", "Crédito"
        VALE = "vale", "Vale"

    class Origem(models.TextChoices):
        MANUAL = "manual", "Lançamento manual"
        IMPORTADO = "importado", "Importado de extrato"

    class Status(models.TextChoices):
        CONFIRMADA = "confirmada", "Confirmada"
        PENDENTE = "pendente_conciliacao", "Pendente de conciliação"
    
    class TipoRecorrencia(models.TextChoices):
        UNICA = 'UNICA', 'Única / Pontual'
        FIXA = 'FIXA', 'Fixa / Recorrente'
        PARCELADA = 'PARCELADA', 'Parcelada'

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="transacoes")
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data = models.DateField()
    categoria = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="transacoes", null=True, blank=True
    )
    descricao = models.CharField(max_length=255, blank=True)
    forma_pagamento = models.CharField(
        max_length=10, choices=FormaPagamento.choices, blank=True
    )
    origem = models.CharField(max_length=10, choices=Origem.choices, default=Origem.MANUAL)
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.CONFIRMADA)
    import_batch = models.ForeignKey(
        ImportBatch, null=True, blank=True, on_delete=models.SET_NULL, related_name="transacoes"
    )
    descricao_origem_banco = models.CharField(
        max_length=255, blank=True, help_text="Texto bruto vindo do extrato, antes da categorização"
    )
    categoria_sugerida_confianca = models.CharField(
        max_length=10,
        blank=True,
        choices=[("alta", "Alta"), ("baixa", "Baixa")],
        help_text="Usado na tela de conciliação (UC05) para o marcador verde/amarelo",
    )
    hash_dedup = models.CharField(max_length=64, blank=True, db_index=True)
    debito_fatura_cartao = models.ForeignKey(
        "debts.Debt", null=True, blank=True, on_delete=models.SET_NULL, related_name="transacoes_fatura"
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    tipo_recorrencia = models.CharField(
        max_length=10,
        choices=TipoRecorrencia.choices,
        default=TipoRecorrencia.UNICA,
        verbose_name='Tipo de Recorrência',
    )

    parcela_atual = models.PositiveIntegerField(
        default=1,
        verbose_name='Parcela Atual',
    )

    total_parcelas = models.PositiveIntegerField(
        default=1,
        verbose_name='Total de Parcelas',
    )

    grupo_recorrencia_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name='ID do Grupo de Recorrência',
    )

    @property
    def identificador_parcela(self):
        """Retorna a identificação da parcela ou da recorrência."""
        if (
            self.tipo_recorrencia == self.TipoRecorrencia.PARCELADA
            and self.total_parcelas > 1
        ):
            return f'{self.parcela_atual}/{self.total_parcelas}'
        
        if self.tipo_recorrencia == self.TipoRecorrencia.FIXA:
            return 'Fixa'
        
        return ""

    class Meta:
        ordering = ["-data", "-criado_em"]
        indexes = [models.Index(fields=["usuario", "data"])]

    def __str__(self):
        sinal = "+" if self.tipo == self.Tipo.RECEITA else "-"
        return f"{sinal}R$ {self.valor} em {self.data:%d/%m/%Y}"

    @staticmethod
    def calcular_hash(usuario_id, data, valor, descricao):
        base = f"{usuario_id}|{data}|{valor}|{(descricao or '').strip().lower()}"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()

    def save(self, *args, **kwargs):
        if not self.hash_dedup:
            self.hash_dedup = self.calcular_hash(
                self.usuario_id, self.data, self.valor, self.descricao_origem_banco or self.descricao
            )
        super().save(*args, **kwargs)


class RecurringBill(models.Model):
    """UC07 — contas fixas e assinaturas recorrentes. Também cobre RF03
    (despesas essenciais de moradia) quando a categoria é Moradia/Casa."""

    class Periodicidade(models.TextChoices):
        MENSAL = "mensal", "Mensal"
        ANUAL = "anual", "Anual"

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recorrencias")
    nome_servico = models.CharField(max_length=120)
    categoria = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="recorrencias")
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    periodicidade = models.CharField(max_length=10, choices=Periodicidade.choices, default=Periodicidade.MENSAL)
    dia_vencimento = models.PositiveSmallIntegerField(help_text="Dia do mês (1-31)")
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["dia_vencimento"]

    def __str__(self):
        return f"{self.nome_servico} — R$ {self.valor} ({self.get_periodicidade_display()})"

    @property
    def valor_mensalizado(self):
        if self.periodicidade == self.Periodicidade.ANUAL:
            return round(self.valor / 12, 2)
        return self.valor

    @property
    def valor_anualizado(self):
        if self.periodicidade == self.Periodicidade.ANUAL:
            return self.valor
        return self.valor * 12
