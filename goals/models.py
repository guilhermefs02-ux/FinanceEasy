```python
from decimal import Decimal

from django.conf import settings
from django.db import models


class Goal(models.Model):
    """UC12 — reservas e objetivos financeiros (RF11), com foco em
    microvalores para a meta padrão "Colchão para Imprevistos"."""

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

    arquivado = models.BooleanField(
        default=False,
        help_text="Indica se o objetivo foi arquivado sem apagar seu histórico",
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    concluido_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-is_colchao_padrao", "criado_em"]

    def __str__(self):
        return self.nome

    @property
    def valor_acumulado(self):
        total = self.contribuicoes.aggregate(
            total=models.Sum("valor")
        )["total"]
        return total or Decimal("0")

    @property
    def percentual_concluido(self):
        if not self.valor_alvo:
            return 0

        return min(
            round(
                float(self.valor_acumulado)
                / float(self.valor_alvo)
                * 100
            ),
            100,
        )


class GoalContribution(models.Model):
    """Cada "guardar um troco" (R$5/R$10/R$20 ou valor livre)."""

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
```
