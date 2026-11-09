import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class ApiService {
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.14.64.15:8000/api',
  );

  String? _deviceToken;

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

    if (response.statusCode >= 200 && response.statusCode < 300) {
      if (response.body.isEmpty) {
        return <String, dynamic>{};
      }
      return jsonDecode(response.body) as Map<String, dynamic>;
    }

    throw ApiException(
      statusCode: response.statusCode,
      message: response.body,
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
