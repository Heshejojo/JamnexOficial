from unittest.mock import patch

from django.apps import apps
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from areas.models import Area, Proceso, Subproceso
from dispositivos.models import Dispositivo
from usuarios.models import Rol, Usuario


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


class ConsultaRolePermissionsTest(TestCase):
    def setUp(self):
        role = Rol.objects.get(nombre='CONSULTA')
        self.user = Usuario.objects.create_user(
            username='consulta',
            email='consulta@example.com',
            password='test-password',
            rol=role,
            permisos={
                'dashboard': False,
                'dispositivos': False,
                'sims': False,
                'usuarios': False,
                'zonas': True,
            },
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_can_read_all_modules_but_cannot_modify_them(self):
        response = self.client.get('/api/areas/')
        self.assertEqual(response.status_code, 200)

        response = self.client.get('/api/usuarios/')
        self.assertEqual(response.status_code, 200)

        response = self.client.post('/api/areas/', {'nombre': 'Nueva zona'}, format='json')
        self.assertEqual(response.status_code, 403)

    def test_admin_still_requires_zones_permission(self):
        admin_role = Rol.objects.get(nombre='ADMIN')
        admin = Usuario.objects.create_user(
            username='area-admin',
            email='area-admin@example.com',
            password='test-password',
            rol=admin_role,
            permisos={'dashboard': True, 'dispositivos': True, 'sims': True, 'usuarios': True, 'zonas': False},
        )
        self.client.force_authenticate(user=admin)

        response = self.client.get('/api/areas/')
        self.assertEqual(response.status_code, 403)

    def test_consulta_role_remains_read_only_for_superusers(self):
        admin = Usuario.objects.create_superuser(
            username='readonly-superuser',
            email='readonly-superuser@example.com',
            password='test-password',
        )
        admin.rol = self.user.rol
        admin.save(update_fields=['rol'])
        self.client.force_authenticate(user=admin)

        response = self.client.get('/api/areas/')
        self.assertEqual(response.status_code, 200)

        response = self.client.post('/api/areas/', {'nombre': 'No editable'}, format='json')
        self.assertEqual(response.status_code, 403)

    def test_admin_can_assign_consulta_role_with_zones_access(self):
        admin = Usuario.objects.create_superuser(
            username='role-admin',
            email='role-admin@example.com',
            password='test-password',
        )
        self.client.force_authenticate(user=admin)

        response = self.client.post('/api/usuarios/', {
            'username': 'readonly-user',
            'email': 'readonly@example.com',
            'password': 'test-password',
            'rol_id': self.user.rol_id,
            'permisos': {
                'dashboard': False,
                'dispositivos': False,
                'sims': False,
                'usuarios': False,
                'zonas': True,
            },
        }, format='json')

        self.assertEqual(response.status_code, 201)
        created_user = Usuario.objects.get(username='readonly-user')
        self.assertEqual(created_user.rol.nombre, 'CONSULTA')
        self.assertTrue(created_user.permisos['zonas'])

    def test_consulta_cannot_assign_device_zone(self):
        device = Dispositivo.objects.create(device_uuid='readonly-zone-device')
        response = self.client.patch(
            f'/api/zonas/dispositivos/{device.pk}/',
            {'area_id': None},
            format='json',
        )
        self.assertEqual(response.status_code, 403)


class ZoneCatalogApiTest(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(
            username='zone-admin',
            email='zone-admin@example.com',
            password='test-password',
            rol=Rol.objects.get(nombre='ADMIN'),
            permisos={
                'dashboard': True,
                'dispositivos': True,
                'sims': True,
                'usuarios': True,
                'zonas': True,
            },
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_hierarchy_and_assign_terminal_from_zones(self):
        distribution_response = self.client.post(
            '/api/procesos/',
            {'nombre': 'Distribución Norte'},
            format='json',
        )
        self.assertEqual(distribution_response.status_code, 201)
        distribution_id = distribution_response.data['id']

        division_response = self.client.post(
            '/api/subprocesos/',
            {'nombre': 'División 1', 'proceso_id': distribution_id},
            format='json',
        )
        self.assertEqual(division_response.status_code, 201)

        zone_response = self.client.post(
            '/api/areas/',
            {'nombre': 'Zona A', 'subproceso_id': division_response.data['id']},
            format='json',
        )
        self.assertEqual(zone_response.status_code, 201)

        device = Dispositivo.objects.create(device_uuid='zone-assignment-device')
        assignment_response = self.client.patch(
            f'/api/zonas/dispositivos/{device.pk}/',
            {'area_id': zone_response.data['id']},
            format='json',
        )
        self.assertEqual(assignment_response.status_code, 200)
        self.assertEqual(assignment_response.data['zona_nombre'], 'Zona A')
        self.assertEqual(assignment_response.data['division_nombre'], 'División 1')
        self.assertEqual(assignment_response.data['distribucion_nombre'], 'Distribución Norte')

        device.refresh_from_db()
        self.assertEqual(device.area_id, zone_response.data['id'])

    def test_zone_requires_existing_division_for_assignment(self):
        response = self.client.post(
            '/api/areas/',
            {'nombre': 'Zona sin división'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

        legacy_area = Area.objects.create(nombre='Zona sin relación')
        device = Dispositivo.objects.create(device_uuid='unassigned-zone-device')
        response = self.client.patch(
            f'/api/zonas/dispositivos/{device.pk}/',
            {'area_id': legacy_area.pk},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_empty_zone_can_be_deleted_but_assigned_zone_cannot(self):
        process = Proceso.objects.create(nombre='Distribución para borrar')
        division = Subproceso.objects.create(nombre='División para borrar', proceso=process)
        zone = Area.objects.create(nombre='Zona para borrar', subproceso=division)
        device = Dispositivo.objects.create(
            device_uuid='assigned-zone-delete-device',
            area=zone,
        )

        response = self.client.delete(f'/api/areas/{zone.pk}/')
        self.assertEqual(response.status_code, 400)
        self.assertTrue(Area.objects.filter(pk=zone.pk).exists())

        device.area = None
        device.save(update_fields=['area'])
        response = self.client.delete(f'/api/areas/{zone.pk}/')
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Area.objects.filter(pk=zone.pk).exists())


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
