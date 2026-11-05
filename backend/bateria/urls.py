from django.urls import path

from .views import RegistroBateriaDetailAPIView, RegistroBateriaListAPIView

urlpatterns = [
    path('bateria/', RegistroBateriaListAPIView.as_view(), name='bateria-list'),
    path('bateria/<int:pk>/', RegistroBateriaDetailAPIView.as_view(), name='bateria-detail'),
]
