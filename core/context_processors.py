def privacy_mode(request):
    """Expõe o estado do Modo Privacidade para todos os templates."""
    return {
        "privacy_mode_on": request.session.get(
            "privacy_mode_on",
            False,
        )
    }


def notificacoes(request):
    """Disponibiliza notificações lidas e não lidas para o sino."""
    if not request.user.is_authenticated:
        return {
            "notificacoes_recentes": [],
            "total_notificacoes_nao_lidas": 0,
        }

    notificacoes_usuario = request.user.notificacoes.all().order_by(
        "-criada_em"
    )

    nao_lidas = notificacoes_usuario.filter(lida=False)

    return {
        # As cinco notificações mais recentes, independentemente
        # de estarem lidas ou não.
        "notificacoes_recentes": notificacoes_usuario[:5],

        # O contador continua considerando somente as não lidas.
        "total_notificacoes_nao_lidas": nao_lidas.count(),
    }
