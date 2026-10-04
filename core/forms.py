from django import forms

from .models import ContactMessage, FAQ


def _bootstrap_widget_class(widget):
    """Qaysi widget uchun qaysi Bootstrap klassi ishlatilishini aniqlaydi."""
    if isinstance(widget, (forms.CheckboxInput, forms.RadioSelect,
                           forms.CheckboxSelectMultiple)):
        return 'form-check-input'
    if isinstance(widget, (forms.Select, forms.SelectMultiple)):
        return 'form-select'
    return 'form-control'


class BootstrapFormMixin:
    """Barcha maydon widget'lariga Bootstrap klasslarini qo'shadi."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.HiddenInput):
                continue
            if getattr(widget, 'skip_bootstrap_class', False):
                continue          # markupni o'z shabloni bilan chizadi
            css = _bootstrap_widget_class(widget)
            existing = widget.attrs.get('class', '')
            if css not in existing.split():
                widget.attrs['class'] = (existing + ' ' + css).strip()


class ContactForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ('name', 'phone', 'message')
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': "Ismingiz"}),
            'phone': forms.TextInput(attrs={'placeholder': '+998 90 123 45 67'}),
            'message': forms.Textarea(
                attrs={'rows': 5, 'placeholder': 'Xabaringiz...'}
            ),
        }
        labels = {
            'name': "Ism",
            'phone': "Telefon",
            'message': "Xabar",
        }


class FAQForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = FAQ
        fields = ('question', 'answer', 'order', 'is_active')