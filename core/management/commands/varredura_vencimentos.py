from django.core.management.base import BaseCommand

from core.services.due_date_scan import run_scan_for_all_users


class Command(BaseCommand):
    help = (
        "UC14 — Varredura diária automática de vencimentos. "
        "Agende este comando para rodar todo dia às 08h00 "
        "(Agendador de Tarefas do Windows, cron no Linux/Mac, etc.)."
    )

    def handle(self, *args, **options):
        total = run_scan_for_all_users()
        self.stdout.write(self.style.SUCCESS(f"Varredura concluída: {total} notificações novas geradas."))
