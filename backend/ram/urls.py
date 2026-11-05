from django.urls import path

from .views import RegistroRamDetailAPIView, RegistroRamListAPIView

urlpatterns = [
    path('ram/', RegistroRamListAPIView.as_view(), name='ram-list'),
    path('ram/<int:pk>/', RegistroRamDetailAPIView.as_view(), name='ram-detail'),
]
