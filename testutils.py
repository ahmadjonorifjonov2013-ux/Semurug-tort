"""Testlar uchun yordamchi funksiyalar."""

import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template import TemplateDoesNotExist
from django.template.loaders.base import Loader as BaseLoader
from django.test import TestCase, override_settings
from django.test.signals import template_rendered

# 1x1 pikselli PNG
PNG_BYTES = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00'
    b'\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc'
    b'\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB'
    b'`\x82'
)


def image_file(name='tort.png'):
    """Test uchun vaqtinchalik rasm fayli."""
    return SimpleUploadedFile(name, PNG_BYTES, content_type='image/png')


class _StubTemplate:
    """Har qanday shablonni bo'sh string bilan almashtiradi."""

    origin = None

    def __init__(self, template_name):
        self.template_name = template_name
        self.name = template_name

    def render(self, context=None, request=None):
        # Haqiqiy shablon kabi `template_rendered` signalini yuboramiz —
        # shunda test clientda response.context ishlaydi.
        template_rendered.send(sender=self, template=self, context=context)
        return ''

    def render_to_string(self, context=None):
        return ''


class _StubOrigin:
    def __init__(self, path):
        self.name = str(path)
        self.template_name = str(path)

    def __str__(self):
        return self.name


class StubTemplateLoader(BaseLoader):
    """View'larni test qilish uchun — haqiqiy shablon kerak emas."""

    def __init__(self, engine, dirs=None):
        super().__init__(engine)
        self.dirs = list(dirs or [])

    def get_template_sources(self, template_name):
        from pathlib import Path

        for directory in self.dirs:
            candidate = Path(directory) / template_name
            if candidate.is_file():
                yield _StubOrigin(candidate)

    def get_template(self, template_name, skip=None):
        try:                      # haqiqiy shablon bo'lsa — uni ishlatamiz
            return super().get_template(template_name, skip=skip)
        except TemplateDoesNotExist:
            return _StubTemplate(template_name)

    def get_template_names(self, template_name):
        return [template_name]


STUB_TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    # Haqiqiy shablonlar bo'lsa ular ishlatiladi, bo'lmasa — bo'sh.
    'DIRS': [settings.BASE_DIR / 'templates'],
    'APP_DIRS': False,
    'OPTIONS': {
        'loaders': [
            ('django.template.loaders.filesystem.Loader',
             [settings.BASE_DIR / 'templates']),
            ('testutils.StubTemplateLoader', []),
        ],
        'context_processors': [
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
            'core.context_processors.site_settings',
            'core.context_processors.cart_badge',
        ],
    },
}]


class ModelTestCase(TestCase):
    """main_image ni avtomatik to'ldiradigan asos.

    Saytga kirish talabi (`SITE_REQUIRE_LOGIN`) o'chiriladi — model/view
    testlari autentifikatsiyani tekshirmaydi. Kirish talabi alohida
    testlarda `panel/tests.py` da `override_settings` bilan tekshiriladi.
    """

    def setUp(self):
        from cakes.models import Category

        open_site = override_settings(SITE_REQUIRE_LOGIN=False)
        open_site.enable()
        self.addCleanup(open_site.disable)

        # Testlar haqiqiy media/ papkasiga yozmasligi uchun vaqtinchalik
        # papka (aks holda media/cakes/ga tort_*.png qoldig'i to'planadi).
        tmp_media = tempfile.mkdtemp(prefix='test-media-')
        self._media_override = override_settings(MEDIA_ROOT=tmp_media)
        self._media_override.enable()
        self.addCleanup(self._media_override.disable)
        self.addCleanup(shutil.rmtree, tmp_media, True)

        self.category = Category.objects.create(name="Tug'ilgan kun")

    def make_cake(self, **kwargs):
        from cakes.models import Cake

        defaults = {
            'category': self.category,
            'description': "Tort tavsifi",
            'price': 450000,
            'weight_gram': 1000,
            'main_image': image_file(),
        }
        defaults.update(kwargs)
        return Cake.objects.create(**defaults)


class SiteLoginRequiredTestCase(ModelTestCase):
    """ModelTestCase + saytga kirish talabi yoqiq (`SITE_REQUIRE_LOGIN=True`).

    ModelTestCase saytni ochiq qilib qo'yadi; bu test sinfi talabni
    qayta yoqadi.
    """

    def setUp(self):
        super().setUp()
        require_login = override_settings(SITE_REQUIRE_LOGIN=True)
        require_login.enable()
        self.addCleanup(require_login.disable)


@override_settings(TEMPLATES=STUB_TEMPLATES)
class ViewTestCase(ModelTestCase):
    """ModelTestCase + shablonlarsiz view testlari."""

    def login_user(self, username='ali', password='YangiParol!2026',
                   **kwargs):
        """Tizimga kiritilgan oddiy mijoz (staff emas)."""
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_user(
            username=username, password=password, **kwargs)
        self.client.force_login(user)
        return user

    def login_staff(self, username='admin', password='YangiParol!2026',
                    **kwargs):
        """Panelga kira oladigan xodim + panel sessiyasi belgisi."""
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_superuser(
            username=username, password=password, email='admin@example.com',
            **kwargs)
        self.client.force_login(user)
        session = self.client.session
        session['panel_admin_id'] = user.pk
        session.save()
        return user