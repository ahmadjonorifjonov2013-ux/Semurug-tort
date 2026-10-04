from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render, redirect

from orders.services import send_contact_to_telegram

from .models import Banner, GalleryPhoto, FAQ
from .forms import ContactForm


def home(request):
    from cakes.models import Cake, Category

    cakes = Cake.objects.filter(is_active=True, is_available=True).select_related('category')

    context = {
        'banners': Banner.objects.filter(is_active=True),
        'categories': Category.objects.filter(is_active=True)[:6],
        'new_cakes': cakes[:8],
        'featured': cakes.exclude(main_image='').order_by('-created_at').first(),
        'gallery': GalleryPhoto.objects.filter(is_active=True)[:12],
        'faqs': FAQ.objects.filter(is_active=True)[:6],
        'reviews': None,
    }

    try:
        from reviews.models import Review
        context['reviews'] = Review.objects.filter(
            is_published=True, cake__isnull=True
        ).select_related('client')[:6]
    except Exception:
        context['reviews'] = None

    return render(request, 'core/home.html', context)


def about(request):
    return render(request, 'core/about.html')


def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            contact_msg = form.save()
            send_contact_to_telegram(contact_msg)
            messages.success(request, "Xabaringiz yuborildi. Tez orada aloqa qilamiz!")
            return redirect('core:contact')
    else:
        form = ContactForm()

    return render(request, 'core/contact.html', {'form': form})


def faq(request):
    context = {'faqs': FAQ.objects.filter(is_active=True)}
    return render(request, 'core/faq.html', context)


# ---------------------------------------------------------------------------
# SEO: robots.txt va sitemap.xml
# ---------------------------------------------------------------------------

ROBOTS_RULES = (
    'User-agent: *',
    'Allow: /',
    'Disallow: /admin/',
    'Disallow: /api/',
    'Disallow: /api-auth/',
    'Disallow: /clients/',
    'Disallow: /orders/',
    'Disallow: /reviews/add/',
)


def robots_txt(request):
    lines = list(ROBOTS_RULES)
    lines.append(f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}")
    return HttpResponse('\n'.join(lines) + '\n',
                        content_type='text/plain; charset=utf-8')


def _sitemap_url(location, changefreq, priority, lastmod=None):
    parts = [f"<url><loc>{location}</loc>"]
    if lastmod:
        value = lastmod.date().isoformat() if hasattr(lastmod, 'date') else lastmod
        parts.append(f"<lastmod>{value}</lastmod>")
    parts.append(f"<changefreq>{changefreq}</changefreq>")
    parts.append(f"<priority>{priority}</priority></url>")
    return ''.join(parts)


def sitemap_xml(request):
    """Statik sahifalar + faol tortlar, kategoriyalar va sharhlar."""
    from django.urls import reverse
    from django.utils import timezone

    from cakes.models import Cake, Category
    from reviews.models import Review

    base = request.build_absolute_uri('/').rstrip('/')
    today = timezone.now().date().isoformat()
    entries = []

    static_pages = (
        ('/', 'daily', '1.0'),
        ('/cakes/', 'daily', '0.9'),
        ('/about/', 'monthly', '0.6'),
        ('/faq/', 'monthly', '0.6'),
        ('/contact/', 'monthly', '0.7'),
        ('/reviews/', 'weekly', '0.6'),
    )
    for path_, freq, priority in static_pages:
        entries.append(_sitemap_url(f"{base}{path_}", freq, priority, today))

    for category in Category.objects.filter(is_active=True):
        entries.append(_sitemap_url(
            f"{base}{reverse('cakes:category', kwargs={'category_slug': category.slug})}",
            'weekly', '0.7', today,
        ))

    for cake in Cake.objects.filter(is_active=True, is_available=True):
        entries.append(_sitemap_url(
            f"{base}{cake.get_absolute_url()}", 'weekly', '0.9',
            getattr(cake, 'updated_at', None) or today,
        ))

    for review in Review.objects.filter(is_published=True).select_related('cake'):
        path_ = (f"/reviews/tort/{review.cake.slug}/" if review.cake else "/reviews/")
        entries.append(_sitemap_url(f"{base}{path_}", 'weekly', '0.4', today))

    body = ''.join(entries)
    return HttpResponse(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f'{body}</urlset>',
        content_type='application/xml; charset=utf-8',
    )