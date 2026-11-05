import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'models/device_snapshot.dart';
import 'services/api_service.dart';
import 'services/device_service.dart';
import 'providers/sync_provider.dart';

void main() {
  runApp(const AgenteCfeApp());
}

class AgenteCfeApp extends StatelessWidget {
  const AgenteCfeApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Jamnex',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF1E3A8A),
          brightness: Brightness.light,
        ),
        scaffoldBackgroundColor: const Color(0xFFF5F7FB),
        useMaterial3: true,
      ),
      home: const DeviceAgentHome(),
    );
  }
}

class DeviceAgentHome extends StatefulWidget {
  const DeviceAgentHome({super.key});

  @override
  State<DeviceAgentHome> createState() => _DeviceAgentHomeState();
}

class _DeviceAgentHomeState extends State<DeviceAgentHome> {
  final DeviceService _deviceService = DeviceService();
  final ApiService _apiService = ApiService();
  final SyncProvider _syncProvider = SyncProvider();
  static const MethodChannel _simChannel = MethodChannel('agente_cfe/sim');
  bool _isLoading = false;
  String _status = 'Pendiente';
  String _lastSync = 'Nunca';
  DeviceSnapshot? _snapshot;

  @override
  void initState() {
    super.initState();
    _initialize();
  }

  Future<void> _initialize() async {
    await Future.wait([
      _apiService.loadDeviceToken(),
      _syncProvider.load(),
    ]);

    try {
      await _simChannel.invokeMethod<void>(
        'scheduleBackgroundSync',
        {'baseUrl': ApiService.baseUrl},
      );
    } on PlatformException catch (error) {
      debugPrint(
          'No se pudo programar la sincronización en segundo plano: $error');
    }

    await _collectAndSend();
  }

