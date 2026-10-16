import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/app/test_runtime_detector.dart';

import 'gte_api_repository.dart';
import 'gte_authed_api.dart';
import 'gte_http_transport.dart';

class PlayerCardWatchlistEntry {
  const PlayerCardWatchlistEntry({
    required this.id,
    required this.userId,
    this.playerId,
    this.playerCardId,
    this.notes,
    this.createdAt,
    this.updatedAt,
  });

  final String id;
  final String userId;
  final String? playerId;
  final String? playerCardId;
  final String? notes;
  final String? createdAt;
  final String? updatedAt;

  factory PlayerCardWatchlistEntry.fromJson(Map<String, dynamic> json) {
    return PlayerCardWatchlistEntry(
      id: (json['id'] ?? '').toString(),
      userId: (json['user_id'] ?? json['userId'] ?? '').toString(),
      playerId: json['player_id']?.toString() ?? json['playerId']?.toString(),
      playerCardId:
          json['player_card_id']?.toString() ?? json['playerCardId']?.toString(),
      notes: json['notes']?.toString(),
      createdAt: json['created_at']?.toString() ?? json['createdAt']?.toString(),
      updatedAt: json['updated_at']?.toString() ?? json['updatedAt']?.toString(),
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'id': id,
      'user_id': userId,
      'player_id': playerId,
      'player_card_id': playerCardId,
      'notes': notes,
      'created_at': createdAt,
      'updated_at': updatedAt,
    };
  }
}

abstract class PlayerCardWatchlistApi {
  Future<List<PlayerCardWatchlistEntry>> fetchWatchlist();
  Future<PlayerCardWatchlistEntry> addWatchlist({
    required String playerId,
    String? playerCardId,
    String? notes,
  });
  Future<void> removeWatchlist(String watchlistId);

  factory PlayerCardWatchlistApi.standard({
    required String baseUrl,
    String? accessToken,
    GteBackendMode mode = GteBackendMode.live,
    GteTransport? transport,
    GteAuthedApi? client,
  }) {
    final GteBackendMode resolvedMode = gteProductionBackendMode(mode);
    if (resolvedMode == GteBackendMode.fixture) {
      return FixturePlayerCardWatchlistApi();
    }
    return HttpPlayerCardWatchlistApi(
      client:
          client ??
          GteAuthedApi(
            config: GteRepositoryConfig(baseUrl: baseUrl, mode: resolvedMode),
            transport: transport ?? GteHttpTransport(),
            accessToken: accessToken,
            mode: resolvedMode,
          ),
    );
  }
}

class HttpPlayerCardWatchlistApi implements PlayerCardWatchlistApi {
  const HttpPlayerCardWatchlistApi({required this.client});

  final GteAuthedApi client;

  @override
  Future<List<PlayerCardWatchlistEntry>> fetchWatchlist() async {
    final List<dynamic> payload = await client.getList('/api/player-cards/watchlist');
    return payload
        .whereType<Map<String, dynamic>>()
        .map(PlayerCardWatchlistEntry.fromJson)
        .toList(growable: false);
  }

  @override
  Future<PlayerCardWatchlistEntry> addWatchlist({
    required String playerId,
    String? playerCardId,
    String? notes,
  }) async {
    final Object? response = await client.request(
      'POST',
      '/api/player-cards/watchlist',
      body: <String, dynamic>{
        'player_id': playerId,
        if (playerCardId != null) 'player_card_id': playerCardId,
        if (notes != null) 'notes': notes,
      },
    );
    if (response is Map<String, dynamic>) {
      return PlayerCardWatchlistEntry.fromJson(response);
    }
    if (response is Map) {
      return PlayerCardWatchlistEntry.fromJson(Map<String, dynamic>.from(response));
    }
    throw const FormatException('Invalid watchlist add response format');
  }

  @override
  Future<void> removeWatchlist(String watchlistId) async {
    await client.request('DELETE', '/api/player-cards/watchlist/$watchlistId');
  }
}

class FixturePlayerCardWatchlistApi implements PlayerCardWatchlistApi {
  FixturePlayerCardWatchlistApi();

  final List<PlayerCardWatchlistEntry> _items = <PlayerCardWatchlistEntry>[];

  @override
  Future<List<PlayerCardWatchlistEntry>> fetchWatchlist() async {
    return List<PlayerCardWatchlistEntry>.unmodifiable(_items);
  }

  @override
  Future<PlayerCardWatchlistEntry> addWatchlist({
    required String playerId,
    String? playerCardId,
    String? notes,
  }) async {
    final String id = 'fixture-watchlist-${_items.length + 1}';
    final PlayerCardWatchlistEntry entry = PlayerCardWatchlistEntry(
      id: id,
      userId: 'fixture-user',
      playerId: playerId,
      playerCardId: playerCardId,
      notes: notes,
      createdAt: DateTime.now().toIso8601String(),
      updatedAt: DateTime.now().toIso8601String(),
    );
    _items.removeWhere((PlayerCardWatchlistEntry item) => item.playerId == playerId);
    _items.add(entry);
    return entry;
  }

  @override
  Future<void> removeWatchlist(String watchlistId) async {
    _items.removeWhere((PlayerCardWatchlistEntry item) => item.id == watchlistId);
  }
}
