from django.contrib import admin

from .models import Order, OrderItem, PromoCode
from .services import send_status_to_telegram


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ('cake', 'quantity', 'price', 'comment')
    readonly_fields = ('price',)
    autocomplete_fields = ('cake',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'client', 'phone', 'items_count',
                    'total_price', 'status', 'is_paid', 'delivery_date')
    list_filter = ('status', 'is_paid', 'payment_method', 'delivery_date',
                   'created_at')
    list_editable = ('status', 'is_paid')
    search_fields = ('id', 'client__full_name', 'client__phone',
                     'delivery_address')
    date_hierarchy = 'created_at'
    list_select_related = ('client', 'promo_code')
    inlines = [OrderItemInline]
    readonly_fields = ('subtotal', 'delivery_price', 'discount', 'total_price',
                       'created_at', 'updated_at')
    actions = ['mark_paid', 'mark_delivered', 'mark_cancelled']
    fieldsets = (
        ('Buyurtma', {
            'fields': ('client', 'status', 'payment_method', 'is_paid',
                       'promo_code'),
        }),
        ('Yetkazib berish', {
            'fields': ('delivery_address', 'delivery_date', 'delivery_time',
                       'comment'),
        }),
        ('Hisob', {
            'fields': ('subtotal', 'delivery_price', 'discount', 'total_price'),
        }),
        ('Vaqt', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('client')

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        """Holat o'zgarganda Telegramga xabar yuboradi."""
        old_status = None
        if change and 'status' in form.changed_data:
            old_status = (
                Order.objects.filter(pk=obj.pk)
                .values_list('status', flat=True).first()
            )
        super().save_model(request, obj, form, change)
        if old_status and old_status != obj.status:
            # blocking=True — nechta xabar ketganini aniq hisoblaymiz
            if send_status_to_telegram(obj, old_status, blocking=True):
                self.message_user(request, "Holat Telegramga yuborildi.")

    @admin.display(description="Telefon", ordering='client__phone')
    def phone(self, obj):
        return obj.client.phone

    @admin.display(description="Tort soni", ordering='items_count')
    def items_count(self, obj):
        return obj.items_count

    @admin.action(description="To'landi deb belgilash")
    def mark_paid(self, request, queryset):
        updated = queryset.update(is_paid=True)
        self.message_user(request, f"{updated} ta buyurtma "
                                   "to'landi deb belgilandi")

    @admin.action(description="Yetkazildi deb belgilash")
    def mark_delivered(self, request, queryset):
        self._set_status(request, queryset, Order.Status.DELIVERED, is_paid=True)

    @admin.action(description="Bekor qilish")
    def mark_cancelled(self, request, queryset):
        self._set_status(request, queryset, Order.Status.CANCELLED)

    def _set_status(self, request, queryset, status, is_paid=None):
        """Holatni o'rnatadi va har bir buyurtma uchun Telegramga xabar beradi."""
        sent = 0
        for order in queryset:
            old_status = order.status
            if old_status == status:
                continue
            order.status = status
            update_fields = ['status']
            if is_paid is not None:
                order.is_paid = is_paid
                update_fields.append('is_paid')
            order.save(update_fields=update_fields)
            if send_status_to_telegram(order, old_status, blocking=True):
                sent += 1

        self.message_user(
            request,
            f"{queryset.count()} ta buyurtma yangilandi "
            f"({sent} ta Telegram xabari yuborildi).",
        )


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'cake', 'quantity', 'price', 'subtotal')
    list_select_related = ('order', 'cake')
    autocomplete_fields = ('cake',)


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_percent', 'min_order_sum',
                    'is_active', 'used_count')
    list_editable = ('is_active',)
    search_fields = ('code',)
    readonly_fields = ('used_count',)
    fieldsets = (
        (None, {'fields': ('code', 'discount_percent', 'min_order_sum')}),
        ('Muddat', {'fields': ('valid_from', 'valid_until', 'is_active')}),
        ('Statistika', {'fields': ('used_count',)}),
    )