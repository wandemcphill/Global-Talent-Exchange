import 'package:flutter/foundation.dart';

import 'gte_theme_metadata.dart';
import 'gte_theme_registry.dart';
import 'gte_theme_store.dart';

class GteThemeController extends ChangeNotifier {
  GteThemeController({
    GteThemeStore? store,
    GteThemeId initialThemeId = GteThemeId.darkGold,
  })  : _store = store ?? GteMemoryThemeStore(),
        _activeThemeId = initialThemeId;

  final GteThemeStore _store;
  GteThemeId _activeThemeId;

  GteThemeId get activeThemeId => _activeThemeId;
  GteThemeDefinition get activeTheme =>
      GteThemeRegistry.resolve(_activeThemeId);

  static Future<GteThemeController> bootstrap({
    GteThemeStore? store,
    GteThemeId initialThemeId = GteThemeId.darkGold,
  }) async {
    final GteThemeStore resolvedStore =
        store ?? await GteSharedPreferencesThemeStore.create();
    final GteThemeController controller = GteThemeController(
      store: resolvedStore,
      initialThemeId: initialThemeId,
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
    if (themeId == _activeThemeId) {
      return;
    }
    _activeThemeId = themeId;
    notifyListeners();
    await _store.writeThemeId(themeId);
  }
}
