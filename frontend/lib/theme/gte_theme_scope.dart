import 'package:flutter/material.dart';

import 'gte_theme_controller.dart';

class GteThemeControllerScope extends InheritedNotifier<GteThemeController> {
  const GteThemeControllerScope({
    super.key,
    required GteThemeController controller,
    required super.child,
  }) : super(notifier: controller);

  static GteThemeController of(BuildContext context) {
    final GteThemeController? controller = maybeOf(context);
    assert(
      controller != null,
      'GteThemeControllerScope.of() called with no scope in context.',
    );
    return controller!;
  }

  static GteThemeController? maybeOf(BuildContext context) {
    final GteThemeControllerScope? scope =
        context.dependOnInheritedWidgetOfExactType<GteThemeControllerScope>();
    return scope?.notifier;
  }
}
