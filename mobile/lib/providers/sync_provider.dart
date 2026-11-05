import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

class SyncProvider {
  static const _storageKey = 'pending_sync_events';
  final List<Map<String, dynamic>> _pendingEvents = [];

  Future<void> load() async {
    final preferences = await SharedPreferences.getInstance();
    final storedEvents = preferences.getString(_storageKey);
    if (storedEvents == null) return;

    final decoded = jsonDecode(storedEvents);
    if (decoded is! List) {
      throw const FormatException('La cola de sincronización no es válida.');
    }
    _pendingEvents
      ..clear()
      ..addAll(
        decoded.map((event) {
          if (event is! Map) {
            throw const FormatException(
              'Un evento de la cola de sincronización no es válido.',
            );
          }
          return Map<String, dynamic>.from(event);
        }),
      );
  }

  Future<void> enqueue(Map<String, dynamic> event) async {
    _pendingEvents.add(event);
    await _save();
  }

  Future<void> retry(
    Future<void> Function(Map<String, dynamic> event) send,
  ) async {
    while (_pendingEvents.isNotEmpty) {
      await send(Map<String, dynamic>.from(_pendingEvents.first));
      _pendingEvents.removeAt(0);
      await _save();
    }
  }

  Future<void> _save() async {
    final preferences = await SharedPreferences.getInstance();
    await preferences.setString(_storageKey, jsonEncode(_pendingEvents));
  }
}
