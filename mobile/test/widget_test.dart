import 'package:agente_cfe/main.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('Agente CFE app loads', (WidgetTester tester) async {
    await tester.pumpWidget(const AgenteCfeApp());

    expect(find.text('Agente CFE'), findsOneWidget);
    expect(find.text('Estado del dispositivo'), findsOneWidget);
  });
}
