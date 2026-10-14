from django.contrib import admin

from .models import Category, CategoryBudget, ImportBatch, RecurringBill, Transaction

admin.site.register(Category)
admin.site.register(CategoryBudget)
admin.site.register(ImportBatch)
admin.site.register(RecurringBill)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ["usuario", "tipo", "valor", "data", "categoria", "origem", "status"]
    list_filter = ["tipo", "origem", "status", "categoria"]
    search_fields = ["descricao", "descricao_origem_banco"]
