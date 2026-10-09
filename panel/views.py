"""Sayt ichidagi boshqaruv paneli.

Admin shu yerdan saytni to'liq boshqaradi:
  * barcha buyurtmalarni ko'rish va rasmiylash (holat, to'lov, yetkazish);
  * tort qo'shish / tahrirlash / arxivlash (rasm bilan);
  * kategoriya, variant, allergen, promo kodlar;
  * mijozlar, kontakt xabarlari, sharhlar moderatsiyasi;
  * sayt sozlamalari, banner, galereya, savol-javoblar.

Kirish alohida: `panel:login` — faqat `is_staff` akkauntlar uchun.
"""

from django.contrib import messages
from django.contrib.auth import login, logout
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.core.paginator import Paginator
from django.db.models import Count, ProtectedError, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from cakes.models import Allergen, Cake, CakeImage, Category, Option
from clients.models import Client
from core.models import Banner, ContactMessage, FAQ, GalleryPhoto, SiteSettings
from core.ratelimit import rate_limit, reset_rate_limit
from orders.models import Order, PromoCode
from orders.services import send_order_to_telegram, send_status_to_telegram
from reviews.models import Review

from .decorators import SESSION_KEY, is_panel_admin, panel_required
from .forms import (PanelAllergenForm, PanelBannerForm, PanelCakeForm,
                    PanelCategoryForm, PanelClientForm, PanelFAQForm,
                    PanelGalleryForm, PanelLoginForm, PanelOptionForm,
                    PanelOrderForm, PanelPromoCodeForm, PanelSiteSettingsForm)

PAGE_SIZE = 20


def _paginate(request, queryset, per_page=PAGE_SIZE):
    paginator = Paginator(queryset, per_page)
    return paginator.get_page(request.GET.get('page'))


# ---------------------------------------------------------------------------
# Kirish / chiqish
# ---------------------------------------------------------------------------

@rate_limit('panel_login', limit=5, minutes=15, page='panel/login.html',
            message="Juda ko'p urinish. 15 daqiqa kutib, qayta urinib ko'ring.")
def panel_login(request):
    if is_panel_admin(request):
        return redirect('panel:dashboard')

    form = PanelLoginForm(request, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        request.session[SESSION_KEY] = user.pk     # panelga kirish belgisi
        reset_rate_limit(request, 'panel_login')
        next_url = request.POST.get('next') or ''
        return redirect(next_url if next_url.startswith('/') else 'panel:dashboard')

    # Sayt loginidan kirgan administrator — parol qayta so'ralmaydi.
    user = request.user
    if user.is_authenticated and user.is_staff:
        request.session[SESSION_KEY] = user.pk
        return redirect('panel:dashboard')

    return render(request, 'panel/login.html', {
        'form': form,
        'next': request.GET.get('next', ''),
    })


@panel_required
def panel_logout(request):
    request.session.pop(SESSION_KEY, None)
    logout(request)
    messages.info(request, "Chiqdingiz")
    return redirect('clients:login')


# ---------------------------------------------------------------------------
# Boshqaruv paneli
# ---------------------------------------------------------------------------

@panel_required
def dashboard(request):
    orders = Order.objects.select_related('client')
    today = timezone.localdate()

    stats = {
        'new_orders': orders.filter(status=Order.Status.NEW).count(),
        'today_orders': orders.filter(
            created_at__date=today).count(),
        'active_orders': orders.exclude(
            status__in=[Order.Status.DELIVERED, Order.Status.CANCELLED]
        ).count(),
        'delivered_count': orders.filter(
            status=Order.Status.DELIVERED).count(),
        'income': orders.filter(status=Order.Status.DELIVERED).aggregate(
            total=Sum('total_price'))['total'] or 0,
        'clients': Client.objects.count(),
        'cakes': Cake.objects.filter(is_active=True).count(),
        'archived_cakes': Cake.objects.filter(is_active=False).count(),
        'new_messages': ContactMessage.objects.filter(is_handled=False).count(),
        'pending_reviews': Review.objects.filter(is_published=False).count(),
    }

    return render(request, 'panel/dashboard.html', {
        'stats': stats,
        'today': today,
        'recent_orders': orders[:8],
        'messages_list': ContactMessage.objects.filter(
            is_handled=False)[:5],
        'reviews_list': Review.objects.filter(is_published=False)[:5],
    })


# ---------------------------------------------------------------------------
# Buyurtmalar
# ---------------------------------------------------------------------------

@panel_required
def order_list(request):
    orders = Order.objects.select_related('client')

    status = request.GET.get('status', '')
    if status in dict(Order.Status.choices):
        orders = orders.filter(status=status)

    query = request.GET.get('q', '').strip()
    if query:
        condition = (Q(client__full_name__icontains=query)
                     | Q(client__phone__icontains=query)
                     | Q(delivery_address__icontains=query))
        if query.isdigit():
            condition |= Q(pk=int(query))
        orders = orders.filter(condition)

    counts = {row['status']: row['n'] for row in
              Order.objects.values('status').annotate(n=Count('id'))}
    counts['all'] = Order.objects.count()
    status_tabs = [(value, label, counts.get(value, 0))
                   for value, label in Order.Status.choices]

    return render(request, 'panel/orders.html', {
        'page': _paginate(request, orders),
        'status': status,
        'query': query,
        'counts': counts,
        'statuses': status_tabs,
    })


@panel_required
def order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.select_related('client', 'promo_code').prefetch_related(
            'items__cake', 'items__options'),
        pk=pk,
    )
    form = PanelOrderForm(request.POST or None, instance=order)

    if request.method == 'POST' and form.is_valid():
        old_status = order.status
        form.save()
        if old_status != order.status:
            send_status_to_telegram(order, old_status)
        messages.success(request, "Buyurtma yangilandi")
        return redirect('panel:order_detail', pk=order.pk)

    return render(request, 'panel/order_detail.html', {
        'order': order,
        'form': form,
    })


