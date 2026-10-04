from django.urls import path

from . import views

app_name = 'orders'

urlpatterns = [
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:pk>/', views.cart_add, name='cart_add'),
    path('cart/update/<int:pk>/', views.cart_update, name='cart_update'),
    path('cart/remove/<int:pk>/', views.cart_remove, name='cart_remove'),
    path('cart/clear/', views.cart_clear, name='cart_clear'),
    path('checkout/', views.checkout, name='checkout'),
    path('success/', views.success_public, name='success_public'),
    path('success/<int:pk>/', views.success, name='success'),
    path('my/', views.my_orders, name='my'),
    path('<int:pk>/', views.order_detail, name='detail'),
    path('<int:pk>/cancel/', views.cancel_order, name='cancel'),
]