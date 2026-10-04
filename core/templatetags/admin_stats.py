from django import template
from django.db.models import Sum
from django.utils import timezone

register = template.Library()


@register.simple_tag
def admin_stats():
    """Admin bosh sahifasidagi statistik ko'rsatkichlar."""
    from cakes.models import Cake
    from clients.models import Client
    from core.models import ContactMessage
    from orders.models import Order
    from reviews.models import Review

    today = timezone.localdate()
    return {
        'cakes': Cake.objects.filter(is_active=True).count(),
        'orders': Order.objects.count(),
        'orders_new': Order.objects.filter(status=Order.Status.NEW).count(),
        'orders_today': Order.objects.filter(created_at__date=today).count(),
        'revenue': Order.objects.filter(
            status=Order.Status.DELIVERED
        ).aggregate(total=Sum('total_price'))['total'] or 0,
        'clients': Client.objects.count(),
        'reviews_pending': Review.objects.filter(is_published=False).count(),
        'messages_new': ContactMessage.objects.filter(is_handled=False).count(),
    }
