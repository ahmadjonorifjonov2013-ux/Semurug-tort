from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from orders.services import send_review_to_telegram

from .models import Review
from .serializers import ReviewCreateSerializer, ReviewSerializer


class ReviewViewSet(viewsets.ModelViewSet):
    """Faqat o'qiladigan (tasdiqlangan) + har kim yoza oladigan (moderatsiya)."""

    permission_classes = [AllowAny]
    throttle_scope = 'review'
    http_method_names = ['get', 'post', 'head', 'options']

    def get_serializer_class(self):
        return ReviewCreateSerializer if self.action == 'create' \
            else ReviewSerializer

    def get_queryset(self):
        qs = Review.objects.filter(is_published=True).select_related('cake')
        cake = self.request.query_params.get('cake')
        if cake:
            qs = qs.filter(cake__slug=cake)
        return qs

    def perform_create(self, serializer):
        # is_published har doim False — admin tasdiqlaydi
        review = serializer.save(is_published=False)
        send_review_to_telegram(review)