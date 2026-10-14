import base64
import os
from datetime import date

from django.core.cache import cache
from django.http import HttpResponse


class TunnelBasicAuthMiddleware:
    """Camada extra de proteção (HTTP Basic Auth) para quando o app é
    exposto temporariamente pela internet via túnel (ngrok/Cloudflare
    Tunnel) para testes com o time.

    Fica DESLIGADA por padrão. Só ativa se TUNNEL_BASIC_AUTH_USER e
    TUNNEL_BASIC_AUTH_PASS estiverem definidos no .env — nesse caso, TODA
    requisição (inclusive a tela de login/cadastro) exige essa senha
    compartilhada antes mesmo de chegar nas views do Django. É uma
    segunda trava, além do login normal de cada usuário.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.user = os.getenv("TUNNEL_BASIC_AUTH_USER", "")
        self.password = os.getenv("TUNNEL_BASIC_AUTH_PASS", "")

    def __call__(self, request):
        if not self.user or not self.password:
            return self.get_response(request)

        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if auth_header.startswith("Basic "):
            try:
                decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
                sent_user, sent_password = decoded.split(":", 1)
            except Exception:
                sent_user, sent_password = "", ""
            if sent_user == self.user and sent_password == self.password:
                return self.get_response(request)

        response = HttpResponse("Autenticação necessária.", status=401)
        response["WWW-Authenticate"] = 'Basic realm="FinanceEasy (teste)"'
        return response


class DailyDueDateScanMiddleware:
    """Dispara a varredura diária de vencimentos (UC14) de forma "preguiçosa":
    a primeira requisição autenticada do dia para cada usuário roda a
    varredura e gera as notificações preventivas (D+5, D+2, D=0).

    O projeto também expõe a mesma rotina como management command
    (`python manage.py varredura_vencimentos`), que é a forma recomendada
    de executar em produção via agendador do sistema operacional (cron ou
    Agendador de Tarefas do Windows) às 08h00, como especifica o caso de
    uso. Este middleware é o respaldo do MVP para quem ainda não configurou
    o agendamento, garantindo que o usuário sempre veja avisos atualizados
    ao abrir o app.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            cache_key = f"varredura_vencimentos:{user.pk}:{date.today().isoformat()}"
            if not cache.get(cache_key):
                cache.set(cache_key, True, timeout=60 * 60 * 20)  # ~20h
                try:
                    from core.services.due_date_scan import run_scan_for_user

                    run_scan_for_user(user)
                except Exception:
                    # Nunca deixa a varredura derrubar a requisição do usuário.
                    import logging

                    logging.getLogger(__name__).exception(
                        "Falha ao rodar a varredura diária de vencimentos"
                    )
        return self.get_response(request)
