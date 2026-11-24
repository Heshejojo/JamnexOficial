import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

/// Cola persistente FIFO para telemetría que todavía no pudo llegar al backend.
class SyncProvider {
  // La clave se comparte con la versión instalada para conservar reintentos.
  static const _storageKey = 'pending_sync_events';
  final List<Map<String, dynamic>> _pendingEvents = [];

  /// Recupera la cola local y rechaza datos corruptos en vez de enviarlos a ciegas.
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

  /// Añade el evento al final y persiste inmediatamente la cola completa.
  Future<void> enqueue(Map<String, dynamic> event) async {
    _pendingEvents.add(event);
    await _save();
  }

  /// Reenvía del más antiguo al más reciente y lo borra solo tras el éxito.
  Future<void> retry(
    Future<void> Function(Map<String, dynamic> event) send,
  ) async {
    while (_pendingEvents.isNotEmpty) {
      await send(Map<String, dynamic>.from(_pendingEvents.first));
      _pendingEvents.removeAt(0);
      await _save();
    }
  }

  /// Serializa la cola para poder restaurarla después de cerrar la aplicación.
  Future<void> _save() async {
    final preferences = await SharedPreferences.getInstance();
    await preferences.setString(_storageKey, jsonEncode(_pendingEvents));
  }
}
