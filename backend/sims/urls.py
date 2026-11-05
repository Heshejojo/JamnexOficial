from django.urls import path

from .views import (
    AsignacionSimDetailAPIView,
    AsignacionSimListCreateAPIView,
    SimDetailAPIView,
    SimHistorialAPIView,
    SimListCreateAPIView,
    SimMovimientosAPIView,
    SimStatusAPIView,
    SimTransferConflictActionAPIView,
    SimTransferConflictListAPIView,
)

urlpatterns = [
    path('sims/conflicts/', SimTransferConflictListAPIView.as_view(), name='sims-conflicts-list'),
    path('sims/conflicts/<int:pk>/<str:action>/', SimTransferConflictActionAPIView.as_view(), name='sims-conflicts-action'),
    path('sims/movimientos/', SimMovimientosAPIView.as_view(), name='sims-movimientos'),
    path('sims/<int:pk>/historial/', SimHistorialAPIView.as_view(), name='sims-historial'),
    path('sims/<int:pk>/status/', SimStatusAPIView.as_view(), name='sims-status'),
    path('asignaciones-sim/', AsignacionSimListCreateAPIView.as_view(), name='asignaciones-sim-list'),
    path('asignaciones-sim/<int:pk>/', AsignacionSimDetailAPIView.as_view(), name='asignaciones-sim-detail'),
    path('sims/', SimListCreateAPIView.as_view(), name='sims-list'),
    path('sims/<int:pk>/', SimDetailAPIView.as_view(), name='sims-detail'),
]
