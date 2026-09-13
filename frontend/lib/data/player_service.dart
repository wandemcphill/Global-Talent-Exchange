import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/models/player.dart';

class PaginatedPlayers {
  const PaginatedPlayers({
    required this.players,
    required this.nextCursor,
    required this.hasMore,
  });

  final List<Player> players;
  final String? nextCursor;
  final bool hasMore;
}

class PlayerService {
  PlayerService({required GteAuthedApi client}) : _client = client;

  factory PlayerService.standard({
    required String baseUrl,
    String? accessToken,
    GteBackendMode mode = GteBackendMode.live,
  }) {
    return PlayerService(
      client: GteAuthedApi(
        config: GteRepositoryConfig(baseUrl: baseUrl, mode: mode),
        transport: GteHttpTransport(),
        accessToken: accessToken,
        mode: mode,
      ),
    );
  }

  final GteAuthedApi _client;

  Future<Player> getPlayer(String id) async {
    final Map<String, dynamic> payload = await _client.getMap(
      '/players/real-universe/$id',
      auth: false,
    );
    return Player.fromBackend(payload);
  }

  Future<PaginatedPlayers> getPlayers({
    String? cursor,
    String? search,
    String? position,
    String? country,
    String? nationality,
    int limit = 20,
    int? offset,
    int? minAge,
    int? maxAge,
    String? availability,
  }) async {
    final String trimmedSearch = search?.trim() ?? '';
    final String trimmedCursor = cursor?.trim() ?? '';
    final String? resolvedCountry =
        country?.trim().isNotEmpty == true
            ? country!.trim()
            : nationality?.trim();
    final Map<String, dynamic> payload = await _client.getMap(
      '/players',
      query: <String, Object?>{
        if (trimmedSearch.isNotEmpty) 'search': trimmedSearch,
        if (position != null && position.trim().isNotEmpty)
          'position': position.trim(),
        if (resolvedCountry != null && resolvedCountry.isNotEmpty)
          'country': resolvedCountry,
        if (minAge != null) 'min_age': minAge,
        if (maxAge != null) 'max_age': maxAge,
        if (availability != null && availability.trim().isNotEmpty)
          'availability': availability.trim(),
        if (trimmedCursor.isNotEmpty) 'cursor': trimmedCursor,
        if (trimmedCursor.isEmpty && offset != null && offset > 0)
          'offset': offset,
        'limit': limit,
      },
      auth: false,
    );
    final Map<String, Object?> json = Map<String, Object?>.from(payload);
    final List<Player> players = GteJson.list(
      GteJson.value(json, <String>['players', 'items']),
      label: 'players',
    ).map(Player.fromBackend).toList(growable: false);
    final int currentOffset =
        GteJson.integerOrNull(json, <String>['offset']) ??
        offset ??
        int.tryParse(trimmedCursor) ??
        0;
    final String? nextCursor = _resolveNextCursor(
      json,
      currentOffset: currentOffset,
      pageSize: players.length,
      requestedLimit: limit,
    );

    return PaginatedPlayers(
      players: players,
      nextCursor: nextCursor,
      hasMore: _resolveHasMore(json, nextCursor: nextCursor),
    );
  }

  Future<List<Player>> listPlayers({
    String? search,
    String? position,
    String? country,
    String? nationality,
    int limit = 20,
    int offset = 0,
    int? minAge,
    int? maxAge,
    String? availability,
  }) async {
    final PaginatedPlayers page = await getPlayers(
      search: search,
      position: position,
      country: country,
      nationality: nationality,
      limit: limit,
      offset: offset,
      minAge: minAge,
      maxAge: maxAge,
      availability: availability,
    );
    return page.players;
  }

  Future<void> scout(String id) async {
    final String playerId = id.trim();
    if (playerId.isEmpty) return;
    await _client.getMap('/api/scout/report/$playerId');
  }

  Future<void> shortlist(String id) async {
    await _ensurePlayerPipelineStatus(id.trim(), desiredStatus: 'shortlisted');
  }

  Future<void> contact(String id) async {
    await _ensurePlayerPipelineStatus(id.trim(), desiredStatus: 'contacted');
  }

  Future<void> _ensurePlayerPipelineStatus(
    String playerId, {
    required String desiredStatus,
  }) async {
    if (playerId.isEmpty) return;

    final Map<String, dynamic> shortlistsPayload = await _client.getMap(
      '/api/talent/shortlists',
      query: <String, Object?>{'include_entries': true},
    );
    final List<Object?> items = GteJson.list(
      shortlistsPayload['shortlists'] ?? const <Object?>[],
    );

    String? shortlistId;
    String? entryId;
    for (final Object? rawItem in items) {
      if (rawItem is! Map) continue;
      final Map<String, dynamic> shortlist = Map<String, dynamic>.from(rawItem);
      shortlistId ??= GteJson.stringOrNull(shortlist, <String>['id']);
      final List<Object?> entries = GteJson.list(
        shortlist['entries'] ?? const <Object?>[],
      );
      for (final Object? rawEntry in entries) {
        if (rawEntry is! Map) continue;
        final Map<String, dynamic> entry = Map<String, dynamic>.from(rawEntry);
        if (GteJson.stringOrNull(entry, <String>['player_id']) == playerId) {
          shortlistId = GteJson.stringOrNull(shortlist, <String>['id']);
          entryId = GteJson.stringOrNull(entry, <String>['id']);
          break;
        }
      }
      if (entryId != null) break;
    }

    if (shortlistId == null) {
      final Object? newShortlist = await _client.post(
        '/api/talent/shortlists',
        body: <String, Object?>{
          'name': 'Default Shortlist',
          'description': 'Main scouting shortlist',
        },
      );
      final Map<String, dynamic> created = Map<String, dynamic>.from(
        newShortlist as Map,
      );
      shortlistId = GteJson.stringOrNull(created, <String>['id']);
    }

    if (shortlistId == null) {
      throw StateError('Unable to resolve an authenticated scouting shortlist.');
    }

    if (entryId == null) {
      await _client.post(
        '/api/talent/shortlists/$shortlistId/entries',
        body: <String, Object?>{
          'player_id': playerId,
          'priority': 'medium',
          'status': desiredStatus,
          'note': 'Updated from player detail',
        },
      );
      return;
    }

    await _client.patch(
      '/api/talent/shortlists/$shortlistId/entries/$entryId',
      body: <String, Object?>{
        'status': desiredStatus,
        'note': 'Updated from player detail',
      },
    );
  }

  String? _resolveNextCursor(
    Map<String, Object?> json, {
    required int currentOffset,
    required int pageSize,
    required int requestedLimit,
  }) {
    final String? explicitCursor = GteJson.stringOrNull(json, <String>[
      'next_cursor',
      'nextCursor',
    ]);
    if (explicitCursor != null) {
      return explicitCursor;
    }

    final int? total = GteJson.integerOrNull(json, <String>['total']);
    if (total != null) {
      final int nextOffset = currentOffset + pageSize;
      return nextOffset < total ? nextOffset.toString() : null;
    }

    if (pageSize >= requestedLimit && pageSize > 0) {
      return (currentOffset + pageSize).toString();
    }
    return null;
  }

  bool _resolveHasMore(
    Map<String, Object?> json, {
    required String? nextCursor,
  }) {
    final Object? rawHasMore = GteJson.value(json, <String>[
      'has_more',
      'hasMore',
    ]);
    if (rawHasMore != null) {
      return GteJson.boolean(json, <String>['has_more', 'hasMore']);
    }
    return nextCursor != null;
  }
}
