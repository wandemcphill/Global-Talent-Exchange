import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/launch_control_redesign/gtex_feature_flags_launch_control_screen_v2.dart';
import 'package:gte_frontend/features/launch_control_redesign/launch_control_api.dart';
import 'package:gte_frontend/features/launch_control_redesign/launch_control_controller.dart';

void main() {
  testWidgets('launch-control screen renders fixture dashboard', (
    WidgetTester tester,
  ) async {
    final controller = GtexLaunchControlController(
      api: GtexLaunchControlApi.fixture(),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: GtexFeatureFlagsLaunchControlScreenV2(
          baseUrl: 'http://127.0.0.1:8000',
          accessToken: 'fixture-token',
          backendMode: GteBackendMode.fixture,
          controller: controller,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Launch Control'), findsWidgets);
    expect(find.text('Feature flags'), findsOneWidget);
    expect(find.text('Transfer Hub'), findsWidgets);
    expect(find.text('Module health'), findsOneWidget);
    expect(find.text('Command router'), findsOneWidget);
    expect(find.text('Beta grants'), findsOneWidget);
    expect(find.text('Client flags'), findsOneWidget);
    expect(find.text('user-beta'), findsOneWidget);
  });
}
