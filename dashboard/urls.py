from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path(
        "",
        views.painel,
        name="painel",
    ),
    path(
        "privacidade/",
        views.alternar_privacidade,
        name="alternar_privacidade",
    ),
    path(
        "notificacoes/marcar-lidas/",
        views.marcar_notificacoes_lidas,
        name="marcar_notificacoes_lidas",
    ),
    path(
        "contas/<int:pagamento_id>/marcar-pago/",
        views.marcar_conta_paga,
        name="marcar_conta_paga",
    ),
]
