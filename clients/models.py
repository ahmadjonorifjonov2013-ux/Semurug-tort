from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator

phone_validator = RegexValidator(
    regex=r'^\+998\d{9}$',
    message="Telefon +998 XX XXX XX XX ko'rinishida bo'lishi kerak",
)


class Client(models.Model):
    """Mijoz. Django User bilan bog'lanadi, lekin login bo'lmagan ham bo'lishi mumkin."""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, null=True, blank=True,
        related_name='client', verbose_name="Login",
    )
    full_name = models.CharField("F.I.O", max_length=120)
    phone = models.CharField(
        "Telefon", max_length=20, unique=True, validators=[phone_validator]
    )
    telegram = models.CharField("Telegram", max_length=60, blank=True)
    email = models.EmailField("Email", blank=True)
    birthday = models.DateField("Tug'ilgan kuni", null=True, blank=True)
    address = models.TextField("Manzil", blank=True)
    notes = models.TextField("Izoh (allergiya, xohish)", blank=True)
    is_vip = models.BooleanField("VIP mijoz", default=False)
    created_at = models.DateTimeField("Ro'yxatdan o'tgan", auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Mijoz"
        verbose_name_plural = "Mijozlar"

    def __str__(self):
        return f"{self.full_name} ({self.phone})"

    @property
    def orders_count(self):
        return self.orders.count()

    @property
    def total_spent(self):
        return sum(o.total_price for o in self.orders.filter(status='delivered'))

    @property
    def telegram_username(self):
        """Telegram orqali xabar yuborish uchun (@username)."""
        return self.telegram.lstrip('@')