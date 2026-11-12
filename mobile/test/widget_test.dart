import 'package:agente_cfe/main.dart';
import 'package:agente_cfe/widgets/edit_identity_dialog.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('identifier dialog saves and closes cleanly',
      (WidgetTester tester) async {
    Map<String, dynamic>? result;
    await tester.pumpWidget(
      MaterialApp(
        home: Builder(
          builder: (context) => Scaffold(
            body: TextButton(
              onPressed: () async {
                result = await showDialog<Map<String, dynamic>>(
                  context: context,
                  builder: (_) => const EditIdentityDialog(
                    serial: 'SERIAL-ORIGINAL',
                    simTargets: {
                      'sim-1': {
                        'sim_uuid': 'sim-1',
                        'slot': 0,
                        'label': 'ICCID · SIM 1',
                      },
                    },
                    initialIccids: {'sim-1': '1234567890123456789'},
                  ),
                );
              },
              child: const Text('Abrir'),
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('Abrir'));
    await tester.pumpAndSettle();
    tester.view.viewInsets = const FakeViewPadding(bottom: 300);
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextFormField).first, 'SERIAL-EDITADO');
    await tester.ensureVisible(find.text('Guardar'));
    await tester.tap(find.text('Guardar'));
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(result?['serial'], 'SERIAL-EDITADO');
    expect(result?['sims'], hasLength(1));
  });

  testWidgets('Agente CFE app loads', (WidgetTester tester) async {
    await tester.pumpWidget(const AgenteCfeApp());

    expect(find.text('Agente CFE'), findsOneWidget);
    expect(find.text('Estado del dispositivo'), findsOneWidget);
  });
}
