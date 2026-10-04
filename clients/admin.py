from django.contrib import admin

from .models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'telegram', 'is_vip',
                    'orders_count', 'created_at')
    list_filter = ('is_vip', 'created_at')
    search_fields = ('full_name', 'phone', 'email', 'telegram')
    list_display_links = ('full_name',)
    list_select_related = ('user',)
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Mijoz', {'fields': ('full_name', 'phone', 'telegram', 'email')}),
        ('Qo\'shimcha', {'fields': ('birthday', 'address', 'notes', 'is_vip')}),
        ('Tizim', {'fields': ('user', 'created_at')}),
    )

    @admin.display(description="Buyurtmalar", ordering='created_at')
    def orders_count(self, obj):
        return obj.orders.count()