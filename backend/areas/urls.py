from django.urls import path

from .views import (
    AreaDetailAPIView,
    AreaListAPIView,
    ProcesoDetailAPIView,
    ProcesoListCreateAPIView,
    SubprocesoDetailAPIView,
    SubprocesoListCreateAPIView,
    ZonaDispositivoDetailAPIView,
    ZonaDispositivoListAPIView,
)

urlpatterns = [
    path('procesos/', ProcesoListCreateAPIView.as_view(), name='procesos-list'),
    path('procesos/<int:pk>/', ProcesoDetailAPIView.as_view(), name='procesos-detail'),
    path('subprocesos/', SubprocesoListCreateAPIView.as_view(), name='subprocesos-list'),
    path('subprocesos/<int:pk>/', SubprocesoDetailAPIView.as_view(), name='subprocesos-detail'),
    path('areas/', AreaListAPIView.as_view(), name='areas-list'),
    path('areas/<int:pk>/', AreaDetailAPIView.as_view(), name='areas-detail'),
    path('zonas/dispositivos/', ZonaDispositivoListAPIView.as_view(), name='zonas-dispositivos-list'),
    path('zonas/dispositivos/<int:pk>/', ZonaDispositivoDetailAPIView.as_view(), name='zonas-dispositivos-detail'),
]
