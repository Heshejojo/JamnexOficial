from django.urls import path

from .views import RegistroRedDetailAPIView, RegistroRedListAPIView

urlpatterns = [
    path('redes/', RegistroRedListAPIView.as_view(), name='redes-list'),
    path('redes/<int:pk>/', RegistroRedDetailAPIView.as_view(), name='redes-detail'),
]
