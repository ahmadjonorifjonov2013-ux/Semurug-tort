from rest_framework import serializers

from clients.serializers import ClientSerializer
from cakes.models import Cake
from cakes.serializers import CakeListSerializer, OptionSerializer

from .models import Order, OrderItem, PromoCode


class OrderItemSerializer(serializers.ModelSerializer):
    cake_name = serializers.CharField(source='cake.name', read_only=True)
    cake_image = serializers.ImageField(source='cake.main_image',
                                        read_only=True)
    options = OptionSerializer(many=True, read_only=True)
    options_names = serializers.CharField(read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2,
                                        read_only=True)

    class Meta:
        model = OrderItem
        fields = ('id', 'cake', 'cake_name', 'cake_image', 'quantity', 'price',
                  'options', 'options_names', 'comment', 'subtotal')


class PromoCodeSerializer(serializers.ModelSerializer):
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = PromoCode
        fields = ('id', 'code', 'discount_percent', 'min_order_sum',
                  'valid_from', 'valid_until', 'is_active', 'used_count',
                  'is_expired')
        read_only_fields = ('id', 'used_count')


class OrderListSerializer(serializers.ModelSerializer):
    order_number = serializers.IntegerField(source='id', read_only=True)
    client_name = serializers.CharField(source='client.full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display',
                                            read_only=True)
    payment_method_display = serializers.CharField(
        source='get_payment_method_display', read_only=True)
    items_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Order
        fields = ('id', 'order_number', 'client_name', 'status',
                  'status_display', 'payment_method', 'payment_method_display',
                  'is_paid', 'delivery_date', 'delivery_time', 'total_price',
                  'items_count', 'created_at')
        read_only_fields = ('id', 'client', 'subtotal', 'delivery_price',
                            'discount', 'total_price', 'created_at',
                            'updated_at')


class OrderDetailSerializer(OrderListSerializer):
    client = ClientSerializer(read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    promo_code = PromoCodeSerializer(read_only=True)

    class Meta(OrderListSerializer.Meta):
        fields = OrderListSerializer.Meta.fields + (
            'client', 'items', 'delivery_address', 'comment', 'promo_code',
            'subtotal', 'delivery_price', 'discount',
        )


class CheckoutSerializer(serializers.Serializer):
    """Savatni buyurtmaga aylantirish (API checkout)."""

    phone = serializers.CharField(max_length=20)
    name = serializers.CharField(max_length=120)
    telegram = serializers.CharField(max_length=60, required=False,
                                     allow_blank=True)
    delivery_address = serializers.CharField()
    delivery_date = serializers.DateField()
    delivery_time = serializers.TimeField(required=False, allow_null=True)
    payment_method = serializers.ChoiceField(
        choices=Order.PaymentMethod.choices, default=Order.PaymentMethod.CASH
    )
    comment = serializers.CharField(required=False, allow_blank=True)
    promo_code = serializers.CharField(max_length=20, required=False,
                                       allow_blank=True)

    def validate_phone(self, value):
        from clients.forms import clean_phone_value

        return clean_phone_value(value)

    def validate_delivery_date(self, value):
        from django.utils import timezone

        if value < timezone.localdate():
            raise serializers.ValidationError(
                "Sana bugundan oldin bo'lmasligi kerak"
            )
        return value


class CartAddSerializer(serializers.Serializer):
    cake = serializers.PrimaryKeyRelatedField(
        queryset=Cake.objects.filter(is_active=True)
    )
    quantity = serializers.IntegerField(min_value=1, max_value=99, default=1)
    options = serializers.ListField(
        child=serializers.IntegerField(), required=False, default=list
    )
    comment = serializers.CharField(required=False, allow_blank=True,
                                     default='')


class CartItemSerializer(serializers.Serializer):
    cake = CakeListSerializer(read_only=True)
    quantity = serializers.IntegerField(read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2,
                                        read_only=True)


class CartSerializer(serializers.Serializer):
    """Savat holati (GET /api/cart/)."""

    rows = CartItemSerializer(many=True, read_only=True)
    count = serializers.IntegerField(read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2,
                                     read_only=True)


class CouponCheckSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=20)

    def validate(self, attrs):
        code = attrs['code'].strip().upper()
        promo = PromoCode.objects.filter(code=code, is_active=True).first()
        if not promo:
            raise serializers.ValidationError({"code": "Promo kod topilmadi"})
        attrs['promo'] = promo
        return attrs


__all__ = [
    'OrderItemSerializer', 'PromoCodeSerializer', 'OrderListSerializer',
    'OrderDetailSerializer', 'CheckoutSerializer', 'CartAddSerializer',
    'CartItemSerializer', 'CartSerializer', 'CouponCheckSerializer',
]