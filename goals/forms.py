from django import forms

from .models import Goal


class GoalForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = ["nome", "valor_alvo"]
        widgets = {
            "nome": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex.: Viagem, Trocar de celular"}),
            "valor_alvo": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        }


class ContribuicaoForm(forms.Form):
    valor = forms.DecimalField(
        min_value=0.01,
        max_digits=8,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "placeholder": "Outro valor"}),
    )
