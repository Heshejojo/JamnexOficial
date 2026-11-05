import 'package:flutter/services.dart';

import 'package:battery_plus/battery_plus.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:device_info_plus/device_info_plus.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../models/device_snapshot.dart';

class DeviceService {
  static const MethodChannel _simChannel = MethodChannel('agente_cfe/sim');
  final DeviceInfoPlugin _deviceInfo = DeviceInfoPlugin();
  final Battery _battery = Battery();
  final Connectivity _connectivity = Connectivity();

  Future<DeviceSnapshot> collectDeviceSnapshot() async {
    var connectivityResult = <ConnectivityResult>[ConnectivityResult.none];
    var batteryLevel = 0;
    var batteryState = BatteryState.unknown;

    try {
      connectivityResult = await _connectivity.checkConnectivity();
    } catch (_) {}
    try {
      batteryLevel = await _battery.batteryLevel;
      batteryState = await _battery.batteryState;
    } catch (_) {}

    String? manufacturer;
    String? model;
    String? osVersion;
    int? androidSdk;
    int? ramTotalMb;
    int? storageTotalMb;
    String? deviceId;
    String? serial;
    List<Map<String, dynamic>> sims = const [];
    bool? simsReadable;
    Map<String, dynamic> telemetry = const {};

    try {
      final info = await _deviceInfo.deviceInfo;
      if (info is AndroidDeviceInfo) {
        manufacturer = info.manufacturer;
        model = info.model;
        osVersion = info.version.release;
        androidSdk = info.version.sdkInt;
        deviceId = info.id;
        ramTotalMb = _bytesToMb(info.physicalRamSize);
        storageTotalMb = _bytesToMb(info.totalDiskSize);
        try {
          Map<dynamic, dynamic>? simInfo;
          for (var attempt = 0; attempt < 8; attempt++) {
            simInfo = await _simChannel
                .invokeMethod<Map<dynamic, dynamic>>('getSimInfo');
            final hasSimData = simInfo?['readable'] == true &&
                (simInfo?['sims'] as List<dynamic>? ?? const []).isNotEmpty;
            if (hasSimData) break;
            if (attempt < 7) {
              await Future<void>.delayed(const Duration(seconds: 1));
            }
          }
          if (simInfo != null && simInfo['readable'] == true) {
            simsReadable = true;
            sims = (simInfo['sims'] as List<dynamic>? ?? const [])
                .map((item) => Map<String, dynamic>.from(item as Map))
                .toList();
          } else {
            simsReadable = false;
          }
        } catch (_) {
          sims = const [];
          simsReadable = false;
        }
        try {
          for (var attempt = 0; attempt < 8; attempt++) {
            telemetry = Map<String, dynamic>.from(
              await _simChannel
                      .invokeMethod<Map<dynamic, dynamic>>('getTelemetry') ??
                  {},
            );
            final hasDeviceIdentity = telemetry['imei_1'] != null ||
                telemetry['imei_2'] != null ||
                telemetry['serial'] != null;
            if (hasDeviceIdentity) break;
            if (attempt < 7) {
              await Future<void>.delayed(const Duration(seconds: 1));
            }
          }
        } catch (_) {
          telemetry = const {};
        }
      } else if (info is WebBrowserInfo) {
        manufacturer = 'Microsoft Edge';
        model = info.userAgent ?? 'Web';
        osVersion = info.platform ?? 'web';
        deviceId = info.vendor ?? 'edge-web';
      }
    } catch (_) {
      manufacturer = null;
      model = null;
      osVersion = null;
      androidSdk = null;
      deviceId = null;
    }

    final connected = connectivityResult.isNotEmpty &&
        !connectivityResult.contains(ConnectivityResult.none);

    final stableDeviceId = telemetry['device_uuid']?.toString().trim().isNotEmpty ==
            true
        ? telemetry['device_uuid']!.toString().trim()
        : deviceId ?? await _persistentDeviceId();
    final reportedSerial = _usableSerial(
      telemetry['serial']?.toString(),
      stableDeviceId,
    );

    return DeviceSnapshot(
      deviceId: stableDeviceId,
      fabricante: manufacturer,
      modelo: model,
      versionAndroid: osVersion,
      imei1: telemetry['imei_1']?.toString(),
      imei2: telemetry['imei_2']?.toString(),
      serial: reportedSerial ?? serial,
      androidSdk: androidSdk,
      ramTotalMb: _asInt(telemetry['ram_total_mb']) ?? ramTotalMb,
      ramUsedMb: _asInt(telemetry['ram_used_mb']),
      ramAvailableMb: _asInt(telemetry['ram_available_mb']),
      almacenamientoTotalMb:
          _asInt(telemetry['storage_total_mb']) ?? storageTotalMb,
      almacenamientoUsadoMb: _asInt(telemetry['storage_used_mb']),
      almacenamientoDisponibleMb: _asInt(telemetry['storage_available_mb']),
      batteryPercent:
          (telemetry['battery_percent'] as num?)?.toInt() ?? batteryLevel,
      batteryStatus: _mapBatteryState(batteryState),
      connectionType: summarizeConnectivity(connectivityResult),
      sims: sims,
      batteryTemperature:
          (telemetry['battery_temperature_c'] as num?)?.toDouble(),
      mobileDataMb: (telemetry['mobile_data_mb'] as num?)?.toDouble(),
      mobileDataDayMb: (telemetry['mobile_data_day_mb'] as num?)?.toDouble(),
      mobileDataSimSlot: (telemetry['mobile_data_sim_slot'] as num?)?.toInt(),
      mobileDataLimitMb:
          (telemetry['mobile_data_limit_mb'] as num?)?.toDouble(),
      networkTechnology: telemetry['network_technology']?.toString(),
      carrierName: telemetry['carrier_name']?.toString(),
      carrierId: (telemetry['carrier_id'] as num?)?.toInt(),
      roaming: telemetry['roaming'] == true,
      simsReadable: simsReadable,
      applications: (telemetry['applications'] as List<dynamic>?)
              ?.map((item) => Map<String, dynamic>.from(item as Map))
              .toList() ??
          const [],
      connected: connected,
      timestamp: DateTime.now(),
    );
  }

