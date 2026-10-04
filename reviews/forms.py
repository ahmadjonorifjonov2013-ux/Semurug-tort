from django import forms

from core.forms import BootstrapFormMixin

from .models import Review


class StarRatingWidget(forms.RadioSelect):
    """Baho uchun bosiladigan yulduzlar (5 ta).

    Radio inputlar yashiriladi, yulduzcha belgisi `★` ko'rsatiladi.
    `skip_bootstrap_class` — BootstrapFormMixin bu widgetga klass
    qo'shmasligi kerak, chunki markupni o'zimiz chizamyiz.
    """

    template_name = 'reviews/widgets/stars.html'
    skip_bootstrap_class = True


class ReviewForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Review
        fields = ('rating', 'text', 'cake')
        widgets = {
            'rating': StarRatingWidget,
            'text': forms.Textarea(
                attrs={'rows': 4, 'placeholder': "Tajribangizni yozing..."}
            ),
            'cake': forms.Select,
        }
        labels = {
            'rating': "Baho",
            'text': "Sharh",
            'cake': "Tort",
        }

    def clean_text(self):
        text = (self.cleaned_data.get('text') or '').strip()
        if len(text) < 10:
            raise forms.ValidationError("Kamida 10 ta belgi yozing")
        return text

    def __init__(self, *args, **kwargs):
        cake = kwargs.pop('cake', None)
        super().__init__(*args, **kwargs)
        # Modelda default 5 — forma esa tanlanmagan holatdan boshlanadi,
        # aks holda mijoz yulduzni bosmay 5 yulduz qo'yib yuboradi.
        self.fields['rating'].initial = None
        if cake is not None:
            self.fields['cake'].initial = cake.pk
            self.fields['cake'].widget = forms.HiddenInput()