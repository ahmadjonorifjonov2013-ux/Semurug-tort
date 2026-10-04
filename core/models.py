from django.db import models
from django.utils.text import slugify


class SiteSettings(models.Model):
    """Butun sayt sozlamalari. Faqat 1 ta qator bo'ladi (core/signals.py)."""

    site_name = models.CharField(
        "Nomi", max_length=100, default="Semurg' TORT Markazi"
    )
    phone = models.CharField("Telefon", max_length=30)
    telegram = models.CharField("Telegram", max_length=60, blank=True)
    instagram = models.URLField("Instagram", blank=True)
    address = models.CharField("Manzil", max_length=200)
    work_hours = models.CharField(
        "Ish vaqti", max_length=100, default="Har kuni 09:00 - 22:00"
    )
    delivery_price = models.PositiveIntegerField(
        "Yetkazib berish narxi", default=0
    )
    free_delivery_from = models.PositiveIntegerField(
        "Bunda katta bo'lsa bepul", null=True, blank=True
    )
    about_text = models.TextField("Biz haqimizda", blank=True)
    map_url = models.URLField("Xarita", blank=True)

    class Meta:
        verbose_name = "Sayt sozlamalari"
        verbose_name_plural = "Sayt sozlamalari"

    def __str__(self):
        return self.site_name


class Banner(models.Model):
    """Bosh sahifadagi slayder."""

    title = models.CharField("Sarlavha", max_length=150)
    subtitle = models.CharField("Matn", max_length=255, blank=True)
    image = models.ImageField("Rasm", upload_to='banners/')
    link = models.URLField("Havola", blank=True)
    is_active = models.BooleanField("Faol", default=True)
    order = models.PositiveIntegerField("Tartib", default=0)

    class Meta:
        ordering = ['order']
        verbose_name = "Banner"
        verbose_name_plural = "Bannerlar"

    def __str__(self):
        return self.title


class GalleryPhoto(models.Model):
    """Tayyor tortlar fotosi (bosh sahifadagi galereya)."""

    image = models.ImageField("Rasm", upload_to='gallery/')
    caption = models.CharField("Izoh", max_length=150, blank=True)
    is_active = models.BooleanField("Faol", default=True)
    order = models.PositiveIntegerField("Tartib", default=0)

    class Meta:
        ordering = ['order']
        verbose_name = "Galereya rasmi"
        verbose_name_plural = "Galereya rasmlari"

    def __str__(self):
        return self.caption or f"Galereya #{self.pk}"


class FAQ(models.Model):
    """Savol-javob bloklari."""

    question = models.CharField("Savol", max_length=255)
    answer = models.TextField("Javob")
    order = models.PositiveIntegerField("Tartib", default=0)
    is_active = models.BooleanField("Faol", default=True)

    class Meta:
        ordering = ['order']
        verbose_name = "Savol-javob"
        verbose_name_plural = "Savol-javoblar"

    def __str__(self):
        return self.question


class ContactMessage(models.Model):
    """Kontakt formasi orqali kelgan xabarlar."""

    name = models.CharField("Ism", max_length=120)
    phone = models.CharField("Telefon", max_length=20)
    message = models.TextField("Xabar")
    is_handled = models.BooleanField("Ko'rib chiqildi", default=False)
    created_at = models.DateTimeField("Kelgan vaqti", auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Xabar"
        verbose_name_plural = "Xabarlar"

    def __str__(self):
        return f"{self.name} — {self.created_at:%d.%m.%Y %H:%M}"


class SlugModel(models.Model):
    """Slug avtomatik to'ldiriladigan modellarning umumiy poydevori."""

    slug = models.SlugField("URL", max_length=160, unique=True, blank=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)