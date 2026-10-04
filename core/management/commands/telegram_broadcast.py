import html

from django.core.management.base import BaseCommand, CommandError

from orders.services import broadcast, send_test_message


class Command(BaseCommand):
    help = "Barcha Telegram chatlariga xabar yuboradi (aktsiya e'loni)"

    def add_arguments(self, parser):
        parser.add_argument('text', nargs='+', help="Yuboriladigan matn")

    def handle(self, *args, **options):
        raw = ' '.join(options['text']).strip()
        if not raw:
            raise CommandError("Matn bo'sh bo'lib qoldi")

        ok, message = send_test_message()
        if not ok:
            raise CommandError(message)

        text = f"📣 <b>{html.escape(raw)}</b>"
        if not broadcast(text):
            raise CommandError("Xabar yuborilmadi")

        self.stdout.write(self.style.SUCCESS(text))
        self.stdout.write(f"{message}.")
