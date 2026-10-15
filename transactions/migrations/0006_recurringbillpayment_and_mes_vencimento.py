from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("transactions", "0005_transaction_grupo_recorrencia_id_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="recurringbill",
            name="mes_vencimento",
            field=models.PositiveSmallIntegerField(
                choices=[
                    (1, "Janeiro"),
                    (2, "Fevereiro"),
                    (3, "Março"),
                    (4, "Abril"),
                    (5, "Maio"),
                    (6, "Junho"),
                    (7, "Julho"),
                    (8, "Agosto"),
                    (9, "Setembro"),
                    (10, "Outubro"),
                    (11, "Novembro"),
                    (12, "Dezembro"),
                ],
                null=True,
                blank=True,
                help_text="Mês do vencimento, utilizado nas despesas anuais.",
            ),
        ),
        migrations.CreateModel(
            name="RecurringBillPayment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("data_vencimento", models.DateField()),
                (
                    "valor",
                    models.DecimalField(
                        max_digits=10,
                        decimal_places=2,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=10,
                        choices=[
                            ("pendente", "Pendente"),
                            ("pago", "Pago"),
                        ],
                        default="pendente",
                    ),
                ),
                (
                    "pago_em",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                    ),
                ),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                (
                    "conta",
                    models.ForeignKey(
                        to="transactions.recurringbill",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="pagamentos",
                    ),
                ),
                (
                    "transacao",
                    models.ForeignKey(
                        to="transactions.transaction",
                        on_delete=django.db.models.deletion.SET_NULL,
                        null=True,
                        blank=True,
                        related_name="pagamentos_contas_fixas",
                    ),
                ),
            ],
            options={
                "ordering": ["data_vencimento"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("conta", "data_vencimento"),
                        name="unique_conta_fixa_vencimento",
                    ),
                ],
            },
        ),
    ]
