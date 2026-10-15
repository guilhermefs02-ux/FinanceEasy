from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("goals", "0002_goalwithdrawal_arquivado_em"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="goal",
            name="arquivado",
        ),
    ]
