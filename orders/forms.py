from django import forms
from django.utils import timezone

from clients.forms import clean_phone_value
from clients.models import Client

from core.forms import BootstrapFormMixin

from .models import Order


class OrderForm(BootstrapFormMixin, forms.ModelForm):
    """Anonim va ro'yxatdan o'tgan mijoz uchun bir xil forma."""

    phone = forms.CharField(label="Telefon", max_length=20)
    name = forms.CharField(label="F.I.O", max_length=120)
    telegram = forms.CharField(label="Telegram", max_length=60,
                               required=False)
    delivery_date = forms.DateField(label="Yetkazish sanasi",
                                    initial=timezone.localdate)
    delivery_time = forms.TimeField(label="Vaqt", required=False)
    comment = forms.CharField(label="Izoh", widget=forms.Textarea,
                            required=False)
    promo_code = forms.CharField(label="Promo kod", required=False)

    class Meta:
        model = Order
        fields = ('delivery_address', 'delivery_date', 'delivery_time',
                  'payment_method', 'comment')
        widgets = {
            'delivery_address': forms.Textarea(attrs={'rows': 3}),
            'delivery_time': forms.TimeInput(attrs={'type': 'time'}),
            'comment': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'delivery_address': "Yetkazish manzili",
            'payment_method': "To'lov usuli",
        }

    def __init__(self, *args, **kwargs):
        self.min_date = kwargs.pop('min_date', timezone.localdate())
        super().__init__(*args, **kwargs)
        self.fields['delivery_date'].widget.attrs.update(
            {'min': self.min_date.isoformat()}
        )

    def clean_phone(self):
        return clean_phone_value(self.cleaned_data['phone'])

    def clean_promo_code(self):
        return (self.cleaned_data.get('promo_code') or '').strip().upper()

    def clean_delivery_date(self):
        date = self.cleaned_data['delivery_date']
        if date < timezone.localdate():
            raise forms.ValidationError("Sana bugundan oldin bo'lmasligi kerak")
        return date

    def clean_delivery_address(self):
        address = (self.cleaned_data.get('delivery_address') or '').strip()
        if len(address) < 8:
            raise forms.ValidationError("Manzilni to'liqroq yozing")
        return address

    def get_or_create_client(self):
        """Ro'yxatdan o'tmagan mijoz uchun ham Client qatori yaratiladi."""
        phone = self.cleaned_data['phone']
        client = Client.objects.filter(phone=phone).first()
        if client:
            client.full_name = self.cleaned_data['name']
            update_fields = ['full_name']
            if self.cleaned_data.get('telegram'):
                client.telegram = self.cleaned_data['telegram']
                update_fields.append('telegram')
            client.save(update_fields=update_fields)
            return client

        return Client.objects.create(
            phone=phone,
            full_name=self.cleaned_data['name'],
            telegram=self.cleaned_data.get('telegram', ''),
            address=self.cleaned_data.get('delivery_address', ''),
        )


class CouponForm(BootstrapFormMixin, forms.Form):
    code = forms.CharField(
        label="Promo kod", max_length=20,
        widget=forms.TextInput(attrs={'placeholder': 'MASALAN: YANVAR10'}),
    )