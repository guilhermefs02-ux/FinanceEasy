from django.conf import settings
from django.db import models


class Notification(models.Model):
    """Notificações em tela que simulam o push do UC14 (varredura diária de
    vencimentos) e os alertas preventivos do UC06.

    Não há infraestrutura de push real neste MVP: as mensagens aparecem
    no sino de notificações do topo e, quando fizer sentido, como card no
    painel principal (UC08).
    """

    class Nivel(models.TextChoices):
        INFO = "info", "Informativo"
        ALERTA = "alerta", "Alerta amigável"
        URGENTE = "urgente", "Urgente"

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notificacoes"
    )
    mensagem = models.CharField(max_length=280)
    nivel = models.CharField(max_length=10, choices=Nivel.choices, default=Nivel.INFO)
    lida = models.BooleanField(default=False)
    criada_em = models.DateTimeField(auto_now_add=True)
    # Evita duplicar o mesmo aviso no mesmo dia (ex.: mesma conta, mesmo D-x)
    chave_deduplicacao = models.CharField(max_length=120, blank=True, default="")

    class Meta:
        ordering = ["-criada_em"]
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "chave_deduplicacao"],
                condition=models.Q(chave_deduplicacao__gt=""),
                name="notification_unique_dedup_per_user",
            )
        ]

    def __str__(self):
        return f"[{self.nivel}] {self.mensagem[:40]}"
