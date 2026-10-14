from django import forms

from .models import Goal


class GoalForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = ["nome", "valor_alvo"]
        widgets = {
            "nome": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ex.: Viagem, Trocar de celular",
                }
            ),
            "valor_alvo": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0.01",
                }
            ),
        }

    def clean_valor_alvo(self):
        valor = self.cleaned_data["valor_alvo"]

        if valor <= 0:
            raise forms.ValidationError(
                "O valor da meta precisa ser maior que zero."
            )

        return valor


class ContribuicaoForm(forms.Form):
    valor = forms.DecimalField(
        min_value=0.01,
        max_digits=8,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0.01",
                "placeholder": "Outro valor",
            }
        ),
    )
