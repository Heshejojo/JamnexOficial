from django.urls import path

from .views import (
    DeviceConsumptionView,
    DeviceNetworkView,
    DeviceRegisterView,
    DeviceRevokeView,
    DeviceStatusView,
    DeviceSimView,
    DeviceSimStatusView,
    DispositivoDetailAPIView,
    DispositivoListCreateAPIView,
)

urlpatterns = [
    path('device/register/', DeviceRegisterView.as_view(), name='device-register'),
    path('device/status/', DeviceStatusView.as_view(), name='device-status'),
    path('device/consumption/', DeviceConsumptionView.as_view(), name='device-consumption'),
    path('device/network/', DeviceNetworkView.as_view(), name='device-network'),
    path('device/sim/', DeviceSimView.as_view(), name='device-sim'),
    path('device/sims/status/', DeviceSimStatusView.as_view(), name='device-sims-status'),
    path('dispositivos/<int:pk>/revoke/', DeviceRevokeView.as_view(), name='device-revoke'),
    path('dispositivos/', DispositivoListCreateAPIView.as_view(), name='dispositivos-list'),
    path('dispositivos/<int:pk>/', DispositivoDetailAPIView.as_view(), name='dispositivos-detail'),
]
