from django.db import models
from django.core.validators import MinLengthValidator, MinValueValidator, MaxValueValidator

from cakes.models import Cake
from clients.models import Client


class Review(models.Model):
    """Mijoz sharhi. Admin tasdiqlagandan keyin saytda ko'rinadi."""

    class Rating(models.IntegerChoices):
        ONE = 1, '1 yulduz'
        TWO = 2, '2 yulduz'
        THREE = 3, '3 yulduz'
        FOUR = 4, '4 yulduz'
        FIVE = 5, '5 yulduz'

    cake = models.ForeignKey(
        Cake, on_delete=models.CASCADE, null=True, blank=True,
        related_name='reviews', verbose_name="Tort",
    )
    client = models.ForeignKey(
        Client, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviews', verbose_name="Mijoz",
    )
    author_name = models.CharField("Ism", max_length=120)
    rating = models.PositiveSmallIntegerField(
        "Baho", choices=Rating.choices, default=Rating.FIVE,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    text = models.TextField(
        "Sharh", max_length=1000, validators=[MinLengthValidator(10)]
    )
    is_published = models.BooleanField("Tasdiqlangan", default=False)
    is_answered = models.BooleanField("Javob berilgan", default=False)
    created_at = models.DateTimeField("Yozilgan", auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Sharh"
        verbose_name_plural = "Sharhlar"

    def __str__(self):
        return f"{self.author_name} — {self.get_rating_display()}"

    @property
    def stars(self):
        return range(1, self.rating + 1)