from django import forms

from .models import Debt


class DebtForm(forms.ModelForm):
    """UC10 — Adicionar Nova Dívida."""

    class Meta:
        model = Debt
        fields = [
            "credor",
            "categoria_passivo",
            "saldo_total_devedor",
            "total_parcelas",
            "parcelas_pagas",
            "valor_parcela",
            "dia_vencimento",
        ]
        widgets = {
            "credor": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex.: Nubank, Banco X, Casas Bahia"}),
            "categoria_passivo": forms.Select(attrs={"class": "form-select"}),
            "saldo_total_devedor": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "total_parcelas": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "parcelas_pagas": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "valor_parcela": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "dia_vencimento": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 31}),
        }


class PagamentoParcelaForm(forms.Form):
    debita_saldo_mes = forms.BooleanField(
        label="Debitar este pagamento do meu saldo do mês corrente",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
