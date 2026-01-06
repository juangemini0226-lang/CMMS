from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('panel-tecnico/', views.panel_tecnico, name='panel_tecnico'),
]
