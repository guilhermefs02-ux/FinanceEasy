from django.urls import path

from . import views

app_name = "goals"

urlpatterns = [
    path(
        "",
        views.lista_objetivos,
        name="lista",
    ),
    path(
        "<int:pk>/guardar/",
        views.guardar_troco,
        name="guardar_troco",
    ),
    path(
        "colchao/editar/",
        views.editar_colchao,
        name="editar_colchao",
    ),
    path(
        "<int:pk>/editar/",
        views.editar_objetivo,
        name="editar_objetivo",
    ),
    path(
        "<int:pk>/excluir/",
        views.excluir_objetivo,
        name="excluir_objetivo",
    ),
]
