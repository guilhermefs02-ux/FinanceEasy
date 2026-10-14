"""URL configuration for financeeasy project."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", RedirectView.as_view(pattern_name="dashboard:painel", permanent=False), name="home"),
    path("contas/", include("accounts.urls")),
    path("painel/", include("dashboard.urls")),
    path("financas/", include("transactions.urls")),
    path("dividas/", include("debts.urls")),
    path("objetivos/", include("goals.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
