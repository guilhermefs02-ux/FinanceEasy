from django import forms
from django.forms import formset_factory
from django.utils import timezone

from .models import (
    Category,
    CategoryBudget,
    ImportBatch,
    RecurringBill,
    Transaction,
)


class ReceitaForm(forms.ModelForm):
    """UC02 — Nova Entrada / Receita."""

    class Meta:
        model = Transaction
        fields = [
            "valor",
            "data",
            "categoria",
            "descricao",
            "tipo_recorrencia",
            "total_parcelas",
        ]
        widgets = {
            "valor": forms.NumberInput(
                attrs={
                    "class": "form-control form-control-lg",
                    "step": "0.01",
                    "placeholder": "0,00",
                    "autofocus": True,
                }
            ),
            "data": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "categoria": forms.Select(attrs={"class": "form-select"}),
            "descricao": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Descrição (opcional)",
                }
            ),
            "tipo_recorrencia": forms.Select(
                attrs={"class": "form-select"}
            ),
            "total_parcelas": forms.NumberInput(
                attrs={"class": "form-control", "min": 1, "value": 1}
            ),
        }
        labels = {
            "valor": "Valor (por parcela, se parcelado)",
            "data": "Data",
            "categoria": "Categoria",
            "descricao": "Descrição",
            "tipo_recorrencia": "Tipo de lançamento",
            "total_parcelas": "Quantidade de parcelas",
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Category.objects.all()
        qs = (
            qs.para_usuario(user, Category.Tipo.RECEITA)
            if user
            else qs.filter(tipo=Category.Tipo.RECEITA)
        )
        self.fields["categoria"].queryset = qs
        self.fields["categoria"].empty_label = None

        if not self.instance.pk:
            self.fields["data"].initial = timezone.localdate()

        self.fields["descricao"].required = False

    def save(self, commit=True):
        transacao = super().save(commit=False)
        transacao.tipo = Transaction.Tipo.RECEITA

        if commit:
            transacao.save()

        return transacao


class DespesaForm(forms.ModelForm):
    """UC03 — Nova Despesa (apontamento rápido)."""

    class Meta:
        model = Transaction
        fields = [
            "valor",
            "categoria",
            "forma_pagamento",
            "data",
            "descricao",
            "tipo_recorrencia",
            "total_parcelas",
        ]
        widgets = {
            "valor": forms.NumberInput(
                attrs={
                    "class": "form-control form-control-lg",
                    "step": "0.01",
                    "placeholder": "0,00",
                    "autofocus": True,
                }
            ),
            "categoria": forms.Select(attrs={"class": "form-select"}),
            "forma_pagamento": forms.Select(
                attrs={"class": "form-select"}
            ),
            "data": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "descricao": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Descrição (opcional)",
                }
            ),
            "tipo_recorrencia": forms.Select(
                attrs={"class": "form-select"}
            ),
            "total_parcelas": forms.NumberInput(
                attrs={"class": "form-control", "min": 1, "value": 1}
            ),
        }
        labels = {
            "valor": "Valor (por parcela, se parcelado)",
            "categoria": "Categoria",
            "forma_pagamento": "Forma de pagamento",
            "data": "Data",
            "descricao": "Descrição",
            "tipo_recorrencia": "Tipo de lançamento",
            "total_parcelas": "Quantidade de parcelas",
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Category.objects.all()
        qs = (
            qs.para_usuario(user, Category.Tipo.DESPESA)
            if user
            else qs.filter(tipo=Category.Tipo.DESPESA)
        )
        self.fields["categoria"].queryset = qs
        self.fields["categoria"].empty_label = None

        if not self.instance.pk:
            self.fields["data"].initial = timezone.localdate()

        self.fields["descricao"].required = False

    def save(self, commit=True):
        transacao = super().save(commit=False)
        transacao.tipo = Transaction.Tipo.DESPESA

        if commit:
            transacao.save()

        return transacao


class ImportUploadForm(forms.Form):
    """UC04, passo 2-3 — upload do extrato/fatura."""

    arquivo = forms.FileField(
        label="Selecione o arquivo (.ofx, .csv ou .pdf)",
        widget=forms.ClearableFileInput(
            attrs={
                "class": "form-control",
                "accept": ".ofx,.csv,.pdf",
            }
        ),
    )
    tipo_conta = forms.ChoiceField(
        choices=ImportBatch.TipoConta.choices,
        widget=forms.RadioSelect,
        initial=ImportBatch.TipoConta.CORRENTE,
        label="O que você está importando?",
    )


class RecurringBillForm(forms.ModelForm):
    """UC07 — contas fixas e assinaturas recorrentes."""

    class Meta:
        model = RecurringBill
        fields = [
            "nome_servico",
            "categoria",
            "valor",
            "periodicidade",
            "mes_vencimento",
            "dia_vencimento",
        ]
        widgets = {
            "nome_servico": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ex.: Netflix, Aluguel, Internet",
                }
            ),
            "categoria": forms.Select(
                attrs={"class": "form-select"}
            ),
            "valor": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "periodicidade": forms.Select(
                attrs={
                    "class": "form-select",
                    "id": "id_periodicidade",
                }
            ),
            "mes_vencimento": forms.Select(
                attrs={
                    "class": "form-select",
                    "id": "id_mes_vencimento",
                }
            ),
            "dia_vencimento": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                    "max": 31,
                    "placeholder": "Dia do vencimento",
                }
            ),
        }
        labels = {
            "nome_servico": "Nome da despesa",
            "categoria": "Categoria",
            "valor": "Valor",
            "periodicidade": "Periodicidade",
            "mes_vencimento": "Mês do vencimento (despesas anuais)",
            "dia_vencimento": "Dia do vencimento",
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        qs = Category.objects.all()
        self.fields["categoria"].queryset = (
            qs.para_usuario(user, Category.Tipo.DESPESA)
            if user
            else qs.filter(tipo=Category.Tipo.DESPESA)
        )

        self.fields["mes_vencimento"].required = False

    def clean(self):
        cleaned = super().clean()
        periodicidade = cleaned.get("periodicidade")
        mes = cleaned.get("mes_vencimento")
        dia = cleaned.get("dia_vencimento")

        if periodicidade == RecurringBill.Periodicidade.ANUAL and not mes:
            self.add_error(
                "mes_vencimento",
                "Selecione o mês de vencimento da despesa anual.",
            )

        if (
            periodicidade == RecurringBill.Periodicidade.MENSAL
            and mes
        ):
            cleaned["mes_vencimento"] = None

        if dia and mes and periodicidade == RecurringBill.Periodicidade.ANUAL:
            dias_por_mes = {
                1: 31,
                2: 29,
                3: 31,
                4: 30,
                5: 31,
                6: 30,
                7: 31,
                8: 31,
                9: 30,
                10: 31,
                11: 30,
                12: 31,
            }

            if dia > dias_por_mes.get(mes, 31):
                self.add_error(
                    "dia_vencimento",
                    "O dia informado não existe no mês selecionado.",
                )

        return cleaned


class CategoryBudgetForm(forms.ModelForm):
    """UC06 — teto mensal por categoria."""

    class Meta:
        model = CategoryBudget
        fields = ["categoria", "teto_mensal"]
        widgets = {
            "categoria": forms.Select(
                attrs={"class": "form-select"}
            ),
            "teto_mensal": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Category.objects.all()
        self.fields["categoria"].queryset = (
            qs.para_usuario(user, Category.Tipo.DESPESA)
            if user
            else qs.filter(tipo=Category.Tipo.DESPESA)
        )


class CategoryForm(forms.ModelForm):
    """Criação de categoria própria pelo usuário."""

    class Meta:
        model = Category
        fields = ["nome", "tipo", "icone", "cor"]
        widgets = {
            "nome": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "Ex.: Academia, Cabeleireiro, Curso de inglês"
                    ),
                }
            ),
            "tipo": forms.Select(
                attrs={"class": "form-select"}
            ),
            "icone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "bi-tag (opcional — veja icons.getbootstrap.com)"
                    ),
                }
            ),
            "cor": forms.TextInput(
                attrs={
                    "class": "form-control form-control-color",
                    "type": "color",
                }
            ),
        }
        labels = {
            "nome": "Nome da categoria",
            "tipo": "Tipo",
            "icone": "Ícone (Bootstrap Icons)",
            "cor": "Cor",
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields["icone"].required = False
        self.fields["cor"].required = False
        self.fields["cor"].initial = "#6c63ff"

    def clean_nome(self):
        return self.cleaned_data["nome"].strip()

    def clean(self):
        cleaned = super().clean()
        nome = cleaned.get("nome")
        tipo = cleaned.get("tipo")

        if nome and tipo and self.user is not None:
            ja_existe = (
                Category.objects.para_usuario(self.user, tipo)
                .filter(nome__iexact=nome)
                .exists()
            )
            if ja_existe:
                self.add_error(
                    "nome",
                    "Você já tem uma categoria com esse nome para este tipo.",
                )

        return cleaned

    def save(self, commit=True):
        categoria = super().save(commit=False)
        categoria.usuario = self.user
        categoria.is_padrao = False

        if not categoria.icone:
            categoria.icone = "bi-tag"

        if not categoria.cor:
            categoria.cor = "#6c63ff"

        if commit:
            categoria.save()

        return categoria


class LoteDespesaItemForm(forms.Form):
    """Uma linha do lançamento em lote de despesas."""

    valor = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control form-control-sm",
                "step": "0.01",
                "placeholder": "0,00",
            }
        ),
    )
    categoria = forms.ModelChoiceField(
        queryset=Category.objects.none(),
        widget=forms.Select(
            attrs={"class": "form-select form-select-sm"}
        ),
    )
    forma_pagamento = forms.ChoiceField(
        choices=[("", "—")] + list(Transaction.FormaPagamento.choices),
        required=False,
        widget=forms.Select(
            attrs={"class": "form-select form-select-sm"}
        ),
    )
    data = forms.DateField(
        widget=forms.DateInput(
            attrs={
                "class": "form-control form-control-sm",
                "type": "date",
            }
        )
    )
    descricao = forms.CharField(
        required=False,
        max_length=255,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-sm",
                "placeholder": "Descrição (opcional)",
            }
        ),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        if user is not None:
            self.fields["categoria"].queryset = (
                Category.objects.para_usuario(
                    user,
                    Category.Tipo.DESPESA,
                )
            )


