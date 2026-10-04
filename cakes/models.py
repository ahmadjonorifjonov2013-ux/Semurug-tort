from decimal import Decimal

from django.db import models
from django.core.validators import MinValueValidator
from django.urls import reverse

from core.models import SlugModel


class Category(SlugModel):
    """Tort turlari: Tug'ilgan kun, To'y torti, Shirinliklar va h.k."""

    name = models.CharField("Nomi", max_length=100, unique=True)
    description = models.TextField("Tavsifi", blank=True)
    image = models.ImageField("Rasm", upload_to='categories/', blank=True)
    order = models.PositiveIntegerField("Tartib", default=0)
    is_active = models.BooleanField("Faol", default=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = "Kategoriya"
        verbose_name_plural = "Kategoriyalar"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return f"{reverse('cakes:list')}?category={self.slug}"

    @property
    def cakes_count(self):
        return self.cakes.filter(is_active=True).count()


class Option(models.Model):
    """O'lcham, ta'm, qatlam — narxga qo'shimcha variant."""

    name = models.CharField("Nomi", max_length=100)
    group = models.CharField("Guruh", max_length=50, default="O'lcham")
    price_delta = models.DecimalField(
        "Qo'shimcha narx", max_digits=10, decimal_places=2, default=0
    )
    is_active = models.BooleanField("Faol", default=True)

    class Meta:
        ordering = ['group', 'name']
        verbose_name = "Variant"
        verbose_name_plural = "Variantlar"

    def __str__(self):
        return f"{self.name} ({self.group})"


class Allergen(models.Model):
    """Yong'oq, tuxum, sut — mijozni ogohlantirish uchun."""

    name = models.CharField("Nomi", max_length=50, unique=True)

    class Meta:
        verbose_name = "Allergen"
        verbose_name_plural = "Allergenlar"

    def __str__(self):
        return self.name


class Cake(SlugModel):
    """Asosiy mahsulot — tort."""

    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name='cakes',
        verbose_name="Kategoriya",
    )
    name = models.CharField("Nomi", max_length=150)
    description = models.TextField("Tavsifi")
    price = models.DecimalField(
        "Narxi", max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    old_price = models.DecimalField(
        "Eski narxi", max_digits=10, decimal_places=2, null=True, blank=True
    )
    weight_gram = models.PositiveIntegerField("Og'irligi (gramm)", default=0)
    main_image = models.ImageField("Asosiy rasm", upload_to='cakes/')
    is_available = models.BooleanField("Mavjud", default=True)
    is_active = models.BooleanField("Saytda ko'rinadi", default=True)
    is_preorder = models.BooleanField("Faqat oldindan buyurtma", default=False)
    min_order_days = models.PositiveSmallIntegerField(
        "Kamida kun oldin", default=0
    )
    options = models.ManyToManyField(
        Option, blank=True, verbose_name="Variantlar", related_name='cakes'
    )
    allergens = models.ManyToManyField(
        Allergen, blank=True, verbose_name="Allergenlar", related_name='cakes'
    )
    created_at = models.DateTimeField("Qo'shilgan", auto_now_add=True)
    updated_at = models.DateTimeField("O'zgartirilgan", auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Tort"
        verbose_name_plural = "Tortlar"
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['price']),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('cakes:detail', kwargs={'slug': self.slug})

    @property
    def has_discount(self):
        return bool(self.old_price and self.old_price > self.price)

    @property
    def discount_percent(self):
        if not self.has_discount:
            return 0
        return int((self.old_price - self.price) / self.old_price * 100)

    @property
    def active_options(self):
        return self.options.filter(is_active=True)

    def price_with(self, option_ids=()):
        """Tanlangan variantlarning qo'shimcha narxi bilan umumiy narx."""
        total = Decimal(self.price)
        if option_ids:
            total += sum(
                (o.price_delta for o in Option.objects.filter(pk__in=option_ids)),
                Decimal('0'),
            )
        return total


class CakeImage(models.Model):
    """Bitta tortning qo'shimcha rasmlari (galereya)."""

    cake = models.ForeignKey(
        Cake, on_delete=models.CASCADE, related_name='images'
    )
    image = models.ImageField("Rasm", upload_to='cakes/gallery/')
    order = models.PositiveIntegerField("Tartib", default=0)

    class Meta:
        ordering = ['order']
        verbose_name = "Tort rasmi"
        verbose_name_plural = "Tort rasmlari"

    def __str__(self):
        return f"{self.cake.name} — rasm {self.pk}"