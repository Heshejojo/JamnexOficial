from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from consumos.models import Consumo
from dispositivos.models import Dispositivo
from dispositivos.serializers import DispositivoSerializer
from redes.models import RegistroRed
from redes.serializers import RegistroRedSerializer
from sims.models import Sim, SimTransferConflict, normalize_iccid


class DeviceActivityTimeoutTest(TestCase):
    def test_device_becomes_inactive_after_seventy_two_hours_without_contact(self):
        device = Dispositivo.objects.create(
            device_uuid='activity-timeout-test',
            ultimo_contacto=timezone.now() - timedelta(hours=71, minutes=59),
        )
        self.assertTrue(device.esta_activo)

        device.ultimo_contacto = timezone.now() - timedelta(hours=72, minutes=1)
        device.save(update_fields=['ultimo_contacto'])

        self.assertFalse(device.esta_activo)
        serialized = DispositivoSerializer(device).data
        self.assertTrue(serialized['activo'])
        self.assertFalse(serialized['en_linea'])

    def test_device_without_contact_is_inactive(self):
        device = Dispositivo.objects.create(device_uuid='never-contacted-test')
        self.assertFalse(device.esta_activo)

    def test_status_uses_server_time_for_last_contact(self):
        client = APIClient()
        registration = client.post(
            '/api/device/register/',
            {'device_uuid': 'status-contact-time-test'},
            format='json',
        )
        self.assertEqual(registration.status_code, 201)
        device = Dispositivo.objects.get(pk=registration.data['device_id'])
        headers = {
            'HTTP_AUTHORIZATION': f"Device {registration.data['token']}",
        }
        stale_timestamp = (timezone.now() - timedelta(days=5)).isoformat()
        before_request = timezone.now()

        response = client.post(
            '/api/device/status/',
            {
                'device_uuid': device.device_uuid,
                'timestamp': stale_timestamp,
            },
            format='json',
            **headers,
        )

        self.assertEqual(response.status_code, 200)
        device.refresh_from_db()
        self.assertGreaterEqual(device.ultimo_contacto, before_request)
        self.assertTrue(device.esta_activo)


