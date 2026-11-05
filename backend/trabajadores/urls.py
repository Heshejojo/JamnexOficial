from django.urls import path

from .views import TrabajadorDetailAPIView, TrabajadorListCreateAPIView

urlpatterns = [
    path('trabajadores/', TrabajadorListCreateAPIView.as_view(), name='trabajadores-list'),
    path('trabajadores/<int:pk>/', TrabajadorDetailAPIView.as_view(), name='trabajadores-detail'),
]
