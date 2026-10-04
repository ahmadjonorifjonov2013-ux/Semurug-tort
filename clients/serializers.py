from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Client


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')
        read_only_fields = ('id',)


class ClientSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    orders_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Client
        fields = ('id', 'user', 'full_name', 'phone', 'telegram', 'email',
                  'birthday', 'address', 'notes', 'is_vip', 'orders_count',
                  'created_at')
        read_only_fields = ('id', 'is_vip', 'created_at', 'orders_count')


class ClientCreateSerializer(serializers.ModelSerializer):
    """Ro'yxatdan o'tish: User va Client bitta zaholda yaratiladi."""

    password = serializers.CharField(write_only=True, min_length=8)
    username = serializers.CharField(max_length=150)

    class Meta:
        model = Client
        fields = ('id', 'username', 'password', 'full_name', 'phone',
                  'telegram', 'email')

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Bu login band")
        return value

    def validate_phone(self, value):
        from .forms import clean_phone_value

        return clean_phone_value(value)

    def create(self, validated_data):
        username = validated_data.pop('username')
        password = validated_data.pop('password')

        user = User.objects.create_user(
            username=username,
            email=validated_data.get('email', ''),
            password=password,
            first_name=validated_data['full_name'].partition(' ')[0],
            last_name=validated_data['full_name'].partition(' ')[2],
        )
        return Client.objects.create(user=user, **validated_data)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)