from django.urls import path

from . import views

app_name = 'clients'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.client_login, name='login'),
    path('logout/', views.client_logout, name='logout'),
    path('parol/', views.password_change, name='password_change'),
    path('profile/', views.profile, name='profile'),
    path('profile/orders/', views.profile_orders, name='profile_orders'),
    path('<int:pk>/', views.client_detail, name='detail'),
]