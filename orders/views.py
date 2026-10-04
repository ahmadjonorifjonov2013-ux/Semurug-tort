from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from cakes.models import Cake

from . import cart
from .forms import OrderForm
from .models import Order, OrderItem, PromoCode
from .services import send_order_to_telegram, send_status_to_telegram


def cart_view(request):
    rows, total = cart.rows(request)
    return render(request, 'orders/cart.html', {
        'rows': rows,
        'total': total,
        'count': cart.count(request),
    })


@require_POST
def cart_add(request, pk):
    cake = get_object_or_404(Cake, pk=pk, is_active=True)
    if not cake.is_available:
        messages.warning(request, "Bu tort hozircha mavjud emas")
        return redirect('cakes:detail', slug=cake.slug)

    quantity = request.POST.get('quantity') or 1
    try:
        quantity = max(1, min(int(quantity), 99))
    except (TypeError, ValueError):
        quantity = 1

    cart.add(request, pk, quantity,
             options=request.POST.getlist('options'))
    messages.success(request, f"«{cake.name}» savatga qo'shildi")

    next_url = request.POST.get('next')
    return redirect(next_url if next_url and next_url.startswith('/')
                    else 'orders:cart')


@require_POST
def cart_update(request, pk):
    try:
        quantity = int(request.POST.get('quantity', 1))
    except (TypeError, ValueError):
        quantity = 1

    cart.update(request, pk, quantity,
                options=request.POST.getlist('options'),
                comment=request.POST.get('comment', ''))
    return redirect('orders:cart')


@require_POST
def cart_remove(request, pk):
    cart.remove(request, pk)
    messages.info(request, "Savatdan o'chirildi")
    return redirect('orders:cart')


@require_POST
def cart_clear(request):
    cart.clear(request)
    messages.info(request, "Savat to'latildi")
    return redirect('cakes:list')


def checkout(request):
    rows, total = cart.rows(request)
    if not rows:
        messages.warning(request, "Savat bo'sh")
        return redirect('cakes:list')

    min_date = timezone.localdate()
    for row in rows:
        min_date = max(min_date, timezone.localdate()
                       + timedelta(days=row['cake'].min_order_days))

    if request.method == 'POST':
        form = OrderForm(request.POST, min_date=min_date)
        if form.is_valid():
            with transaction.atomic():
                client = form.get_or_create_client()
                order = Order.objects.create(
                    client=client,
                    delivery_address=form.cleaned_data['delivery_address'],
                    delivery_date=form.cleaned_data['delivery_date'],
                    delivery_time=form.cleaned_data.get('delivery_time'),
                    payment_method=form.cleaned_data['payment_method'],
                    comment=form.cleaned_data.get('comment', ''),
                )

                for row in rows:
                    item = OrderItem.objects.create(
                        order=order,
                        cake=row['cake'],
                        quantity=row['quantity'],
                        price=row['unit_price'],   # variantlar bilan narx
                        comment=row['comment'],
                    )
                    if row['options']:
                        item.options.set(row['options'])

                code_str = form.cleaned_data.get('promo_code', '')
                if code_str:
                    promo = PromoCode.objects.filter(
                        code=code_str, is_active=True
                    ).first()
                    if promo and promo.is_valid(total):
                        order.promo_code = promo
                        PromoCode.objects.filter(pk=promo.pk).update(
                            used_count=promo.used_count + 1
                        )
                    elif promo is None:
                        messages.warning(request, "Promo kod topilmadi")
                    else:
                        messages.warning(
                            request,
                            "Promo kod shartlarga mos kelmadi",
                        )

                order.recalc_total()
                order_number = order.pk
                cart.clear(request)

            send_order_to_telegram(order)
            messages.success(request, "Buyurtmangiz qabul qilindi!")
            if request.user.is_authenticated:
                return redirect('orders:detail', pk=order_number)
            return redirect(f"{reverse('orders:success_public')}?pk={order_number}")

    else:
        initial = {}
        if request.user.is_authenticated:
            client_profile = getattr(request.user, 'client', None)
            if client_profile:
                initial = {
                    'name': client_profile.full_name,
                    'phone': client_profile.phone,
                    'telegram': client_profile.telegram,
                    'delivery_address': client_profile.address,
                }
        form = OrderForm(initial=initial, min_date=min_date)

    return render(request, 'orders/checkout.html', {
        'form': form,
        'rows': rows,
        'total': total,
        'count': cart.count(request),
    })


@login_required
def success(request, pk):
    order = get_object_or_404(
        Order.objects.select_related('client').prefetch_related(
            'items__cake', 'items__options'
        ),
        pk=pk,
    )
    if order.client.user_id != request.user.id and not request.user.is_staff:
        return redirect('core:home')
    return render(request, 'orders/success.html', {'order': order})


def success_public(request, pk=None):
    """Ro'yxatdan o'tmagan mijoz uchun — faqat tasdiqlash sahifasi.

    Xavfsizlik: telefon raqami yashiriladi, manzil ko'rsatilmaydi.
    """
    if request.user.is_authenticated:
        return redirect('core:home')

    order = None
    if pk:
        order = Order.objects.filter(pk=pk).select_related('client').first()

    return render(request, 'orders/success.html', {
        'order': order,
        'order_number': pk,
        'is_public': True,
    })


@login_required
def order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.select_related('client', 'promo_code').prefetch_related(
            'items__cake', 'items__options'
        ),
        pk=pk,
    )
    is_owner = order.client.user_id == request.user.id
    if not (is_owner or request.user.is_staff):
        messages.error(request, "Bu buyurtma sizniki emas")
        return redirect('orders:my')

    return render(request, 'orders/detail.html', {'order': order})


@login_required
def my_orders(request):
    """Login qilgan mijozning buyurtmalari."""
    client_profile = getattr(request.user, 'client', None)
    orders = client_profile.orders.prefetch_related('items__cake') \
        if client_profile else Order.objects.none()
    return render(request, 'orders/my_orders.html', {
        'orders': orders,
        'client': client_profile,
    })


@login_required
@require_POST
def cancel_order(request, pk):
    order = get_object_or_404(Order, pk=pk, client__user=request.user)
    if order.status not in (Order.Status.NEW, Order.Status.CONFIRMED):
        messages.error(request, "Bu buyurtmani bekor qilib bo'lmaydi")
    else:
        old_status = order.status
        order.status = Order.Status.CANCELLED
        order.save(update_fields=['status'])
        send_status_to_telegram(order, old_status)
        messages.success(request, "Buyurtma bekor qilindi")
    return redirect('orders:detail', pk=pk)