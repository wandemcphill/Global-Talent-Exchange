import 'package:flutter/material.dart';

enum GteThemeId {
  foundersBlack,
  paloAltoGlass,
  sandHillGold,
  menloNightBlue,
  aiArenaCrimson,
}

extension GteThemeIdX on GteThemeId {
  String get storageKey {
    switch (this) {
      case GteThemeId.foundersBlack:
        return 'founders_black';
      case GteThemeId.paloAltoGlass:
        return 'palo_alto_glass';
      case GteThemeId.sandHillGold:
        return 'sand_hill_gold';
      case GteThemeId.menloNightBlue:
        return 'menlo_night_blue';
      case GteThemeId.aiArenaCrimson:
        return 'ai_arena_crimson';
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
