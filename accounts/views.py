import random

from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.db import transaction
from debts.models import Debt
from goals.models import Goal
from transactions.models import Category, Transaction

from .forms import (
    CadastroForm,
    ConfirmarRecuperacaoForm,
    EmailAuthenticationForm,
    OnboardingContextualForm,
    SolicitarRecuperacaoForm,
)
from .models import PasswordResetCode, User


def _criar_dados_iniciais(user):
    """UC12 — a meta padrão "Colchão para Imprevistos" já existe desde o
    primeiro acesso, para a persona nunca ver o app vazio."""
    from decimal import Decimal

    from goals.models import Goal

    Goal.objects.get_or_create(
        usuario=user,
        is_colchao_padrao=True,
        defaults={"nome": "Colchão para Imprevistos", "valor_alvo": Decimal("150.00")},
    )


def cadastro(request):
    if request.user.is_authenticated:
        return redirect("dashboard:painel")

    if request.method == "POST":
        form = CadastroForm(request.POST)
        if form.is_valid():
            user = form.save()
            _criar_dados_iniciais(user)
            auth_login(request, user)
            messages.success(request, f"Bem-vindo(a), {user.primeiro_nome}! Sua conta foi criada.")
            return redirect("accounts:onboarding")
    else:
        form = CadastroForm()

    return render(request, "accounts/cadastro.html", {"form": form})


@login_required
def onboarding(request):
    """UC01, passo 4 — perguntas contextuais, sempre puláveis."""
    if request.method == "POST":
        if "pular" in request.POST:
            messages.info(request, "Sem problemas — você pode preencher isso depois no seu perfil.")
            return redirect("dashboard:painel")

        form = OnboardingContextualForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Prontinho! Isso vai nos ajudar a te dar dicas melhores.")
            return redirect("dashboard:painel")
    else:
        form = OnboardingContextualForm(instance=request.user)

    return render(request, "accounts/onboarding.html", {"form": form})


class EmailLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True


def logout_view(request):
    auth_logout(request)
    return redirect("accounts:login")


def solicitar_recuperacao(request):
    """UC01/FA02, passo 1 — gera e "envia" o código OTP."""
    if request.method == "POST":
        form = SolicitarRecuperacaoForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].lower().strip()
            try:
                user = User.objects.get(email=email)
                codigo = f"{random.randint(0, 999999):06d}"
                PasswordResetCode.objects.create(user=user, codigo=codigo)
                send_mail(
                    subject="FinanceEasy — Código para redefinir sua senha",
                    message=(
                        f"Olá, {user.primeiro_nome}!\n\n"
                        f"Seu código para redefinir a senha é: {codigo}\n"
                        "Ele é válido por 15 minutos.\n\n"
                        "Se você não solicitou isso, ignore este e-mail."
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=True,
                )
                request.session["recuperacao_email"] = email
            except User.DoesNotExist:
                # Não revela se o e-mail existe ou não (RNF03 — segurança).
                pass
            messages.info(
                request,
                "Se este e-mail estiver cadastrado, enviamos um código de 6 dígitos para ele.",
            )
            return redirect("accounts:confirmar_recuperacao")
    else:
        form = SolicitarRecuperacaoForm()

    return render(request, "accounts/solicitar_recuperacao.html", {"form": form})


def confirmar_recuperacao(request):
    """UC01/FA02, passo 2 — valida o OTP e define a nova senha."""
    email = request.session.get("recuperacao_email")
    if not email:
        return redirect("accounts:solicitar_recuperacao")

    if request.method == "POST":
        form = ConfirmarRecuperacaoForm(request.POST)
        if form.is_valid():
            codigo = form.cleaned_data["codigo"]
            try:
                user = User.objects.get(email=email)
                reset = (
                    PasswordResetCode.objects.filter(user=user, codigo=codigo, usado=False)
                    .order_by("-criado_em")
                    .first()
                )
                if reset and reset.esta_valido():
                    user.set_password(form.cleaned_data["nova_senha"])
                    user.save()
                    reset.usado = True
                    reset.save()
                    del request.session["recuperacao_email"]
                    messages.success(request, "Senha redefinida! Faça login com a nova senha.")
                    return redirect("accounts:login")
                form.add_error("codigo", "Código inválido ou expirado.")
            except User.DoesNotExist:
                form.add_error("codigo", "Código inválido ou expirado.")
    else:
        form = ConfirmarRecuperacaoForm()

    return render(request, "accounts/confirmar_recuperacao.html", {"form": form})

@login_required
def zerar_dados_usuario(request):
    """Apaga absolutamente todos os dados financeiros do usuário logado."""
    if request.method == "POST":
        # Garante atrofia completa em uma única transação de banco de dados
        with transaction.atomic():
            Transaction.objects.filter(usuario=request.user).delete()
            Debt.objects.filter(usuario=request.user).delete()
            Goal.objects.filter(usuario=request.user).delete()

            # Apaga categorias personalizadas (mantendo padrões do sistema se houver flag)
            Category.objects.filter(usuario=request.user).delete()

            # Se houver notificações vinculadas
            if hasattr(request.user, "notificacoes"):
                request.user.notificacoes.all().delete()

        messages.success(
            request,
            "Todos os seus dados financeiros foram apagados com sucesso. A conta está limpa!",
        )
        return redirect("dashboard:painel")

    return render(request, "accounts/confirmar_zerar_dados.html")