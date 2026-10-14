from django.db import migrations


def seed(apps, schema_editor):
    Category = apps.get_model("transactions", "Category")
    Category.objects.get_or_create(
        nome="Dívidas/Empréstimos",
        tipo="despesa",
        defaults={"icone": "bi-credit-card", "cor": "#E63946", "is_padrao": True},
    )


def remove(apps, schema_editor):
    Category = apps.get_model("transactions", "Category")
    Category.objects.filter(tipo="despesa", nome="Dívidas/Empréstimos").delete()


class Migration(migrations.Migration):
    dependencies = [("transactions", "0002_seed_categories")]
    operations = [migrations.RunPython(seed, remove)]
