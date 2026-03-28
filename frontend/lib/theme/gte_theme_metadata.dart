import 'package:flutter/material.dart';

enum GteThemeId {
  neonVelocity,
  midnightGlass,
  auroraIntelligence,
  creatorGold,
  minimalCarbon,
}

extension GteThemeIdX on GteThemeId {
  String get storageKey {
    switch (this) {
      case GteThemeId.neonVelocity:
        return 'neon_velocity';
      case GteThemeId.midnightGlass:
        return 'midnight_glass';
      case GteThemeId.auroraIntelligence:
        return 'aurora_intelligence';
      case GteThemeId.creatorGold:
        return 'creator_gold';
      case GteThemeId.minimalCarbon:
        return 'minimal_carbon';
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
