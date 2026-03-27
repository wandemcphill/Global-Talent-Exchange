import 'package:gte_frontend/data/match/match_dto.dart';
import 'package:gte_frontend/domain/match/match_result.dart';
import 'package:gte_frontend/models/player.dart';

class MatchMapper {
  const MatchMapper._();

  static MatchResult toDomain(MatchItemDto dto) {
    return MatchResult(
      player: Player.fromBackend(dto.player),
      score: dto.score,
      reasons: _mapReasons(dto.reasons),
      breakdown: _mapBreakdown(dto.scoreBreakdown),
      flags: _mapFlags(dto),
      preferredFoot: _mapPreferredFoot(dto.player),
      heightMeters: _mapHeightMeters(dto.player),
    );
  }

  static List<String> _mapReasons(List<ReasonDto> reasons) {
    return reasons
        .map((ReasonDto reason) => reason.label.trim())
        .where((String label) => label.isNotEmpty)
        .toList(growable: false);
  }

  static Map<String, double> _mapBreakdown(Map<String, dynamic> raw) {
    final Map<String, double> breakdown = <String, double>{};
    raw.forEach((String key, dynamic value) {
      if (value is num) {
        breakdown[key] = value.toDouble();
      }
    });
    return breakdown;
  }

  static MatchFlags _mapFlags(MatchItemDto dto) {
    final Map<String, dynamic>? flags = dto.flags;
    final List<String> normalizedReasons = _mapReasons(dto.reasons)
        .map((String reason) => reason.trim().toLowerCase())
        .toList(growable: false);
    final bool isFreeAgent =
        flags?['is_free_agent'] == true || dto.player['is_free_agent'] == true;
    final bool isExactPosition = flags?['is_exact_position'] == true ||
        normalizedReasons.contains('perfect position match');
    final bool isHighPotential = flags?['is_high_potential'] == true;
    return MatchFlags(
      isFreeAgent: isFreeAgent,
      isExactPosition: isExactPosition,
      isHighPotential: isHighPotential,
    );
  }

  static String? _mapPreferredFoot(Map<String, dynamic> player) {
    return _asString(
      player['dominant_foot'] ??
          player['preferred_foot'] ??
          player['preferredFoot'],
    );
  }

  static double? _mapHeightMeters(Map<String, dynamic> player) {
    final Object? rawHeight = player['height_meters'] ??
        player['heightMeters'] ??
        player['height_cm'];
    if (rawHeight is num) {
      final double value = rawHeight.toDouble();
      return value > 10 ? value / 100 : value;
    }
    if (rawHeight is String) {
      final double? value = double.tryParse(rawHeight.trim());
      if (value == null) {
        return null;
      }
      return value > 10 ? value / 100 : value;
    }
    return null;
  }

  static String? _asString(Object? value) {
    if (value == null) {
      return null;
    }
    final String text = value.toString().trim();
    return text.isEmpty ? null : text;
  }
}
