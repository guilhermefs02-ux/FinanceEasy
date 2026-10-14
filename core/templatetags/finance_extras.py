from django import template

register = template.Library()


@register.filter(name="brl")
def brl(valor):
    """Formata um número no padrão monetário brasileiro: R$ 1.234,56."""
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        return "R$ 0,00"
    sinal = "-" if valor < 0 else ""
    valor = abs(valor)
    texto = f"{valor:,.2f}"
    texto = texto.replace(",", "_").replace(".", ",").replace("_", ".")
    return f"{sinal}R$ {texto}"


@register.filter(name="dias_ate")
def dias_ate(data):
    from datetime import date

    if not data:
        return ""
    delta = (data - date.today()).days
    if delta == 0:
        return "vence hoje"
    if delta == 1:
        return "vence amanhã"
    if delta < 0:
        return "atrasada"
    return f"vence em {delta} dias"
