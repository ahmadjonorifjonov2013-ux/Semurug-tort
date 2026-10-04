from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('author_name', 'cake', 'rating', 'is_published',
                    'is_answered', 'created_at')
    list_editable = ('is_published', 'is_answered')
    list_filter = ('is_published', 'rating', 'is_answered', 'created_at')
    search_fields = ('author_name', 'text')
    list_select_related = ('cake', 'client')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    actions = ['publish', 'unpublish']

    @admin.display(description="Yulduzlar")
    def stars(self, obj):
        return "*" * obj.rating

    @admin.action(description="Tasdiqlash (saytda ko'rsatish)")
    def publish(self, request, queryset):
        updated = queryset.update(is_published=True)
        self.message_user(request, f"{updated} ta sharh tasdiqlandi")

    @admin.action(description="Yashirish")
    def unpublish(self, request, queryset):
        updated = queryset.update(is_published=False)
        self.message_user(request, f"{updated} ta sharh yashirildi")