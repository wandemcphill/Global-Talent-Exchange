import '../../../data/gte_authed_api.dart';
import 'gtex_community_social_models.dart';

/// Read/write client for the two `club_social` contracts GTEX already
/// publishes and nothing had ever called from Flutter.
///
/// Phase 4G adds no endpoint. `/api/social/follows` is already an
/// authenticated, server-idempotent upsert keyed on
/// `(user_id, target_key)` that validates the club or player exists, and
/// `/api/clubs/{club_id}/challenges` is already a public read of real club
/// challenge rows. Both are registered in `shared/api_contract.json`, so the
/// paths below resolve through `gteCanonicalApiPath` like every other call.
///
/// No composition, ordering or labelling happens here - this layer only
/// speaks HTTP, so the presentation rules stay in one testable place.
class GtexCommunitySocialApi {
  const GtexCommunitySocialApi({required this.client});

  final GteAuthedApi client;

  /// The signed-in user's own follows. Authenticated: the server resolves the
  /// owner from the token, so a client can never read another user's follows.
  Future<List<GtexSocialFollow>> listMyFollows() async {
    final Map<String, dynamic> payload = await client.getMap(
      '/api/social/follows/me',
    );
    final Object? raw = payload['follows'];
    if (raw is! List) {
      return const <GtexSocialFollow>[];
    }
    return raw
        .map(GtexSocialFollow.fromJson)
        .toList(growable: false);
  }

  /// Follows a football object.
  ///
  /// Safe to repeat: the server upserts on `(user_id, target_key)` rather
  /// than inserting, so a double tap or a retried request produces one row,
  /// not two. Nothing is credited for a follow, so there is no reward to
  /// duplicate either.
  Future<GtexSocialFollow> follow({
    required String targetType,
    String? clubId,
    String? playerId,
  }) async {
    final Object? payload = await client.post(
      '/api/social/follows',
      body: <String, Object?>{
        'target_type': targetType,
        'club_id': clubId,
        'player_id': playerId,
        'metadata_json': const <String, Object?>{},
      },
    );
    return GtexSocialFollow.fromJson(payload);
  }

  /// Unfollows a football object. Also idempotent server-side.
  Future<void> unfollow({
    required String targetType,
    String? clubId,
    String? playerId,
  }) async {
    await client.request(
      'DELETE',
      '/api/social/follows',
      body: <String, Object?>{
        'target_type': targetType,
        'club_id': clubId,
        'player_id': playerId,
        'metadata_json': const <String, Object?>{},
      },
    );
  }

  /// Real challenge cards issued or accepted by one club.
  ///
  /// A public read: the community surface must be able to name club challenge
  /// activity without asking for a club-owner session it does not have.
  Future<List<GtexClubChallengeCard>> listClubChallenges(
    String clubId, {
    String direction = 'all',
  }) async {
    final Map<String, dynamic> payload = await client.getMap(
      '/api/clubs/$clubId/challenges',
      query: <String, Object?>{'direction': direction},
      auth: false,
    );
    final Object? raw = payload['challenges'];
    if (raw is! List) {
      return const <GtexClubChallengeCard>[];
    }
    return raw
        .map(GtexClubChallengeCard.fromJson)
        .toList(growable: false);
  }
}