@panel_required
@require_POST
def order_action(request, pk):
    """Holatni tez o'zgartirish (ro'yxadagi tugmalar)."""
    order = get_object_or_404(Order.objects.select_related('client'), pk=pk)
    action = request.POST.get('action', '')

    if action == 'paid':
        order.is_paid = not order.is_paid
        order.save(update_fields=['is_paid', 'updated_at'])
        messages.success(request, "To'lov holati yangilandi")

    elif action == 'recalc':
        total = order.recalc_total()
        messages.success(request, f"Summa qayta hisoblandi: {total:,.0f} so'm")

    elif action == 'notify':
        sent = send_order_to_telegram(order, blocking=True)
        messages.info(request, "Telegram'ga yuborildi" if sent
                      else "Telegram'ga yuborib bo'lmadi (sozlama tekshirilsin)")

    elif action == 'confirm_phone':
        """Rasmiylash: mijoz telefonini aniqlashtirganini belgilash."""
        order.comment = (order.comment or '').rstrip()
        note = f"[{timezone.localtime():%d.%m.%Y %H:%M}] Telefon tasdiqlandi: {order.client.phone}"
        order.comment = f"{order.comment}\n{note}".strip()
        order.save(update_fields=['comment', 'updated_at'])
        messages.success(request, "Telefon tasdiqlandi deb belgilandi")

    else:
        messages.warning(request, "Noma'lum amal")

    return redirect('panel:order_detail', pk=order.pk)


# ---------------------------------------------------------------------------
# Tortlar
# ---------------------------------------------------------------------------

@panel_required
def cake_list(request):
    cakes = Cake.objects.select_related('category')

    query = request.GET.get('q', '').strip()
    if query:
        cakes = cakes.filter(Q(name__icontains=query)
                             | Q(description__icontains=query))

    category = request.GET.get('category', '').strip()
    if category.isdigit():
        cakes = cakes.filter(category_id=int(category))

    show = request.GET.get('show', 'active')
    if show == 'archived':
        cakes = cakes.filter(is_active=False)
    elif show == 'all':
        pass
    else:
        cakes = cakes.filter(is_active=True)

    return render(request, 'panel/cakes.html', {
        'page': _paginate(request, cakes),
        'query': query,
        'category': category,
        'show': show,
        'categories': Category.objects.all(),
        'counts': {
            'active': Cake.objects.filter(is_active=True).count(),
            'archived': Cake.objects.filter(is_active=False).count(),
            'all': Cake.objects.count(),
        },
    })


@panel_required
def cake_create(request):
    form = PanelCakeForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        cake = form.save()
        _add_gallery_images(cake, form.cleaned_data.get('gallery_images'))
        messages.success(request, f"«{cake.name}» qo'shildi")
        return redirect('panel:cake_edit', pk=cake.pk)

    return render(request, 'panel/cake_form.html', {
        'form': form,
        'cake': None,
        'gallery': CakeImage.objects.none(),
    })


