import 'package:agente_cfe/services/api_service.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('refreshes a rejected device token and retries the request', () async {
    SharedPreferences.setMockInitialValues({'device_token': 'stale-token'});
    debugDefaultTargetPlatformOverride = TargetPlatform.android;
    addTearDown(() {
      debugDefaultTargetPlatformOverride = null;
    });

    const channel = MethodChannel('agente_cfe/api');
    final calls = <MethodCall>[];
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, (call) async {
      calls.add(call);
      final arguments = call.arguments as Map<dynamic, dynamic>;
      final endpoint = arguments['endpoint'] as String;
      final token = arguments['token'] as String?;
      if (endpoint == '/device/status/' && token == 'stale-token') {
        return {
          'statusCode': 403,
          'body': '{"detail":"Las credenciales no son válidas."}',
        };
      }
      if (endpoint == '/device/register/') {
        return {
          'statusCode': 201,
          'body': '{"token":"fresh-token"}',
        };
      }
      if (endpoint == '/device/status/' && token == 'fresh-token') {
        return {
          'statusCode': 200,
          'body': '{"received":true}',
        };
      }
      throw StateError('Solicitud inesperada: $endpoint');
    });
    addTearDown(
      () => TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, null),
    );

    final apiService = ApiService();
    await apiService.loadDeviceToken();
    final result = await apiService.postDeviceJson(
      '/device/status/',
      {'connected': true},
      registrationPayload: {'device_uuid': 'test-device'},
    );

    expect(result['received'], isTrue);
    expect(
      calls
          .map((call) => (call.arguments as Map<dynamic, dynamic>)['endpoint'])
          .toList(),
      ['/device/status/', '/device/register/', '/device/status/'],
    );
  });
}
