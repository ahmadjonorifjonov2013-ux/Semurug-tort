from django.apps import AppConfig
from django.contrib import admin


class CoreConfig(AppConfig):
    name = 'core'
    verbose_name = "Sayt sozlamalari"

    def ready(self):
        from .signals import connect_signals

        connect_signals()

        admin.site.site_header = "Semurg' TORT Markazi"
        admin.site.site_title = "Semurg' Tort Admin"
        admin.site.index_title = "Boshqaruv paneli"