@panel_required
def cake_edit(request, pk):
    cake = get_object_or_404(Cake, pk=pk)
    form = PanelCakeForm(request.POST or None, request.FILES or None,
                         instance=cake)

    if request.method == 'POST' and form.is_valid():
        cake = form.save()
        _add_gallery_images(cake, form.cleaned_data.get('gallery_images'))
        messages.success(request, "Tort saqlandi")
        return redirect('panel:cake_edit', pk=cake.pk)

    return render(request, 'panel/cake_form.html', {
        'form': form,
        'cake': cake,
        'gallery': cake.images.all(),
    })


def _add_gallery_images(cake, files):
    if not files:
        return
    if isinstance(files, UploadedFile):
        files = [files]
    order = cake.images.count()
    for index, upload in enumerate(files, start=1):
        CakeImage.objects.create(cake=cake, image=upload,
                                 order=order + index)


@panel_required
@require_POST
def cake_flag(request, pk):
    """Tortni arxivlash / saytga qaytarish, mavjudligini o'zgartirish."""
    cake = get_object_or_404(Cake, pk=pk)
    action = request.POST.get('action', '')

    if action == 'archive':
        cake.is_active = False
        cake.save(update_fields=['is_active', 'updated_at'])
        messages.success(request, f"«{cake.name}» arxivlandi (saytdan berkitildi)")
    elif action == 'restore':
        cake.is_active = True
        cake.save(update_fields=['is_active', 'updated_at'])
        messages.success(request, f"«{cake.name}» saytga qaytarildi")
    elif action == 'available':
        cake.is_available = not cake.is_available
        cake.save(update_fields=['is_available', 'updated_at'])
        state = 'mavjud' if cake.is_available else 'mavjud emas'
        messages.success(request, f"«{cake.name}» — hozir {state}")
    else:
        messages.warning(request, "Noma'lum amal")

    return redirect(request.POST.get('next') or 'panel:cakes')


@panel_required
@require_POST
def cake_delete(request, pk):
    cake = get_object_or_404(Cake, pk=pk)
    name = cake.name
    try:
        cake.delete()
    except ProtectedError:
        messages.error(
            request,
            f"«{name}» buyurtmalarda ishlatilgani uchun o'chirib bo'lmaydi. "
            "Arxivlang (saytdan berkitilsin).",
        )
    else:
        messages.success(request, f"«{name}» o'chirildi")

    return redirect(request.POST.get('next') or 'panel:cakes')


@panel_required
@require_POST
def gallery_image_delete(request, pk):
    """Tort galereyasidan bitta rasmni o'chirish."""
    image = get_object_or_404(CakeImage, pk=pk)
    cake_pk = image.cake_id
    image.image.delete(save=False)
    image.delete()
    messages.success(request, "Rasm o'chirildi")
    return redirect('panel:cake_edit', pk=cake_pk)


# ---------------------------------------------------------------------------
# Katalog: kategoriya, variant, allergen, promo kod
# ---------------------------------------------------------------------------

@panel_required
def catalog(request):
    return render(request, 'panel/catalog.html', {
        'categories': Category.objects.annotate(
            total_cakes=Count('cakes')),
        'category_form': PanelCategoryForm(),
        'options': Option.objects.all(),
        'option_form': PanelOptionForm(),
        'allergens': Allergen.objects.all(),
        'allergen_form': PanelAllergenForm(),
        'promo_codes': PromoCode.objects.all(),
        'promo_form': PanelPromoCodeForm(),
    })


@panel_required
@require_POST
def category_save(request, pk=None):
    instance = get_object_or_404(Category, pk=pk) if pk else None
    form = PanelCategoryForm(request.POST or None, request.FILES or None,
                             instance=instance)
    if form.is_valid():
        form.save()
        messages.success(request, "Kategoriya saqlandi")
    else:
        messages.error(request, "Kategoriya saqlanmadi")
    return redirect('panel:catalog')


@panel_required
@require_POST
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    name = category.name
    try:
        category.delete()
    except ProtectedError:
        messages.error(request, f"«{name}» ichida tortlar bor — "
                                "avval ularni boshqa kategoriyaga ko'chiring")
    else:
        messages.success(request, f"«{name}» kategoriyasi o'chirildi")
    return redirect('panel:catalog')


@panel_required
@require_POST
def option_save(request, pk=None):
    instance = get_object_or_404(Option, pk=pk) if pk else None
    form = PanelOptionForm(request.POST or None, instance=instance)
    if form.is_valid():
        form.save()
        messages.success(request, "Variant saqlandi")
    else:
        messages.error(request, "Variant saqlanmadi")
    return redirect('panel:catalog')


