import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/gte_models.dart';

import '../models/gtex_regen_living_star.dart';
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

  /// `GET /api/players/{player_id}/regen` - the ownership half of the loop:
  /// contract phase, free agency, transfer listing, what the regen is
  /// agitating for, and the offer market around them.
  ///
  /// Returns null when the player has no regen lifecycle row, which is a real
  /// answer and not an error.
  Future<RegenLifecycleState?> fetchLifecycle(String playerId) async {
    final String id = playerId.trim();
    if (id.isEmpty) {
      return null;
    }
    try {
      final Map<String, dynamic> payload = await client.getMap(
        '/api/players/$id/regen',
        auth: false,
      );
      return RegenLifecycleState.fromJson(payload);
    } on GteApiException catch (error) {
      if (error.type == GteApiErrorType.notFound || error.statusCode == 404) {
        return null;
      }
      rethrow;
    }
  }

  /// `POST /api/players/{player_id}/regen/transfer-listing` - list or unlist
  /// a regen. Authenticated: this changes what other clubs can see.
  Future<RegenLifecycleState?> setTransferListing(
    String playerId, {
    required bool listed,
    String? reason,
  }) async {
    final Object? payload = await client.post(
      '/api/players/${playerId.trim()}/regen/transfer-listing',
      body: <String, Object?>{
        'listed': listed,
        if ((reason ?? '').trim().isNotEmpty) 'reason': reason!.trim(),
      },
    );
    return RegenLifecycleState.fromJson(payload);
  }

  /// `POST /api/players/{player_id}/regen/contract-offers/quote` - what an
  /// offer would cost, and whether the offering club can cover it.
  ///
  /// A quote is deliberately a separate step from making the offer: it is
  /// read-only in effect, so the shortfall is known before anything is
  /// committed.
  Future<RegenOfferQuote> quoteContractOffer(
    String playerId,
    GtexRegenOfferDraft draft,
  ) async {
    final Object? payload = await client.post(
      '/api/players/${playerId.trim()}/regen/contract-offers/quote',
      body: draft.toJson(),
    );
    return RegenOfferQuote.fromJson(payload);
  }

  /// Submit the canonical free-agent regen contract offer. The backend maps
  /// this into the existing transfer-bid/RegenContractOffer path, so no second
  /// offer engine is created. Repeating the same offer is replay-safe.
  Future<RegenLifecycleState?> submitContractOffer(
    String playerId,
    GtexRegenOfferDraft draft,
  ) async {
    final Object? payload = await client.post(
      '/api/players/${playerId.trim()}/regen/contract-offers/submit',
      body: draft.toJson(),
    );
    return RegenLifecycleState.fromJson(payload);
  }

  /// Open RegenContractOffer rows for clubs the signed-in owner controls.
  Future<List<Map<String, Object?>>> listContractOfferInbox() async {
    final List<dynamic> payload = await client.getList(
      '/api/regen/contract-offers/inbox',
    );
    return payload
        .whereType<Map>()
        .map((Map item) => Map<String, Object?>.from(item))
        .toList(growable: false);
  }

  /// Resolve the preferred regen bid for [playerId] in the active window.
  Future<void> resolveRegenBid(String playerId) async {
    final List<dynamic> windows = await client.getList(
      '/api/transfers/windows',
      query: <String, Object?>{'active_on': DateTime.now().toIso8601String().split('T').first},
    );
    if (windows.isEmpty) {
      throw StateError('No active transfer window is open for regen resolution.');
    }
    final Map<String, Object?> first = Map<String, Object?>.from(
      windows.first as Map,
    );
    final String windowId =
        (first['id'] ?? first['window_id'] ?? first['windowId'] ?? '')
            .toString()
            .trim();
    if (windowId.isEmpty) {
      throw StateError('Active transfer window id was missing.');
    }
    await client.post(
      '/api/transfers/windows/$windowId/players/${playerId.trim()}/resolve-regen-bid',
    );
  }

  /// `GET /api/players/{player_id}/living-star` — archetype, voice, mood, exit.
  Future<GtexRegenLivingStar?> fetchLivingStar(String playerId) async {
    final String id = playerId.trim();
    if (id.isEmpty) {
      return null;
    }
    try {
      final Map<String, dynamic> payload = await client.getMap(
        '/api/players/$id/living-star',
        auth: false,
      );
      return GtexRegenLivingStar.fromJson(payload);
    } on GteApiException catch (error) {
      if (error.type == GteApiErrorType.notFound || error.statusCode == 404) {
        return null;
      }
      rethrow;
    }
  }

  /// `POST /api/players/{player_id}/agency/exit-petition`.
  Future<GtexRegenLivingStar?> petitionExit(
    String playerId, {
    String? reason,
  }) async {
    final Object? payload = await client.post(
      '/api/players/${playerId.trim()}/agency/exit-petition',
      body: <String, Object?>{
        if ((reason ?? '').trim().isNotEmpty) 'reason': reason!.trim(),
      },
    );
    final Map<String, Object?> json = GteJson.map(
      payload,
      label: 'exit petition',
    );
    return GtexRegenLivingStar.fromJson(
      GteJson.value(json, const <String>['living_star', 'livingStar']) ??
          payload,
    );
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
