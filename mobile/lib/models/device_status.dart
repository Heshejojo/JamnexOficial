class DeviceStatus {
  final String? deviceId;
  final String? model;
  final String? androidVersion;
  final int? batteryLevel;
  final bool? connected;
  final String? timestamp;

  DeviceStatus({
    this.deviceId,
    this.model,
    this.androidVersion,
    this.batteryLevel,
    this.connected,
    this.timestamp,
  });

  Map<String, dynamic> toJson() => {
        'device_id': deviceId,
        'model': model,
        'android_version': androidVersion,
        'battery_level': batteryLevel,
        'connected': connected,
        'timestamp': timestamp,
      };
}
