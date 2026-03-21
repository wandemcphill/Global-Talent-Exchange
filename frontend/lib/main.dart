import 'package:flutter/material.dart';

import 'app/gte_frontend_app.dart';
import 'theme/gte_theme_controller.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final GteThemeController themeController =
      await GteThemeController.bootstrap();
  // Canonical MVP entrypoint for the exchange app.
  runApp(GteFrontendApp(themeController: themeController));
}
