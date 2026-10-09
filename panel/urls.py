from django.urls import path

from . import views

app_name = 'panel'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('kirish/', views.panel_login, name='login'),
    path('chiqish/', views.panel_logout, name='logout'),

    # Buyurtmalar
    path('buyurtmalar/', views.order_list, name='orders'),
    path('buyurtmalar/<int:pk>/', views.order_detail, name='order_detail'),
    path('buyurtmalar/<int:pk>/amal/', views.order_action, name='order_action'),

    # Tortlar
    path('tortlar/', views.cake_list, name='cakes'),
    path('tortlar/yangi/', views.cake_create, name='cake_create'),
    path('tortlar/<int:pk>/', views.cake_edit, name='cake_edit'),
    path('tortlar/<int:pk>/holat/', views.cake_flag, name='cake_flag'),
    path('tortlar/<int:pk>/ochirish/', views.cake_delete, name='cake_delete'),
    path('rasm/<int:pk>/ochirish/', views.gallery_image_delete,
         name='gallery_image_delete'),

    # Katalog
    path('katalog/', views.catalog, name='catalog'),
    path('katalog/kategoriya/', views.category_save, name='category_save'),
    path('katalog/kategoriya/<int:pk>/', views.category_save,
         name='category_edit'),
    path('katalog/kategoriya/<int:pk>/ochirish/', views.category_delete,
         name='category_delete'),
    path('katalog/variant/', views.option_save, name='option_save'),
    path('katalog/variant/<int:pk>/', views.option_save, name='option_edit'),
    path('katalog/variant/<int:pk>/ochirish/', views.option_delete,
         name='option_delete'),
    path('katalog/allergen/', views.allergen_save, name='allergen_save'),
    path('katalog/allergen/<int:pk>/ochirish/', views.allergen_delete,
         name='allergen_delete'),
    path('katalog/promo/', views.promo_save, name='promo_save'),
    path('katalog/promo/<int:pk>/', views.promo_save, name='promo_edit'),
    path('katalog/promo/<int:pk>/ochirish/', views.promo_delete,
         name='promo_delete'),

    # Sayt kontenti
    path('kontent/', views.content, name='content'),
    path('kontent/banner/', views.banner_save, name='banner_save'),
    path('kontent/banner/<int:pk>/ochirish/', views.banner_delete,
         name='banner_delete'),
    path('kontent/rasm/', views.photo_save, name='photo_save'),
    path('kontent/rasm/<int:pk>/ochirish/', views.photo_delete,
         name='photo_delete'),
    path('kontent/faq/', views.faq_save, name='faq_save'),
    path('kontent/faq/<int:pk>/ochirish/', views.faq_delete,
         name='faq_delete'),
    path('kontent/<str:model>/<int:pk>/holat/', views.content_flag,
         name='content_flag'),

    # Mijozlar
    path('mijozlar/', views.client_list, name='clients'),
    path('mijozlar/<int:pk>/', views.client_detail, name='client_detail'),
    path('mijozlar/<int:pk>/vip/', views.client_vip, name='client_vip'),

    # Xabarlar va sharhlar
    path('xabarlar/', views.message_list, name='messages'),
    path('xabarlar/<int:pk>/', views.message_handle, name='message_handle'),
    path('xabarlar/<int:pk>/ochirish/', views.message_delete,
         name='message_delete'),
    path('sharhlar/', views.review_list, name='reviews'),
    path('sharhlar/<int:pk>/', views.review_publish, name='review_publish'),
    path('sharhlar/<int:pk>/ochirish/', views.review_delete,
         name='review_delete'),

    # Sozlamalar
    path('sozlamalar/', views.settings_edit, name='settings'),
]