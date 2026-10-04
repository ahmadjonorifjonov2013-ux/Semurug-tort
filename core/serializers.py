from rest_framework import serializers

from .models import Banner, FAQ, GalleryPhoto, SiteSettings


class SiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSettings
        fields = ('site_name', 'phone', 'telegram', 'instagram', 'address',
                  'work_hours', 'delivery_price', 'free_delivery_from',
                  'about_text', 'map_url')


class BannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = ('id', 'title', 'subtitle', 'image', 'link')


class GalleryPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = GalleryPhoto
        fields = ('id', 'image', 'caption')


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ('id', 'question', 'answer')