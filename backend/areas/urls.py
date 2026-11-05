from django.urls import path

from .views import AreaDetailAPIView, AreaListAPIView

urlpatterns = [
    path('areas/', AreaListAPIView.as_view(), name='areas-list'),
    path('areas/<int:pk>/', AreaDetailAPIView.as_view(), name='areas-detail'),
]
