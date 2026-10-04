from django.db.models import Avg, Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response

from .models import Allergen, Cake, Category, Option
from .serializers import (AllergenSerializer, CakeDetailSerializer,
                          CakeListSerializer, CakeWriteSerializer,
                          CategorySerializer, OptionSerializer)

SORT_FIELDS = {
    'price_asc': 'price',
    'price_desc': '-price',
    'new': '-created_at',
    'name': 'name',
}


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = CategorySerializer
    pagination_class = None
    lookup_field = 'slug'

    def get_queryset(self):
        # Modelda `cakes_count` property bor — queryset annotatsiyasi bilan
        # to'qnashmasligi uchun boshqa nom ishlatiladi.
        return Category.objects.filter(is_active=True).annotate(
            total_cakes=Q(cakes__is_active=True)
        ).distinct()


class OptionViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = OptionSerializer
    pagination_class = None

    def get_queryset(self):
        return Option.objects.filter(is_active=True)


class AllergenViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = AllergenSerializer
    pagination_class = None

    def get_queryset(self):
        return Allergen.objects.all()


class CakeViewSet(viewsets.ModelViewSet):
    """O'qish — hamma uchun, yozish — staff uchun."""

    permission_classes = [AllowAny]
    lookup_field = 'slug'
    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head',
                         'options']

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAdminUser()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return CakeWriteSerializer
        if self.action == 'retrieve':
            return CakeDetailSerializer
        return CakeListSerializer

    def get_queryset(self):
        params = self.request.query_params
        qs = Cake.objects.filter(is_active=True).select_related('category')

        if params.get('category'):
            qs = qs.filter(category__slug=params['category'])
        if params.get('price_min'):
            qs = qs.filter(price__gte=params['price_min'])
        if params.get('price_max'):
            qs = qs.filter(price__lte=params['price_max'])
        if params.get('search'):
            qs = qs.filter(
                Q(name__icontains=params['search'])
                | Q(description__icontains=params['search'])
            )
        if params.get('available'):
            qs = qs.filter(is_available=True)
        if params.get('preorder'):
            qs = qs.filter(is_preorder=True)
        if params.get('allergen'):
            qs = qs.filter(allergens__name=params['allergen'])

        sort = SORT_FIELDS.get(params.get('sort'), '-created_at')
        return qs.order_by(sort).distinct()

    @action(detail=False, methods=['get'])
    def top_rated(self, request):
        """Eng ko'p baholangan tortlar."""
        qs = (Cake.objects.filter(is_active=True, reviews__is_published=True)
              .annotate(avg=Avg('reviews__rating'))
              .order_by('-avg')[:8])
        return Response(CakeListSerializer(qs, many=True).data)