from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("cadastro/", views.cadastro, name="cadastro"),
    path("onboarding/", views.onboarding, name="onboarding"),
    path("login/", views.EmailLoginView.as_view(), name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("recuperar-senha/", views.solicitar_recuperacao, name="solicitar_recuperacao"),
    path("recuperar-senha/confirmar/", views.confirmar_recuperacao, name="confirmar_recuperacao"),
    path("zerar-dados/", views.zerar_dados_usuario, name="zerar_dados"),
]
