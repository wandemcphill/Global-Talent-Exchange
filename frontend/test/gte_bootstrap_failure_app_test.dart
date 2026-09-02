import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/app/gte_bootstrap_failure_app.dart';
import 'package:gte_frontend/theme/gte_theme_controller.dart';

void main() {
  testWidgets('bootstrap failure app renders truthful live-config guidance', (
    WidgetTester tester,
  ) async {
    final GteThemeController controller = GteThemeController();
    addTearDown(controller.dispose);

    await tester.pumpWidget(
      GteBootstrapFailureApp(
        themeController: controller,
        failure: GteBootstrapFailure.fromError(
          StateError(
            'GTE_API_BASE_URL must be set when GTE_BACKEND_MODE is live.',
          ),
        ),
      ),
    );
    await tester.pump();

    expect(find.text('Live configuration missing'), findsOneWidget);
    expect(find.textContaining('GTE_API_BASE_URL'), findsWidgets);
    expect(find.textContaining('flutter run -d <device>'), findsOneWidget);

    // e9abceac ("remove production localhost bootstrap endpoint") replaced the
    // hardcoded http://127.0.0.1:8000 suggestion and its
    // `adb reverse tcp:8000 tcp:8000` pairing advice with a reachable-backend
    // placeholder. Assert the guidance that shipped, and hold the line on the
    // localhost endpoint not creeping back into production copy.
    expect(find.textContaining('<reachable-backend-url>'), findsOneWidget);
    expect(find.textContaining('reachable backend URL'), findsOneWidget);
    expect(find.textContaining('127.0.0.1'), findsNothing);
    expect(find.textContaining('adb reverse'), findsNothing);
  });
}
