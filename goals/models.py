from datetime import timedelta
from decimal import Decimal
from math import ceil

from django.conf import settings
from django.db import models
from django.utils import timezone


class Goal(models.Model):
    """Objetivos financeiros e reserva de segurança."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="objetivos",
    )
    nome = models.CharField(max_length=120)
    valor_alvo = models.DecimalField(max_digits=10, decimal_places=2)

    is_colchao_padrao = models.BooleanField(
        default=False,
        help_text="Meta padrão 'Colchão para Imprevistos' criada no primeiro acesso",
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    concluido_em = models.DateTimeField(null=True, blank=True)
    arquivado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-is_colchao_padrao", "criado_em"]

    def __str__(self):
        return self.nome

    @property
    def valor_acumulado(self):
        total_contribuicoes = (
            self.contribuicoes.aggregate(total=models.Sum("valor"))["total"]
            or Decimal("0.00")
        )

        total_retiradas = (
            self.retiradas.aggregate(total=models.Sum("valor"))["total"]
            or Decimal("0.00")
        )

        return total_contribuicoes - total_retiradas

    @property
    def percentual_concluido(self):
        if not self.valor_alvo:
            return 0

        percentual = (
            float(self.valor_acumulado)
            / float(self.valor_alvo)
            * 100
        )

        return min(max(round(percentual), 0), 100)

    @property
    def data_arquivamento(self):
        if not self.concluido_em:
            return None

        return self.concluido_em + timedelta(days=10)

    @property
    def dias_para_arquivar(self):
        data_limite = self.data_arquivamento

        if not data_limite:
            return None

        segundos_restantes = (
            data_limite - timezone.now()
        ).total_seconds()

        return max(0, ceil(segundos_restantes / 86400))

    def atualizar_status_conclusao(self):
        """Atualiza a conclusão conforme o saldo atual."""

        if self.arquivado_em:
            return

        saldo = self.valor_acumulado
        alterou = False

        if saldo >= self.valor_alvo and not self.concluido_em:
            self.concluido_em = timezone.now()
            alterou = True

        elif saldo < self.valor_alvo and self.concluido_em:
            self.concluido_em = None
            alterou = True

        if alterou:
            self.save(update_fields=["concluido_em"])


class GoalContribution(models.Model):
    """Registro de dinheiro guardado em um objetivo."""

    objetivo = models.ForeignKey(
        Goal,
        on_delete=models.CASCADE,
        related_name="contribuicoes",
    )
    valor = models.DecimalField(max_digits=8, decimal_places=2)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return f"+R$ {self.valor} em {self.objetivo.nome}"


class GoalWithdrawal(models.Model):
    """Registro independente de uma retirada de dinheiro."""

    objetivo = models.ForeignKey(
        Goal,
        on_delete=models.CASCADE,
        related_name="retiradas",
    )
    valor = models.DecimalField(max_digits=8, decimal_places=2)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return f"-R$ {self.valor} de {self.objetivo.nome}"


def atualizar_objetivos_e_arquivar(usuario):
    """
    Atualiza o status dos objetivos e arquiva os que foram concluídos
    há pelo menos 10 dias, preservando seus registros financeiros.
    """

    objetivos = Goal.objects.filter(
        usuario=usuario,
        arquivado_em__isnull=True,
    )

    for objetivo in objetivos.iterator():
        objetivo.atualizar_status_conclusao()

    limite = timezone.now() - timedelta(days=10)

    objetivos_vencidos = Goal.objects.filter(
        usuario=usuario,
        arquivado_em__isnull=True,
        concluido_em__isnull=False,
        concluido_em__lte=limite,
    )

    return objetivos_vencidos.update(
        arquivado_em=timezone.now()
    )
