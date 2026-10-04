from datetime import timedelta

from django.core.paginator import Paginator
from django.db.models import Avg, Max, Min, Q
from django.shortcuts import render, get_object_or_404
from django.utils import timezone

from .models import Category, Cake, Option, Allergen

SORT_MAP = {
    'price_asc': ('price',),
    'price_desc': ('-price',),
    'new': ('-created_at',),
    'name': ('name',),
}

SORT_LABELS = {
    'new': 'Yangi',
    'price_asc': 'Arzon',
    'price_desc': 'Qimmat',
    'name': "A -> Z",
}

PAGE_SIZE = 12


def _filter_cakes(request):
    """URL parametrlariga asoslanib katalogni filtrlaydi."""
    cakes = Cake.objects.filter(is_active=True).select_related('category')

    category = request.GET.get('category')
    if category:
        cakes = cakes.filter(category__slug=category)

    price_min = request.GET.get('price_min')
    price_max = request.GET.get('price_max')
    if price_min:
        cakes = cakes.filter(price__gte=price_min)
    if price_max:
        cakes = cakes.filter(price__lte=price_max)

    search = request.GET.get('search')
    if search:
        cakes = cakes.filter(
            Q(name__icontains=search) | Q(description__icontains=search)
        )

    if request.GET.get('available'):
        cakes = cakes.filter(is_available=True)
    if request.GET.get('preorder'):
        cakes = cakes.filter(is_preorder=True)

    allergen = request.GET.get('allergen')
    if allergen:
        cakes = cakes.filter(allergens__name=allergen)

    sort = request.GET.get('sort', 'new')
    return cakes.order_by(*SORT_MAP.get(sort, SORT_MAP['new'])).distinct()


def cake_list(request, category_slug=None):
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug,
                                     is_active=True)
    else:
        category = None

    if category:
        request.GET = request.GET.copy()
        request.GET['category'] = category.slug

    cakes = _filter_cakes(request)
    page = Paginator(cakes, PAGE_SIZE).get_page(request.GET.get('page'))
    price_range = cakes.aggregate(low=Min('price'), high=Max('price'))

    context = {
        'page_obj': page,
        'cakes': page.object_list,
        'categories': Category.objects.filter(is_active=True),
        'current_category': category,
        'options': Option.objects.filter(is_active=True),
        'allergens': Allergen.objects.all(),
        'selected': request.GET,
        'sort': request.GET.get('sort', 'new'),
        'sort_labels': SORT_LABELS,
        'result_count': cakes.count(),
        'price_range': price_range,
    }
    return render(request, 'cakes/cake_list.html', context)


def cake_detail(request, slug):
    cake = get_object_or_404(
        Cake.objects.select_related('category').prefetch_related(
            'images', 'options', 'allergens'
        ),
        slug=slug, is_active=True,
    )

    min_date = timezone.localdate() + timedelta(days=cake.min_order_days)
    reviews = cake.reviews.filter(is_published=True)
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0

    option_groups = {}
    for opt in cake.options.filter(is_active=True):
        option_groups.setdefault(opt.group, []).append(opt)

    return render(request, 'cakes/cake_detail.html', {
        'cake': cake,
        'images': cake.images.all(),
        'related': cake.category.cakes.exclude(
            pk=cake.pk, is_active=True
        ).select_related('category')[:4],
        'options': cake.options.filter(is_active=True),
        'option_groups': option_groups,
        'allergens': cake.allergens.all(),
        'reviews': reviews,
        'avg_rating': avg_rating,
        'reviews_count': reviews.count(),
        'min_date': min_date,
    })