"""Teste de fumaça manual (não faz parte do app) — percorre o fluxo
principal da persona usando o test client do Django, sem precisar de
navegador. Rode com: python smoke_test.py
"""
import io
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "financeeasy.settings")

import django

django.setup()

from django.test import Client

erros = []


def checar(nome, condicao, extra=""):
    status = "OK " if condicao else "FALHOU"
    print(f"[{status}] {nome} {extra}")
    if not condicao:
        erros.append(nome)


c = Client()

# 1. Cadastro (UC01)
resp = c.post(
    "/contas/cadastro/",
    {
        "nome_completo": "Maria Teste",
        "email": "maria.teste@example.com",
        "celular": "11999990000",
        "senha": "SenhaForte123",
        "confirmar_senha": "SenhaForte123",
    },
    follow=True,
)
checar("Cadastro cria conta e loga", resp.status_code == 200 and "onboarding" in resp.request["PATH_INFO"], f"status={resp.status_code} path={resp.request['PATH_INFO']}")

# 2. Pular onboarding
resp = c.post("/contas/onboarding/", {"pular": "1"}, follow=True)
checar("Pular onboarding vai pro painel", resp.status_code == 200 and "painel" in resp.request["PATH_INFO"])

# 3. Painel carrega (UC08)
resp = c.get("/painel/")
checar("Painel carrega", resp.status_code == 200)
checar("Painel mostra Sobra Segura", b"Quanto sobra com seguran" in resp.content)

# 4. Logout / Login (UC01/FA01)
c.post("/contas/logout/")
resp = c.post("/contas/login/", {"username": "maria.teste@example.com", "password": "SenhaForte123"}, follow=True)
checar("Login por e-mail funciona", resp.status_code == 200 and "painel" in resp.request["PATH_INFO"])

# 5. Nova despesa (UC03)
from transactions.models import Category

cat_alimentacao = Category.objects.get(nome="Alimentação/Supermercado", tipo="despesa")
resp = c.post(
    "/financas/nova-despesa/",
    {"valor": "45.90", "categoria": cat_alimentacao.pk, "forma_pagamento": "pix", "data": "2026-09-10", "descricao": "Mercado"},
    follow=True,
)
checar("Registrar despesa manual (UC03)", resp.status_code == 200)

# 6. Nova receita (UC02)
cat_salario = Category.objects.get(nome="Salário", tipo="receita")
resp = c.post(
    "/financas/nova-receita/",
    {"valor": "2500.00", "categoria": cat_salario.pk, "data": "2026-09-05", "descricao": "Salário"},
    follow=True,
)
checar("Registrar receita manual (UC02)", resp.status_code == 200)

# 7. Orçamento por categoria (UC06)
resp = c.post("/financas/orcamentos/", {"categoria": cat_alimentacao.pk, "teto_mensal": "50.00"}, follow=True)
checar("Definir limite de categoria (UC06)", resp.status_code == 200)

# Nova despesa que deve estourar 80% do limite
resp = c.post(
    "/financas/nova-despesa/",
    {"valor": "5.00", "categoria": cat_alimentacao.pk, "forma_pagamento": "pix", "data": "2026-09-11", "descricao": "Padaria"},
    follow=True,
)
checar("Alerta de 80% do limite aparece", "atingiram" in resp.content.decode("utf-8"))

# 8. Assinatura recorrente (UC07)
resp = c.post(
    "/financas/assinaturas/",
    {"nome_servico": "Netflix", "categoria": Category.objects.get(nome="Assinaturas", tipo="despesa").pk, "valor": "39.90", "periodicidade": "mensal", "dia_vencimento": "10"},
    follow=True,
)
checar("Cadastrar assinatura (UC07)", resp.status_code == 200 and b"Netflix" in resp.content)

# 9. Importar extrato CSV (UC04) + conciliar (UC05)
csv_conteudo = (
    "Data,Descricao,Valor\n"
    "01/09/2026,IFOOD SP,-35.50\n"
    "02/09/2026,NETFLIX.COM,-39.90\n"
    "03/09/2026,SALARIO EMPRESA X,2500.00\n"
)
arquivo = io.BytesIO(csv_conteudo.encode("utf-8"))
arquivo.name = "extrato_teste.csv"
resp = c.post(
    "/financas/importar/",
    {"arquivo": arquivo, "tipo_conta": "corrente"},
    follow=True,
)
checar("Importação de CSV processa e vai para conciliação", resp.status_code == 200 and "conciliar" in resp.request["PATH_INFO"], f"path={resp.request['PATH_INFO']}")

