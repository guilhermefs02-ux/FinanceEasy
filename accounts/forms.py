from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import User


class CadastroForm(forms.ModelForm):
    """UC01, passos 2-3 — formulário inicial: Nome, E-mail, Celular, Senha."""

    senha = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Crie uma senha"}),
        min_length=8,
        help_text="Mínimo de 8 caracteres.",
    )
    confirmar_senha = forms.CharField(
        label="Confirmar senha",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Repita a senha"}),
    )

    class Meta:
        model = User
        fields = ["nome_completo", "email", "celular"]
        widgets = {
            "nome_completo": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Como podemos te chamar?"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "seuemail@exemplo.com"}
            ),
            "celular": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "(11) 90000-0000"}
            ),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Já existe uma conta com este e-mail.")
        return email

    def clean(self):
        cleaned = super().clean()
        senha = cleaned.get("senha")
        confirmar = cleaned.get("confirmar_senha")
        if senha and confirmar and senha != confirmar:
            self.add_error("confirmar_senha", "As senhas não coincidem.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["senha"])
        if commit:
            user.save()
        return user


class OnboardingContextualForm(forms.ModelForm):
    """UC01, passo 4 — perguntas contextuais opcionais.

    Nunca é obrigatório: a view sempre oferece "Fazer isso mais tarde"
    para respeitar a diretriz anti-ansiedade da persona.
    """

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
            "data_nascimento": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "sexo": forms.Select(attrs={"class": "form-select"}),
            "atividade_profissional": forms.TextInput(attrs={"class": "form-control"}),
            "escolaridade": forms.Select(attrs={"class": "form-select"}),
            "renda_mensal_aproximada": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "placeholder": "Opcional"}
            ),
            "tipo_moradia": forms.Select(attrs={"class": "form-select"}),
            "valor_aluguel_mensal": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        }


class EmailAuthenticationForm(AuthenticationForm):
    """UC01/FA01 — login com e-mail e senha."""

    username = forms.EmailField(
        label="E-mail",
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "seuemail@exemplo.com", "autofocus": True}
        ),
    )
    password = forms.CharField(
        label="Senha",
        strip=False,
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Sua senha"}),
    )

    error_messages = {
        "invalid_login": "E-mail ou senha incorretos. Confira e tente novamente.",
        "inactive": "Esta conta está inativa.",
    }


class SolicitarRecuperacaoForm(forms.Form):
    email = forms.EmailField(
        label="E-mail cadastrado",
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "seuemail@exemplo.com"}),
    )


class ConfirmarRecuperacaoForm(forms.Form):
    codigo = forms.CharField(
        label="Código de 6 dígitos",
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "000000", "inputmode": "numeric"}),
    )
    nova_senha = forms.CharField(
        label="Nova senha",
        min_length=8,
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    confirmar_nova_senha = forms.CharField(
        label="Confirmar nova senha",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("nova_senha") != cleaned.get("confirmar_nova_senha"):
            self.add_error("confirmar_nova_senha", "As senhas não coincidem.")
        return cleaned
