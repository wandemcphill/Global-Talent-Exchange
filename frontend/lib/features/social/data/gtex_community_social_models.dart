import 'package:flutter/foundation.dart';

import '../../../data/gte_models.dart' show GteJson;

/// `SocialFollowView` from the existing `club_social` contract.
///
/// GTEX already models a follow as `(user, target_type, club_id|player_id)`
/// with a server-side unique `target_key`. Nothing here re-derives that key;
/// it is read back from the server so the client and the server can never
/// disagree about what is followed.
@immutable
class GtexSocialFollow {
  const GtexSocialFollow({
    required this.id,
    required this.targetKey,
    required this.targetType,
    this.clubId,
    this.playerId,
  });

  factory GtexSocialFollow.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value, label: 'social follow');
    return GtexSocialFollow(
      id: GteJson.string(json, const <String>['id']),
      targetKey: GteJson.string(json, const <String>[
        'target_key',
        'targetKey',
      ]),
      targetType: GteJson.string(json, const <String>[
        'target_type',
        'targetType',
      ]),
      clubId: GteJson.stringOrNull(json, const <String>['club_id', 'clubId']),
      playerId: GteJson.stringOrNull(json, const <String>[
        'player_id',
        'playerId',
      ]),
    );
  }

  final String id;
  final String targetKey;
  final String targetType;
  final String? clubId;
  final String? playerId;
}

/// `ChallengeCardView` from the existing `club_social` contract.
///
/// Only the fields that are literal counts or literal states are read.
/// `spectator_hype_score` is deliberately *not* modelled: it is a weighted
/// composite the backend computes for its own ranking, and rendering it as a
/// community number would be exactly the manufactured-popularity metric the
/// GTEX social rules forbid.
@immutable
class GtexClubChallengeCard {
  const GtexClubChallengeCard({
    required this.challengeId,
    required this.title,
    required this.issuingClubId,
    required this.issuingClubName,
    required this.status,
    this.opponentClubId,
    this.opponentClubName,
    this.stakesText,
    this.shareCount,
  });

  factory GtexClubChallengeCard.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'club challenge card',
    );
    return GtexClubChallengeCard(
      challengeId: GteJson.string(json, const <String>[
        'challenge_id',
        'challengeId',
      ]),
      title: GteJson.string(
        json,
        const <String>['title'],
        fallback: 'Club challenge',
      ),
      issuingClubId: GteJson.string(json, const <String>[
        'issuing_club_id',
        'issuingClubId',
      ]),
      issuingClubName: GteJson.string(
        json,
        const <String>['issuing_club_name', 'issuingClubName'],
        fallback: 'A club',
      ),
      status: GteJson.string(
        json,
        const <String>['status'],
        fallback: 'unknown',
      ),
      opponentClubId: GteJson.stringOrNull(json, const <String>[
        'opponent_club_id',
        'opponentClubId',
      ]),
      opponentClubName: GteJson.stringOrNull(json, const <String>[
        'opponent_club_name',
        'opponentClubName',
      ]),
      stakesText: GteJson.stringOrNull(json, const <String>[
        'stakes_text',
        'stakesText',
      ]),
      shareCount: _nullableInt(json, const <String>[
        'share_count',
        'shareCount',
      ]),
    );
  }

  final String challengeId;
  final String title;
  final String issuingClubId;
  final String issuingClubName;
  final String status;
  final String? opponentClubId;
  final String? opponentClubName;
  final String? stakesText;

  /// Real count of recorded share events, or `null` when the payload omitted
  /// it. A missing count is never rendered as `0 shares`.
  final int? shareCount;
}

int? _nullableInt(Map<String, Object?> json, List<String> keys) {
  for (final String key in keys) {
    final Object? value = json[key];
    if (value is int) {
      return value;
    }
    if (value is num) {
      return value.toInt();
    }
    if (value is String) {
      final int? parsed = int.tryParse(value.trim());
      if (parsed != null) {
        return parsed;
      }
    }
  }
  return null;
}
