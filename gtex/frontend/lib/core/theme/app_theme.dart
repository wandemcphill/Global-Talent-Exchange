import 'package:flutter/material.dart';

import '../../theme/gte_theme_registry.dart';
import '../../widgets/gte_shell_theme.dart';

class AppTheme {
  const AppTheme._();

  static ThemeData dark([GteThemeDefinition? definition]) {
    return GteShellTheme.build(definition ?? GteThemeRegistry.defaultTheme);
  }
}
