from django import forms

from core.forms import BootstrapFormMixin

from .models import Cake


class CakeFilterForm(BootstrapFormMixin, forms.Form):
    """Katalog filtrlari (GET parametrlar)."""

    search = forms.CharField(
        label="Qidiruv", required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Tort nomi...'}),
    )
    category = forms.CharField(label="Kategoriya", required=False)
    price_min = forms.DecimalField(
        label="Narx (dan)", required=False, min_value=0,
        widget=forms.NumberInput(attrs={'min': 0, 'placeholder': '0'}),
    )
    price_max = forms.DecimalField(
        label="Narx (gacha)", required=False, min_value=0,
        widget=forms.NumberInput(attrs={'min': 0, 'placeholder': '0'}),
    )
    sort = forms.ChoiceField(label="Saralash", required=False)
    available = forms.BooleanField(label="Faqat mavjudlari", required=False)
    preorder = forms.BooleanField(label="Faqat oldindan buyurtma",
                                  required=False)
    allergen = forms.CharField(label="Allergen", required=False)


class QuickOrderForm(BootstrapFormMixin, forms.Form):
    """Kartadagi tez buyurtma (savatga qo'shish)."""

    quantity = forms.IntegerField(
        label="Soni", min_value=1, max_value=99, initial=1,
        widget=forms.NumberInput(attrs={'min': 1, 'max': 99}),
    )
    options = forms.ModelMultipleChoiceField(
        label="Variantlar", queryset=None, required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, **kwargs):
        cake = kwargs.pop('cake', None)
        super().__init__(*args, **kwargs)
        if cake is not None:
            self.fields['options'].queryset = cake.options.filter(is_active=True)


class CakeForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Cake
        fields = ('category', 'name', 'slug', 'description', 'price',
                  'old_price', 'weight_gram', 'main_image', 'is_available',
                  'is_active', 'is_preorder', 'min_order_days', 'options',
                  'allergens')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'options': forms.CheckboxSelectMultiple,
            'allergens': forms.CheckboxSelectMultiple,
        }