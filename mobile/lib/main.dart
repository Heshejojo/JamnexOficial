import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';

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
  String? _identitySyncError;
  DeviceSnapshot? _snapshot;
  String? _serialOverride;
  final Map<String, Map<String, dynamic>> _iccidOverrides = {};

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
    await _loadIdentityOverrides();

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
      final collectedSnapshot = await _deviceService.collectDeviceSnapshot();
      var snapshot = collectedSnapshot;
      final deviceUuid = snapshot.deviceId ??
          'flutter-${DateTime.now().millisecondsSinceEpoch}';
      snapshot = _applyIdentityOverrides(snapshot, deviceUuid);
      if (mounted) {
        setState(() {
          _snapshot = snapshot;
        });
      }

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
      for (var index = 0; index < snapshot.sims.length; index++) {
        final sim = snapshot.sims[index];
        final reportedSim = collectedSnapshot.sims[index];
        pendingEvents.add({
          'endpoint': '/device/sim/',
          'payload': {
            'sim_uuid': _simUuid(deviceUuid, sim),
            'iccid': reportedSim['iccid'],
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
      final currentSimIds =
          snapshot.sims.map((sim) => _simUuid(deviceUuid, sim)).toSet();
      final identitySims = _iccidOverrides.entries
          .where((entry) => currentSimIds.contains(entry.key))
          .map((entry) => <String, dynamic>{
                'sim_uuid': entry.value['sim_uuid'],
                if (entry.value['slot'] is int && entry.value['slot'] >= 0)
                  'slot': entry.value['slot'],
                'iccid': entry.value['iccid'],
              })
          .toList();
      final identityPayload = <String, dynamic>{
        if (_serialOverride != null) 'serial': _serialOverride,
        if (identitySims.isNotEmpty) 'sims': identitySims,
      };
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
      await _apiService.withNetworkSession(() async {
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
        if (identityPayload.isNotEmpty) {
          try {
            await _apiService.postDeviceJson(
              '/device/identity/',
              identityPayload,
            );
            _identitySyncError = null;
          } catch (error) {
            debugPrint(
                'No se pudieron sincronizar los identificadores: $error');
            _identitySyncError = error is ApiException
                ? 'El servidor rechazó la edición (HTTP ${error.statusCode}). '
                    'Verifica que la SIM siga asignada a este equipo y que el ICCID no esté duplicado.'
                : 'No se pudieron enviar los identificadores; se volverán a intentar en la próxima sincronización.';
          }
        }
      });

      if (mounted) {
        setState(() {
          _snapshot = snapshot;
          _status = _identitySyncError == null
              ? 'Sincronizado'
              : 'Identificadores pendientes';
          _lastSync = DateTime.now().toLocal().toString().substring(0, 16);
        });
        if (_identitySyncError != null) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(_identitySyncError!)),
          );
        }
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

  Future<void> _loadIdentityOverrides() async {
    final preferences = await SharedPreferences.getInstance();
    final storedIdentity = preferences.getString('manual_device_identity');
    if (storedIdentity == null) return;

    final decoded = jsonDecode(storedIdentity);
    if (decoded is! Map) {
      throw const FormatException(
          'Los identificadores locales no son válidos.');
    }
    final serial = decoded['serial'];
    if (serial != null && serial is! String) {
      throw const FormatException('El número de serie local no es válido.');
    }
    _serialOverride = serial as String?;
    final storedOverrides = decoded['sims'];
    if (storedOverrides == null) return;
    if (storedOverrides is! Map) {
      throw const FormatException(
          'Los ICCID editados localmente no son válidos.');
    }
    for (final entry in storedOverrides.entries) {
      if (entry.key is! String || entry.value is! Map) {
        throw const FormatException(
            'Un ICCID editado localmente no es válido.');
      }
      final override = Map<String, dynamic>.from(entry.value as Map);
      if (override['sim_uuid'] is! String || override['iccid'] is! String) {
        throw const FormatException(
            'Faltan datos de un ICCID editado localmente.');
      }
      _iccidOverrides[entry.key as String] = override;
    }
  }

  DeviceSnapshot _applyIdentityOverrides(
    DeviceSnapshot snapshot,
    String deviceUuid,
  ) {
    final sims = snapshot.sims.map((sim) {
      final override = _iccidOverrides[_simUuid(deviceUuid, sim)];
      return override == null
          ? sim
          : <String, dynamic>{...sim, 'iccid': override['iccid']};
    }).toList();
    return snapshot.copyWith(serial: _serialOverride, sims: sims);
  }

  String _simUuid(String deviceUuid, Map<String, dynamic> sim) {
    final subscriptionId = sim['subscription_id']?.toString().trim();
    if (subscriptionId != null && subscriptionId.isNotEmpty) {
      return subscriptionId;
    }
    return 'sim-$deviceUuid-${sim['slot'] ?? 0}';
  }

  Future<void> _editIdentity() async {
    final snapshot = _snapshot;
    if (snapshot == null) return;

    final deviceUuid =
        snapshot.deviceId ?? 'flutter-${DateTime.now().millisecondsSinceEpoch}';
    final serialController = TextEditingController(text: snapshot.serial ?? '');
    final simControllers = <String, TextEditingController>{};
    final simTargets = <String, Map<String, dynamic>>{};
    for (var index = 0; index < snapshot.sims.length; index++) {
      final sim = snapshot.sims[index];
      final simUuid = _simUuid(deviceUuid, sim);
      simTargets[simUuid] = {
        'sim_uuid': simUuid,
        if (sim['slot'] is num) 'slot': (sim['slot'] as num).toInt(),
        'label': 'ICCID · SIM ${index + 1}',
      };
      simControllers[simUuid] =
          TextEditingController(text: sim['iccid']?.toString() ?? '');
    }

    final formKey = GlobalKey<FormState>();
    String? validationMessage;
    Map<String, dynamic>? updates;
    try {
      updates = await showDialog<Map<String, dynamic>>(
        context: context,
        builder: (dialogContext) => StatefulBuilder(
          builder: (context, setDialogState) => AlertDialog(
            title: const Text('Editar identificadores'),
            content: SizedBox(
              width: double.maxFinite,
              child: SingleChildScrollView(
                child: Form(
                  key: formKey,
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      TextFormField(
                        controller: serialController,
                        maxLength: 255,
                        decoration: const InputDecoration(
                          labelText: 'Número de serie',
                        ),
                        validator: (value) => (value?.length ?? 0) > 255
                            ? 'El número de serie es demasiado largo.'
                            : null,
                      ),
                      if (simControllers.isEmpty)
                        const Padding(
                          padding: EdgeInsets.only(top: 8),
                          child: Text(
                            'No se detectaron SIM. Concede el permiso de teléfono y sincroniza para editar un ICCID.',
                          ),
                        ),
                      for (final entry in simControllers.entries)
                        TextFormField(
                          controller: entry.value,
                          maxLength: 255,
                          decoration: InputDecoration(
                            labelText:
                                simTargets[entry.key]!['label'] as String,
                          ),
                          validator: (value) => (value?.length ?? 0) > 255
                              ? 'El ICCID es demasiado largo.'
                              : null,
                        ),
                      if (validationMessage != null)
                        Padding(
                          padding: const EdgeInsets.only(top: 8),
                          child: Text(
                            validationMessage!,
                            style: TextStyle(
                              color: Theme.of(context).colorScheme.error,
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(dialogContext).pop(),
                child: const Text('Cancelar'),
              ),
              FilledButton(
                onPressed: () {
                  if (!(formKey.currentState?.validate() ?? false)) return;
                  final serial = serialController.text.trim();
                  final sims = <Map<String, dynamic>>[];
                  for (final entry in simControllers.entries) {
                    final iccid = entry.value.text.trim();
                    if (iccid.isEmpty) continue;
                    sims.add({
                      ...simTargets[entry.key]!,
                      'iccid': iccid,
                    }..remove('label'));
                  }
                  if (serial.isEmpty && sims.isEmpty) {
                    setDialogState(() {
                      validationMessage =
                          'Escribe un número de serie o al menos un ICCID.';
                    });
                    return;
                  }
                  Navigator.of(dialogContext).pop({
                    'serial': serial,
                    'sims': sims,
                  });
                },
                child: const Text('Guardar'),
              ),
            ],
          ),
        ),
      );
    } finally {
      serialController.dispose();
      for (final controller in simControllers.values) {
        controller.dispose();
      }
    }
    if (updates == null || !mounted) return;

    final serial = updates['serial'] as String;
    final sims = List<Map<String, dynamic>>.from(updates['sims'] as List);
    final updatedSerial = serial.isNotEmpty ? serial : _serialOverride;
    final updatedIccidOverrides =
        Map<String, Map<String, dynamic>>.from(_iccidOverrides);
    for (final sim in sims) {
      final simUuid = sim['sim_uuid'] as String;
      final override = Map<String, dynamic>.from(sim)..remove('label');
      updatedIccidOverrides[simUuid] = override;
    }

    final preferences = await SharedPreferences.getInstance();
    final saved = await preferences.setString(
      'manual_device_identity',
      jsonEncode({
        if (updatedSerial != null) 'serial': updatedSerial,
        'sims': updatedIccidOverrides,
      }),
    );
    if (!saved) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content:
                Text('No se pudieron guardar los cambios en este teléfono.'),
          ),
        );
      }
      return;
    }
    _serialOverride = updatedSerial;
    _iccidOverrides
      ..clear()
      ..addAll(updatedIccidOverrides);
    await _collectAndSend();
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

  Future<void> _requestDevicePermissions() async {
    try {
      await _simChannel.invokeMethod<void>('requestPermissions');
    } on PlatformException catch (error) {
      debugPrint('No se pudieron solicitar permisos del dispositivo: $error');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('No fue posible abrir la solicitud de permisos.'),
          ),
        );
      }
    } on MissingPluginException catch (error) {
      debugPrint('El canal Android de permisos no está disponible: $error');
    }
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
              const SizedBox(height: 10),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed:
                      _snapshot == null || _isLoading ? null : _editIdentity,
                  icon: const Icon(Icons.edit_outlined),
                  label: const Text('Editar serie e ICCID'),
                ),
              ),
              const SizedBox(height: 18),
              _MobileDataHero(snapshot: _snapshot),
              const SizedBox(height: 20),
              _MonitoringPanel(snapshot: _snapshot),
              if (_snapshot?.simsReadable != true) ...[
                const SizedBox(height: 8),
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton.icon(
                    onPressed: _requestDevicePermissions,
                    icon: const Icon(Icons.security_rounded),
                    label: const Text('Solicitar permisos de SIM'),
                  ),
                ),
              ],
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
