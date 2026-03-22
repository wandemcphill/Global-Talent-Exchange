import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/screens/creators/creator_access_request_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets(
      'creator access request screen submits a creator application after contact confirmation',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1600, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(),
    );
    controller.session = _authenticatedSession(
      userId: 'creator-user',
      userName: 'Creator User',
      phoneNumber: '1234567890',
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: CreatorAccessRequestScreen(exchangeController: controller),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Use account email'), findsOneWidget);
    expect(find.text('Use account phone'), findsOneWidget);

    await tester.ensureVisible(find.text('Use account email'));
    await tester.tap(find.text('Use account email'));
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('Use account phone'));
    await tester.tap(find.text('Use account phone'));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField).at(0), 'creator.one');
    await tester.enterText(find.byType(TextField).at(1), 'Creator One');
    await tester.enterText(find.byType(TextField).at(2), '250000');
    await tester.enterText(
      find.byType(TextField).at(3),
      'https://youtube.com/@creatorone',
    );

    await tester.ensureVisible(find.text('Submit creator application'));
    await tester.tap(find.text('Submit creator application'));
    await tester.pumpAndSettle();

    expect(find.text('Creator application pending review'), findsOneWidget);
  });
}

GteAuthSession _authenticatedSession({
  required String userId,
  required String userName,
  required String phoneNumber,
}) {
  return GteAuthSession.fromJson(
    <String, Object?>{
      'access_token': 'test-token',
      'token_type': 'bearer',
      'expires_in': 3600,
      'user': <String, Object?>{
        'id': userId,
        'email': '$userId@gtex.test',
        'username': userId,
        'display_name': userName,
        'phone_number': phoneNumber,
        'role': 'user',
      },
    },
  );
}
