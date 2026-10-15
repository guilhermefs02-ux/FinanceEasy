import base64
import logging
import os

from django.core.cache import cache
from django.http import HttpResponse
from django.utils import timezone


logger = logging.getLogger(__name__)


class TunnelBasicAuthMiddleware:
    """Proteção HTTP Basic Auth opcional para testes por túnel."""

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
                decoded = base64.b64decode(
                    auth_header[6:],
                    validate=True,
                ).decode("utf-8")

                sent_user, sent_password = decoded.split(":", 1)
            except (ValueError, UnicodeDecodeError):
                sent_user, sent_password = "", ""

            if (
                sent_user == self.user
                and sent_password == self.password
            ):
                return self.get_response(request)

        response = HttpResponse(
            "Autenticação necessária.",
            status=401,
        )
        response["WWW-Authenticate"] = (
            'Basic realm="FinanceEasy (teste)"'
        )
        return response


class DailyDueDateScanMiddleware:
    """Executa a varredura de vencimentos no primeiro acesso diário.

    A rotina de varredura também pode ser executada pelo comando
    de gerenciamento varredura_vencimentos.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)

        if user is not None and user.is_authenticated:
            hoje = timezone.localdate()

            cache_key = (
                f"varredura_vencimentos:{user.pk}:{hoje.isoformat()}"
            )

            if not cache.get(cache_key):
                try:
                    from core.services.due_date_scan import (
                        run_scan_for_user,
                    )

                    run_scan_for_user(user)

                except Exception:
                    # Não interrompe o uso do sistema e permite
                    # que outro acesso tente executar a varredura.
                    logger.exception(
                        "Falha ao rodar a varredura diária "
                        "de vencimentos para o usuário %s.",
                        user.pk,
                    )

                else:
                    # Marca como executada somente após o sucesso.
                    cache.set(
                        cache_key,
                        True,
                        timeout=60 * 60 * 20,
                    )

        return self.get_response(request)
