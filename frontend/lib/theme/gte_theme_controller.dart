import 'package:flutter/foundation.dart';

import 'gte_theme_metadata.dart';
import 'gte_theme_registry.dart';
import 'gte_theme_store.dart';

class GteThemeController extends ChangeNotifier {
  GteThemeController({
    GteThemeStore? store,
    GteThemeId initialThemeId = GteThemeId.foundersBlack,
    bool useGtexNavyShell = false,
  }) : _store = store ?? GteMemoryThemeStore(),
       _activeThemeId = initialThemeId,
       _useGtexNavyShell = useGtexNavyShell;

  final GteThemeStore _store;
  GteThemeId _activeThemeId;
  bool _useGtexNavyShell;

  GteThemeId get activeThemeId => _activeThemeId;
  bool get useGtexNavyShell => _useGtexNavyShell;

  GteThemeDefinition get activeTheme => GteThemeRegistry.resolve(
    _activeThemeId,
    preferGtexNavy: _useGtexNavyShell,
  );

  static Future<GteThemeController> bootstrap({
    GteThemeStore? store,
    GteThemeId initialThemeId = GteThemeId.foundersBlack,
    bool useGtexNavyShell = false,
  }) async {
    final GteThemeStore resolvedStore =
        store ?? await GteSharedPreferencesThemeStore.create();
    final GteThemeController controller = GteThemeController(
      store: resolvedStore,
      initialThemeId: initialThemeId,
      useGtexNavyShell: useGtexNavyShell,
    );
    await controller.restore();
    return controller;
  }

  Future<void> restore() async {
    final GteThemeId? restoredThemeId = await _store.readThemeId();
    if (restoredThemeId == null || restoredThemeId == _activeThemeId) {
      return;
    }
    _activeThemeId = restoredThemeId;
    notifyListeners();
  }

  Future<void> selectTheme(GteThemeId themeId) async {
    if (themeId == _activeThemeId && !_useGtexNavyShell) {
      return;
    }
    _activeThemeId = themeId;
    _useGtexNavyShell = false;
    notifyListeners();
    await _store.writeThemeId(themeId);
  }

  /// Reversible toggle between the canonical GTEX Navy shell theme (`O-06`)
  /// and the user's selected legacy registry theme (`foundersBlack` fallback).
  void setUseGtexNavyShell(bool enabled) {
    if (_useGtexNavyShell == enabled) {
      return;
    }
    _useGtexNavyShell = enabled;
    notifyListeners();
  }
}
