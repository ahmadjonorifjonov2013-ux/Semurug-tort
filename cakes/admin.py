from django.contrib import admin

from .models import Category, Cake, CakeImage, Option, Allergen


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