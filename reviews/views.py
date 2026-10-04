from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from cakes.models import Cake
from orders.services import send_review_to_telegram

from .forms import ReviewForm
from .models import Review


def review_list(request, slug=None):
    """Barcha sharhlar yoki bitta tortning sharhlari."""
    reviews = Review.objects.filter(is_published=True).select_related('cake')

    cake = None
    if slug:
        cake = get_object_or_404(Cake, slug=slug)
        reviews = reviews.filter(cake=cake)

    return render(request, 'reviews/list.html', {
        'reviews': reviews,
        'cake': cake,
    })


def add_review(request, slug):
    cake = get_object_or_404(Cake, slug=slug)
    form = ReviewForm(request.POST or None, cake=cake)

    if request.method == 'POST' and form.is_valid():
        review = form.save(commit=False)
        review.cake = cake
        review.client = getattr(request.user, 'client', None)
        review.author_name = (
            review.client.full_name
            if review.client else 'Mehmon'
        )
        review.is_published = False        # admin tasdiqlaydi
        review.save()
        send_review_to_telegram(review)
        messages.info(request, "Sharhingiz qabul qilindi. Tez orada ko'rinadi.")
        return redirect('cakes:detail', slug=slug)

    return render(request, 'reviews/add.html', {'form': form, 'cake': cake})


def delete_own_review(request, pk):
    """Faqat sharh egasi yoki admin o'chira oladi."""
    review = get_object_or_404(Review, pk=pk)

    is_owner = (review.client and review.client.user_id == request.user.id)
    if not (is_owner or request.user.is_staff):
        messages.error(request, "Bu sharhni o'chira olmaysiz")
        return redirect('reviews:list')

    cake_slug = review.cake.slug if review.cake else None
    review.delete()
    messages.success(request, "Sharh o'chirildi")
    if cake_slug:
        return redirect('cakes:detail', slug=cake_slug)
    return redirect(reverse('reviews:list'))