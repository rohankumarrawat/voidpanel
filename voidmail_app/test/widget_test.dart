import 'package:flutter_test/flutter_test.dart';
import 'package:voidmail_app/main.dart';

void main() {
  testWidgets('VoidMailApp smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const VoidMailApp());
    expect(find.text('VoidMail'), findsOneWidget);
  });
}
