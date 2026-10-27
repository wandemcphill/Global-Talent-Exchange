import 'package:flutter/foundation.dart';

/// Compile-time default for the `shell_v3` flag (Master Plan Document K5).
const bool kGtexShellV3EnvironmentDefault = bool.fromEnvironment(
  'GTEX_SHELL_V3',
  defaultValue: true,
);

/// Runtime controller for the `shell_v3` feature flag (Master Plan Document K5).
///
/// Allows Phase B–F tests and launch-control overrides to toggle the v3 shell
/// behaviour (per-lane state preservation, 5-slot `ShellNavigationModel`, and
/// GTEX Navy shell chrome) while keeping existing P7-FEV tests deterministic.
class GtexShellFeatureFlag {
  const GtexShellFeatureFlag._();

  static final ValueNotifier<bool> _overrideNotifier = ValueNotifier<bool>(
    kGtexShellV3EnvironmentDefault,
  );
  static bool _hasRuntimeOverride = false;

  static ValueListenable<bool> get listenable => _overrideNotifier;

  /// Resolve whether `shell_v3` is enabled, preferring an explicit widget flag,
  /// then a runtime override, then the compile-time `GTEX_SHELL_V3` flag.
  static bool isEnabled({bool? explicitOverride}) {
    if (explicitOverride != null) {
      return explicitOverride;
    }
    if (_hasRuntimeOverride) {
      return _overrideNotifier.value;
    }
    return kGtexShellV3EnvironmentDefault;
  }

  /// Override `shell_v3` at runtime (for tests, Design Lab, or Launch Control).
  static void setRuntimeOverride(bool? enabled) {
    if (enabled == null) {
      _hasRuntimeOverride = false;
      _overrideNotifier.value = kGtexShellV3EnvironmentDefault;
      return;
    }
    _hasRuntimeOverride = true;
    _overrideNotifier.value = enabled;
  }
}