class LoteReceitaItemForm(forms.Form):
    """Uma linha do lançamento em lote de receitas."""

    valor = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control form-control-sm",
                "step": "0.01",
                "placeholder": "0,00",
            }
        ),
    )
    categoria = forms.ModelChoiceField(
        queryset=Category.objects.none(),
        widget=forms.Select(
            attrs={"class": "form-select form-select-sm"}
        ),
    )
    data = forms.DateField(
        widget=forms.DateInput(
            attrs={
                "class": "form-control form-control-sm",
                "type": "date",
            }
        )
    )
    descricao = forms.CharField(
        required=False,
        max_length=255,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-sm",
                "placeholder": "Descrição (opcional)",
            }
        ),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        if user is not None:
            self.fields["categoria"].queryset = (
                Category.objects.para_usuario(
                    user,
                    Category.Tipo.RECEITA,
                )
            )


class LoteRecorrenciaItemForm(forms.Form):
    """Uma linha do lançamento em lote de despesas fixas/recorrentes."""

    nome_servico = forms.CharField(
        max_length=120,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-sm",
                "placeholder": "Ex.: Aluguel, Internet, Netflix",
            }
        ),
    )
    categoria = forms.ModelChoiceField(
        queryset=Category.objects.none(),
        widget=forms.Select(
            attrs={"class": "form-select form-select-sm"}
        ),
    )
    valor = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control form-control-sm",
                "step": "0.01",
                "placeholder": "0,00",
            }
        ),
    )
    periodicidade = forms.ChoiceField(
        choices=[("", "—")] + list(RecurringBill.Periodicidade.choices),
        widget=forms.Select(
            attrs={"class": "form-select form-select-sm"}
        ),
    )
    mes_vencimento = forms.TypedChoiceField(
        choices=[("", "— Selecione o mês —")] + RecurringBill.MESES,
        required=False,
        coerce=int,
        empty_value=None,
        widget=forms.Select(
            attrs={"class": "form-select form-select-sm"}
        ),
    )
    dia_vencimento = forms.IntegerField(
        min_value=1,
        max_value=31,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control form-control-sm",
                "placeholder": "Dia (1-31)",
            }
        ),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        if user is not None:
            self.fields["categoria"].queryset = (
                Category.objects.para_usuario(
                    user,
                    Category.Tipo.DESPESA,
                )
            )

    def clean(self):
        cleaned = super().clean()
        periodicidade = cleaned.get("periodicidade")
        mes = cleaned.get("mes_vencimento")
        dia = cleaned.get("dia_vencimento")

        if periodicidade == RecurringBill.Periodicidade.ANUAL and not mes:
            self.add_error(
                "mes_vencimento",
                "Selecione o mês de vencimento da despesa anual.",
            )

        if periodicidade == RecurringBill.Periodicidade.MENSAL and mes:
            cleaned["mes_vencimento"] = None

        if (
            dia
            and mes
            and periodicidade == RecurringBill.Periodicidade.ANUAL
        ):
            dias_por_mes = {
                1: 31,
                2: 29,
                3: 31,
                4: 30,
                5: 31,
                6: 30,
                7: 31,
                8: 31,
                9: 30,
                10: 31,
                11: 30,
                12: 31,
            }

            if dia > dias_por_mes.get(mes, 31):
                self.add_error(
                    "dia_vencimento",
                    "O dia informado não existe no mês selecionado.",
                )

        return cleaned


LoteDespesaFormSet = formset_factory(
    LoteDespesaItemForm,
    extra=5,
)
LoteReceitaFormSet = formset_factory(
    LoteReceitaItemForm,
    extra=5,
)
LoteRecorrenciaFormSet = formset_factory(
    LoteRecorrenciaItemForm,
    extra=5,
)
