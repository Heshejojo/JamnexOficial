from django.urls import path

from .views import ConsumoDetailAPIView, ConsumoListAPIView

urlpatterns = [
    path('consumos/', ConsumoListAPIView.as_view(), name='consumos-list'),
    path('consumos/<int:pk>/', ConsumoDetailAPIView.as_view(), name='consumos-detail'),
]
