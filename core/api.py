from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Banner, FAQ, GalleryPhoto, SiteSettings
from .serializers import (BannerSerializer, FAQSerializer,
                          GalleryPhotoSerializer, SiteSettingsSerializer)


class BannerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Banner.objects.filter(is_active=True)
    serializer_class = BannerSerializer
    pagination_class = None


class GalleryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GalleryPhoto.objects.filter(is_active=True)
    serializer_class = GalleryPhotoSerializer
    pagination_class = None


class FAQViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FAQ.objects.filter(is_active=True)
    serializer_class = FAQSerializer
    pagination_class = None


class SiteSettingsViewSet(viewsets.ReadOnlyModelViewSet):
    """Sayt sozlamalari — bitta qator."""

    serializer_class = SiteSettingsSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        return SiteSettings.objects.all()[:1]