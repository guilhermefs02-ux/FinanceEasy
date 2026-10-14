def privacy_mode(request):
    """Expõe o estado do Modo Privacidade ("Olho Fechado" — UC08/FA01,
    RNF13) para todos os templates, sem precisar repetir em cada view.
    """
    return {"privacy_mode_on": request.session.get("privacy_mode_on", False)}


def notificacoes(request):
    """Expõe o sino de notificações (usado na navbar em todas as páginas,
    não só no painel) — UC06/UC14."""
    if not request.user.is_authenticated:
        return {}
    qs = request.user.notificacoes.filter(lida=False)
    return {
        "notificacoes_recentes": qs[:5],
        "total_notificacoes_nao_lidas": qs.count(),
    }
