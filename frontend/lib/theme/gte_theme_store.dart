import 'package:shared_preferences/shared_preferences.dart';

import 'gte_theme_metadata.dart';

abstract class GteThemeStore {
  Future<GteThemeId?> readThemeId();

  Future<void> writeThemeId(GteThemeId themeId);
}

class GteMemoryThemeStore implements GteThemeStore {
  GteThemeId? _themeId;

  @override
  Future<GteThemeId?> readThemeId() async => _themeId;

  @override
  Future<void> writeThemeId(GteThemeId themeId) async {
    _themeId = themeId;
  }
}

class GteSharedPreferencesThemeStore implements GteThemeStore {
  GteSharedPreferencesThemeStore(
    this._preferences, [
    this.storageKey = 'gte_theme_id',
  ]);

  final SharedPreferences _preferences;
  final String storageKey;

  static Future<GteSharedPreferencesThemeStore> create() async {
    final SharedPreferences preferences = await SharedPreferences.getInstance();
    return GteSharedPreferencesThemeStore(preferences);
  }

  @override
  Future<GteThemeId?> readThemeId() async {
    return GteThemeIdX.tryParse(_preferences.getString(storageKey));
  }

  @override
  Future<void> writeThemeId(GteThemeId themeId) {
    return _preferences.setString(storageKey, themeId.storageKey);
  }
}