from transactions.models import ImportBatch, Transaction

batch = ImportBatch.objects.filter(usuario__email="maria.teste@example.com").order_by("-id").first()
checar("Batch de importação criado com 3 novas transações", batch is not None and batch.total_novas == 3, f"total_novas={batch.total_novas if batch else None}")

pendentes = list(batch.transacoes.filter(status="pendente_conciliacao"))
checar("3 transações pendentes de conciliação", len(pendentes) == 3, f"count={len(pendentes)}")

# Checa auto-categorização por regra (IFOOD -> Alimentação, NETFLIX -> Assinaturas)
ifood = next((t for t in pendentes if "IFOOD" in t.descricao_origem_banco), None)
netflix = next((t for t in pendentes if "NETFLIX" in t.descricao_origem_banco), None)
checar("IFOOD categorizado como Alimentação/Supermercado", ifood and ifood.categoria.nome == "Alimentação/Supermercado")
checar("NETFLIX categorizado como Assinaturas", netflix and netflix.categoria.nome == "Assinaturas")

# Aprova conciliação
post_data = {}
for t in pendentes:
    post_data[f"incluir_{t.pk}"] = "on"
    post_data[f"categoria_{t.pk}"] = t.categoria_id
resp = c.post(f"/financas/importar/{batch.pk}/conciliar/", post_data, follow=True)
checar("Conciliação em lote aprova transações", resp.status_code == 200 and "transações importadas" in resp.content.decode("utf-8"))

confirmadas = Transaction.objects.filter(import_batch=batch, status="confirmada").count()
checar("3 transações confirmadas após conciliação", confirmadas == 3, f"confirmadas={confirmadas}")

# 10. Reimportar o mesmo arquivo deve detectar duplicidade (FE02)
arquivo2 = io.BytesIO(csv_conteudo.encode("utf-8"))
arquivo2.name = "extrato_teste.csv"
resp = c.post("/financas/importar/", {"arquivo": arquivo2, "tipo_conta": "corrente"}, follow=True)
checar("Reimportação detecta 100% duplicidade (FE02)", "já foram importadas" in resp.content.decode("utf-8"))

# 11. Dívidas (UC10/UC11)
resp = c.post(
    "/dividas/nova/",
    {
        "credor": "Cartão Nubank",
        "categoria_passivo": "cartao_credito",
        "saldo_total_devedor": "1200.00",
        "total_parcelas": "12",
        "parcelas_pagas": "0",
        "valor_parcela": "100.00",
        "dia_vencimento": "15",
    },
    follow=True,
)
checar("Cadastrar dívida (UC10)", resp.status_code == 200 and b"Cart\xc3\xa3o Nubank" in resp.content)

from debts.models import Debt

divida = Debt.objects.get(usuario__email="maria.teste@example.com", credor="Cartão Nubank")
resp = c.post(f"/dividas/{divida.pk}/pagar-parcela/", {"debita_saldo_mes": "on"}, follow=True)
divida.refresh_from_db()
checar("Pagar parcela reduz saldo devedor (UC11)", divida.parcelas_pagas == 1 and divida.saldo_total_devedor == 1100)

# 12. Objetivos / microvalores (UC12)
from goals.models import Goal

colchao = Goal.objects.get(usuario__email="maria.teste@example.com", is_colchao_padrao=True)
resp = c.post(f"/objetivos/{colchao.pk}/guardar/", {"valor_atalho": "10.00"}, follow=True)
colchao.refresh_from_db()
checar("Guardar troco de R$10 no colchão (UC12)", colchao.valor_acumulado == 10, f"acumulado={colchao.valor_acumulado}")

# 13. Extrato com filtros (UC09)
resp = c.get("/financas/extrato/?periodo=mensal")
checar("Extrato com filtro de período carrega", resp.status_code == 200)

# 14. Varredura de vencimentos (UC14) via management command
from django.core.management import call_command

call_command("varredura_vencimentos")
checar("Management command de varredura roda sem erro", True)

print()
if erros:
    print(f"{len(erros)} verificações falharam: {erros}")
    raise SystemExit(1)
else:
    print("Todas as verificações passaram.")
