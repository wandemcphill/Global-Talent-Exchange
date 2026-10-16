import 'package:flutter/foundation.dart';

enum AvatarMode { card, chip, lineup, hud, hudMinimal, profile }

@immutable
class PlayerAvatarSeedData {
  const PlayerAvatarSeedData({
    this.playerId,
    this.playerName,
    this.position,
    this.normalizedPosition,
    this.nationality,
    this.nationalityCode,
    this.birthYear,
    this.age,
    this.preferredFoot,
    this.avatarSeedToken,
    this.avatarDnaSeed,
    this.contextLabel,
  });

  final String? playerId;
  final String? playerName;
  final String? position;
  final String? normalizedPosition;
  final String? nationality;
  final String? nationalityCode;
  final int? birthYear;
  final int? age;
  final String? preferredFoot;
  final String? avatarSeedToken;
  final String? avatarDnaSeed;
  final String? contextLabel;
}

@immutable
class PlayerAvatar {
  const PlayerAvatar({
    required this.avatarVersion,
    required this.version,
    required this.seedToken,
    required this.dnaSeed,
    required this.skinTone,
    required this.hairStyle,
    required this.hairColor,
    required this.faceShape,
    required this.eyebrowStyle,
    required this.eyeType,
    required this.noseType,
    required this.mouthType,
    required this.beardStyle,
    required this.hasAccessory,
    required this.accessoryType,
    required this.jerseyStyle,
    required this.accentTone,
  });

  final int avatarVersion;
  final String version;
  final String seedToken;
  final int dnaSeed;
  final int skinTone;
  final int hairStyle;
  final int hairColor;
  final int faceShape;
  final int eyebrowStyle;
  final int eyeType;
  final int noseType;
  final int mouthType;
  final int beardStyle;
  final bool hasAccessory;
  final int accessoryType;
  final int jerseyStyle;
  final int accentTone;

  String get debugSummary =>
      'v$avatarVersion d$dnaSeed s$skinTone h$hairStyle/$hairColor '
      'f$faceShape b$beardStyle a$accessoryType';

  factory PlayerAvatar.fromJson(Map<String, Object?> json) {
    return PlayerAvatar(
      avatarVersion: _intValue(json['avatar_version'], fallback: 1),
      version: _stringValue(json['version'], fallback: 'fm_v1'),
      seedToken: _stringValue(json['seed_token']),
      dnaSeed: _intValue(json['dna_seed']),
      skinTone: _intValue(json['skin_tone']),
      hairStyle: _intValue(json['hair_style']),
      hairColor: _intValue(json['hair_color']),
      faceShape: _intValue(json['face_shape']),
      eyebrowStyle: _intValue(json['eyebrow_style']),
      eyeType: _intValue(json['eye_type']),
      noseType: _intValue(json['nose_type']),
      mouthType: _intValue(json['mouth_type']),
      beardStyle: _intValue(json['beard_style']),
      hasAccessory: _boolValue(json['has_accessory']),
      accessoryType: _intValue(json['accessory_type']),
      jerseyStyle: _intValue(json['jersey_style']),
      accentTone: _intValue(json['accent_tone']),
    );
  }

  static PlayerAvatar? fromJsonOrNull(Object? value) {
    if (value is! Map<Object?, Object?>) {
      return null;
    }
    final Map<String, Object?> normalized = <String, Object?>{};
    for (final MapEntry<Object?, Object?> entry in value.entries) {
      final Object? key = entry.key;
      if (key is String) {
        normalized[key] = entry.value;
      }
    }
    if (normalized.isEmpty) {
      return null;
    }
    return PlayerAvatar.fromJson(normalized);
  }

  Map<String, Object?> toJson() {
    return <String, Object?>{
      'avatar_version': avatarVersion,
      'version': version,
      'seed_token': seedToken,
      'dna_seed': dnaSeed,
      'skin_tone': skinTone,
      'hair_style': hairStyle,
      'hair_color': hairColor,
      'face_shape': faceShape,
      'eyebrow_style': eyebrowStyle,
      'eye_type': eyeType,
      'nose_type': noseType,
      'mouth_type': mouthType,
      'beard_style': beardStyle,
      'has_accessory': hasAccessory,
      'accessory_type': accessoryType,
      'jersey_style': jerseyStyle,
      'accent_tone': accentTone,
    };
  }

  static String _stringValue(Object? value, {String fallback = ''}) {
    final String text = value?.toString().trim() ?? '';
    return text.isEmpty ? fallback : text;
  }

  static int _intValue(Object? value, {int fallback = 0}) {
    if (value is int) {
      return value;
    }
    if (value is num) {
      return value.round();
    }
    return int.tryParse(value?.toString() ?? '') ?? fallback;
  }

  static bool _boolValue(Object? value, {bool fallback = false}) {
    if (value is bool) {
      return value;
    }
    if (value is num) {
      return value != 0;
    }
    final String normalized = value?.toString().trim().toLowerCase() ?? '';
    if (normalized == 'true') {
      return true;
    }
    if (normalized == 'false') {
      return false;
    }
    return fallback;
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is PlayerAvatar &&
            avatarVersion == other.avatarVersion &&
            version == other.version &&
            seedToken == other.seedToken &&
            dnaSeed == other.dnaSeed &&
            skinTone == other.skinTone &&
            hairStyle == other.hairStyle &&
            hairColor == other.hairColor &&
            faceShape == other.faceShape &&
            eyebrowStyle == other.eyebrowStyle &&
            eyeType == other.eyeType &&
            noseType == other.noseType &&
            mouthType == other.mouthType &&
            beardStyle == other.beardStyle &&
            hasAccessory == other.hasAccessory &&
            accessoryType == other.accessoryType &&
            jerseyStyle == other.jerseyStyle &&
            accentTone == other.accentTone;
  }

  @override
  int get hashCode => Object.hash(
        avatarVersion,
        version,
        seedToken,
        dnaSeed,
        skinTone,
        hairStyle,
        hairColor,
        faceShape,
        eyebrowStyle,
        eyeType,
        noseType,
        mouthType,
        beardStyle,
        hasAccessory,
        accessoryType,
        jerseyStyle,
        accentTone,
      );
}
