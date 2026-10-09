"""Saytni faqat ro'yxatdan o'tgan foydalanuvchilarga ochish.

`RequireLoginMiddleware` saytdagi barcha sahifalarni kirish talab qiladi:

  * ro'yxatdan o'tish, kirish, chiqish — ochiq;
  * media (rasmlar), static, robots.txt, sitemap.xml — ochiq;
  * Django admin (`/admin/`) — o'z autentifikatsiyasini boshqaradi;
  * boshqaruv paneli (`/boshqaruv/`) — o'z staff tekshiruvini qiladi;
  * API (`/api/`) — o'z qoidalarini DRF'dan oladi (savat/savatcha/order
    allaqachon `IsAuthenticated` talab qiladi).

`SITE_REQUIRE_LOGIN=False` bo'lsa hamma narsa oldingi kabi ochiq ishlaydi
(testlar uchun qulay).
"""

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.utils.deprecation import MiddlewareMixin

# Kirishsiz foydalanish mumkin bo'lgan sayt sahifalari.
OPEN_CLIENT_VIEWS = {'login', 'register', 'logout'}


class RequireLoginMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        if not getattr(settings, 'SITE_REQUIRE_LOGIN', True):
            return None

        resolver = getattr(request, 'resolver_match', None)
        namespace = getattr(resolver, 'namespace', None)
        url_name = getattr(resolver, 'url_name', None)
        path = request.path

        # Ochiq sahifalar
        if namespace == 'clients' and url_name in OPEN_CLIENT_VIEWS:
            return None
        # API — DRF permission_classes qaror beradi
        if path.startswith('/api/'):
            return None
        if path.startswith(settings.STATIC_URL):
            return None

        # Media (rasmlar) har doim ochiq: ular nginx orqali ham beriladi,
        # shuning uchun MEDIA_VIA_DJANGO da ham bir xil bo'lishi kerak.
        # Aks holda token bilan ishlaydigan API foydalanuvchisi rasmni
        # ko'ra olmaydi (token auth'da sessiya cookie bo'lmaydi).
        if path.startswith(settings.MEDIA_URL):
            return None

        # Robotlar fayllari — HTML sahifaga redirect bo'lmasligi kerak.
        if path in ('/robots.txt', '/sitemap.xml'):
            return None

        # Django admin va boshqaruv paneli — o'z tekshiruviga ega
        if namespace == 'admin' or path.startswith('/admin/'):
            return None
        if namespace == 'panel' or path.startswith(
                getattr(settings, 'PANEL_URL_PREFIX', '/boshqaruv/')):
            return None

        if request.user.is_active:
            return None

        return redirect_to_login(request.get_full_path(),
                                 settings.LOGIN_URL,
                                 redirect_field_name='next')