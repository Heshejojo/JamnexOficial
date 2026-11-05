from django.urls import path

from .views import RegistroAlmacenamientoDetailAPIView, RegistroAlmacenamientoListAPIView

urlpatterns = [
    path('almacenamiento/', RegistroAlmacenamientoListAPIView.as_view(), name='almacenamiento-list'),
    path('almacenamiento/<int:pk>/', RegistroAlmacenamientoDetailAPIView.as_view(), name='almacenamiento-detail'),
]
