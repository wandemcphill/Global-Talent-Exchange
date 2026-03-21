import 'package:flutter/material.dart';

enum GteThemeId {
  darkGold,
  stadiumNight,
  ultraRed,
  iceWhite,
}

extension GteThemeIdX on GteThemeId {
  String get storageKey {
    switch (this) {
      case GteThemeId.darkGold:
        return 'dark_gold';
      case GteThemeId.stadiumNight:
        return 'stadium_night';
      case GteThemeId.ultraRed:
        return 'ultra_red';
      case GteThemeId.iceWhite:
        return 'ice_white';
    }
  }

  static GteThemeId? tryParse(String? raw) {
    final String normalized = (raw ?? '').trim().toLowerCase();
    for (final GteThemeId value in GteThemeId.values) {
      if (value.storageKey == normalized) {
        return value;
      }
    }
    return null;
  }
}

@immutable
class GteThemeMetadata {
  const GteThemeMetadata({
    required this.id,
    required this.label,
    required this.tagline,
    required this.description,
    required this.icon,
    required this.brightness,
  });

  final GteThemeId id;
  final String label;
  final String tagline;
  final String description;
  final IconData icon;
  final Brightness brightness;
}
