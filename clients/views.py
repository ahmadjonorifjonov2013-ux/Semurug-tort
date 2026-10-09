from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from core.ratelimit import rate_limit, reset_rate_limit
from panel.decorators import SESSION_KEY

from .models import Client
from .forms import (ClientRegistrationForm, ClientLoginForm,
                    ClientProfileForm, clean_phone_value)


def _free_phone(user):
    """Client yaratish uchun unikal telefon raqami.

    Profili yo'q foydalanuvchi saytga kirganda Client qatori avtomatik
    yaratiladi. Telefon esa unique — agar raqam band bo'lsa (masalan,
    boshqa akkaunt allaqachon `+99800000000` ni olgan), 500 xato chiqmasligi
    kerak. Shuning uchun 00 bilan boshlangan vaqtinchalik raqam tanlanadi
    (haqiqiy raqamlar 90/93/94/95/97/99 bilan boshlanadi).
    """

    def variants():
        if user.username.isdigit() and len(user.username) == 9:
            yield f"+998{user.username}"
        seed = (user.pk or 0) % 10_000_000
        for i in range(1000):
            yield f"+99800{(seed + i) % 10_000_000:07d}"

    taken = set(Client.objects.values_list('phone', flat=True))
    for phone in variants():
        if phone not in taken:
            return phone
    # Amalda yetib qolmaydi: 1000 ta variant va faqat bitta foydalanuvchi.
    return "+99800000001"


def _client_for(user):
    """Login qilgan userga Client qatorini qaytaradi, yo'q bo'lsa yaratadi."""
    client = Client.objects.filter(user=user).first()
    if client:
        return client
    return Client.objects.create(
        user=user,
        full_name=user.get_full_name() or user.username,
        phone=_free_phone(user),
        email=user.email,
    )


@rate_limit('register', limit=6, minutes=60, page='clients/register.html')
def register(request):
    if request.user.is_authenticated:
        return redirect('core:home')

    form = ClientRegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        phone = form.cleaned_data['phone']
        if Client.objects.filter(phone=phone).exists():
            form.add_error('phone', "Bu telefon allaqachon ro'yxatdan o'tgan")
            return render(request, 'clients/register.html', {'form': form})

        user = form.save()                        # 1. User yaratildi
        Client.objects.create(                    # 2. Client yaratildi
            user=user,
            full_name=form.cleaned_data['full_name'],
            phone=phone,
            telegram=form.cleaned_data.get('telegram', ''),
            email=form.cleaned_data.get('email', ''),
        )
        login(request, user)                      # 3. Avtomatik kiritish
        reset_rate_limit(request, 'register')
        messages.success(request, "Xush kelibsiz!")
        return redirect('core:home')

    return render(request, 'clients/register.html', {'form': form})


@rate_limit('login', limit=8, minutes=10, page='clients/login.html')
def client_login(request):
    form = ClientLoginForm(request, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        reset_rate_limit(request, 'login')

        if user.is_staff:
            # Administrator sayt loginidan kirdi — panelga qayta login
            # so'ralmaydi, shu yerda panel belgisi qo'yiladi.
            request.session[SESSION_KEY] = user.pk
            return redirect('panel:dashboard')

        next_url = request.GET.get('next') or request.POST.get('next')
        if next_url and next_url.startswith('/'):
            return redirect(next_url)
        return redirect('core:home')
    return render(request, 'clients/login.html',
                  {'form': form, 'next': request.GET.get('next', '')})


@login_required
def client_logout(request):
    logout(request)
    messages.info(request, "Siz chiqdingiz")
    return redirect('core:home')


@login_required
def profile(request):
    client = _client_for(request.user)
    form = ClientProfileForm(request.POST or None, instance=client)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Ma'lumotlar saqlandi")
        return redirect('clients:profile')

    return render(request, 'clients/profile.html',
                  {'form': form, 'client': client})


@login_required
def profile_orders(request):
    """Mijozning buyurtmalari (tarixi)."""
    client = _client_for(request.user)
    orders = client.orders.prefetch_related('items').all()
    return render(request, 'clients/profile_orders.html', {
        'client': client,
        'orders': orders,
        'orders_count': client.orders_count,
        'total_spent': client.total_spent,
    })


def client_detail(request, pk):
    """Admin va xodimlar uchun mijoz sahifasi."""
    if not request.user.is_staff:
        return redirect('clients:profile')

    client = get_object_or_404(Client.objects.prefetch_related('orders'), pk=pk)
    return render(request, 'clients/client_detail.html', {
        'client': client,
        'orders': client.orders.all(),
        'reviews': client.reviews.all(),
    })


__all__ = [
    'register', 'client_login', 'client_logout', 'profile',
    'profile_orders', 'client_detail', 'clean_phone_value',
]