  Future<void> _collectAndSend() async {
    final pendingEvents = <Map<String, dynamic>>[];
    if (mounted) {
      setState(() {
        _isLoading = true;
        _status = 'Sincronizando';
      });
    }

    try {
      final snapshot = await _deviceService.collectDeviceSnapshot();
      if (mounted) {
        setState(() {
          _snapshot = snapshot;
        });
      }

      final deviceUuid = snapshot.deviceId ??
          'flutter-${DateTime.now().millisecondsSinceEpoch}';
      final devicePayload = snapshot.toBackendPayload()
        ..['device_uuid'] = deviceUuid;
      final statusPayload = <String, dynamic>{
        'device_uuid': deviceUuid,
        'battery_percent': snapshot.batteryPercent,
        'battery_status': snapshot.batteryStatus,
        'connected': snapshot.connected,
        'ram_total': snapshot.ramTotalMb,
        'almacenamiento_total': snapshot.almacenamientoTotalMb,
        'ram_usada': snapshot.ramUsedMb,
        'ram_disponible': snapshot.ramAvailableMb,
        'almacenamiento_usado': snapshot.almacenamientoUsadoMb,
        'almacenamiento_disponible': snapshot.almacenamientoDisponibleMb,
        'battery_temperature': snapshot.batteryTemperature,
        'timestamp': snapshot.timestamp.toUtc().toIso8601String(),
      };
      pendingEvents
          .add({'endpoint': '/device/status/', 'payload': statusPayload});
      pendingEvents.add({
        'endpoint': '/device/network/',
        'payload': {
          'tipo_conexion': _networkType(snapshot.connectionType),
        },
      });
      for (final sim in snapshot.sims) {
        pendingEvents.add({
          'endpoint': '/device/sim/',
          'payload': {
            'sim_uuid': sim['subscription_id']?.toString() ??
                'sim-${deviceUuid}-${sim['slot'] ?? 0}',
            'iccid': sim['iccid'],
            'slot': sim['slot'],
            'operador_nombre': sim['operador'],
            'pais': sim['pais'],
            'mcc': sim['mcc'],
            'mnc': sim['mnc'],
            'numero_telefonico': sim['numero'],
            'carrier_id': sim['carrier_id'],
            'esim': sim['esim'],
            'tecnologia': snapshot.networkTechnology,
            'roaming': snapshot.roaming,
          },
        });
      }
      if (snapshot.simsReadable == true) {
        pendingEvents.add({
          'endpoint': '/device/sims/status/',
          'payload': {
            'sim_count': snapshot.sims.length,
            'sim_slots': snapshot.sims
                .map((sim) => sim['slot'])
                .whereType<num>()
                .map((slot) => slot.toInt())
                .toList(),
          },
        });
      }
      if (snapshot.mobileDataDayMb != null) {
        pendingEvents.add({
          'endpoint': '/device/consumption/',
          'payload': {
            'consumo_datos_movil': snapshot.mobileDataDayMb,
            'periodo': 'diario',
            'sim_slot': snapshot.mobileDataSimSlot ?? -1,
          },
        });
      }
      await _apiService.registerDevice(devicePayload);
      await _syncProvider.retry((item) async {
        final payload =
            Map<String, dynamic>.from(item['payload'] as Map? ?? {});
        payload['device_uuid'] = deviceUuid;
        await _postDeviceEvent(item['endpoint'] as String, payload);
      });
      for (final event in pendingEvents) {
        await _postDeviceEvent(
          event['endpoint'] as String,
          Map<String, dynamic>.from(event['payload'] as Map),
        );
      }

      if (mounted) {
        setState(() {
          _snapshot = snapshot;
          _status = 'Sincronizado';
          _lastSync = DateTime.now().toLocal().toString().substring(0, 16);
        });
      }
    } catch (error) {
      debugPrint('Error al sincronizar datos del dispositivo: $error');
      for (final event in pendingEvents) {
        await _syncProvider.enqueue({
          ...event,
          'type': 'device_event',
          'created_at': DateTime.now().toUtc().toIso8601String(),
        });
      }
      if (mounted) {
        setState(() {
          _status = 'Error de sincronización';
        });
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
                'No se pudieron enviar los cambios. Revisa la conexión y vuelve a sincronizar.'),
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _postDeviceEvent(
    String endpoint,
    Map<String, dynamic> payload,
  ) async {
    if (endpoint == '/device/sims/status/') {
      await _apiService.postDeviceJsonIfAvailable(endpoint, payload);
      return;
    }
    await _apiService.postDeviceJson(endpoint, payload);
  }

  String _networkType(String? connectionType) {
    switch (connectionType) {
      case 'Wi‑Fi':
        return 'WIFI';
      case 'Datos móviles':
        return 'DATOS_MOVILES';
      default:
        return 'SIN_CONEXION';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Jamnex'),
        actions: [
          Chip(
            label: Text(_status),
            backgroundColor: _status == 'Sincronizado'
                ? const Color(0xFFDCFCE7)
                : _status == 'Sincronizando'
                    ? const Color(0xFFDBEAFE)
                    : const Color(0xFFFEE2E2),
            labelStyle: TextStyle(
              color: _status == 'Sincronizado'
                  ? const Color(0xFF166534)
                  : _status == 'Sincronizando'
                      ? const Color(0xFF1D4ED8)
                      : const Color(0xFF991B1B),
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(width: 12),
        ],
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(18),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Consumo de datos',
                style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 18),
              _snapshot == null
                  ? const DeviceSummaryCard(
                      title: 'Equipo no revisado',
                      value: 'Sin datos aún',
                      subtitle:
                          'Presiona sincronizar para recoger información.',
                      icon: Icons.phone_android_rounded,
                      color: Color(0xFF3B82F6),
                    )
                  : DeviceSummaryCard(
                      title: _snapshot!.fabricante ?? 'Dispositivo',
                      value: _snapshot!.modelo ?? 'Modelo no disponible',
                      subtitle:
                          '${_snapshot!.versionAndroid ?? 'Android no disponible'} · ${_snapshot!.batteryPercent ?? 0}% batería\nIMEI: ${_snapshot!.imei1 ?? 'No disponible'}\nSerie: ${_snapshot!.serial ?? 'No disponible'}',
                      icon: Icons.phone_android_rounded,
                      color: const Color(0xFF2563EB),
                    ),
              const SizedBox(height: 18),
              _MobileDataHero(snapshot: _snapshot),
              const SizedBox(height: 20),
              _MonitoringPanel(snapshot: _snapshot),
              const SizedBox(height: 20),
              Container(
                padding: const EdgeInsets.all(18),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(20),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.04),
                      blurRadius: 12,
                      offset: const Offset(0, 8),
                    ),
                  ],
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Sincronización',
                      style:
                          TextStyle(fontSize: 18, fontWeight: FontWeight.w800),
                    ),
                    const SizedBox(height: 10),
                    Text('Última sincronización: $_lastSync'),
                    const SizedBox(height: 16),
                    SizedBox(
                      width: double.infinity,
                      child: FilledButton.icon(
                        onPressed: _isLoading ? null : _collectAndSend,
                        icon: _isLoading
                            ? const SizedBox(
                                width: 18,
                                height: 18,
                                child:
                                    CircularProgressIndicator(strokeWidth: 2),
                              )
                            : const Icon(Icons.sync_rounded),
                        label: Text(_isLoading
                            ? 'Sincronizando...'
                            : 'Sincronizar ahora'),
                      ),
                    ),
                    const SizedBox(height: 18),
                    const Center(
                      child: Column(
                        children: [
                          Text(
                            'Developed by Julio Cesar C Acosta & Adrian M Mancha',
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              color: Color(0xFF64748B),
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          SizedBox(height: 4),
                          Text(
                            '© 2026 Jamnex. All rights reserved.',
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              color: Color(0xFF94A3B8),
                              fontSize: 10,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _MobileDataHero extends StatelessWidget {
  final DeviceSnapshot? snapshot;

  const _MobileDataHero({required this.snapshot});

  String _formatMb(num? megabytes) {
    if (megabytes == null) return 'No disponible';
    return '${megabytes.toStringAsFixed(2)} MB';
  }

  String _formatGb(num? megabytes) {
    if (megabytes == null) return 'No disponible';
    return '${(megabytes / 1024).toStringAsFixed(2)} GB';
  }

  @override
  Widget build(BuildContext context) {
    final used = snapshot?.mobileDataDayMb;
    final limit = snapshot?.mobileDataLimitMb ?? 2048;
    final progress =
        used == null ? 0.0 : (used / limit).clamp(0.0, 1.0).toDouble();
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        color: const Color(0xFF0F766E),
        borderRadius: BorderRadius.circular(22),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.data_usage_rounded, color: Colors.white),
              SizedBox(width: 10),
              Text('Datos móviles',
                  style: TextStyle(
                      color: Colors.white,
                      fontSize: 18,
                      fontWeight: FontWeight.w800)),
            ],
          ),
          const SizedBox(height: 18),
          Text(_formatMb(used),
              style: const TextStyle(
                  color: Colors.white,
                  fontSize: 36,
                  fontWeight: FontWeight.w900)),
          const SizedBox(height: 4),
          const Text('Usados hoy',
              style: TextStyle(color: Color(0xFFCCFBF1), fontSize: 13)),
          const SizedBox(height: 18),
          ClipRRect(
            borderRadius: BorderRadius.circular(8),
            child: LinearProgressIndicator(
              value: progress,
              minHeight: 10,
              backgroundColor: const Color(0xFF115E59),
              valueColor:
                  const AlwaysStoppedAnimation<Color>(Color(0xFFFDE68A)),
            ),
          ),
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('${(progress * 100).toStringAsFixed(1)}% del límite',
                  style: const TextStyle(
                      color: Colors.white, fontWeight: FontWeight.w700)),
              Text('Límite ${_formatGb(limit)}',
                  style: const TextStyle(color: Color(0xFFCCFBF1))),
            ],
          ),
          const SizedBox(height: 14),
        ],
      ),
    );
  }
}

