from django.apps import AppConfig
from django.contrib import admin


class CoreConfig(AppConfig):
    name = 'core'
    verbose_name = "Sayt sozlamalari"

    def ready(self):
        import core.signals  # noqa: F401

        admin.site.site_header = "Semurg' TORT Markazi"
        admin.site.site_title = "Semurg' Tort Admin"
        admin.site.index_title = "Boshqaruv paneli"