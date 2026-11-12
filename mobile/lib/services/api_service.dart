import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class ApiService {
  static const MethodChannel _apiChannel = MethodChannel('agente_cfe/api');
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://jamnex-api.cfe.mx/api',
  );

  String? _deviceToken;

  Future<T> withNetworkSession<T>(Future<T> Function() action) async {
    if (kIsWeb || defaultTargetPlatform != TargetPlatform.android) {
      return action();
    }

    await _apiChannel.invokeMethod<void>('beginNetworkSession');
    try {
      return await action();
    } finally {
      await _apiChannel.invokeMethod<void>('endNetworkSession');
    }
  }

  void setDeviceToken(String token) {
    _deviceToken = token;
    SharedPreferences.getInstance().then((preferences) {
      preferences.setString('device_token', token);
    });
  }

  Future<void> loadDeviceToken() async {
    final preferences = await SharedPreferences.getInstance();
    _deviceToken = preferences.getString('device_token');
  }

  Future<String> registerDevice(Map<String, dynamic> payload) async {
    final response = await _post('/device/register/', payload);
    final token = response['token'] as String?;
    if (token == null || token.isEmpty) {
      throw const ApiException(
          statusCode: 502,
          message: 'El backend no devolvió token de dispositivo.');
    }
    setDeviceToken(token);
    return token;
  }

  Future<String> ensureDeviceRegistered(Map<String, dynamic> payload) async {
    final token = _deviceToken;
    if (token != null && token.isNotEmpty) return token;
    return registerDevice(payload);
  }

  Future<Map<String, dynamic>> postDeviceJson(
      String endpoint, Map<String, dynamic> payload) {
    if (_deviceToken == null) {
      throw const ApiException(
          statusCode: 401, message: 'El dispositivo no está registrado.');
    }
    return _post(endpoint, payload, deviceToken: _deviceToken);
  }

  Future<void> postDeviceJsonIfAvailable(
    String endpoint,
    Map<String, dynamic> payload,
  ) async {
    try {
      await postDeviceJson(endpoint, payload);
    } on ApiException catch (error) {
      if (error.statusCode != 404) rethrow;
      debugPrint(
        'El backend aún no admite $endpoint; se omite solo este reporte.',
      );
    }
  }

  Future<Map<String, dynamic>> _post(
    String endpoint,
    Map<String, dynamic> payload, {
    String? deviceToken,
  }) async {
    late final int statusCode;
    late final String responseBody;
    if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
      final response = await _apiChannel.invokeMapMethod<String, dynamic>(
        'postJson',
        {
          'baseUrl': baseUrl,
          'endpoint': endpoint,
          'payload': payload,
          'token': deviceToken,
        },
      );
      if (response == null || response['statusCode'] is! int) {
        throw const ApiException(
          statusCode: 502,
          message: 'Respuesta inválida del cliente de red Android.',
        );
      }
      statusCode = response['statusCode'] as int;
      responseBody = response['body'] as String? ?? '';
    } else {
      final response = await http
          .post(
            Uri.parse('$baseUrl$endpoint'),
            headers: {
              'Content-Type': 'application/json',
              if (deviceToken != null) 'Authorization': 'Device $deviceToken',
            },
            body: jsonEncode(payload),
          )
          .timeout(const Duration(seconds: 60));
      statusCode = response.statusCode;
      responseBody = response.body;
    }

    if (statusCode >= 200 && statusCode < 300) {
      if (responseBody.isEmpty) {
        return <String, dynamic>{};
      }
      return jsonDecode(responseBody) as Map<String, dynamic>;
    }

    throw ApiException(
      statusCode: statusCode,
      message: responseBody,
    );
  }
}

class ApiException implements Exception {
  final int statusCode;
  final String message;

  const ApiException({required this.statusCode, required this.message});

  @override
  String toString() =>
      'ApiException(statusCode: $statusCode, message: $message)';
}
