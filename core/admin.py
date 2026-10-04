from django.contrib import admin

from .models import SiteSettings, Banner, GalleryPhoto, FAQ, ContactMessage


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ('site_name', 'phone', 'delivery_price',
                    'free_delivery_from')

    fieldsets = (
        ('Asosiy', {
            'fields': ('site_name', 'phone', 'address', 'work_hours'),
        }),
        ('Aloqa', {
            'fields': ('telegram', 'instagram', 'map_url'),
        }),
        ('Yetkazib berish', {
            'fields': ('delivery_price', 'free_delivery_from'),
        }),
        ('Matnlar', {
            'fields': ('about_text',),
        }),
    )


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'order')
    list_editable = ('is_active', 'order')
    list_display_links = ('title',)
    ordering = ('order',)


@admin.register(GalleryPhoto)
class GalleryPhotoAdmin(admin.ModelAdmin):
    list_display = ('caption', 'image', 'is_active', 'order')
    list_editable = ('is_active', 'order')
    list_display_links = ('caption',)
    ordering = ('order',)


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    list_display_links = ('question',)
    search_fields = ('question',)
    ordering = ('order',)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'is_handled', 'created_at')
    list_editable = ('is_handled',)
    list_filter = ('is_handled', 'created_at')
    search_fields = ('name', 'phone', 'message')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'