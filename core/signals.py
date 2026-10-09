from django.db.models.signals import post_save

from .models import SiteSettings


def ensure_single_row(sender, instance, created, **kwargs):
    """Sozlamalar jadvalida har doim 1 ta qator bo'lsin."""
    SiteSettings.objects.filter(pk__in=SiteSettings.objects
                               .exclude(pk=instance.pk)
                               .values_list('pk', flat=True)).delete()


def connect_signals():
    """`post_save` signalini biriktiradi (AppConfig.ready dan chaqiriladi).

    `dispatch_uid` tufayli bir necha marta chaqirilsa ham qayta
    biriktirilmaydi — ortiqcha signal chaqiruqlari bo'lmaydi.
    """
    post_save.connect(
        ensure_single_row,
        sender=SiteSettings,
        dispatch_uid='core.sitesettings.ensure_single_row',
    )


def get_settings():
    """Sozlamalarni oladi; yo'q bo'lsa None (template'da tekshiriladi)."""
    return SiteSettings.objects.first()
