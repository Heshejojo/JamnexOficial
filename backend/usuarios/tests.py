from unittest.mock import patch

from django.apps import apps
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from areas.models import Area
from dispositivos.models import Dispositivo
from usuarios.models import Usuario


class DemoUserPostMigrateTest(TestCase):
    def test_existing_admin_username_does_not_break_migrate(self):
        admin = Usuario.objects.create_superuser(
            username='admin',
            email='existing-admin@example.com',
            password='test-password',
        )

        with patch('usuarios.apps.sys.argv', ['manage.py', 'migrate']):
            from usuarios.apps import create_demo_user

            create_demo_user(sender=apps.get_app_config('usuarios'))

        self.assertTrue(Usuario.objects.filter(pk=admin.pk).exists())
        self.assertEqual(Usuario.objects.filter(username='admin').count(), 1)


class UsuariosAuthSmokeTest(TestCase):
    def test_smoke(self):
        self.assertTrue(True)

    def test_login_accepts_email_credentials(self):
        user = Usuario.objects.create_user(
            username='admin',
            email='admin@agente.cfe',
            password='Admin123!',
            is_staff=True,
            is_superuser=True,
        )

        login_data = {'email': user.email, 'password': 'Admin123!'}
        serializer = __import__('usuarios.serializers', fromlist=['LoginSerializer']).LoginSerializer(data=login_data)

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['user']['email'], user.email)


class TrabajadorCrudApiTest(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(
            username='tester',
            email='tester@agente.cfe',
            password='Admin123!',
            is_staff=True,
            is_superuser=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.area = Area.objects.create(nombre='Operación', descripcion='Area de prueba')

    def test_trabajador_create_list_and_delete(self):
        payload = {
            'numero_empleado': 'EMP-1001',
            'nombre': 'Juan',
            'apellido_paterno': 'Pérez',
            'apellido_materno': 'López',
            'area_id': self.area.id,
            'activo': True,
        }

        response = self.client.post('/api/trabajadores/', payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['nombre'], 'Juan')

        list_response = self.client.get('/api/trabajadores/')
        self.assertEqual(list_response.status_code, 200)
        self.assertGreaterEqual(len(list_response.data), 1)

        delete_response = self.client.delete(f"/api/trabajadores/{response.data['id']}/")
        self.assertEqual(delete_response.status_code, 204)


class DeviceSecurityApiTest(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_superuser(
            username='device-admin', email='device-admin@agente.cfe', password='Admin123!'
        )
        self.client = APIClient()

    def test_device_register_status_and_revoke(self):
        registration = self.client.post('/api/device/register/', {'device_uuid': 'test-device'}, format='json')
        self.assertEqual(registration.status_code, 201)
        device = Dispositivo.objects.get(pk=registration.data['device_id'])
        device_headers = {'HTTP_AUTHORIZATION': f"Device {registration.data['token']}"}

        status_response = self.client.post(
            '/api/device/status/',
            {'device_uuid': device.device_uuid, 'battery_percent': 70, 'connected': True},
            format='json', **device_headers
        )
        self.assertEqual(status_response.status_code, 200)

        self.client.force_authenticate(user=self.user)
        revoke_response = self.client.post(f'/api/dispositivos/{device.pk}/revoke/')
        self.assertEqual(revoke_response.status_code, 200)

        self.client.force_authenticate(user=None)
        rejected = self.client.post('/api/device/status/', {'device_uuid': device.device_uuid}, format='json', **device_headers)
        self.assertEqual(rejected.status_code, 403)

    def test_logout(self):
        self.client.force_authenticate(user=self.user)
        refresh = RefreshToken.for_user(self.user)
        access = str(refresh.access_token)
        logout = self.client.post(
            '/api/auth/logout/', {'refresh': str(refresh)}, format='json',
            HTTP_AUTHORIZATION=f'Bearer {access}',
        )
        self.assertEqual(logout.status_code, 205)
