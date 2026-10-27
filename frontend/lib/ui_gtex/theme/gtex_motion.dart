import 'package:flutter/material.dart';

/// Canonical motion specifications for the GTEX shell (Master Plan Document F6).
///
/// - `stateDuration`: 120 ms (chip/button/selection state changes)
/// - `enterExitDuration`: 200 ms (panel/card enter/exit transitions)
/// - `sheetRouteDuration`: 320 ms (bottom sheets, modals, and route transitions)
/// - `curve`: `Curves.easeOutCubic`
/// - Respects `MediaQuery.disableAnimationsOf(context)` for reduced-motion users.
class GtexMotion {
  const GtexMotion._();

  static const Duration stateDuration = Duration(milliseconds: 120);
  static const Duration enterExitDuration = Duration(milliseconds: 200);
  static const Duration sheetRouteDuration = Duration(milliseconds: 320);

  static const Curve curve = Curves.easeOutCubic;
  static const Curve standardCurve = Curves.easeInOutCubic;

  static bool shouldReduceMotion(BuildContext context) {
    return MediaQuery.maybeDisableAnimationsOf(context) ?? false;
  }

  static Duration effectiveDuration(
    BuildContext context,
    Duration normal, {
    Duration reduced = Duration.zero,
  }) {
    return shouldReduceMotion(context) ? reduced : normal;
  }

  static bool shouldPauseTicker({
    required BuildContext context,
    bool isHovered = false,
    bool isFocused = false,
  }) {
    return shouldReduceMotion(context) || isHovered || isFocused;
  }
}
