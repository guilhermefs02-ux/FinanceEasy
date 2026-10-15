from django.urls import path
from transactions.views import lancamentos_futuros_view

from . import views

app_name = "transactions"

urlpatterns = [
    path("nova-receita/", views.registrar_receita, name="registrar_receita"),
    path("nova-despesa/", views.registrar_despesa, name="registrar_despesa"),
    path("lote/despesas/", views.lote_despesas, name="lote_despesas"),
    path("lote/receitas/", views.lote_receitas, name="lote_receitas"),
    path(
        "lote/despesas-fixas/",
        views.lote_despesas_fixas,
        name="lote_despesas_fixas",
    ),
    path("importar/", views.importar_extrato, name="importar_extrato"),
    path(
        "importar/<int:batch_id>/conciliar/",
        views.conciliar,
        name="conciliar",
    ),
    path("extrato/", views.extrato, name="extrato"),
    path(
        "extrato/<int:pk>/editar/",
        views.editar_transacao,
        name="editar_transacao",
    ),
    path(
        "extrato/<int:pk>/excluir/",
        views.excluir_transacao,
        name="excluir_transacao",
    ),
    path("assinaturas/", views.assinaturas, name="assinaturas"),
    path(
        "assinaturas/<int:pk>/remover/",
        views.remover_assinatura,
        name="remover_assinatura",
    ),
    path(
        "assinaturas/pagamento/<int:pagamento_id>/pagar/",
        views.marcar_conta_fixa_paga,
        name="marcar_conta_fixa_paga",
    ),
    path("orcamentos/", views.orcamentos, name="orcamentos"),
    path("categorias/", views.categorias, name="categorias"),
    path(
        "categorias/<int:pk>/excluir/",
        views.excluir_categoria,
        name="excluir_categoria",
    ),
    path(
        "importar/<int:batch_id>/cancelar/",
        views.cancelar_importacao,
        name="cancelar_importacao",
    ),
    path("futuros/", lancamentos_futuros_view, name="futuros"),
    path(
        "reajustar-grupo/<uuid:grupo_id>/",
        views.reajustar_grupo_recorrente,
        name="reajustar_grupo",
    ),
    path(
        "comparativo/",
        views.comparativo_mensal,
        name="comparativo_mensal",
    ),
]