  static int? _bytesToMb(int value) {
    if (value <= 0) return null;
    return (value / (1024 * 1024)).round();
  }

  static int? _asInt(dynamic value) => value is num ? value.round() : null;

  static String? _usableSerial(String? value, String? deviceId) {
    final serial = value?.trim();
    if (serial == null || serial.isEmpty) return null;
    if (serial.toLowerCase() == 'unknown' ||
        serial.toLowerCase() == 'null' ||
        serial == '000000000000000' ||
        serial == deviceId) {
      return null;
    }
    return serial;
  }

  Future<String> _persistentDeviceId() async {
    final preferences = await SharedPreferences.getInstance();
    const key = 'persistent_device_id';
    final existing = preferences.getString(key);
    if (existing != null && existing.isNotEmpty) return existing;

    final generated =
        'flutter-device-${DateTime.now().microsecondsSinceEpoch}';
    await preferences.setString(key, generated);
    return generated;
  }

  static String _mapBatteryState(BatteryState state) {
    switch (state) {
      case BatteryState.charging:
        return 'cargando';
      case BatteryState.full:
        return 'completa';
      case BatteryState.discharging:
        return 'descargando';
      case BatteryState.unknown:
      default:
        return 'desconocida';
    }
  }

  static String summarizeConnectivity(List<ConnectivityResult> results) {
    if (results.contains(ConnectivityResult.wifi)) {
      return 'Wi‑Fi';
    }
    if (results.contains(ConnectivityResult.mobile)) {
      return 'Datos móviles';
    }
    if (results.contains(ConnectivityResult.none) || results.isEmpty) {
      return 'Sin conexión';
    }
    return 'No disponible';
  }
}
