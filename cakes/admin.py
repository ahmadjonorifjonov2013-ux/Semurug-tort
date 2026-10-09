from django.contrib import admin, messages
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import unquote

from .models import Category, Cake, CakeImage, Option, Allergen

ARCHIVE_PARAM = 'archive_cake'


class CakeImageInline(admin.TabularInline):
    model = CakeImage
    extra = 1
    fields = ('image', 'order')
    ordering = ('order',)


class OptionInline(admin.TabularInline):
    model = Cake.options.through
    extra = 1
    fields = ('option',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'cakes_count', 'is_active', 'order')
    list_editable = ('is_active', 'order')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'description')
    ordering = ('order',)
    fieldsets = (
        (None, {'fields': ('name', 'slug', 'description', 'image')}),
        ('Holat', {'fields': ('order', 'is_active')}),
    )

    @admin.display(description="Tort soni")
    def cakes_count(self, obj):
        return obj.cakes.filter(is_active=True).count()


@admin.register(Cake)
class CakeAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'weight_gram',
                    'is_available', 'is_active', 'is_preorder')
    list_filter = ('category', 'is_active', 'is_available', 'is_preorder')
    list_editable = ('price', 'is_available', 'is_active')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    list_select_related = ('category',)
    inlines = [CakeImageInline, OptionInline]
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    actions = ('archive_cakes', 'restore_cakes')
    fieldsets = (
        ('Asosiy', {
            'fields': ('category', 'name', 'slug', 'description'),
        }),
        ('Narx', {
            'fields': ('price', 'old_price', 'weight_gram'),
        }),
        ('Rasm', {
            'fields': ('main_image',),
        }),
        ('Variantlar', {
            'fields': ('allergens',),
        }),
        ('Holat', {
            'fields': ('is_available', 'is_active', 'is_preorder',
                       'min_order_days'),
        }),
        ('Vaqt', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.action(description='Arxivlash — saytdan berkitish (ma\'lumot saqlanadi)')
    def archive_cakes(self, request, queryset):
        updated = queryset.filter(is_active=True).update(is_active=False)
        self.message_user(
            request,
            f'{updated} ta tort arxivlandi: saytdan berkitildi, ma\'lumot saqlandi.',
            messages.SUCCESS if updated else messages.WARNING,
        )

    @admin.action(description='Arxivdan chiqarish — saytga qaytarish')
    def restore_cakes(self, request, queryset):
        updated = queryset.filter(is_active=False).update(is_active=True)
        self.message_user(
            request,
            f'{updated} ta tort arxivdan chiqarildi va saytga qaytarildi.',
            messages.SUCCESS if updated else messages.WARNING,
        )

    def _archive(self, request, obj):
        """Tortni butunlay o'chirmasdan arxivga o'tkazish."""
        if obj.is_active:
            obj.is_active = False
            obj.save(update_fields=['is_active', 'updated_at'])
            self.log_change(request, obj, 'Arxivlandi: is_active True -> False')
            text = f'«{obj}» arxivlandi — saytdan berkitildi, ma\'lumot saqlandi.'
        else:
            obj.is_active = True
            obj.save(update_fields=['is_active', 'updated_at'])
            self.log_change(request, obj, 'Arxivdan chiqarildi: is_active False -> True')
            text = f'«{obj}» arxivdan chiqarildi va saytga qaytarildi.'
        self.message_user(request, text, messages.SUCCESS)

        if self.has_change_permission(request, None):
            post_url = reverse(
                'admin:cakes_cake_changelist', current_app=self.admin_site.name,
            )
            return HttpResponseRedirect(add_preserved_filters(
                {'preserved_filters': self.get_preserved_filters(request),
                 'opts': self.opts},
                post_url,
            ))
        return HttpResponseRedirect(reverse('admin:index',
                                            current_app=self.admin_site.name))

    def delete_view(self, request, object_id, extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_archive_option'] = True
        extra_context['archive_param'] = ARCHIVE_PARAM
        extra_context['archive_is_archived'] = False

        if request.method == 'POST' and request.POST.get(ARCHIVE_PARAM) == 'yes':
            obj = self.get_object(request, unquote(object_id))
            if obj is None:
                self.message_user(request, 'Obyekt topilmadi.', messages.ERROR)
                return HttpResponseRedirect(
                    reverse('admin:cakes_cake_changelist',
                            current_app=self.admin_site.name))
            if not self.has_change_permission(request, obj):
                raise PermissionDenied
            return self._archive(request, obj)

        obj = self.get_object(request, unquote(object_id))
        if obj is not None:
            extra_context['archive_is_archived'] = not obj.is_active

        return super().delete_view(request, object_id, extra_context)


@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    list_display = ('name', 'group', 'price_delta', 'is_active')
    list_filter = ('group', 'is_active')
    list_editable = ('price_delta', 'is_active')
    search_fields = ('name',)
    ordering = ('group', 'name')


@admin.register(Allergen)
class AllergenAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(CakeImage)
class CakeImageAdmin(admin.ModelAdmin):
    list_display = ('cake', 'image', 'order')
    list_select_related = ('cake',)
    ordering = ('order',)