import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:voidmail_app/main.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('VoidMailApp smoke test', (WidgetTester tester) async {
    SharedPreferences.setMockInitialValues({});
    await tester.pumpWidget(const VoidMailApp());
    await tester.pump(const Duration(milliseconds: 200));
    expect(find.text('VoidMail'), findsWidgets);
    await tester.pumpAndSettle(const Duration(seconds: 2));
  });
}
