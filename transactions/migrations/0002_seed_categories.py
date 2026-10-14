from django.db import migrations

DESPESAS = [
    ("Alimentação/Supermercado", "bi-basket", "#FF6B6B"),
    ("Moradia/Casa", "bi-house-door", "#4D96FF"),
    ("Transporte", "bi-bus-front", "#FFB84D"),
    ("Educação", "bi-mortarboard", "#6BCB77"),
    ("Lazer", "bi-controller", "#C77DFF"),
    ("Assinaturas", "bi-collection-play", "#FF9F1C"),
    ("Outros", "bi-three-dots", "#9CA3AF"),
]

RECEITAS = [
    ("Salário", "bi-cash-stack", "#2EC4B6"),
    ("Bicos/Extras", "bi-briefcase", "#118AB2"),
    ("Venda de Usados", "bi-bag-check", "#06D6A0"),
    ("Benefício", "bi-gift", "#EF476F"),
    ("Outros", "bi-plus-circle", "#9CA3AF"),
]


def seed(apps, schema_editor):
    Category = apps.get_model("transactions", "Category")
    for nome, icone, cor in DESPESAS:
        Category.objects.get_or_create(
            nome=nome, tipo="despesa", defaults={"icone": icone, "cor": cor, "is_padrao": True}
        )
    for nome, icone, cor in RECEITAS:
        Category.objects.get_or_create(
            nome=nome, tipo="receita", defaults={"icone": icone, "cor": cor, "is_padrao": True}
        )


def remove(apps, schema_editor):
    Category = apps.get_model("transactions", "Category")
    nomes_despesa = [n for n, _, _ in DESPESAS]
    nomes_receita = [n for n, _, _ in RECEITAS]
    Category.objects.filter(tipo="despesa", nome__in=nomes_despesa).delete()
    Category.objects.filter(tipo="receita", nome__in=nomes_receita).delete()


class Migration(migrations.Migration):
    dependencies = [("transactions", "0001_initial")]
    operations = [migrations.RunPython(seed, remove)]
