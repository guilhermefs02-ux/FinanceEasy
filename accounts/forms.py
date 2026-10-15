from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password

from .models import User


def validar_requisitos_senha(senha):
    """Exige maiúscula, minúscula, número e caractere especial."""

    erros = []

    if len(senha) < 8:
        erros.append("A senha deve ter pelo menos 8 caracteres.")

    if not any(c.isupper() for c in senha):
        erros.append("A senha deve conter pelo menos uma letra maiúscula.")

    if not any(c.islower() for c in senha):
        erros.append("A senha deve conter pelo menos uma letra minúscula.")

    if not any(c.isdigit() for c in senha):
        erros.append("A senha deve conter pelo menos um número.")

    if not any(not c.isalnum() for c in senha):
        erros.append(
            "A senha deve conter pelo menos um caractere especial, "
            "como @, #, ! ou $."
        )

    if erros:
        raise forms.ValidationError(erros)


def validar_senha_completa(senha, user=None):
    """Aplica os requisitos próprios e os validadores do Django."""

    validar_requisitos_senha(senha)
    validate_password(senha, user=user)


class CadastroForm(forms.ModelForm):
    """Cadastro com validação de senha."""

    senha = forms.CharField(
        label="Senha",
        min_length=8,
        help_text=(
            "Mínimo de 8 caracteres, com maiúscula, minúscula, "
            "número e caractere especial."
        ),
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Crie uma senha",
                "autocomplete": "new-password",
            }
        ),
    )

    confirmar_senha = forms.CharField(
        label="Confirmar senha",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Repita a senha",
                "autocomplete": "new-password",
            }
        ),
    )

    class Meta:
        model = User
        fields = ["nome_completo", "email", "celular"]
        widgets = {
            "nome_completo": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Como podemos te chamar?",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "seuemail@exemplo.com",
                    "autocomplete": "email",
                }
            ),
            "celular": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "(11) 90000-0000",
                }
            ),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()

        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                "Já existe uma conta com este e-mail."
            )

        return email

    def clean(self):
        cleaned = super().clean()
        senha = cleaned.get("senha")
        confirmar = cleaned.get("confirmar_senha")

        if senha:
            usuario = User(
                nome_completo=cleaned.get("nome_completo", ""),
                email=cleaned.get("email", ""),
            )

            try:
                validar_senha_completa(senha, user=usuario)
            except forms.ValidationError as erro:
                self.add_error("senha", erro)

        if senha and confirmar and senha != confirmar:
            self.add_error(
                "confirmar_senha",
                "As senhas não coincidem.",
            )

        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["senha"])

        if commit:
            user.save()

        return user


class OnboardingContextualForm(forms.ModelForm):
    """Perguntas contextuais opcionais do primeiro acesso."""

    class Meta:
        model = User
        fields = [
            "data_nascimento",
            "sexo",
            "atividade_profissional",
            "escolaridade",
            "renda_mensal_aproximada",
            "tipo_moradia",
            "valor_aluguel_mensal",
        ]
        widgets = {
            "data_nascimento": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "sexo": forms.Select(
                attrs={"class": "form-select"}
            ),
            "atividade_profissional": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "escolaridade": forms.Select(
                attrs={"class": "form-select"}
            ),
            "renda_mensal_aproximada": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "placeholder": "Opcional",
                }
            ),
            "tipo_moradia": forms.Select(
                attrs={"class": "form-select"}
            ),
            "valor_aluguel_mensal": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
        }


class EmailAuthenticationForm(AuthenticationForm):
    """Login com e-mail e senha."""

    username = forms.EmailField(
        label="E-mail",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "seuemail@exemplo.com",
                "autofocus": True,
                "autocomplete": "email",
            }
        ),
    )

    password = forms.CharField(
        label="Senha",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Sua senha",
                "autocomplete": "current-password",
            }
        ),
    )

    error_messages = {
        "invalid_login": (
            "E-mail ou senha incorretos. Confira e tente novamente."
        ),
        "inactive": "Esta conta está inativa.",
    }


class SolicitarRecuperacaoForm(forms.Form):
    email = forms.EmailField(
        label="E-mail cadastrado",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "seuemail@exemplo.com",
                "autocomplete": "email",
            }
        ),
    )


class ConfirmarRecuperacaoForm(forms.Form):
    codigo = forms.CharField(
        label="Código de 6 dígitos",
        max_length=6,
        min_length=6,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "000000",
                "inputmode": "numeric",
                "autocomplete": "one-time-code",
            }
        ),
    )

    nova_senha = forms.CharField(
        label="Nova senha",
        min_length=8,
        help_text=(
            "Mínimo de 8 caracteres, com maiúscula, minúscula, "
            "número e caractere especial."
        ),
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "autocomplete": "new-password",
            }
        ),
    )

    confirmar_nova_senha = forms.CharField(
        label="Confirmar nova senha",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "autocomplete": "new-password",
            }
        ),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean(self):
        cleaned = super().clean()
        senha = cleaned.get("nova_senha")
        confirmar = cleaned.get("confirmar_nova_senha")

        if senha:
            try:
                validar_senha_completa(senha, user=self.user)
            except forms.ValidationError as erro:
                self.add_error("nova_senha", erro)

        if senha and confirmar and senha != confirmar:
            self.add_error(
                "confirmar_nova_senha",
                "As senhas não coincidem.",
            )

        return cleaned
