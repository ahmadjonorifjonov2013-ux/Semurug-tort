"""Panelga kirish tekshiruvlari.

Panel sayt ichidagi alohida boshqaruv sahifasi. Uni ochish uchun
ikkala shart bajarilishi kerak:

  1. Akkaunt `is_staff` (superuser ham shu qatorda);
  2. Panelga kirish belgisi sessiyada `panel_admin_id` sifatida saqlangan.

Belgini ikkala joy qo'yadi: `panel:login` (alohida kirish) va
`clients:login` (sayt loginidan kirgan administrator). Shuning uchun
administrator ikkinchi marta parol kiritmaydi, lekin mijoz logini
bilan panel ochilmaydi.
"""

from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.urls import reverse

SESSION_KEY = 'panel_admin_id'


def is_panel_admin(request):
    """Sessiya panelga kirish belgisini olib chiqadimi?"""
    user = request.user
    return bool(
        user.is_authenticated
        and user.is_staff
        and request.session.get(SESSION_KEY) == user.pk
    )


def panel_required(view_func):
    """Panel sahifalarini himoya qiladi (kirish yoki chiqishdan tashqari)."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_panel_admin(request):
            # Muddati o'tgan yoki boshqa akkaunt bilan kirilgan bo'lsa —
            # belgi tozalanadi, keyin panel login sahifasiga yuboriladi.
            request.session.pop(SESSION_KEY, None)
            return redirect_to_login(request.get_full_path(),
                                     reverse('panel:login'))
        return view_func(request, *args, **kwargs)

    return wrapper