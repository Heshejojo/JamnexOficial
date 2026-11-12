import 'package:flutter/material.dart';

class EditIdentityDialog extends StatefulWidget {
  const EditIdentityDialog({
    super.key,
    required this.serial,
    required this.simTargets,
    required this.initialIccids,
  });

  final String serial;
  final Map<String, Map<String, dynamic>> simTargets;
  final Map<String, String> initialIccids;

  @override
  State<EditIdentityDialog> createState() => _EditIdentityDialogState();
}

class _EditIdentityDialogState extends State<EditIdentityDialog> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _serialController;
  final Map<String, TextEditingController> _simControllers = {};
  String? _validationMessage;

  @override
  void initState() {
    super.initState();
    _serialController = TextEditingController(text: widget.serial);
    for (final entry in widget.simTargets.entries) {
      _simControllers[entry.key] =
          TextEditingController(text: widget.initialIccids[entry.key] ?? '');
    }
  }

  @override
  void dispose() {
    _serialController.dispose();
    for (final controller in _simControllers.values) {
      controller.dispose();
    }
    super.dispose();
  }

  void _save() {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    final serial = _serialController.text.trim();
    final sims = <Map<String, dynamic>>[];
    for (final entry in _simControllers.entries) {
      final iccid = entry.value.text.trim();
      if (iccid.isEmpty) continue;
      sims.add({
        ...widget.simTargets[entry.key]!,
        'iccid': iccid,
      }..remove('label'));
    }
    if (serial.isEmpty && sims.isEmpty) {
      setState(() {
        _validationMessage = 'Escribe un número de serie o al menos un ICCID.';
      });
      return;
    }
    Navigator.of(context).pop({
      'serial': serial,
      'sims': sims,
    });
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      scrollable: true,
      insetPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
      title: const Text('Editar identificadores'),
      content: SizedBox(
        width: double.maxFinite,
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextFormField(
                controller: _serialController,
                maxLength: 255,
                decoration: const InputDecoration(
                  labelText: 'Número de serie',
                ),
                validator: (value) => (value?.length ?? 0) > 255
                    ? 'El número de serie es demasiado largo.'
                    : null,
              ),
              if (_simControllers.isEmpty)
                const Padding(
                  padding: EdgeInsets.only(top: 8),
                  child: Text(
                    'No se detectaron SIM. Concede el permiso de teléfono y sincroniza para editar un ICCID.',
                  ),
                ),
              for (final entry in _simControllers.entries)
                TextFormField(
                  controller: entry.value,
                  maxLength: 255,
                  decoration: InputDecoration(
                    labelText: widget.simTargets[entry.key]!['label'] as String,
                  ),
                  validator: (value) => (value?.length ?? 0) > 255
                      ? 'El ICCID es demasiado largo.'
                      : null,
                ),
              if (_validationMessage != null)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text(
                    _validationMessage!,
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.error,
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancelar'),
        ),
        FilledButton(
          onPressed: _save,
          child: const Text('Guardar'),
        ),
      ],
    );
  }
}