class _MonitoringPanel extends StatelessWidget {
  final DeviceSnapshot? snapshot;

  const _MonitoringPanel({required this.snapshot});

  String _formatMb(num? megabytes) {
    if (megabytes == null) return 'No disponible';
    return '${megabytes.toStringAsFixed(2)} MB';
  }

  String _formatGb(num? megabytes) {
    if (megabytes == null) return 'No disponible';
    return '${(megabytes / 1024).toStringAsFixed(2)} GB';
  }

  String _value(Map<String, dynamic> sim, String key) {
    final value = sim[key];
    return value == null || value.toString().isEmpty
        ? 'No disponible'
        : value.toString();
  }

  Widget _detail(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 116,
            child: Text(label,
                style: const TextStyle(color: Color(0xFF64748B), fontSize: 12)),
          ),
          Expanded(
              child: Text(value,
                  style: const TextStyle(
                      fontWeight: FontWeight.w600, fontSize: 12))),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final current = snapshot;
    final usingMobile = current?.connectionType == 'Datos móviles';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Supervisión del dispositivo',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
        const SizedBox(height: 10),
        _resourceCard(
          title: 'Sistema',
          icon: Icons.memory_rounded,
          children: [
            _detail('RAM total', _formatGb(current?.ramTotalMb)),
            _detail('RAM usada', _formatGb(current?.ramUsedMb)),
            _detail('RAM libre', _formatGb(current?.ramAvailableMb)),
            _detail('Almacenamiento total',
                _formatGb(current?.almacenamientoTotalMb)),
            _detail('Almacenamiento usado',
                _formatGb(current?.almacenamientoUsadoMb)),
            _detail('Almacenamiento libre',
                _formatGb(current?.almacenamientoDisponibleMb)),
          ],
          expandable: true,
        ),
        const SizedBox(height: 10),
        Card(
          margin: EdgeInsets.zero,
          elevation: 0,
          color: Colors.white,
          child: ExpansionTile(
            leading: Icon(
                usingMobile
                    ? Icons.signal_cellular_alt_rounded
                    : Icons.wifi_rounded,
                color: const Color(0xFF2563EB)),
            title: Text(current?.connectionType ?? 'Sin datos',
                style: const TextStyle(fontWeight: FontWeight.w800)),
            subtitle: Text(usingMobile
                ? 'Datos móviles'
                : current?.connectionType == 'Wi‑Fi'
                    ? 'Wi-Fi en uso'
                    : 'Wi-Fi no está en uso'),
            childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
            children: usingMobile
                ? [
                    _detail('Consumo hoy', _formatMb(current?.mobileDataDayMb)),
                    _detail('Límite', _formatGb(current?.mobileDataLimitMb)),
                    _detail('Tecnología',
                        current?.networkTechnology ?? 'No disponible'),
                    _detail(
                        'Operador', current?.carrierName ?? 'No disponible'),
                    _detail('Roaming',
                        current?.roaming == true ? 'Activo' : 'Inactivo'),
                  ]
                : [
                    _detail(
                        'Estado',
                        current?.connectionType == 'Wi‑Fi'
                            ? 'Wi-Fi en uso'
                            : 'Wi-Fi no está en uso'),
                  ],
          ),
        ),
        const SizedBox(height: 14),
        const Text('Estado de SIM',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
        const SizedBox(height: 8),
        if (current == null || current.sims.isEmpty)
          const Text('No se detectaron SIM o faltan permisos.')
        else
          ...current.sims.asMap().entries.map((entry) {
            final index = entry.key;
            final sim = entry.value;
            return Card(
              margin: const EdgeInsets.only(bottom: 8),
              elevation: 0,
              color: Colors.white,
              child: ExpansionTile(
                leading: Icon(sim['activa'] == true
                    ? Icons.sim_card_rounded
                    : Icons.sim_card_alert_rounded),
                title: Text(_value(sim, 'operador'),
                    style: const TextStyle(fontWeight: FontWeight.w700)),
                subtitle: Text(
                    'SIM ${index + 1} · ${sim['esim'] == true ? 'eSIM' : 'Física'}'),
                childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
                children: [
                  _detail(
                      'Estado', sim['activa'] == true ? 'Activa' : 'Inactiva'),
                  _detail('Tipo hardware',
                      sim['esim'] == true ? 'eSIM / digital' : 'SIM física'),
                  _detail('Operador', _value(sim, 'operador')),
                  _detail('País', _value(sim, 'pais')),
                  _detail('MCC / MNC',
                      '${_value(sim, 'mcc')} / ${_value(sim, 'mnc')}'),
                  _detail('Carrier ID', _value(sim, 'carrier_id')),
                  _detail('Número celular', _value(sim, 'numero')),
                  _detail('ICCID', _value(sim, 'iccid')),
                  _detail('ID SIM', _value(sim, 'subscription_id')),
                  _detail(
                      'Ranura',
                      sim['slot'] is num
                          ? 'Ranura ${(sim['slot'] as num).toInt() + 1}'
                          : _value(sim, 'slot')),
                  _detail('Tecnología',
                      current.networkTechnology ?? 'No disponible'),
                  _detail('Roaming', current.roaming ? 'Activo' : 'Inactivo'),
                ],
              ),
            );
          }),
      ],
    );
  }

  Widget _resourceCard(
      {required String title,
      required IconData icon,
      required List<Widget> children,
      bool expandable = false}) {
    if (expandable) {
      return Card(
        margin: EdgeInsets.zero,
        elevation: 0,
        color: Colors.white,
        child: ExpansionTile(
          leading: Icon(icon, color: const Color(0xFF8B5CF6)),
          title:
              Text(title, style: const TextStyle(fontWeight: FontWeight.w800)),
          childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
          children: children,
        ),
      );
    }
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: const Color(0xFF8B5CF6)),
              const SizedBox(width: 10),
              Text(title, style: const TextStyle(fontWeight: FontWeight.w800)),
            ],
          ),
          const SizedBox(height: 12),
          ...children,
        ],
      ),
    );
  }
}

class DeviceSummaryCard extends StatelessWidget {
  final String title;
  final String value;
  final String subtitle;
  final IconData icon;
  final Color color;

  const DeviceSummaryCard({
    super.key,
    required this.title,
    required this.value,
    required this.subtitle,
    required this.icon,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(22),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.04),
            blurRadius: 12,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            width: 52,
            height: 52,
            decoration: BoxDecoration(
              color: color.withOpacity(0.14),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Icon(icon, color: color),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                      fontWeight: FontWeight.w700, fontSize: 18),
                ),
                const SizedBox(height: 4),
                Text(value,
                    style: const TextStyle(fontWeight: FontWeight.w800)),
                const SizedBox(height: 2),
                Text(
                  subtitle,
                  style:
                      const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
