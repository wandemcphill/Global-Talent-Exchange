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
    _throwUnsupportedPlayerAction('scout');
  }

  Future<void> shortlist(String id) async {
    _throwUnsupportedPlayerAction('shortlist');
  }

  Future<void> contact(String id) async {
    _throwUnsupportedPlayerAction('contact');
  }

  Never _throwUnsupportedPlayerAction(String action) {
    throw GteApiException(
      type: GteApiErrorType.unavailable,
      message:
          'Player action "$action" is blocked because no live backend route is mounted for it.',
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
