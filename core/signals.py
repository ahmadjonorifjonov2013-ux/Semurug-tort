from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import SiteSettings


@receiver(post_save, sender=SiteSettings)
def ensure_single_row(sender, instance, created, **kwargs):
    """Sozlamalar jadvalida har doim 1 ta qator bo'lsin."""
    SiteSettings.objects.filter(pk__in=SiteSettings.objects
                               .exclude(pk=instance.pk)
                               .values_list('pk', flat=True)).delete()


def get_settings():
    """Sozlamalarni oladi; yo'q bo'lsa None (template'da tekshiriladi)."""
    return SiteSettings.objects.first()