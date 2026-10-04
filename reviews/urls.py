from django.urls import path

from . import views

app_name = 'reviews'

urlpatterns = [
    path('', views.review_list, name='list'),
    path('tort/<slug:slug>/', views.review_list, name='cake_list'),
    path('add/<slug:slug>/', views.add_review, name='add'),
    path('<int:pk>/delete/', views.delete_own_review, name='delete'),
]