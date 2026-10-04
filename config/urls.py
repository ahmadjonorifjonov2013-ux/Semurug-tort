"""URL configuration for config project."""

import re

from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path, re_path
from django.views.static import serve
from rest_framework.routers import DefaultRouter

# --- API router ---
from core.api import (BannerViewSet, FAQViewSet, GalleryViewSet,
                     SiteSettingsViewSet)
from clients.api import ClientViewSet, LoginView, RegisterView
from cakes.api import (AllergenViewSet, CakeViewSet, CategoryViewSet,
                       OptionViewSet)
from orders.api import (CartItemView, CartView, CheckoutAPIView, OrderViewSet,
                        PromoCodeViewSet)
from reviews.api import ReviewViewSet

router = DefaultRouter()
router.register('banners', BannerViewSet, basename='banner')
router.register('gallery', GalleryViewSet, basename='gallery')
router.register('faqs', FAQViewSet, basename='faq')
router.register('settings', SiteSettingsViewSet, basename='settings')
router.register('clients', ClientViewSet, basename='client')
router.register('cakes', CakeViewSet, basename='cake')
router.register('categories', CategoryViewSet, basename='category')
router.register('cake-options', OptionViewSet, basename='cake-option')
router.register('allergens', AllergenViewSet, basename='allergen')
router.register('orders', OrderViewSet, basename='order')
router.register('promo-codes', PromoCodeViewSet, basename='promo-code')
router.register('reviews', ReviewViewSet, basename='review')

urlpatterns = [
    path('admin/', admin.site.urls),

    # API
    path('api/', include(router.urls)),
    path('api/auth/register/', RegisterView.as_view(), name='api_register'),
    path('api/auth/login/', LoginView.as_view(), name='api_login'),
    path('api/cart/', CartView.as_view(), name='api_cart'),
    path('api/cart/<int:pk>/', CartItemView.as_view(), name='api_cart_item'),
    path('api/checkout/', CheckoutAPIView.as_view(), name='api_checkout'),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),

    # Sayt
    path('', include('core.urls')),
    path('clients/', include('clients.urls')),
    path('cakes/', include('cakes.urls')),
    path('orders/', include('orders.urls')),
    path('reviews/', include('reviews.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# nginx'siz hostingda (tunnel, PythonAnywhere) media fayllarini
# Django beradi. Faqat MEDIA_VIA_DJANGO=True bo'lganda yoqiladi.
elif settings.MEDIA_VIA_DJANGO:
    urlpatterns += [
        re_path(
            r'^media/(?P<path>.*)$',
            serve,
            {'document_root': settings.MEDIA_ROOT},
        ),
    ]