import random

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import redirect, render

from debts.models import Debt
from goals.models import Goal
from transactions.models import (
    Category,
    CategoryBudget,
    ImportBatch,
    RecurringBill,
    Transaction,
)

from .forms import (
    CadastroForm,
    ConfirmarRecuperacaoForm,
    EmailAuthenticationForm,
    OnboardingContextualForm,
    SolicitarRecuperacaoForm,
)
from .models import PasswordResetCode, User


def _criar_dados_iniciais(user):
    """Cria o colchão para imprevistos no primeiro acesso."""

    from decimal import Decimal

    Goal.objects.get_or_create(
        usuario=user,
        is_colchao_padrao=True,
        defaults={
            "nome": "Colchão para Imprevistos",
            "valor_alvo": Decimal("150.00"),
        },
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

            messages.success(
                request,
                f"Bem-vindo(a), {user.primeiro_nome}! Sua conta foi criada.",
            )
            return redirect("accounts:onboarding")
    else:
        form = CadastroForm()

    return render(
        request,
        "accounts/cadastro.html",
        {"form": form},
    )


@login_required
def onboarding(request):
    """Perguntas contextuais opcionais do primeiro acesso."""

    if request.method == "POST":
        if "pular" in request.POST:
            messages.info(
                request,
                "Sem problemas — você pode preencher isso depois no seu perfil.",
            )
            return redirect("dashboard:painel")

        form = OnboardingContextualForm(
            request.POST,
            instance=request.user,
        )

        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Prontinho! Isso vai nos ajudar a te dar dicas melhores.",
            )
            return redirect("dashboard:painel")
    else:
        form = OnboardingContextualForm(
            instance=request.user,
        )

    return render(
        request,
        "accounts/onboarding.html",
        {"form": form},
    )


class EmailLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True


def logout_view(request):
    auth_logout(request)
    return redirect("accounts:login")


def solicitar_recuperacao(request):
    """Gera e envia o código de recuperação de senha."""

    if request.method == "POST":
        form = SolicitarRecuperacaoForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data["email"].lower().strip()

            try:
                user = User.objects.get(email=email)
                codigo = f"{random.randint(0, 999999):06d}"

                PasswordResetCode.objects.create(
                    user=user,
                    codigo=codigo,
                )

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
                # Não revela se o e-mail existe.
                pass

            messages.info(
                request,
                "Se este e-mail estiver cadastrado, enviamos um código "
                "de 6 dígitos para ele.",
            )
            return redirect("accounts:confirmar_recuperacao")
    else:
        form = SolicitarRecuperacaoForm()

    return render(
        request,
        "accounts/solicitar_recuperacao.html",
        {"form": form},
    )


def confirmar_recuperacao(request):
    """Valida o código e define a nova senha com os validadores ativos."""

    email = request.session.get("recuperacao_email")

    if not email:
        return redirect("accounts:solicitar_recuperacao")

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        request.session.pop("recuperacao_email", None)
        messages.error(
            request,
            "Não foi possível concluir a recuperação. Solicite um novo código.",
        )
        return redirect("accounts:solicitar_recuperacao")

    if request.method == "POST":
        form = ConfirmarRecuperacaoForm(
            request.POST,
            user=user,
        )

        if form.is_valid():
            codigo = form.cleaned_data["codigo"]

            reset = (
                PasswordResetCode.objects.filter(
                    user=user,
                    codigo=codigo,
                    usado=False,
                )
                .order_by("-criado_em")
                .first()
            )

            if reset and reset.esta_valido():
                user.set_password(
                    form.cleaned_data["nova_senha"]
                )
                user.save(update_fields=["password"])

                reset.usado = True
                reset.save(update_fields=["usado"])

                request.session.pop("recuperacao_email", None)

                messages.success(
                    request,
                    "Senha redefinida! Faça login com a nova senha.",
                )
                return redirect("accounts:login")

            form.add_error(
                "codigo",
                "Código inválido ou expirado.",
            )
    else:
        form = ConfirmarRecuperacaoForm(user=user)

    return render(
        request,
        "accounts/confirmar_recuperacao.html",
        {"form": form},
    )


@login_required
def zerar_dados_usuario(request):
    """Apaga os dados financeiros do usuário autenticado."""

    if request.method == "POST":
        usuario = request.user

        with transaction.atomic():
            # 1. Apaga as transações do usuário.
            # Os pagamentos vinculados deixam de apontar para elas.
            Transaction.objects.filter(
                usuario=usuario
            ).delete()

            # 2. Apaga as contas fixas.
            # Os pagamentos de cada conta fixa são excluídos em cascata,
            # evitando que pagamentos antigos sejam recriados depois.
            RecurringBill.objects.filter(
                usuario=usuario
            ).delete()

            # 3. Apaga os registros de importação financeira.
            ImportBatch.objects.filter(
                usuario=usuario
            ).delete()

            # 4. Apaga dívidas e metas financeiras.
            Debt.objects.filter(
                usuario=usuario
            ).delete()

            Goal.objects.filter(
                usuario=usuario
            ).delete()

            # 5. Apaga os orçamentos por categoria.
            CategoryBudget.objects.filter(
                usuario=usuario
            ).delete()

            # 6. Apaga as categorias personalizadas do usuário.
            # As contas fixas já foram excluídas para evitar conflitos
            # com categorias protegidas por relacionamentos.
            Category.objects.filter(
                usuario=usuario
            ).delete()

            # 7. Apaga as notificações do usuário, se o relacionamento existir.
            if hasattr(usuario, "notificacoes"):
                usuario.notificacoes.all().delete()

        messages.success(
            request,
            "Todos os seus dados financeiros foram apagados com sucesso. "
            "A conta está limpa!",
        )
        return redirect("dashboard:painel")

    return render(
        request,
        "accounts/confirmar_zerar_dados.html",
    )