class DeviceRegisterManualFieldsTest(TestCase):
    def test_device_registration_does_not_overwrite_edited_serial_or_imei(self):
        client = APIClient()
        response = client.post(
            '/api/device/register/',
            {
                'device_uuid': 'manual-device-fields-test',
                'serial': 'SERIAL-MANUAL',
                'imei_1': 'IMEI-MANUAL',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        device = Dispositivo.objects.get(device_uuid='manual-device-fields-test')

        response = client.post(
            '/api/device/register/',
            {
                'device_uuid': device.device_uuid,
                'serial': 'SERIAL-REPORTED',
                'imei_1': 'IMEI-REPORTED',
                'modelo': 'Updated model',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        device.refresh_from_db()
        self.assertEqual(device.serial, 'SERIAL-MANUAL')
        self.assertEqual(device.imei_1, 'IMEI-MANUAL')
        self.assertEqual(device.modelo, 'Updated model')

    def test_register_fills_empty_serial_and_ignores_extra_fields(self):
        client = APIClient()
        client.post(
            '/api/device/register/',
            {'device_uuid': 'fill-serial-test'},
            format='json',
        )

        response = client.post(
            '/api/device/register/',
            {
                'device_uuid': 'fill-serial-test',
                'serial': 'SERIAL-APP',
                'ram_usada': 100,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            Dispositivo.objects.get(device_uuid='fill-serial-test').serial,
            'SERIAL-APP',
        )


class DeviceConsumptionMobileOnlyTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        registration = self.client.post(
            '/api/device/register/',
            {'device_uuid': 'mobile-consumption-test'},
            format='json',
        )
        self.assertEqual(registration.status_code, 201)
        self.device = Dispositivo.objects.get(pk=registration.data['device_id'])
        self.sim = Sim.objects.create(
            dispositivo=self.device,
            sim_uuid='mobile-consumption-sim-1',
            iccid='8952020320430379646',
            slot=0,
        )
        self.second_sim = Sim.objects.create(
            dispositivo=self.device,
            sim_uuid='mobile-consumption-sim-2',
            iccid='8952020320430379653',
            slot=1,
        )
        self.device_headers = {
            'HTTP_AUTHORIZATION': f"Device {registration.data['token']}",
        }

    def test_wifi_and_submitted_total_do_not_change_mobile_consumption(self):
        response = self.client.post(
            '/api/device/consumption/',
            {
                'consumo_datos_movil': 12.5,
                'consumo_wifi': 900,
                'consumo_total': 1000,
                'periodo': 'diario',
                'sim_slot': 0,
            },
            format='json',
            **self.device_headers,
        )

        self.assertEqual(response.status_code, 201)
        consumption = Consumo.objects.get(dispositivo=self.device, sim=self.sim)
        self.assertEqual(consumption.consumo_datos_movil, 12.5)
        self.assertEqual(consumption.consumo_wifi, 0)
        self.assertEqual(consumption.consumo_total, 12.5)
        self.assertEqual(response.data['consumo_total'], 12.5)

        self.client.post(
            '/api/device/consumption/',
            {
                'consumo_datos_movil': 20,
                'consumo_wifi': 700,
                'consumo_total': 900,
                'periodo': 'diario',
                'sim_slot': 0,
            },
            format='json',
            **self.device_headers,
        )
        consumption.refresh_from_db()
        self.assertEqual(consumption.consumo_datos_movil, 20)
        self.assertEqual(consumption.consumo_wifi, 0)
        self.assertEqual(consumption.consumo_total, 20)

    def test_daily_counter_is_accumulated_separately_for_each_sim(self):
        def report(value, slot):
            return self.client.post(
                '/api/device/consumption/',
                {
                    'consumo_datos_movil': value,
                    'periodo': 'diario',
                    'sim_slot': slot,
                },
                format='json',
                **self.device_headers,
            )

        report(10, 0)
        report(16, 1)
        report(0, 1)
        report(3, 1)

        first_sim_consumption = Consumo.objects.get(
            dispositivo=self.device,
            sim=self.sim,
            periodo='diario',
        )
        second_sim_consumption = Consumo.objects.get(
            dispositivo=self.device,
            sim=self.second_sim,
            periodo='diario',
        )
        self.assertEqual(first_sim_consumption.consumo_datos_movil, 10)
        self.assertEqual(second_sim_consumption.consumo_datos_movil, 3)

    def test_missing_sim_slot_does_not_assign_usage_to_another_sim(self):
        response = self.client.post(
            '/api/device/consumption/',
            {
                'consumo_datos_movil': 12,
                'periodo': 'diario',
                'sim_slot': -1,
            },
            format='json',
            **self.device_headers,
        )

        self.assertEqual(response.status_code, 201)
        self.assertFalse(
            Consumo.objects.filter(
                dispositivo=self.device,
                periodo='diario',
            ).exists()
        )

    def test_monthly_usage_updates_month_to_date_record(self):
        def report(value):
            return self.client.post(
                '/api/device/consumption/',
                {
                    'consumo_datos_movil': value,
                    'periodo': 'mensual',
                    'sim_slot': 0,
                },
                format='json',
                **self.device_headers,
            )

        first_response = report(17.86)
        second_response = report(34.0)

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 201)
        monthly_records = Consumo.objects.filter(
            dispositivo=self.device,
            sim=self.sim,
            periodo='mensual',
            fecha__year=timezone.now().year,
            fecha__month=timezone.now().month,
        )
        self.assertEqual(monthly_records.count(), 1)
        self.assertEqual(monthly_records.get().consumo_datos_movil, 34.0)

    def test_wifi_network_record_stores_only_connection_status(self):
        response = self.client.post(
            '/api/device/network/',
            {
                'tipo_conexion': 'WIFI',
                'ssid': 'private-network-name',
                'rssi': -30,
                'frecuencia': 5200,
                'velocidad': 800,
            },
            format='json',
            **self.device_headers,
        )

        self.assertEqual(response.status_code, 201)
        network = RegistroRed.objects.get(dispositivo=self.device)
        self.assertEqual(network.tipo_conexion, 'WIFI')
        self.assertIsNone(network.ssid)
        self.assertIsNone(network.rssi)
        self.assertIsNone(network.frecuencia)
        self.assertIsNone(network.velocidad)
        network_data = RegistroRedSerializer(network).data
        self.assertEqual(set(network_data), {'id', 'dispositivo', 'sim', 'tipo_conexion', 'fecha_hora'})


class DeviceSimStatusTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        registration = self.client.post(
            '/api/device/register/',
            {'device_uuid': 'sim-status-report-test'},
            format='json',
        )
        self.device = Dispositivo.objects.get(pk=registration.data['device_id'])
        self.device_headers = {
            'HTTP_AUTHORIZATION': f"Device {registration.data['token']}",
        }

    def test_empty_sim_report_is_stored_and_exposed_to_frontend(self):
        response = self.client.post(
            '/api/device/sims/status/',
            {'sim_count': 0},
            format='json',
            **self.device_headers,
        )

        self.assertEqual(response.status_code, 200)
        self.device.refresh_from_db()
        self.assertEqual(self.device.sim_count_reported, 0)
        self.assertIsNotNone(self.device.sims_reported_at)

        admin = get_user_model().objects.create_superuser(
            username='sim-status-admin',
            email='sim-status-admin@example.com',
            password='test-password',
        )
        admin_client = APIClient()
        admin_client.force_authenticate(user=admin)
        devices_response = admin_client.get('/api/dispositivos/')
        device_data = next(
            item for item in devices_response.data
            if item['id'] == self.device.id
        )
        self.assertEqual(device_data['sim_count_reported'], 0)
        self.assertIsNotNone(device_data['sims_reported_at'])

    def test_invalid_sim_count_is_not_accepted_as_empty(self):
        response = self.client.post(
            '/api/device/sims/status/',
            {'sim_count': -1},
            format='json',
            **self.device_headers,
        )

        self.assertEqual(response.status_code, 400)
        self.device.refresh_from_db()
        self.assertIsNone(self.device.sim_count_reported)


class DeviceSimPhoneNumberTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        registration = self.client.post(
            '/api/device/register/',
            {'device_uuid': 'sim-phone-number-test'},
            format='json',
        )
        self.assertEqual(registration.status_code, 201)
        self.headers = {
            'HTTP_AUTHORIZATION': f"Device {registration.data['token']}",
        }
        self.sim_uuid = 'sim-phone-number-test-1'
        self.phone_number = '+52 555 123 4567'
        self.iccid = 'ICCID-MANUAL-123'

    def test_empty_device_number_does_not_clear_manually_saved_number(self):
        first_response = self.client.post(
            '/api/device/sim/',
            {
                'sim_uuid': self.sim_uuid,
                'iccid': self.iccid,
                'numero_telefonico': self.phone_number,
            },
            format='json',
            **self.headers,
        )
        self.assertEqual(first_response.status_code, 201)
        sim = Sim.objects.get(sim_uuid=self.sim_uuid)

        for reported_number in ('', None):
            with self.subTest(reported_number=reported_number):
                response = self.client.post(
                    '/api/device/sim/',
                    {
                        'sim_uuid': self.sim_uuid,
                        'iccid': '',
                        'numero_telefonico': reported_number,
                    },
                    format='json',
                    **self.headers,
                )
                self.assertEqual(response.status_code, 201)
                sim.refresh_from_db()
                self.assertEqual(sim.numero_telefonico, self.phone_number)
                self.assertEqual(sim.iccid, self.iccid)

    def test_device_values_do_not_overwrite_manually_edited_sim_fields(self):
        response = self.client.post(
            '/api/device/sim/',
            {
                'sim_uuid': self.sim_uuid,
                'iccid': self.iccid,
                'numero_telefonico': self.phone_number,
            },
            format='json',
            **self.headers,
        )
        self.assertEqual(response.status_code, 201)

        response = self.client.post(
            '/api/device/sim/',
            {
                'sim_uuid': self.sim_uuid,
                'iccid': 'ICCID-REPORTED-BY-DEVICE',
                'numero_telefonico': '+52 555 000 0000',
            },
            format='json',
            **self.headers,
        )
        self.assertEqual(response.status_code, 201)
        sim = Sim.objects.get(sim_uuid=self.sim_uuid)
        self.assertEqual(sim.iccid, self.iccid)
        self.assertEqual(sim.numero_telefonico, self.phone_number)


class DeviceSimTransferTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.source = Dispositivo.objects.create(device_uuid='sim-source-device')
        self.target = Dispositivo.objects.create(
            device_uuid='sim-target-device',
            fabricante='Lenovo',
            modelo='TB-7104I',
        )
        self.sim = Sim.objects.create(
            dispositivo=self.source,
            sim_uuid='source-subscription-id',
            iccid='S.8952020320430379646',
            numero_telefonico='+52 555 123 4567',
        )
        self.target_registration = self.client.post(
            '/api/device/register/',
            {'device_uuid': self.target.device_uuid},
            format='json',
        )
        self.device_headers = {
            'HTTP_AUTHORIZATION': f"Device {self.target_registration.data['token']}",
        }

    def test_same_iccid_transfers_existing_sim_and_creates_one_notice(self):
        payload = {
            'sim_uuid': 'target-subscription-id',
            'iccid': '89520203204303796467F',
            'numero_telefonico': '+52 555 123 4567',
        }

        first_response = self.client.post(
            '/api/device/sim/',
            payload,
            format='json',
            **self.device_headers,
        )
        second_response = self.client.post(
            '/api/device/sim/',
            payload,
            format='json',
            **self.device_headers,
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertTrue(first_response.data['transferred'])
        self.assertEqual(second_response.status_code, 201)
        self.assertFalse(second_response.data['transferred'])
        self.assertEqual(Sim.objects.filter(iccid=self.sim.iccid).count(), 1)
        self.assertEqual(
            SimTransferConflict.objects.filter(
                sim=self.sim,
                target_device=self.target,
                status=SimTransferConflict.Status.TRANSFERRED,
            ).count(),
            1,
        )
        self.sim.refresh_from_db()
        self.assertEqual(self.sim.dispositivo, self.target)

    def test_iccid_normalization_matches_prefix_f_and_twentieth_digit_variants(self):
        expected = '8952020320430379646'
        self.assertEqual(normalize_iccid('S.8952020320430379646'), expected)
        self.assertEqual(normalize_iccid('8952020320430379646F'), expected)
        self.assertEqual(normalize_iccid('89520203204303796467'), expected)

    def test_transfer_notice_can_be_acknowledged_without_changing_assignment(self):
        self.sim.dispositivo = self.target
        self.sim.save(update_fields=['dispositivo'])
        conflict = SimTransferConflict.objects.create(
            sim=self.sim,
            source_device=self.source,
            target_device=self.target,
            status=SimTransferConflict.Status.TRANSFERRED,
            resolved_at=timezone.now(),
        )
        admin = get_user_model().objects.create_superuser(
            username='sim-transfer-admin',
            email='sim-transfer@example.com',
            password='test-password',
        )
        admin_client = APIClient()
        admin_client.force_authenticate(user=admin)

        response = admin_client.get('/api/sims/conflicts/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['source_device_name'], self.source.device_uuid)
        self.assertEqual(response.data[0]['target_device_name'], 'Lenovo TB-7104I')

        response = admin_client.post(
            f'/api/sims/conflicts/{conflict.id}/acknowledge/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.sim.refresh_from_db()
        conflict.refresh_from_db()
        self.assertEqual(self.sim.dispositivo, self.target)
        self.assertEqual(conflict.status, SimTransferConflict.Status.ACKNOWLEDGED)
        self.assertEqual(Sim.objects.filter(iccid=self.sim.iccid).count(), 1)
        self.assertEqual(admin_client.get('/api/sims/conflicts/').data, [])

    def test_transfer_rejects_a_conflict_if_sim_assignment_changed(self):
        conflict = SimTransferConflict.objects.create(
            sim=self.sim,
            source_device=self.source,
            target_device=self.target,
        )
        other_device = Dispositivo.objects.create(device_uuid='sim-other-device')
        self.sim.dispositivo = other_device
        self.sim.save(update_fields=['dispositivo'])
        admin = get_user_model().objects.create_superuser(
            username='stale-transfer-admin',
            email='stale-transfer@example.com',
            password='test-password',
        )
        admin_client = APIClient()
        admin_client.force_authenticate(user=admin)

        response = admin_client.post(
            f'/api/sims/conflicts/{conflict.id}/transfer/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, 409)
        self.sim.refresh_from_db()
        conflict.refresh_from_db()
        self.assertEqual(self.sim.dispositivo, other_device)
        self.assertEqual(conflict.status, SimTransferConflict.Status.STALE)

    def test_legacy_dismissed_conflict_does_not_change_assignment(self):
        conflict = SimTransferConflict.objects.create(
            sim=self.sim,
            source_device=self.source,
            target_device=self.target,
        )
        admin = get_user_model().objects.create_superuser(
            username='dismiss-transfer-admin',
            email='dismiss-transfer@example.com',
            password='test-password',
        )
        admin_client = APIClient()
        admin_client.force_authenticate(user=admin)

        response = admin_client.post(
            f'/api/sims/conflicts/{conflict.id}/dismiss/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.sim.refresh_from_db()
        conflict.refresh_from_db()
        self.assertEqual(self.sim.dispositivo, self.source)
        self.assertEqual(conflict.status, SimTransferConflict.Status.DISMISSED)
