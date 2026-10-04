from django.urls import path

from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('faq/', views.faq, name='faq'),
    path('robots.txt', views.robots_txt, name='robots'),
    path('sitemap.xml', views.sitemap_xml, name='sitemap'),
]