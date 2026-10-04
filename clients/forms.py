from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User

from core.forms import BootstrapFormMixin

from .models import Client


def clean_phone_value(raw):
    """'+998 90 123 45 67' → '+998901234567'"""
    digits = ''.join(ch for ch in str(raw) if ch.isdigit())
    if not digits.startswith('998') and len(digits) == 9:
        digits = '998' + digits
    if not digits.startswith('998') or len(digits) != 12:
        raise forms.ValidationError("Telefon +998 XX XXX XX XX bo'lishi kerak")
    return '+' + digits


class ClientRegistrationForm(BootstrapFormMixin, UserCreationForm):
    full_name = forms.CharField(label="F.I.O", max_length=120)
    phone = forms.CharField(label="Telefon", max_length=20)
    telegram = forms.CharField(label="Telegram", max_length=60, required=False)

    class Meta:
        model = User
        fields = ('username', 'email')

    def clean_phone(self):
        return clean_phone_value(self.cleaned_data['phone'])

    def save(self, commit=True):
        user = super().save(commit=False)
        full_name = self.cleaned_data.get('full_name', '').strip()
        user.first_name, _, user.last_name = full_name.partition(' ')
        if commit:
            user.save()
        return user


class ClientProfileForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Client
        fields = ('full_name', 'phone', 'telegram', 'email', 'birthday',
                  'address', 'notes')
        widgets = {
            'birthday': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_phone(self):
        return clean_phone_value(self.cleaned_data['phone'])


class ClientLoginForm(BootstrapFormMixin, AuthenticationForm):
    username = forms.CharField(label="Login", max_length=150)
    password = forms.CharField(label="Parol", widget=forms.PasswordInput)

    error_messages = {
        **AuthenticationForm.error_messages,
        'invalid_login': "Login yoki parol xato",
        'inactive': "Bu akkaunt bloklangan",
    }