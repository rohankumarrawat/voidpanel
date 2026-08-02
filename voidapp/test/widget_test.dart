import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:voidapp/main.dart';

void main() {
  testWidgets('VoidApp smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const VoidApp());
    await tester.pumpAndSettle();

    // App should render without crashing
    expect(find.byType(MaterialApp), findsOneWidget);
  });
}
