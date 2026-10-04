from rest_framework import serializers

from .models import Review


class ReviewSerializer(serializers.ModelSerializer):
    cake_name = serializers.CharField(source='cake.name', read_only=True)
    cake_slug = serializers.CharField(source='cake.slug', read_only=True)
    rating_display = serializers.CharField(source='get_rating_display',
                                            read_only=True)

    class Meta:
        model = Review
        fields = ('id', 'cake', 'cake_name', 'cake_slug', 'author_name',
                  'rating', 'rating_display', 'text', 'is_published',
                  'created_at')
        read_only_fields = ('id', 'author_name', 'is_published', 'created_at')


class ReviewCreateSerializer(serializers.ModelSerializer):
    """Har qanday foydalanuvchi yozishi mumkin (moderatsiyali)."""

    author_name = serializers.CharField(max_length=120, required=False,
                                       allow_blank=True)

    class Meta:
        model = Review
        fields = ('id', 'cake', 'author_name', 'rating', 'text')

    def validate_text(self, value):
        value = (value or '').strip()
        if len(value) < 10:
            raise serializers.ValidationError("Kamida 10 ta belgi yozing")
        return value

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Baho 1 dan 5 gacha bo'lsin")
        return value

    def create(self, validated_data):
        request = self.context.get('request')
        user = getattr(request, 'user', None)

        if user is not None and user.is_authenticated:
            validated_data['client'] = getattr(user, 'client', None)
            if validated_data.get('client'):
                validated_data['author_name'] = \
                    validated_data['client'].full_name
        validated_data.setdefault('author_name', 'Mehmon')
        validated_data['is_published'] = False      # admin tasdiqlaydi
        return super().create(validated_data)