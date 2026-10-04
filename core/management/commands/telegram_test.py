from django.core.management.base import BaseCommand

from orders.services import _chat_ids, _configured, _token, send_test_message


class Command(BaseCommand):
    help = "Telegram bot sozlamalarini tekshiradi va test xabari yuboradi"

    def handle(self, *args, **options):
        token = _token()
        chat_ids = _chat_ids()

        self.stdout.write("Telegram sozlamalari:")
        self.stdout.write(f"  token:  {'berilgan' if token else 'YO\'Q'}")
        self.stdout.write(f"  chat:   {', '.join(chat_ids) if chat_ids else 'YO\'Q'}")

        if not _configured():
            self.stdout.write(self.style.ERROR(
                "\nXato: .env fayliga TELEGRAM_BOT_TOKEN va "
                "TELEGRAM_CHAT_ID yozing, so'ng Django'ni qayta ishga tushiring."
            ))
            return

        ok, message = send_test_message()
        if ok:
            self.stdout.write(self.style.SUCCESS(f"\n{message}"))
        else:
            self.stdout.write(self.style.ERROR(f"\n{message}"))
