from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import cart
from .models import Order, OrderItem, PromoCode
from .serializers import (CartAddSerializer, CartSerializer,
                          CheckoutSerializer, OrderDetailSerializer,
                          OrderListSerializer, PromoCodeSerializer)
from .services import send_order_to_telegram


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    """Mijoz o'z buyurtmalarini ko'radi, admin — hammasini."""

    serializer_class = OrderListSerializer

    def get_permissions(self):
        if self.action in ('update', 'partial_update', 'destroy'):
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        return OrderDetailSerializer if self.action == 'retrieve' \
            else OrderListSerializer

    def get_queryset(self):
        qs = Order.objects.select_related('client').prefetch_related(
            'items__cake'
        )
        if self.request.user.is_staff:
            return qs
        return qs.filter(client__user=self.request.user)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()
        if order.status not in (Order.Status.NEW, Order.Status.CONFIRMED):
            return Response({'detail': "Bekor qilib bo'lmaydi"},
                            status=status.HTTP_400_BAD_REQUEST)
        order.status = Order.Status.CANCELLED
        order.save(update_fields=['status'])
        return Response(OrderDetailSerializer(order).data)


class CartView(APIView):
    """Savat: GET holati, POST qo'shish."""

    throttle_scope = 'cart'

    def get(self, request):
        rows, total = cart.rows(request)
        return Response(CartSerializer({
            'rows': rows,
            'count': cart.count(request),
            'total': total,
        }).data)

    def post(self, request):
        serializer = CartAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cake = serializer.validated_data['cake']
        if not cake.is_available:
            return Response({'cake': "Bu tort mavjud emas"},
                            status=status.HTTP_400_BAD_REQUEST)

        cart.add(request, cake.pk,
                 serializer.validated_data.get('quantity', 1),
                 options=serializer.validated_data.get('options'))

        rows, total = cart.rows(request)
        return Response(CartSerializer({
            'rows': rows, 'count': cart.count(request), 'total': total,
        }).data, status=status.HTTP_201_CREATED)


class CartItemView(APIView):
    def patch(self, request, pk):
        quantity = request.data.get('quantity', 1)
        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            quantity = 1
        cart.update(request, pk, quantity,
                    options=request.data.get('options'),
                    comment=request.data.get('comment'))
        rows, total = cart.rows(request)
        return Response(CartSerializer({
            'rows': rows, 'count': cart.count(request), 'total': total,
        }).data)

    def delete(self, request, pk):
        cart.remove(request, pk)
        rows, total = cart.rows(request)
        return Response(CartSerializer({
            'rows': rows, 'count': cart.count(request), 'total': total,
        }).data)


class CheckoutAPIView(APIView):
    """Savatdagi tortlarni buyurtmaga aylantiradi."""

    throttle_scope = 'checkout'

    def post(self, request):
        rows, total = cart.rows(request)
        if not rows:
            return Response({'detail': "Savat bo'sh"},
                            status=status.HTTP_400_BAD_REQUEST)

        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            from clients.models import Client
            client = Client.objects.filter(phone=data['phone']).first()
            if client:
                client.full_name = data['name']
                client.save(update_fields=['full_name'])
            else:
                client = Client.objects.create(
                    phone=data['phone'],
                    full_name=data['name'],
                    telegram=data.get('telegram', ''),
                    address=data['delivery_address'],
                )

            order = Order.objects.create(
                client=client,
                delivery_address=data['delivery_address'],
                delivery_date=data['delivery_date'],
                delivery_time=data.get('delivery_time'),
                payment_method=data['payment_method'],
                comment=data.get('comment', ''),
            )

            for row in rows:
                item = OrderItem.objects.create(
                    order=order, cake=row['cake'],
                    quantity=row['quantity'], price=row['unit_price'],
                    comment=row['comment'],
                )
                if row['options']:
                    item.options.set(row['options'])

            code = (data.get('promo_code') or '').strip().upper()
            if code:
                promo = PromoCode.objects.filter(code=code,
                                                is_active=True).first()
                if promo and promo.is_valid(total):
                    order.promo_code = promo
                    PromoCode.objects.filter(pk=promo.pk).update(
                        used_count=promo.used_count + 1
                    )

            order.recalc_total()
            cart.clear(request)

        send_order_to_telegram(order)
        return Response(OrderDetailSerializer(order).data,
                        status=status.HTTP_201_CREATED)


class PromoCodeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PromoCodeSerializer
    permission_classes = [IsAdminUser]
    queryset = PromoCode.objects.all()
    pagination_class = None