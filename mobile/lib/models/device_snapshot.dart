/// Fotografía inmutable de identidad, hardware, red, SIMs y consumo del teléfono.
///
/// Los campos opcionales representan datos que Android puede ocultar por versión,
/// permisos o limitaciones del fabricante.
class DeviceSnapshot {
  // Identidad y sistema operativo reportados por Android.
  final String? deviceId;
  final String? fabricante;
  final String? modelo;
  final String? versionAndroid;
  final String? imei1;
  final String? imei2;
  final String? serial;
  final int? androidSdk;
  // Capacidades de memoria y almacenamiento, expresadas en megabytes.
  final int? ramTotalMb;
  final int? ramUsedMb;
  final int? ramAvailableMb;
  final int? almacenamientoTotalMb;
  final int? almacenamientoUsadoMb;
  final int? almacenamientoDisponibleMb;
  // Estado instantáneo de batería y conectividad.
  final int? batteryPercent;
  final String? batteryStatus;
  final String? connectionType;
  // Medidas complementarias de red celular y SIM activa.
  final double? batteryTemperature;
  final double? mobileDataMb;
  final double? mobileDataDayMb;
  final int? mobileDataSimSlot;
  final double? mobileDataLimitMb;
  final String? networkTechnology;
  final String? carrierName;
  final int? carrierId;
  final bool roaming;
  final bool? simsReadable;
  // Registros completos capturados por los canales Flutter y Android.
  final List<Map<String, dynamic>> applications;
  final List<Map<String, dynamic>> sims;
  final bool connected;
  // Momento local de captura; se convierte a UTC al serializar para el servidor.
  final DateTime timestamp;

  /// Construye una lectura sin mutaciones posteriores.
  const DeviceSnapshot({
    this.deviceId,
    this.fabricante,
    this.modelo,
    this.versionAndroid,
    this.imei1,
    this.imei2,
    this.serial,
    this.androidSdk,
    this.ramTotalMb,
    this.ramUsedMb,
    this.ramAvailableMb,
    this.almacenamientoTotalMb,
    this.almacenamientoUsadoMb,
    this.almacenamientoDisponibleMb,
    this.batteryPercent,
    this.batteryStatus,
    this.connectionType,
    this.batteryTemperature,
    this.mobileDataMb,
    this.mobileDataDayMb,
    this.mobileDataSimSlot,
    this.mobileDataLimitMb,
    this.networkTechnology,
    this.carrierName,
    this.carrierId,
    this.roaming = false,
    this.simsReadable,
    this.applications = const [],
    this.sims = const [],
    required this.connected,
    required this.timestamp,
  });

  /// Reduce la fotografía a los campos que acepta el endpoint de registro.
  Map<String, dynamic> toBackendPayload() {
    return {
      'device_uuid': deviceId,
      'fabricante': fabricante,
      'modelo': modelo,
      'version_android': versionAndroid,
      'imei_1': imei1,
      'imei_2': imei2,
      'serial': serial,
      'android_sdk': androidSdk,
      'ram_total': ramTotalMb,
      'almacenamiento_total': almacenamientoTotalMb,
      'activo': connected,
      'ultimo_contacto': timestamp.toUtc().toIso8601String(),
    };
  }

  /// Crea otra fotografía conservando todo salvo los identificadores solicitados.
  DeviceSnapshot copyWith({
    String? imei1,
    String? imei2,
    String? serial,
    List<Map<String, dynamic>>? sims,
  }) {
    return DeviceSnapshot(
      deviceId: deviceId,
      fabricante: fabricante,
      modelo: modelo,
      versionAndroid: versionAndroid,
      imei1: imei1 ?? this.imei1,
      imei2: imei2 ?? this.imei2,
      serial: serial ?? this.serial,
      androidSdk: androidSdk,
      ramTotalMb: ramTotalMb,
      ramUsedMb: ramUsedMb,
      ramAvailableMb: ramAvailableMb,
      almacenamientoTotalMb: almacenamientoTotalMb,
      almacenamientoUsadoMb: almacenamientoUsadoMb,
      almacenamientoDisponibleMb: almacenamientoDisponibleMb,
      batteryPercent: batteryPercent,
      batteryStatus: batteryStatus,
      connectionType: connectionType,
      batteryTemperature: batteryTemperature,
      mobileDataMb: mobileDataMb,
      mobileDataDayMb: mobileDataDayMb,
      mobileDataSimSlot: mobileDataSimSlot,
      mobileDataLimitMb: mobileDataLimitMb,
      networkTechnology: networkTechnology,
      carrierName: carrierName,
      carrierId: carrierId,
      roaming: roaming,
      simsReadable: simsReadable,
      applications: applications,
      sims: sims ?? this.sims,
      connected: connected,
      timestamp: timestamp,
    );
  }
}
