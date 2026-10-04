from django.urls import path

from . import views

app_name = 'cakes'

urlpatterns = [
    path('', views.cake_list, name='list'),
    path('kategoriya/<slug:category_slug>/', views.cake_list,
         name='category'),
    path('<slug:slug>/', views.cake_detail, name='detail'),
]