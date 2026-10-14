from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("goals", "0002_goal_arquivado"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="goal",
            name="arquivado",
        ),
    ]