@panel_required
@require_POST
def option_delete(request, pk):
    option = get_object_or_404(Option, pk=pk)
    name = option.name
    option.delete()
    messages.success(request, f"«{name}» varianti o'chirildi")
    return redirect('panel:catalog')


@panel_required
@require_POST
def allergen_save(request):
    form = PanelAllergenForm(request.POST)
    if form.is_valid():
        name = form.cleaned_data['name']
        if Allergen.objects.filter(name__iexact=name).exists():
            messages.warning(request, "Bunday allergen allaqachon bor")
        else:
            form.save()
            messages.success(request, "Allergen qo'shildi")
    return redirect('panel:catalog')


@panel_required
@require_POST
def allergen_delete(request, pk):
    allergen = get_object_or_404(Allergen, pk=pk)
    name = allergen.name
    allergen.delete()
    messages.success(request, f"«{name}» o'chirildi")
    return redirect('panel:catalog')


@panel_required
@require_POST
def promo_save(request, pk=None):
    instance = get_object_or_404(PromoCode, pk=pk) if pk else None
    form = PanelPromoCodeForm(request.POST or None, instance=instance)
    if form.is_valid():
        try:
            form.save()
        except ValidationError as err:
            messages.error(request, "; ".join(err.messages))
            return redirect('panel:catalog')
        messages.success(request, "Promo kod saqlandi")
    else:
        messages.error(request, "Promo kod saqlanmadi")
    return redirect('panel:catalog')


@panel_required
@require_POST
def promo_delete(request, pk):
    promo = get_object_or_404(PromoCode, pk=pk)
    code = promo.code
    promo.delete()
    messages.success(request, f"«{code}» o'chirildi")
    return redirect('panel:catalog')


# ---------------------------------------------------------------------------
# Sayt kontenti: banner, galereya, savol-javob
# ---------------------------------------------------------------------------

@panel_required
def content(request):
    return render(request, 'panel/content.html', {
        'banners': Banner.objects.all(),
        'banner_form': PanelBannerForm(),
        'photos': GalleryPhoto.objects.all(),
        'photo_form': PanelGalleryForm(),
        'faqs': FAQ.objects.all(),
        'faq_form': PanelFAQForm(),
    })


@panel_required
@require_POST
def banner_save(request):
    form = PanelBannerForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Banner qo'shildi")
    else:
        messages.error(request, "Banner saqlanmadi")
    return redirect('panel:content')


@panel_required
@require_POST
def banner_delete(request, pk):
    banner = get_object_or_404(Banner, pk=pk)
    banner.image.delete(save=False)
    banner.delete()
    messages.success(request, "Banner o'chirildi")
    return redirect('panel:content')


@panel_required
@require_POST
def photo_save(request):
    form = PanelGalleryForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Rasm qo'shildi")
    else:
        messages.error(request, "Rasm saqlanmadi")
    return redirect('panel:content')


@panel_required
@require_POST
def photo_delete(request, pk):
    photo = get_object_or_404(GalleryPhoto, pk=pk)
    photo.image.delete(save=False)
    photo.delete()
    messages.success(request, "Rasm o'chirildi")
    return redirect('panel:content')


@panel_required
@require_POST
def faq_save(request):
    form = PanelFAQForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Savol-javob qo'shildi")
    else:
        messages.error(request, "Saqlanmadi")
    return redirect('panel:content')


@panel_required
@require_POST
def faq_delete(request, pk):
    faq = get_object_or_404(FAQ, pk=pk)
    faq.delete()
    messages.success(request, "Savol-javob o'chirildi")
    return redirect('panel:content')


@panel_required
@require_POST
def content_flag(request, model, pk):
    """`Faol` belgisini tez o'zgartirish (banner / galereya / FAQ)."""
    allowed = {'banner': Banner, 'photo': GalleryPhoto, 'faq': FAQ}
    model_class = allowed.get(model)
    if model_class is None:
        messages.warning(request, "Noma'lum bo'lim")
        return redirect('panel:content')

    obj = get_object_or_404(model_class, pk=pk)
    obj.is_active = not obj.is_active
    obj.save(update_fields=['is_active'])
    state = 'yoqildi' if obj.is_active else 'yoqilindi'
    messages.success(request, f"{state}")
    return redirect('panel:content')


# ---------------------------------------------------------------------------
# Mijozlar
# ---------------------------------------------------------------------------

