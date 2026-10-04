from django.test import TestCase

from core.models import SiteSettings


class SiteSettingsSignalTests(TestCase):
    """Sozlamalar jadvalida har doim 1 ta qator bo'lishi kerak."""

    def test_only_one_row_survives(self):
        SiteSettings.objects.create(site_name='Birinchi', phone='+998901234567',
                                    address='Toshkent')
        SiteSettings.objects.create(site_name='Ikkinchi', phone='+998901234568',
                                    address='Samarqand')
        self.assertEqual(SiteSettings.objects.count(), 1)
        self.assertEqual(SiteSettings.objects.first().site_name, 'Ikkinchi')

    def test_str(self):
        settings_obj = SiteSettings.objects.create(
            site_name='Semurog Tort', phone='+998901234567',
            address='Toshkent',
        )
        self.assertEqual(str(settings_obj), 'Semurog Tort')