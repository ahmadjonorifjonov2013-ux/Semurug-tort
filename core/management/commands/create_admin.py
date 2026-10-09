"""Administrator (superuser) akkauntini yaratadi yoki yangilaydi.

Buyruq ikki usulda ishlaydi:

    # .env dan ADMIN_USERNAME / ADMIN_PASSWORD ni o'qib
    python manage.py create_admin

    # yoki qo'lda argumentlar bilan
    python manage.py create_admin --username Zulayho --password "Parol123"

Parol hech qachon terminalga yozilmaydi va koding ichida saqlanmaydi —
faqat .env fayli va bazadagi xesh orqali. `.env` git'ga qo'shilmaydi.
"""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Boshqaruv paneli uchun administrator akkauntini yaratadi"

    def add_arguments(self, parser):
        parser.add_argument('--username', help="Admin login")
        parser.add_argument('--password', help="Admin parol")
        parser.add_argument('--email', default='', help="Admin email (ixtiyoriy)")

    def handle(self, *args, **options):
        username = (options.get('username')
                    or os.environ.get('ADMIN_USERNAME', '')).strip()
        password = options.get('password') or os.environ.get(
            'ADMIN_PASSWORD', '').strip()
        email = options.get('email') or os.environ.get('ADMIN_EMAIL', '').strip()

        if not username or not password:
            raise CommandError(
                "Login va parol kerak: --username/--password bering yoki "
                ".env fayliga ADMIN_USERNAME va ADMIN_PASSWORD yozing."
            )

        User = get_user_model()

        with transaction.atomic():
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'email': email},
            )
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            if email:
                user.email = email
            # Parol har doim qayta o'rnatiladi — .env dagi parol yetakli
            # bo'lishi uchun. Parol validatorlari tekshirilmaydi (bu
            # majburiy akkaunt, foydalanuvchi tanlagan parol emas).
            user.set_password(password)
            user.save()

        verb = 'yaratildi' if created else 'yangilandi'
        self.stdout.write(self.style.SUCCESS(
            f"Administrator {verb}: {username} (staff: {user.is_staff}, "
            f"superuser: {user.is_superuser})"
        ))
        self.stdout.write(
            "Panel manzili: /boshqaruv/kirish/  "
            "(Django admin: /admin/)"
        )