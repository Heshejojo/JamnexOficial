from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from consumos.models import Consumo
from dispositivos.models import Dispositivo
from sims.models import Sim
from usuarios.models import Rol, Usuario


class DashboardSummaryPermissionTest(TestCase):
    def setUp(self):
        role = Rol.objects.create(nombre='VIEWER', activo=True)
        user = Usuario.objects.create_user(
            username='dashboard-only',
            email='dashboard@example.com',
            password='Test-password-123',
            rol=role,
            permisos={
                'dashboard': True,
                'dispositivos': False,
                'sims': False,
                'usuarios': False,
            },
        )
        self.client = APIClient()
        self.client.force_authenticate(user=user)
        device = Dispositivo.objects.create(modelo='Test device')
        sim = Sim.objects.create(dispositivo=device, numero_telefonico='5550000000')
        Consumo.objects.create(
            dispositivo=device,
            sim=sim,
            fecha=timezone.now(),
            periodo='diario',
            consumo_datos_movil=120,
        )

    def test_dashboard_permission_gets_summary_without_device_inventory(self):
        today = timezone.localdate()
        response = self.client.get(
            '/api/dashboard/summary/',
            {'anio': today.year, 'mes': today.month},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['metrics']['devices'], 1)
        self.assertEqual(response.data['metrics']['sims'], 1)
        self.assertEqual(response.data['consumption'][0]['consumo_datos_movil'], 120)
        self.assertNotIn('consumo_wifi', response.data['consumption'][0])
        self.assertNotIn('serial', response.data['devices'][0])
        self.assertEqual(self.client.get('/api/dispositivos/').status_code, 403)