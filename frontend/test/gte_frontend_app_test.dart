import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/app/gte_frontend_app.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';

void main() {
  testWidgets('frontend app renders the canonical home shell',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1600, 2200);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(),
    );
    controller.session = _authenticatedSession(
      userId: 'user-ibadan',
      userName: 'Ibadan Owner',
      clubId: 'ibadan-lions',
      clubName: 'Ibadan Lions FC',
    );

    await tester.pumpWidget(
      GteFrontendApp(
        controller: controller,
        config: const GteAppConfig(
          apiBaseUrl: 'http://127.0.0.1:8000',
          backendMode: GteBackendMode.fixture,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Global Talent Exchange'), findsOneWidget);
    expect(find.text('Home'), findsWidgets);
    expect(find.text('Expansion lanes'), findsOneWidget);
    expect(find.text('No canonical club is selected'), findsNothing);
  });
}

GteAuthSession _authenticatedSession({
  required String userId,
  required String userName,
  String? clubId,
  String? clubName,
}) {
  return GteAuthSession.fromJson(
    <String, Object?>{
      'access_token': 'test-token',
      'token_type': 'bearer',
      'expires_in': 3600,
      if (clubId != null) 'current_club_id': clubId,
      if (clubName != null) 'current_club_name': clubName,
      'user': <String, Object?>{
        'id': userId,
        'email': '$userId@gtex.test',
        'username': userId,
        'display_name': userName,
        'role': 'user',
        if (clubId != null) 'current_club_id': clubId,
        if (clubName != null) 'current_club_name': clubName,
      },
    },
  );
}
