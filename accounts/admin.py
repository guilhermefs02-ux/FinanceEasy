from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import PasswordResetCode, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["email"]
    list_display = ["email", "nome_completo", "is_active", "is_staff", "date_joined"]
    search_fields = ["email", "nome_completo"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Dados pessoais",
            {
                "fields": (
                    "nome_completo",
                    "celular",
                    "data_nascimento",
                    "sexo",
                    "atividade_profissional",
                    "escolaridade",
                    "renda_mensal_aproximada",
                    "tipo_moradia",
                    "valor_aluguel_mensal",
                )
            },
        ),
        ("Permissões", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "nome_completo", "password1", "password2")}),
    )


admin.site.register(PasswordResetCode)
