import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/app/gte_frontend_app.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';

void main() {
  Future<void> pumpGuestShell(
    WidgetTester tester, {
    required String initialPath,
  }) async {
    tester.view.physicalSize = const Size(360, 740);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(),
    );
    addTearDown(controller.dispose);

    await tester.pumpWidget(
      GteFrontendApp(
        controller: controller,
        config: const GteAppConfig(
          apiBaseUrl: 'http://192.168.43.162:8000',
          backendMode: GteBackendMode.fixture,
        ),
        initialPath: initialPath,
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
  }

  testWidgets('guest home fits a small phone viewport', (
    WidgetTester tester,
  ) async {
    await pumpGuestShell(tester, initialPath: '/app/world');

    final Object? exception = tester.takeException();
    expect(find.text('World'), findsWidgets);
    expect(exception, isNull, reason: '$exception');
  });

  testWidgets('guest community fits a small phone viewport', (
    WidgetTester tester,
  ) async {
    await pumpGuestShell(tester, initialPath: '/app/community');

    final Object? exception = tester.takeException();
    expect(find.text('Community'), findsWidgets);
    expect(exception, isNull, reason: '$exception');
  });
}