@panel_required
def client_list(request):
    clients = Client.objects.annotate(
        total_orders=Count('orders', distinct=True),
    ).order_by('-created_at')

    query = request.GET.get('q', '').strip()
    if query:
        clients = clients.filter(Q(full_name__icontains=query)
                                 | Q(phone__icontains=query)
                                 | Q(telegram__icontains=query))

    only_vip = request.GET.get('vip') == '1'
    if only_vip:
        clients = clients.filter(is_vip=True)

    return render(request, 'panel/clients.html', {
        'page': _paginate(request, clients),
        'query': query,
        'only_vip': only_vip,
        'counts': {
            'all': Client.objects.count(),
            'vip': Client.objects.filter(is_vip=True).count(),
        },
    })


@panel_required
def client_detail(request, pk):
    client = get_object_or_404(
        Client.objects.prefetch_related('orders__items', 'reviews'), pk=pk)
    form = PanelClientForm(request.POST or None, instance=client)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Mijoz ma'lumotlari saqlandi")
        return redirect('panel:client_detail', pk=client.pk)

    return render(request, 'panel/client_detail.html', {
        'client': client,
        'form': form,
        'orders': client.orders.all(),
        'reviews': client.reviews.all(),
    })


@panel_required
@require_POST
def client_vip(request, pk):
    client = get_object_or_404(Client, pk=pk)
    client.is_vip = not client.is_vip
    client.save(update_fields=['is_vip'])
    state = 'VIP qilindi' if client.is_vip else 'VIP olindi'
    messages.success(request, state)
    return redirect(request.POST.get('next') or 'panel:clients')


# ---------------------------------------------------------------------------
# Xabarlar (kontakt formasi) va sharhlar
# ---------------------------------------------------------------------------

@panel_required
def message_list(request):
    messages_list = ContactMessage.objects.all()
    if request.GET.get('status') == 'handled':
        messages_list = messages_list.filter(is_handled=True)
    elif request.GET.get('status') != 'all':
        messages_list = messages_list.filter(is_handled=False)

    return render(request, 'panel/messages.html', {
        'page': _paginate(request, messages_list),
        'counts': {
            'new': ContactMessage.objects.filter(is_handled=False).count(),
            'all': ContactMessage.objects.count(),
        },
        'status': request.GET.get('status', 'new'),
    })


@panel_required
@require_POST
def message_handle(request, pk):
    msg = get_object_or_404(ContactMessage, pk=pk)
    msg.is_handled = not msg.is_handled
    msg.save(update_fields=['is_handled'])
    return redirect('panel:messages')


@panel_required
@require_POST
def message_delete(request, pk):
    msg = get_object_or_404(ContactMessage, pk=pk)
    msg.delete()
    messages.success(request, "Xabar o'chirildi")
    return redirect('panel:messages')


@panel_required
def review_list(request):
    reviews = Review.objects.select_related('cake', 'client')
    if request.GET.get('status') == 'published':
        reviews = reviews.filter(is_published=True)
    elif request.GET.get('status') == 'all':
        pass
    else:
        reviews = reviews.filter(is_published=False)

    return render(request, 'panel/reviews.html', {
        'page': _paginate(request, reviews),
        'counts': {
            'pending': Review.objects.filter(is_published=False).count(),
            'all': Review.objects.count(),
        },
        'status': request.GET.get('status', 'pending'),
    })


@panel_required
@require_POST
def review_publish(request, pk):
    review = get_object_or_404(Review.objects.select_related('cake'), pk=pk)
    review.is_published = not review.is_published
    review.save(update_fields=['is_published'])
    state = 'saytga chiqarildi' if review.is_published else 'yashirildi'
    messages.success(request, f"Sharh {state}")
    return redirect('panel:reviews')


@panel_required
@require_POST
def review_delete(request, pk):
    review = get_object_or_404(Review, pk=pk)
    review.delete()
    messages.success(request, "Sharh o'chirildi")
    return redirect('panel:reviews')


# ---------------------------------------------------------------------------
# Sayt sozlamalari
# ---------------------------------------------------------------------------

@panel_required
def settings_edit(request):
    # Sozlamalar qatori yo'q bo'lsa ham forma ishlaydi (bo'sh instance).
    form = PanelSiteSettingsForm(request.POST or None,
                                instance=SiteSettings.objects.first())

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Sozlamalar saqlandi")
        return redirect('panel:settings')

    return render(request, 'panel/settings.html', {'form': form})