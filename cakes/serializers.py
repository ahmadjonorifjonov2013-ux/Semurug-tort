from django.db.models import Avg
from rest_framework import serializers

from .models import Allergen, Cake, CakeImage, Category, Option


class CategorySerializer(serializers.ModelSerializer):
    cakes_count = serializers.IntegerField(source='total_cakes',
                                           read_only=True, default=0)

    class Meta:
        model = Category
        fields = ('id', 'name', 'slug', 'description', 'image', 'order',
                  'is_active', 'cakes_count')


class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ('id', 'name', 'group', 'price_delta', 'is_active')


class AllergenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Allergen
        fields = ('id', 'name')


class CakeImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CakeImage
        fields = ('id', 'image', 'order')


class CakeListSerializer(serializers.ModelSerializer):
    """Katalog ro'yxati — yengil versiya."""

    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    has_discount = serializers.BooleanField(read_only=True)
    discount_percent = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cake
        fields = ('id', 'name', 'slug', 'category_name', 'category_slug',
                  'price', 'old_price', 'has_discount', 'discount_percent',
                  'weight_gram', 'main_image', 'is_available', 'is_preorder')


class CakeDetailSerializer(serializers.ModelSerializer):
    """Tort sahifasi — to'liq ma'lumot."""

    category = CategorySerializer(read_only=True)
    images = CakeImageSerializer(many=True, read_only=True)
    options = OptionSerializer(many=True, read_only=True)
    allergens = AllergenSerializer(many=True, read_only=True)
    has_discount = serializers.BooleanField(read_only=True)
    discount_percent = serializers.IntegerField(read_only=True)
    avg_rating = serializers.SerializerMethodField()
    reviews_count = serializers.SerializerMethodField()

    class Meta:
        model = Cake
        fields = ('id', 'name', 'slug', 'description', 'category', 'price',
                  'old_price', 'has_discount', 'discount_percent',
                  'weight_gram', 'main_image', 'images', 'options',
                  'allergens', 'is_available', 'is_preorder', 'min_order_days',
                  'avg_rating', 'reviews_count', 'created_at')

    def get_avg_rating(self, obj):
        published = obj.reviews.filter(is_published=True)
        return published.aggregate(r=Avg('rating'))['r'] or 0

    def get_reviews_count(self, obj):
        return obj.reviews.filter(is_published=True).count()


class CakeWriteSerializer(serializers.ModelSerializer):
    """Admin/API orqali tort yaratish va tahrirlash."""

    class Meta:
        model = Cake
        fields = ('id', 'category', 'name', 'slug', 'description', 'price',
                  'old_price', 'weight_gram', 'main_image', 'is_available',
                  'is_active', 'is_preorder', 'min_order_days', 'options',
                  'allergens')

    def validate(self, attrs):
        old_price = attrs.get('old_price') or getattr(
            self.instance, 'old_price', None)
        price = attrs.get('price') or getattr(self.instance, 'price', None)
        if old_price and price and old_price < price:
            raise serializers.ValidationError(
                {"old_price": "Eski narx yangisidan katta bo'lishi kerak"}
            )
        return attrs