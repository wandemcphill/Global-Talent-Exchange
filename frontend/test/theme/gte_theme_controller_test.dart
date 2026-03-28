import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:gte_frontend/theme/gte_theme_controller.dart';
import 'package:gte_frontend/theme/gte_theme_metadata.dart';
import 'package:gte_frontend/theme/gte_theme_registry.dart';
import 'package:gte_frontend/theme/gte_theme_store.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  group('GteThemeController', () {
    setUp(() {
      SharedPreferences.setMockInitialValues(<String, Object>{});
    });

    test('restores a persisted theme id', () async {
      SharedPreferences.setMockInitialValues(<String, Object>{
        'gte_theme_id': 'minimal_carbon',
      });

      final GteThemeController controller = await GteThemeController.bootstrap(
        store: await GteSharedPreferencesThemeStore.create(),
      );

      expect(controller.activeThemeId, GteThemeId.minimalCarbon);
    });

    test('writes the selected theme id to preferences', () async {
      final GteThemeController controller = GteThemeController(
        store: await GteSharedPreferencesThemeStore.create(),
      );

      await controller.selectTheme(GteThemeId.neonVelocity);

      final SharedPreferences preferences =
          await SharedPreferences.getInstance();
      expect(preferences.getString('gte_theme_id'), 'neon_velocity');
    });

    testWidgets('builds a renderable ThemeData for every registered theme', (
      WidgetTester tester,
    ) async {
      for (final GteThemeDefinition definition in GteThemeRegistry.themes) {
        await tester.pumpWidget(
          MaterialApp(
            theme: GteShellTheme.build(definition),
            home: Scaffold(
              body: Center(child: Text(definition.metadata.label)),
            ),
          ),
        );
        await tester.pump();

        expect(find.text(definition.metadata.label), findsOneWidget);
      }
    });
  });
}
