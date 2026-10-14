from django.urls import path

from . import views

app_name = "goals"

urlpatterns = [
    path("", views.lista_objetivos, name="lista"),
    path("<int:pk>/guardar/", views.guardar_troco, name="guardar_troco"),
]
