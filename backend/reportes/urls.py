from django.urls import path

from .views import DashboardSummaryView, DevicesMonthlyExportView, SimMonthlyExportView

urlpatterns = [
    path('dashboard/summary/', DashboardSummaryView.as_view(), name='dashboard-summary'),
    path('reportes/sims/<int:pk>/exportar/', SimMonthlyExportView.as_view(), name='sim-monthly-export'),
    path('reportes/dispositivos/exportar/', DevicesMonthlyExportView.as_view(), name='devices-monthly-export'),
]
