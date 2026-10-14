from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Prefetch
from django.shortcuts import redirect, render

from goals.models import Goal, GoalContribution
from transactions.models import Transaction

from .services.hgbrasil import obter_dados_financeiros

def _inicio_fim_mes(referencia: date):
inicio = referencia.replace(day=1)

if referencia.month == 12:
    fim = date(referencia.year + 1, 1, 1) - timedelta(days=1)
else:
    fim = date(referencia.year, referencia.month + 1, 1) - timedelta(days=1)

return inicio, fim

def _proximas_contas(user, dias_janela=7):
"""Busca contas fixas, assinaturas e parcelas de dívidas próximas do vencimento."""
from core.services.due_date_scan import _proxima_data_vencimento

hoje = date.today()
limite = hoje + timedelta(days=dias_janela)
itens = []

for conta in user.recorrencias.filter(ativo=True):
    vencimento = _proxima_data_vencimento(conta.dia_vencimento, hoje)

    if hoje <= vencimento <= limite:
        itens.append(
            {
                "tipo": "conta",
                "nome": conta.nome_servico,
                "valor": conta.valor_mensalizado,
                "vencimento": vencimento,
                "categoria": conta.categoria,
            }
        )

for divida in user.dividas.filter(quitada=False):
    vencimento = _proxima_data_vencimento(divida.dia_vencimento, hoje)

    if hoje <= vencimento <= limite:
        itens.append(
            {
                "tipo": "divida",
                "nome": divida.credor,
                "valor": divida.valor_parcela,
                "vencimento": vencimento,
                "categoria": None,
            }
        )

itens.sort(key=lambda item: item["vencimento"])
return itens

@login_required
def painel(request):
hoje = date.today()
inicio_mes, fim_mes = _inicio_fim_mes(hoje)

transacoes_mes = Transaction.objects.filter(
    usuario=request.user,
    status=Transaction.Status.CONFIRMADA,
    data__range=[inicio_mes, fim_mes],
)

total_receitas = (
    transacoes_mes.filter(tipo=Transaction.Tipo.RECEITA)
    .aggregate(t=Sum("valor"))["t"]
    or Decimal("0")
)

total_despesas = (
    transacoes_mes.filter(tipo=Transaction.Tipo.DESPESA)
    .aggregate(t=Sum("valor"))["t"]
    or Decimal("0")
)

receitas_confirmadas = (
    Transaction.objects.filter(
        usuario=request.user,
        status=Transaction.Status.CONFIRMADA,
        tipo=Transaction.Tipo.RECEITA,
    ).aggregate(t=Sum("valor"))["t"]
    or Decimal("0")
)

despesas_confirmadas = (
    Transaction.objects.filter(
        usuario=request.user,
        status=Transaction.Status.CONFIRMADA,
        tipo=Transaction.Tipo.DESPESA,
    ).aggregate(t=Sum("valor"))["t"]
    or Decimal("0")
)

saldo_disponivel = receitas_confirmadas - despesas_confirmadas

proximas_contas = _proximas_contas(request.user, dias_janela=7)

total_a_vencer_7_dias = sum(
    (item["valor"] for item in proximas_contas),
    start=Decimal("0"),
)

sobra_segura = saldo_disponivel - total_a_vencer_7_dias

top_categorias = (
    transacoes_mes.filter(tipo=Transaction.Tipo.DESPESA)
    .values("categoria__nome", "categoria__cor", "categoria__icone")
    .annotate(total=Sum("valor"))
    .order_by("-total")[:3]
)

maior_categoria_total = max(
    (categoria["total"] for categoria in top_categorias),
    default=Decimal("0"),
)

dados_hgbrasil = obter_dados_financeiros()

# Colchão para imprevistos já utilizado no painel.
colchao = Goal.objects.filter(
    usuario=request.user,
    is_colchao_padrao=True,
).first()

# Todas as metas pertencentes ao usuário logado.
# As contribuições são carregadas antecipadamente para reduzir consultas.
objetivos = list(
    Goal.objects.filter(usuario=request.user)
    .prefetch_related(
        Prefetch(
            "contribuicoes",
            queryset=GoalContribution.objects.only("objetivo_id", "valor"),
        )
    )
    .order_by("-is_colchao_padrao", "criado_em")
)

# Soma do dinheiro efetivamente guardado em todas as metas.
total_acumulado_objetivos = sum(
    (objetivo.valor_acumulado for objetivo in objetivos),
    start=Decimal("0"),
)

# Valor que falta para alcançar cada objetivo.
for objetivo in objetivos:
    objetivo.valor_restante = max(
        objetivo.valor_alvo - objetivo.valor_acumulado,
        Decimal("0"),
    )

receitas_detalhes = Transaction.objects.filter(
    usuario=request.user,
    tipo=Transaction.Tipo.RECEITA,
    data__range=[inicio_mes, fim_mes],
    status=Transaction.Status.CONFIRMADA,
).order_by("-data")

despesas_detalhes = Transaction.objects.filter(
    usuario=request.user,
    tipo=Transaction.Tipo.DESPESA,
    data__range=[inicio_mes, fim_mes],
    status=Transaction.Status.CONFIRMADA,
).order_by("-data")

contexto = {
    "total_receitas": total_receitas,
    "total_despesas": total_despesas,
    "saldo_disponivel": saldo_disponivel,
    "sobra_segura": sobra_segura,
    "proximas_contas": proximas_contas,
    "top_categorias": top_categorias,
    "maior_categoria_total": maior_categoria_total,
    "hgbrasil": dados_hgbrasil,
    "colchao": colchao,
    "objetivos": objetivos,
    "total_acumulado_objetivos": total_acumulado_objetivos,
    "mes_referencia": hoje,
    "receitas_detalhes": receitas_detalhes,
    "despesas_detalhes": despesas_detalhes,
}

return render(request, "dashboard/painel.html", contexto)

@login_required
def alternar_privacidade(request):
"""FA01 — Modo Privacidade ('Olho Fechado'), RNF13."""
if request.method == "POST":
atual = request.session.get("privacy_mode_on", False)
request.session["privacy_mode_on"] = not atual

proximo = request.META.get("HTTP_REFERER") or "dashboard:painel"
return redirect(proximo)

@login_required
def marcar_notificacoes_lidas(request):
if request.method == "POST":
request.user.notificacoes.filter(lida=False).update(lida=True)

proximo = request.META.get("HTTP_REFERER") or "dashboard:painel"
return redirect(proximo)
