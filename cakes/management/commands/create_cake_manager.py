"""Tort boshqaruvchisi uchun alohida hisob yaratadi.

Boshqaruvchi faqat "cakes" ilovasini ko'radi va boshqaradi: tort, kategoriya,
rasm, variant va allergenlarni qo'sha/tuzata oladi. Mijozlar, buyurtmalar,
fikrlar, foydalanuvchilar va sayt sozlamalari esa faqat admin (superuser)
ko'radi — chunki bu modellarga ruxsat berilmaydi.

    python manage.py create_cake_manager gulnora
    python manage.py create_cake_manager gulnora --email g@mail.com
    python manage.py create_cake_manager gulnora --password "YangiParol123"

Parol berilmasa, foydalanuvchi parolsiz (unusable) yaratiladi va admin panelda
birinchi marta kirganda Django o'zi parol o'rnatishga majbur qiladi.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

GROUP_NAME = "Tort boshqaruvchisi"

# Boshqaruvchi ko'ra oladigan modellar: (app_label, model nomi)
MANAGED_MODELS = [
    ('cakes', 'category'),
    ('cakes', 'cake'),
    ('cakes', 'cakeimage'),
    ('cakes', 'option'),
    ('cakes', 'allergen'),
]

# "O'chirish" (delete) ruxsati berilmaydi — ixtiyoriy.
ALLOWED_ACTIONS = ['view', 'add', 'change']


class Command(BaseCommand):
    help = "Tort boshqaruvchisi uchun alohida admin hisobi yaratadi"

    def add_arguments(self, parser):
        parser.add_argument('username', help="Login (masalan: gulnora)")
        parser.add_argument('--email', default='', help="Email manzili")
        parser.add_argument('--password', default='',
                            help="Parol (berilmasa — admin panelda o'rnatiladi)")

    @transaction.atomic
    def handle(self, *args, **options):
        username = options['username'].strip()
        email = options['email'].strip()
        password = options['password']

        group, perms = self._get_group()
        user, created = self._get_or_create_user(username, email, password)
        user.groups.add(group)

        verb = "yaratildi" if created else "yangilandi"
        self._report(username, group, perms, password=password, verb=verb)

    def _get_group(self):
        group, _ = Group.objects.get_or_create(name=GROUP_NAME)

        wanted = Permission.objects.filter(
            content_type__app_label__in={a for a, _ in MANAGED_MODELS},
            codename__in=[f"{act}_{model}" for act in ALLOWED_ACTIONS
                          for _, model in MANAGED_MODELS],
        ).select_related('content_type')

        found = []
        missing = []
        for app_label, model in MANAGED_MODELS:
            for action in ALLOWED_ACTIONS:
                codename = f"{action}_{model}"
                perm = wanted.filter(
                    content_type__app_label=app_label,
                    content_type__model=model,
                    codename=codename,
                ).first()
                if perm:
                    found.append(perm)
                else:
                    missing.append(f"{app_label}.{codename}")

        if missing:
            raise CommandError(
                "Ruxsatlar topilmadi: "
                + ", ".join(missing)
                + "\nAvval `python manage.py migrate` bajaring."
            )

        # set() — guruhdagi eskirgan ruxsatlar ham olib tashlanadi.
        group.permissions.set(found)

        return group, len(found)

    def _get_or_create_user(self, username, email, password):
        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=username,
            defaults={'email': email},
        )

        user.is_staff = True       # admin panelga kirishi uchun
        user.is_superuser = False  # admin hujjatlari, foydalanuvchilar — yo'q
        user.is_active = True
        if email:
            user.email = email

        if password:
            user.set_password(password)
        elif created:
            user.set_unusable_password()

        user.save()
        return user, created

    def _report(self, username, group, perm_count, password, verb):
        ok = self.style.SUCCESS
        self.stdout.write(ok(f"Tort boshqaruvchisi {verb}: {username}"))
        self.stdout.write(f"  Login:        {username}")
        if password:
            self.stdout.write(f"  Parol:        {password}")
        else:
            self.stdout.write("  Parol:        yo'q — admin panelda birinchi")
            self.stdout.write("                kirganda o'rnatiladi")
        self.stdout.write(f"  Guruh:        {group.name}")
        self.stdout.write(f"  Ruxsatlar:    {perm_count} ta "
                          f"(ko'rish, qo'shish, o'zgartirish)")
        self.stdout.write("")
        self.stdout.write(f"  Panel manzili: /admin/login/  ({username})")
        self.stdout.write("")
        self.stdout.write("  Boshqaruvchi ko'ra oladigan bo'limlar: "
                          "Kategoriyalar, Tortlar, Tort rasmlari,")
        self.stdout.write("  Variantlar, Allergenlar.")
        self.stdout.write("  Mijozlar, Buyurtmalar, Fikrlar va "
                          "Foydalanuvchilar — faqat admin uchun.")