from decimal import Decimal

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

from clients.models import Client
from core.models import SiteSettings
from cakes.models import Cake, Option


class PromoCode(models.Model):
    """Chegirma kodi (masalan: YANVAR10)."""

    code = models.CharField("Kod", max_length=20, unique=True)
    discount_percent = models.PositiveSmallIntegerField(
        "Chegirma %", default=10,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
    )
    min_order_sum = models.DecimalField(
        "Minimal summa", max_digits=12, decimal_places=2, default=0
    )
    valid_from = models.DateTimeField("Boshlanishi", null=True, blank=True)
    valid_until = models.DateTimeField("Tugashi", null=True, blank=True)
    is_active = models.BooleanField("Faol", default=True)
    used_count = models.PositiveIntegerField("Ishlatilgan", default=0)

    class Meta:
        ordering = ['-used_count', 'code']
        verbose_name = "Promo kod"
        verbose_name_plural = "Promo kodlar"

    def __str__(self):
        return self.code

    def is_valid(self, order_sum):
        now = timezone.now()
        if not self.is_active:
            return False
        if order_sum < self.min_order_sum:
            return False
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        return True

    @property
    def is_expired(self):
        return bool(self.valid_until and timezone.now() > self.valid_until)

    def discount_of(self, subtotal):
        return Decimal(subtotal) * self.discount_percent / Decimal(100)


class Order(models.Model):
    """Mijozning buyurtmasi."""

    class Status(models.TextChoices):
        NEW = 'new', 'Yangi'
        CONFIRMED = 'confirmed', 'Tasdiqlandi'
        IN_PROGRESS = 'in_progress', 'Tayyorlanmoqda'
        READY = 'ready', 'Tayyor'
        DELIVERED = 'delivered', 'Yetkazildi'
        CANCELLED = 'cancelled', 'Bekor qilindi'

    class PaymentMethod(models.TextChoices):
        CASH = 'cash', 'Naqd'
        CARD = 'card', 'Karta'
        CLICK = 'click', 'Click / Payme'

    client = models.ForeignKey(
        Client, on_delete=models.PROTECT, related_name='orders',
        verbose_name="Mijoz",
    )
    status = models.CharField(
        "Holat", max_length=20, choices=Status.choices,
        default=Status.NEW, db_index=True,
    )
    payment_method = models.CharField(
        "To'lov", max_length=10, choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
    )
    is_paid = models.BooleanField("To'landi", default=False)
    delivery_address = models.TextField("Yetkazish manzili")
    delivery_date = models.DateField("Yetkazish sanasi", db_index=True)
    delivery_time = models.TimeField("Vaqt", null=True, blank=True)
    comment = models.TextField("Izoh", blank=True)
    subtotal = models.DecimalField(
        "Tovar summasi", max_digits=12, decimal_places=2, default=0
    )
    delivery_price = models.DecimalField(
        "Yetkazib berish", max_digits=10, decimal_places=2, default=0
    )
    discount = models.DecimalField(
        "Chegirma", max_digits=12, decimal_places=2, default=0
    )
    total_price = models.DecimalField(
        "Jami", max_digits=12, decimal_places=2, default=0
    )
    promo_code = models.ForeignKey(
        PromoCode, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='orders', verbose_name="Promo kod",
    )
    created_at = models.DateTimeField("Yaratilgan", auto_now_add=True)
    updated_at = models.DateTimeField("O'zgartirilgan", auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Buyurtma"
        verbose_name_plural = "Buyurtmalar"
        indexes = [
            models.Index(fields=['status', '-created_at']),
        ]

    def __str__(self):
        return f"Buyurtma #{self.pk} — {self.client.full_name}"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('orders:detail', kwargs={'pk': self.pk})

    @property
    def items_count(self):
        return sum(i.quantity for i in self.items.all())

    @property
    def is_active(self):
        return self.status not in (self.Status.DELIVERED, self.Status.CANCELLED)

    @property
    def timeline(self):
        """Buyurtma holati bosqichlari (timeline uchun).

        Har bir element: {'key', 'label', 'state'}.
        state: done | current | pending | cancelled
        """
        flow = [
            (self.Status.NEW, 'Qabul qilindi'),
            (self.Status.CONFIRMED, 'Tasdiqlandi'),
            (self.Status.IN_PROGRESS, 'Tayyorlanmoqda'),
            (self.Status.READY, 'Tayyor'),
            (self.Status.DELIVERED, 'Yetkazildi'),
        ]

        if self.status == self.Status.CANCELLED:
            return [
                {'key': k, 'label': label,
                 'state': 'cancelled' if i == 0 else 'pending'}
                for i, (k, label) in enumerate(flow)
            ]

        current = next(
            (i for i, (k, _) in enumerate(flow) if k == self.status), 0
        )
        steps = []
        for i, (k, label) in enumerate(flow):
            if i < current:
                state = 'done'
            elif i == current:
                state = 'current'
            else:
                state = 'pending'
            steps.append({'key': k, 'label': label, 'state': state})
        return steps

    def recalc_total(self):
        """Jami summani qayta hisoblaydi va saqlaydi."""
        subtotal = sum(
            (i.subtotal for i in self.items.select_related('cake')), Decimal('0')
        )

        delivery = Decimal('0')
        site = SiteSettings.objects.first()
        if site:
            delivery = Decimal(site.delivery_price or 0)
            if site.free_delivery_from and subtotal >= site.free_delivery_from:
                delivery = Decimal('0')

        discount = Decimal('0')
        if self.promo_code:
            discount = self.promo_code.discount_of(subtotal)

        self.subtotal = subtotal
        self.delivery_price = delivery
        self.discount = discount
        self.total_price = subtotal + delivery - discount
        self.save(update_fields=['promo_code', 'subtotal', 'delivery_price',
                                  'discount', 'total_price'])
        return self.total_price


class OrderItem(models.Model):
    """Buyurtmadagi bitta tort."""

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='items'
    )
    cake = models.ForeignKey(
        Cake, on_delete=models.PROTECT, verbose_name="Tort"
    )
    quantity = models.PositiveIntegerField(
        "Soni", default=1, validators=[MinValueValidator(1)]
    )
    price = models.DecimalField("Narxi", max_digits=10, decimal_places=2)
    options = models.ManyToManyField(
        Option, blank=True, verbose_name="Variantlar"
    )
    comment = models.CharField("Yozuv", max_length=255, blank=True)

    class Meta:
        verbose_name = "Buyurtma tarkibi"
        verbose_name_plural = "Buyurtma tarkiblari"

    def __str__(self):
        return f"{self.cake.name} × {self.quantity}"

    @property
    def subtotal(self):
        return self.price * self.quantity

    @property
    def options_names(self):
        return ", ".join(o.name for o in self.options.all())