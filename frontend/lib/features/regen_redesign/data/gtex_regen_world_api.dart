import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/gte_models.dart';

import '../models/gtex_regen_wire_models.dart';

/// Thrown when a regen has no dossier on the backend.
///
/// `GET /regen-universe/players/{id}` resolves through `RegenProfile`, so a
/// regen that exists only as a national-pool seed row genuinely has no
/// lineage, personality or development record. That is a real absence and the
/// world screen states it; it does not fall back to invented values.
class GtexRegenDossierUnavailable implements Exception {
  const GtexRegenDossierUnavailable(this.playerId);

  final String playerId;

  @override
  String toString() => 'No regen dossier is published for $playerId.';
}

/// The regen backend surfaces Phase 3 shipped but never called.
///
/// This is not a second networking system: it borrows the [GteAuthedApi] that
/// `RegenUniverseApi` already owns, so base url, auth, refresh and backend
/// mode all stay in one place. Phase 4 contract §4.4 puts regen networking in
/// this directory.
class GtexRegenWorldApi {
  const GtexRegenWorldApi({required this.client});

  final GteAuthedApi client;

  /// `GET /regen-universe/players/{player_id}` - profile (personality, origin,
  /// lineage, ability bands), prestige, legacy, latest value, timeline and
  /// achievements in one response.
  Future<RegenPlayerShowcase> fetchDossier(String playerId) async {
    final String id = playerId.trim();
    if (id.isEmpty) {
      throw const GtexRegenDossierUnavailable('');
    }
    try {
      final Map<String, dynamic> payload = await client.getMap(
        '/regen-universe/players/$id',
        auth: false,
      );
      return RegenPlayerShowcase.fromJson(payload);
    } on GteApiException catch (error) {
      if (error.type == GteApiErrorType.notFound || error.statusCode == 404) {
        throw GtexRegenDossierUnavailable(id);
      }
      rethrow;
    }
  }

  /// `GET /regens/{regen_id}/lineage` - the multi-generation chain, keyed by
  /// regen profile id rather than player id.
  Future<List<RegenLineageChainNode>> fetchLineageChain(
    String regenProfileId,
  ) async {
    final String id = regenProfileId.trim();
    if (id.isEmpty) {
      return const <RegenLineageChainNode>[];
    }
    final Map<String, dynamic> payload = await client.getMap(
      '/regens/$id/lineage',
      auth: false,
    );
    return GteJson.list(payload['chain'] ?? const <Object?>[])
        .map(RegenLineageChainNode.fromJson)
        .toList(growable: false);
  }

  /// `GET /regen-universe/bloodlines`.
  Future<List<RegenBloodlineChain>> listBloodlines({int limit = 12}) async {
    final Map<String, dynamic> payload = await client.getMap(
      '/regen-universe/bloodlines',
      query: <String, Object?>{'per_page': limit},
      auth: false,
    );
    return GteJson.list(payload['entries'] ?? const <Object?>[])
        .map(RegenBloodlineChain.fromJson)
        .toList(growable: false);
  }

  /// `GET /regen-universe/rankings`.
  Future<List<RegenRankingEntry>> listRankings({int limit = 20}) async {
    final Map<String, dynamic> payload = await client.getMap(
      '/regen-universe/rankings',
      query: <String, Object?>{'per_page': limit},
      auth: false,
    );
    return GteJson.list(payload['entries'] ?? const <Object?>[])
        .map(RegenRankingEntry.fromJson)
        .toList(growable: false);
  }

  /// `GET /regen-universe/hall-of-fame`.
  Future<List<RegenHallOfFameEntry>> listHallOfFame({int limit = 20}) async {
    final Map<String, dynamic> payload = await client.getMap(
      '/regen-universe/hall-of-fame',
      query: <String, Object?>{'per_page': limit},
      auth: false,
    );
    return GteJson.list(payload['entries'] ?? const <Object?>[])
        .map(RegenHallOfFameEntry.fromJson)
        .toList(growable: false);
  }
}
