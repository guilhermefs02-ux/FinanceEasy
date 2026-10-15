from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("goals", "0003_remove_goal_arquivado"),
    ]

    operations = [
        migrations.AddField(
            model_name="goal",
            name="arquivado_em",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="GoalWithdrawal",
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
                ("valor", models.DecimalField(decimal_places=2, max_digits=8)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                (
                    "objetivo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="retiradas",
                        to="goals.goal",
                    ),
                ),
            ],
            options={
                "ordering": ["-criado_em"],
            },
        ),
    ]
