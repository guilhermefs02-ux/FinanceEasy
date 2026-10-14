from django.urls import path
from . import views

app_name = "debts"

urlpatterns = [
    path("", views.lista_dividas, name="lista"),
    path("nova/", views.nova_divida, name="nova"),
    path("<int:pk>/editar/", views.editar_divida, name="editar"),
    path("<int:pk>/excluir/", views.excluir_divida, name="excluir"),
    path("<int:pk>/pagar/", views.pagar_parcela, name="pagar"),
    path("<int:pk>/fatura/", views.fatura_cartao, name="fatura"),
]