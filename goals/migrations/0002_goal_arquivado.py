from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("goals", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="goal",
            name="arquivado",
            field=models.BooleanField(
                default=False,
                help_text="Indica se o objetivo foi arquivado sem apagar seu histórico",
            ),
        ),
    ]
