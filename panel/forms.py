"""Panel shakllari (boshqaruv sahifalari uchun)."""

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone

from cakes.models import Allergen, Cake, Category, Option
from clients.forms import clean_phone_value
from clients.models import Client
from core.forms import BootstrapFormMixin
from core.models import Banner, FAQ, GalleryPhoto, SiteSettings
from orders.models import Order, PromoCode


class PanelLoginForm(BootstrapFormMixin, AuthenticationForm):
    """Faqat xodim (staff) akkauntlari uchun.

    Noto'g'ri parol yoki xodim emasligi — bir xil xabar bilan qaytariladi.
    """

    username = forms.CharField(label="Admin login", max_length=150)
    password = forms.CharField(label="Parol", widget=forms.PasswordInput)

    error_messages = {
        **AuthenticationForm.error_messages,
        'invalid_login': "Login yoki parol xato",
        'inactive': "Bu akkaunt bloklangan",
    }

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_staff:
            raise forms.ValidationError(
                "Bu akkaunt administrator emas",
                code='invalid_login',
            )


# ---------------------------------------------------------------------------
# Tortlar
# ---------------------------------------------------------------------------

class OptionalFieldsMixin:
    """Modeli default qiymatga ega maydonlar bo'sh qoldirilgan bo'lsa ham
    forma to'ldirilgan hisoblanadi (Qiymat model default'idan olinadi).

    Django admin ham shunday qiladi — admin uchun majburiy emas.
    """

    optional_fields = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in self.optional_fields:
            if name in self.fields:
                self.fields[name].required = False


class MultipleFileInput(forms.FileInput):
    """`<input type="file" multiple>` — rasm tanlash maydoni."""

    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """Bir nechta faylni qabul qiladi, `cleaned_data` — ro'yxat qaytaradi."""

    def to_python(self, data):
        if not isinstance(data, (list, tuple)):
            return super().to_python(data)
        files = []
        for item in data:
            if item in self.empty_values:
                continue
            files.append(super().to_python(item))
        return files


class PanelCakeForm(OptionalFieldsMixin, BootstrapFormMixin, forms.ModelForm):
    optional_fields = ('slug', 'weight_gram', 'min_order_days')

    gallery_images = MultipleFileField(
        label="Qo'shimcha rasmlar (bir nechta tanlash mumkin)",
        required=False,
        widget=MultipleFileInput(attrs={'accept': 'image/*'}),
    )

    class Meta:
        model = Cake
        fields = ('category', 'name', 'slug', 'description', 'price',
                  'old_price', 'weight_gram', 'main_image', 'is_available',
                  'is_active', 'is_preorder', 'min_order_days', 'options',
                  'allergens')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'price': forms.NumberInput(attrs={'step': '1000', 'min': 0}),
            'old_price': forms.NumberInput(attrs={'step': '1000', 'min': 0}),
            'slug': forms.TextInput(attrs={'placeholder': 'bo\'sh qoldirilsa '
                                                 'avtomatik yaratiladi'}),
            'main_image': forms.ClearableFileInput(
                attrs={'accept': 'image/*'}),
        }
        labels = {
            'min_order_days': "Kamida necha kun oldin buyurtma kerak",
            'is_active': "Saytda ko'rinadi",
            'is_available': "Hozir mavjud",
            'is_preorder': "Faqat oldindan buyurtma",
        }
        help_texts = {
            'old_price': "Chegirma ko'rsatish uchun (narxdan katta bo'lishi "
                         "kerak)",
            'options': "Bu tortga mos variantlar",
            'allergens': "Tarkibida bor allergenlar",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Rasm faqat yangi tortda majburiy — tahrirlashda eskisi saqlanadi.
        self.fields['main_image'].required = not (
            self.instance.pk and self.instance.main_image
        )


class PanelCategoryForm(OptionalFieldsMixin, BootstrapFormMixin,
                        forms.ModelForm):
    optional_fields = ('order',)

    class Meta:
        model = Category
        fields = ('name', 'description', 'image', 'order', 'is_active')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
            'image': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
        }
        labels = {'is_active': "Faol"}


class PanelOptionForm(OptionalFieldsMixin, BootstrapFormMixin, forms.ModelForm):
    optional_fields = ('group', 'price_delta')

    class Meta:
        model = Option
        fields = ('name', 'group', 'price_delta', 'is_active')
        widgets = {
            'price_delta': forms.NumberInput(attrs={'step': '1000'}),
            'group': forms.TextInput(attrs={'placeholder': "O'lcham / Ta'm"}),
        }
        labels = {
            'group': "Guruh",
            'price_delta': "Qo'shimcha narx (so'm)",
            'is_active': "Faol",
        }


class PanelAllergenForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Allergen
        fields = ('name',)
        widgets = {'name': forms.TextInput(
            attrs={'placeholder': "Masalan: yong'oq"})}


# ---------------------------------------------------------------------------
# Buyurtmalar
# ---------------------------------------------------------------------------

class PanelOrderForm(BootstrapFormMixin, forms.ModelForm):
    """Admin buyurtmani rasmiylashganda to'ldiradi."""

    class Meta:
        model = Order
        fields = ('status', 'payment_method', 'is_paid', 'delivery_address',
                  'delivery_date', 'delivery_time', 'comment')
        widgets = {
            'delivery_address': forms.Textarea(attrs={'rows': 2}),
            'delivery_time': forms.TimeInput(attrs={'type': 'time'}),
            'comment': forms.Textarea(attrs={'rows': 2}),
        }
        labels = {
            'is_paid': "To'lov olindi",
            'comment': "Buyurtma izohi",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['delivery_date'].widget.attrs.update(
            {'min': timezone.localdate().isoformat()}
        )


class PanelPromoCodeForm(OptionalFieldsMixin, BootstrapFormMixin,
                        forms.ModelForm):
    optional_fields = ('discount_percent', 'min_order_sum')

    class Meta:
        model = PromoCode
        fields = ('code', 'discount_percent', 'min_order_sum', 'valid_from',
                  'valid_until', 'is_active')
        widgets = {
            'code': forms.TextInput(attrs={'placeholder': 'YANVAR10'}),
            'discount_percent': forms.NumberInput(attrs={'min': 1, 'max': 100}),
            'min_order_sum': forms.NumberInput(attrs={'step': '1000', 'min': 0}),
            'valid_from': forms.DateTimeInput(
                attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'valid_until': forms.DateTimeInput(
                attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        }
        labels = {
            'discount_percent': "Chegirma (%)",
            'min_order_sum': "Minimal buyurtma (so'm)",
            'is_active': "Faol",
        }

    def clean_code(self):
        return (self.cleaned_data.get('code') or '').strip().upper()


# ---------------------------------------------------------------------------
# Sayt kontenti va sozlamalari
# ---------------------------------------------------------------------------

class PanelBannerForm(OptionalFieldsMixin, BootstrapFormMixin, forms.ModelForm):
    optional_fields = ('order',)

    class Meta:
        model = Banner
        fields = ('title', 'subtitle', 'image', 'link', 'order', 'is_active')
        widgets = {
            'image': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
        }
        labels = {'is_active': "Faol"}


class PanelGalleryForm(OptionalFieldsMixin, BootstrapFormMixin, forms.ModelForm):
    optional_fields = ('order',)

    class Meta:
        model = GalleryPhoto
        fields = ('image', 'caption', 'order', 'is_active')
        widgets = {
            'image': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
        }
        labels = {'is_active': "Faol"}


class PanelFAQForm(OptionalFieldsMixin, BootstrapFormMixin, forms.ModelForm):
    optional_fields = ('order',)

    class Meta:
        model = FAQ
        fields = ('question', 'answer', 'order', 'is_active')
        widgets = {'answer': forms.Textarea(attrs={'rows': 3})}
        labels = {'is_active': "Faol"}


class PanelSiteSettingsForm(OptionalFieldsMixin, BootstrapFormMixin,
                           forms.ModelForm):
    optional_fields = ('site_name', 'work_hours', 'delivery_price')

    class Meta:
        model = SiteSettings
        fields = ('site_name', 'phone', 'telegram', 'instagram', 'address',
                  'work_hours', 'delivery_price', 'free_delivery_from',
                  'about_text', 'map_url')
        widgets = {
            'about_text': forms.Textarea(attrs={'rows': 5}),
        }
        labels = {
            'delivery_price': "Yetkazib berish narxi (so'm)",
            'free_delivery_from': "Bu summa dan katta bo'lsa — bepul",
            'about_text': "Biz haqimizda matni",
        }


class PanelClientForm(BootstrapFormMixin, forms.ModelForm):
    """Mijoz ma'lumotlarini admin to'ldiradi/tuzatadi.

    Ro'yxatdan o'tishda telefon allaqachon so'raladi, lekin buyurtmani
    rasmiylashda admin uni aniqlashtirishi (tug'ilgan kun, manzil, VIP)
    mumkin.
    """

    class Meta:
        model = Client
        fields = ('full_name', 'phone', 'telegram', 'email', 'birthday',
                  'address', 'notes', 'is_vip')
        widgets = {
            'birthday': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {'is_vip': "VIP mijoz"}

    def clean_phone(self):
        return clean_phone_value(self.cleaned_data['phone'])