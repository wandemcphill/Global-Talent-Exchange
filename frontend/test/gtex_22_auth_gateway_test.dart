import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/screens/auth/gtex_22_auth_gateway.dart';

void main() {
  testWidgets('login validates required fields before signing in', (
    WidgetTester tester,
  ) async {
    final _RecordingExchangeController controller =
        _RecordingExchangeController();

      await tester.pumpWidget(
        MaterialApp(home: Gtex22LoginScreen(controller: controller)),
      );
      await tester.ensureVisible(find.text('ENTER GTEX'));
      await tester.tap(find.text('ENTER GTEX'));
      await tester.pumpAndSettle();

    expect(find.text('Enter your email address.'), findsOneWidget);
    expect(find.text('Enter your password.'), findsOneWidget);
    expect(controller.signInCalls, 0);
  });
}

class _RecordingExchangeController extends GteExchangeController {
  _RecordingExchangeController() : super(api: GteExchangeApiClient.fixture());

  int signInCalls = 0;

  @override
  Future<void> signIn({required String email, required String password}) async {
    signInCalls += 1;
  }
}
