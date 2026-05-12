import 'dart:async';
import 'dart:convert';
import 'dart:math' as math;

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/gte_app_config.dart';
import '../../data/gte_api_repository.dart';
import '../../data/gte_authed_api.dart';
import '../../data/gte_http_transport.dart';
import '../../services/reliability/reliable_websocket_manager.dart';
import '../models/player.dart';
import 'auth_provider.dart';

enum TransferMarketFilter {
  all,
  forwards,
  midfielders,
  defenders,
  goalkeepers,
  trending,
}

extension TransferMarketFilterLabel on TransferMarketFilter {
  String get label {
    return switch (this) {
      TransferMarketFilter.all => 'All',
      TransferMarketFilter.forwards => 'Forwards',
      TransferMarketFilter.midfielders => 'Midfield',
      TransferMarketFilter.defenders => 'Defense',
      TransferMarketFilter.goalkeepers => 'Goalkeepers',
      TransferMarketFilter.trending => 'Trending',
    };
  }
}

class MarketBidEntry {
  const MarketBidEntry({
    required this.clubName,
    required this.amountInMillions,
    required this.isUser,
    required this.tick,
  });

  final String clubName;
  final double amountInMillions;
  final bool isUser;
  final int tick;
}

class TransferMarketListing {
  const TransferMarketListing({
    required this.id,
    required this.player,
    required this.currentBidInMillions,
    required this.secondsRemaining,
    required this.minimumIncrementInMillions,
    required this.watcherCount,
    required this.bidHistory,
    this.status = 'open',
    this.channel,
  });

  final String id;
  final Player player;
  final double currentBidInMillions;
  final int secondsRemaining;
  final double minimumIncrementInMillions;
  final int watcherCount;
  final List<MarketBidEntry> bidHistory;
  final String status;
  final String? channel;

  MarketBidEntry get leadingBidder {
    if (bidHistory.isEmpty) {
      return const MarketBidEntry(
        clubName: 'Opening bid',
        amountInMillions: 0,
        isUser: false,
        tick: 0,
      );
    }
    return bidHistory.reduce(
      (MarketBidEntry current, MarketBidEntry next) =>
          next.amountInMillions > current.amountInMillions ? next : current,
    );
  }

  bool get userIsHighestBidder => leadingBidder.isUser;

  bool matchesFilter(TransferMarketFilter filter) {
    return switch (filter) {
      TransferMarketFilter.all => true,
      TransferMarketFilter.forwards => <String>{
        'ST',
        'RW',
        'LW',
        'CF',
      }.contains(player.position),
      TransferMarketFilter.midfielders => <String>{
        'CAM',
        'CM',
        'CDM',
        'DM',
      }.contains(player.position),
      TransferMarketFilter.defenders => <String>{
        'CB',
        'LB',
        'RB',
        'LWB',
        'RWB',
      }.contains(player.position),
      TransferMarketFilter.goalkeepers => player.position == 'GK',
      TransferMarketFilter.trending => player.isHot || watcherCount >= 20,
    };
  }

  TransferMarketListing copyWith({
    Player? player,
    double? currentBidInMillions,
    int? secondsRemaining,
    double? minimumIncrementInMillions,
    int? watcherCount,
    List<MarketBidEntry>? bidHistory,
    String? status,
    String? channel,
  }) {
    return TransferMarketListing(
      id: id,
      player: player ?? this.player,
      currentBidInMillions: currentBidInMillions ?? this.currentBidInMillions,
      secondsRemaining: secondsRemaining ?? this.secondsRemaining,
      minimumIncrementInMillions:
          minimumIncrementInMillions ?? this.minimumIncrementInMillions,
      watcherCount: watcherCount ?? this.watcherCount,
      bidHistory: bidHistory ?? this.bidHistory,
      status: status ?? this.status,
      channel: channel ?? this.channel,
    );
  }
}

class TransferMarketState {
  const TransferMarketState({
    required this.players,
    required this.listings,
    required this.searchQuery,
    required this.shortlistedIds,
    required this.activeFilter,
    required this.simulationTick,
  });

  final List<Player> players;
  final List<TransferMarketListing> listings;
  final String searchQuery;
  final Set<String> shortlistedIds;
  final TransferMarketFilter activeFilter;
  final int simulationTick;

  List<TransferMarketListing> get filteredListings {
    final String query = searchQuery.trim().toLowerCase();
    return listings
        .where((TransferMarketListing listing) {
          if (!listing.matchesFilter(activeFilter)) {
            return false;
          }
          if (query.isEmpty) {
            return true;
          }
          final String haystack =
              <String>[
                listing.player.name,
                listing.player.position,
                listing.player.country,
                listing.leadingBidder.clubName,
              ].join(' ').toLowerCase();
          return haystack.contains(query);
        })
        .toList(growable: false);
  }

  List<Player> get filteredPlayers {
    return filteredListings
        .map((TransferMarketListing listing) => listing.player)
        .toList(growable: false);
  }

  TransferMarketListing? listingFor(String playerId) {
    for (final TransferMarketListing listing in listings) {
      if (listing.player.id == playerId) {
        return listing;
      }
    }
    return null;
  }

  TransferMarketState copyWith({
    List<Player>? players,
    List<TransferMarketListing>? listings,
    String? searchQuery,
    Set<String>? shortlistedIds,
    TransferMarketFilter? activeFilter,
    int? simulationTick,
  }) {
    return TransferMarketState(
      players: players ?? this.players,
      listings: listings ?? this.listings,
      searchQuery: searchQuery ?? this.searchQuery,
      shortlistedIds: shortlistedIds ?? this.shortlistedIds,
      activeFilter: activeFilter ?? this.activeFilter,
      simulationTick: simulationTick ?? this.simulationTick,
    );
  }
}

class TransferMarketNotifier extends Notifier<TransferMarketState> {
  static const List<String> _rivalClubs = <String>[
    'North Star FC',
    'Atlas Capital',
    'Blue Coast SC',
    'Emerald Union',
    'Metro Sporting',
  ];

  static const String _fallbackUserClubName = 'GTEX United';
  static const Duration _refreshInterval = Duration(seconds: 20);

  final GteAppConfig _config = GteAppConfig.fromRuntimeEnvironment();
  late final GteBackendMode _backendMode = _config.activeShellBackendMode;
  final Map<String, ReliableWebSocketManager> _listingStreams =
      <String, ReliableWebSocketManager>{};
  final Map<String, StreamSubscription<dynamic>> _listingSubscriptions =
      <String, StreamSubscription<dynamic>>{};

  late final GteRepositoryConfig _repositoryConfig = GteRepositoryConfig(
    baseUrl: _config.apiBaseUrl,
    mode: _backendMode,
  );
  late final GteHttpTransport _transport = GteHttpTransport(
    connectionTimeout: const Duration(seconds: 2),
  );

  Timer? _refreshTimer;
  bool _disposed = false;
  bool _refreshInFlight = false;
  bool _liveSyncStarted = false;
  bool _usesLiveListings = false;

  String get _userClubName {
    try {
      final String clubName =
          ref.read(authPresentationProvider).clubName.trim();
      return clubName.isEmpty ? _fallbackUserClubName : clubName;
    } catch (_) {
      return _fallbackUserClubName;
    }
  }

  @override
  TransferMarketState build() {
    final TransferMarketState initialState =
        _backendMode == GteBackendMode.fixture
            ? _buildFixtureState()
            : _buildEmptyState();
    ref.onDispose(() {
      _disposed = true;
      _refreshTimer?.cancel();
      for (final StreamSubscription<dynamic> subscription
          in _listingSubscriptions.values) {
        unawaited(subscription.cancel());
      }
      _listingSubscriptions.clear();
      for (final ReliableWebSocketManager manager in _listingStreams.values) {
        unawaited(manager.dispose());
      }
      _listingStreams.clear();
    });
    if (_shouldEnableLiveSync()) {
      _startLiveSync();
    }
    return initialState;
  }

  TransferMarketState _buildEmptyState() {
    return const TransferMarketState(
      players: <Player>[],
      listings: <TransferMarketListing>[],
      searchQuery: '',
      shortlistedIds: <String>{},
      activeFilter: TransferMarketFilter.all,
      simulationTick: 0,
    );
  }

  void setSearchQuery(String value) {
    state = state.copyWith(searchQuery: value);
  }

  void setFilter(TransferMarketFilter filter) {
    state = state.copyWith(activeFilter: filter);
  }

  void toggleShortlist(String playerId) {
    final Set<String> next = <String>{...state.shortlistedIds};
    final bool added = next.add(playerId);
    if (!added) {
      next.remove(playerId);
    }
    state = state.copyWith(shortlistedIds: next);
    if (added && _usesLiveListings) {
      unawaited(_submitWatchlistEntry(playerId));
    }
  }

  double minimumBidFor(String playerId) {
    final TransferMarketListing? listing = state.listingFor(playerId);
    if (listing == null) {
      return 0;
    }
    return _roundBid(
      listing.currentBidInMillions + listing.minimumIncrementInMillions,
    );
  }

  double placeBid(String playerId, double amountInMillions) {
    final TransferMarketListing? listing = state.listingFor(playerId);
    if (listing == null) {
      return 0;
    }

    final double placedBid = _roundBid(
      math.max(amountInMillions, minimumBidFor(playerId)),
    );

    final List<TransferMarketListing> updatedListings = state.listings
        .map((TransferMarketListing current) {
          if (current.player.id != playerId) {
            return current;
          }

          final List<MarketBidEntry> nextHistory = <MarketBidEntry>[
            ...current.bidHistory,
            MarketBidEntry(
              clubName: _userClubName,
              amountInMillions: placedBid,
              isUser: true,
              tick: state.simulationTick,
            ),
          ];

          return current.copyWith(
            currentBidInMillions: placedBid,
            bidHistory: nextHistory,
            secondsRemaining: math.max(current.secondsRemaining, 20),
            watcherCount: current.watcherCount + 2,
          );
        })
        .toList(growable: false);

    final Set<String> nextShortlist = <String>{
      ...state.shortlistedIds,
      playerId,
    };

    _replaceListings(updatedListings, shortlistedIds: nextShortlist);

    return placedBid;
  }

  Future<double?> submitBid(String playerId, double amountInMillions) async {
    if (!_usesLiveListings || !_shouldEnableLiveSync()) {
      return placeBid(playerId, amountInMillions);
    }
    final TransferMarketListing? listing = state.listingFor(playerId);
    if (listing == null) {
      return null;
    }
    final double placedBid = _roundBid(
      math.max(amountInMillions, minimumBidFor(playerId)),
    );
    try {
      final Object? payload = await _api().post(
        '/api/transfer-market/listings/${listing.id}/bids',
        body: <String, Object?>{'amount': placedBid},
      );
      if (_disposed) {
        return null;
      }
      final TransferMarketListing updated = _listingFromPayload(payload);
      _upsertListing(updated);
      _syncListingStreams(state.listings);
      return updated.currentBidInMillions;
    } catch (_) {
      return null;
    }
  }

  void tickSimulation() {
    if (_usesLiveListings) {
      return;
    }
    final int nextTick = state.simulationTick + 1;
    final List<TransferMarketListing> nextListings = state.listings
        .asMap()
        .entries
        .map((MapEntry<int, TransferMarketListing> entry) {
          return _advanceListing(
            listing: entry.value,
            index: entry.key,
            nextTick: nextTick,
          );
        })
        .toList(growable: false);

    _replaceListings(nextListings, simulationTick: nextTick);
  }

  TransferMarketState _buildFixtureState() {
    const List<Player> players = <Player>[
      Player(
        id: 'market-onana',
        name: 'Samuel Onana',
        position: 'CAM',
        country: 'Cameroon',
        age: 21,
        rating: 83,
        potential: 88,
        valueInMillions: 34,
        pace: 0.81,
        technique: 0.89,
        mentality: 0.78,
        image: 'assets/branding/gtex_icon.png',
        isHot: true,
      ),
      Player(
        id: 'market-diallo',
        name: 'Moussa Diallo',
        position: 'CB',
        country: 'Senegal',
        age: 22,
        rating: 82,
        potential: 87,
        valueInMillions: 28,
        pace: 0.74,
        technique: 0.72,
        mentality: 0.86,
        image: 'assets/branding/gtex_icon.png',
      ),
      Player(
        id: 'market-okoro',
        name: 'Daniel Okoro',
        position: 'ST',
        country: 'Nigeria',
        age: 20,
        rating: 84,
        potential: 90,
        valueInMillions: 39,
        pace: 0.88,
        technique: 0.84,
        mentality: 0.8,
        image: 'assets/branding/gtex_icon.png',
        isHot: true,
      ),
      Player(
        id: 'market-zerhouni',
        name: 'Yanis Zerhouni',
        position: 'RW',
        country: 'Morocco',
        age: 19,
        rating: 80,
        potential: 89,
        valueInMillions: 24,
        pace: 0.9,
        technique: 0.86,
        mentality: 0.72,
        image: 'assets/branding/gtex_icon.png',
      ),
      Player(
        id: 'market-kiplimo',
        name: 'Victor Kiplimo',
        position: 'LB',
        country: 'Kenya',
        age: 23,
        rating: 79,
        potential: 84,
        valueInMillions: 18,
        pace: 0.82,
        technique: 0.75,
        mentality: 0.79,
        image: 'assets/branding/gtex_icon.png',
      ),
      Player(
        id: 'market-zuma',
        name: 'Lebo Zuma',
        position: 'GK',
        country: 'South Africa',
        age: 24,
        rating: 81,
        potential: 85,
        valueInMillions: 22,
        pace: 0.58,
        technique: 0.69,
        mentality: 0.88,
        image: 'assets/branding/gtex_icon.png',
      ),
    ];

    return TransferMarketState(
      players: players,
      listings: _buildInitialListings(players),
      searchQuery: '',
      shortlistedIds: const <String>{},
      activeFilter: TransferMarketFilter.all,
      simulationTick: 0,
    );
  }

  void _startLiveSync() {
    if (_liveSyncStarted) {
      return;
    }
    _liveSyncStarted = true;
    unawaited(_refreshLiveListings());
    _refreshTimer = Timer.periodic(
      _refreshInterval,
      (_) => unawaited(_refreshLiveListings()),
    );
  }

  bool _shouldEnableLiveSync() {
    if (_backendMode == GteBackendMode.fixture) {
      return false;
    }
    try {
      ref.read(deviceIdProvider);
      return true;
    } catch (_) {
      return false;
    }
  }

  GteAuthedApi _api() {
    String? deviceId;
    try {
      deviceId = ref.read(deviceIdProvider);
    } catch (_) {
      deviceId = null;
    }
    return GteAuthedApi(
      config: _repositoryConfig,
      transport: _transport,
      authSession: ref.read(authProvider),
      deviceId: deviceId,
      mode: _backendMode,
    );
  }

  Future<void> _refreshLiveListings() async {
    if (_disposed || _refreshInFlight) {
      return;
    }
    _refreshInFlight = true;
    try {
      final List<dynamic> payload = await _api().getList(
        '/api/transfer-market/listings',
        auth: false,
      );
      if (_disposed) {
        return;
      }
      final List<TransferMarketListing> liveListings = payload
          .map(_listingFromPayload)
          .toList(growable: false);
      _usesLiveListings = true;
      _replaceListings(liveListings);
      _syncListingStreams(liveListings);
    } catch (_) {
      if (!_usesLiveListings) {
        _syncListingStreams(const <TransferMarketListing>[]);
      }
    } finally {
      _refreshInFlight = false;
    }
  }

  void _replaceListings(
    List<TransferMarketListing> listings, {
    Set<String>? shortlistedIds,
    int? simulationTick,
  }) {
    state = state.copyWith(
      players: _playersFromListings(listings),
      listings: List<TransferMarketListing>.unmodifiable(listings),
      shortlistedIds: shortlistedIds,
      simulationTick: simulationTick,
    );
  }

  void _upsertListing(TransferMarketListing listing) {
    final List<TransferMarketListing> nextListings =
        List<TransferMarketListing>.from(state.listings);
    final int index = nextListings.indexWhere(
      (TransferMarketListing current) => current.id == listing.id,
    );
    if (index >= 0) {
      nextListings[index] = listing;
    } else {
      nextListings.add(listing);
    }
    _replaceListings(nextListings);
  }

  List<Player> _playersFromListings(List<TransferMarketListing> listings) {
    return listings
        .map((TransferMarketListing listing) => listing.player)
        .toList(growable: false);
  }

  void _syncListingStreams(List<TransferMarketListing> listings) {
    final Set<String> desiredIds =
        listings.map((TransferMarketListing listing) => listing.id).toSet();
    final Set<String> existingIds = _listingStreams.keys.toSet();

    for (final String staleId in existingIds.difference(desiredIds)) {
      final StreamSubscription<dynamic>? subscription = _listingSubscriptions
          .remove(staleId);
      final ReliableWebSocketManager? manager = _listingStreams.remove(staleId);
      unawaited(subscription?.cancel());
      unawaited(manager?.dispose());
    }

    for (final TransferMarketListing listing in listings) {
      if (_listingStreams.containsKey(listing.id)) {
        continue;
      }
      final Uri? socketUri = _resolveWebSocketUri(
        '/api/transfer-market/listings/${listing.id}/stream',
      );
      if (socketUri == null) {
        continue;
      }
      final ReliableWebSocketManager manager = ReliableWebSocketManager(
        socketUri: socketUri,
        onConnectionRestored: () => unawaited(_refreshLiveListings()),
      );
      _listingStreams[listing.id] = manager;
      _listingSubscriptions[listing.id] = manager.messages.listen(
        (dynamic message) => _consumeLiveListingMessage(listing.id, message),
        onError: (_) {},
      );
      manager.connect();
    }
  }

  void _consumeLiveListingMessage(String listingId, dynamic message) {
    final Map<String, Object?>? envelope = _decodeMessage(message);
    if (envelope == null) {
      return;
    }
    final String kind = _stringValue(envelope['kind']).toLowerCase();
    final Map<String, Object?> payload = _mapValue(envelope['payload']);
    switch (kind) {
      case 'timer':
        final int timeRemaining = _intValue(
          payload['time_remaining'],
          fallback: _intValue(payload['timeRemaining']),
        );
        final String status = _stringValue(payload['status']);
        _updateListing(
          listingId,
          (TransferMarketListing current) => current.copyWith(
            secondsRemaining: timeRemaining,
            status: status.isEmpty ? current.status : status,
          ),
        );
        return;
      case 'snapshot':
        final TransferMarketListing snapshot = _listingFromPayload(payload);
        _upsertListing(snapshot);
        return;
      case 'events':
        final List<Object?> events = _listValue(envelope['payload']);
        for (final Object? event in events) {
          _applyLiveEvent(listingId, _mapValue(event));
        }
        return;
      default:
        return;
    }
  }

  void _applyLiveEvent(String listingId, Map<String, Object?> event) {
    final String eventType = _stringValue(event['event_type']).toLowerCase();
    final Map<String, Object?> payload = _mapValue(event['payload']);
    final int eventTick =
        _dateTimeValue(event['created_at'])?.millisecondsSinceEpoch ??
        DateTime.now().millisecondsSinceEpoch;

    switch (eventType) {
      case 'new_bid':
        _updateListing(listingId, (TransferMarketListing current) {
          final double nextAmount = _roundBid(
            _doubleValue(
              payload['amount'],
              fallback: current.currentBidInMillions,
            ),
          );
          final int nextSeconds = _intValue(
            payload['time_remaining'],
            fallback: current.secondsRemaining,
          );
          final String clubName = _stringValue(
            payload['bidder_club_name'],
            fallback: 'Live bidder',
          );
          final List<MarketBidEntry> nextHistory =
              _dedupeBidHistory(<MarketBidEntry>[
                ...current.bidHistory,
                MarketBidEntry(
                  clubName: clubName,
                  amountInMillions: nextAmount,
                  isUser: clubName == _userClubName,
                  tick: eventTick,
                ),
              ]);
          return current.copyWith(
            currentBidInMillions: nextAmount,
            secondsRemaining: nextSeconds,
            bidHistory: nextHistory,
          );
        });
        return;
      case 'auction_extended':
        _updateListing(
          listingId,
          (TransferMarketListing current) => current.copyWith(
            secondsRemaining: _intValue(
              payload['time_remaining'],
              fallback: current.secondsRemaining,
            ),
          ),
        );
        return;
      case 'auction_closed':
        _updateListing(
          listingId,
          (TransferMarketListing current) => current.copyWith(
            currentBidInMillions: _roundBid(
              _doubleValue(
                payload['current_highest_bid'],
                fallback: current.currentBidInMillions,
              ),
            ),
            secondsRemaining: 0,
            status: _stringValue(payload['status'], fallback: current.status),
          ),
        );
        return;
      case 'negotiation_updated':
      case 'negotiation_timer_processed':
      case 'agent_timer_processed':
        _updateListing(
          listingId,
          (TransferMarketListing current) => current.copyWith(
            status: _stringValue(payload['status'], fallback: current.status),
          ),
        );
        return;
      default:
        return;
    }
  }

  void _updateListing(
    String listingId,
    TransferMarketListing Function(TransferMarketListing current) updater,
  ) {
    final int index = state.listings.indexWhere(
      (TransferMarketListing current) => current.id == listingId,
    );
    if (index < 0) {
      return;
    }
    final List<TransferMarketListing> nextListings =
        List<TransferMarketListing>.from(state.listings);
    nextListings[index] = updater(nextListings[index]);
    _replaceListings(nextListings);
  }

  Future<void> _submitWatchlistEntry(String playerId) async {
    final TransferMarketListing? listing = state.listingFor(playerId);
    if (listing == null) {
      return;
    }
    try {
      await _api().post(
        '/api/transfer-market/watchlist',
        body: <String, Object?>{
          'player_id': listing.player.id,
          'source': 'ui_shortlist',
        },
      );
    } catch (_) {}
  }

  Uri? _resolveWebSocketUri(String websocketPath) {
    final String trimmedPath = websocketPath.trim();
    if (trimmedPath.isEmpty) {
      return null;
    }
    final Uri? base = Uri.tryParse(_config.apiBaseUrl);
    if (base == null || !base.hasScheme || base.host.trim().isEmpty) {
      return null;
    }
    final String scheme = switch (base.scheme) {
      'https' => 'wss',
      'http' => 'ws',
      'ws' || 'wss' => base.scheme,
      _ => 'wss',
    };
    final Uri resolved = Uri.parse(trimmedPath);
    if (resolved.hasScheme) {
      return resolved;
    }
    return base.replace(
      scheme: scheme,
      path: resolved.path,
      query: resolved.hasQuery ? resolved.query : null,
    );
  }

  TransferMarketListing _listingFromPayload(Object? value) {
    final Map<String, Object?> json = _mapValue(value);
    final Map<String, Object?> playerPayload = _mapValue(json['player']);
    final String listingId = _stringValue(
      json['id'],
      fallback: _stringValue(
        json['player_id'],
        fallback: 'transfer-listing-${state.listings.length}',
      ),
    );
    final double currentBid = _roundBid(
      _doubleValue(
        json['current_highest_bid'],
        fallback: _doubleValue(json['base_price']),
      ),
    );
    final double referencePrice =
        currentBid > 0
            ? currentBid
            : _roundBid(_doubleValue(json['base_price']));
    final int watchlistCount = _intValue(json['watchlist_count']);
    final int bidCount = _intValue(
      json['bid_count'],
      fallback: _listValue(json['bidders']).length,
    );
    final String marketSignal = _stringValue(json['market_signal']);
    final Player player = _playerFromPayload(
      playerPayload,
      listingId: listingId,
      fallbackValueInMillions: referencePrice,
      isHot:
          watchlistCount >= 10 ||
          bidCount >= 3 ||
          marketSignal.toLowerCase().contains('hot') ||
          marketSignal.toLowerCase().contains('surge'),
    );
    final List<MarketBidEntry> bidHistory = _bidHistoryFromPayload(
      json,
      playerPayload,
      fallbackAmount: referencePrice,
    );

    return TransferMarketListing(
      id: listingId,
      player: player,
      currentBidInMillions: currentBid,
      secondsRemaining: _intValue(
        json['time_remaining'],
        fallback: _secondsUntil(_dateTimeValue(json['expires_at'])),
      ),
      minimumIncrementInMillions: 0.1,
      watcherCount: watchlistCount,
      bidHistory: bidHistory,
      status: _stringValue(json['status'], fallback: 'open'),
      channel: _stringOrNull(json['channel']),
    );
  }

  Player _playerFromPayload(
    Map<String, Object?> payload, {
    required String listingId,
    required double fallbackValueInMillions,
    required bool isHot,
  }) {
    final String playerId = _stringValue(
      payload['id'],
      fallback: 'player-$listingId',
    );
    final String fullName = _stringValue(
      payload['full_name'],
      fallback: 'Transfer Target',
    );
    final String position = _normalizePosition(
      _stringValue(payload['normalized_position'], fallback: 'N/A'),
    );
    final int seed = _stableSeed('$playerId|$fullName|$position');
    final int rating =
        (72 + (seed % 11) + (fallbackValueInMillions ~/ 18))
            .clamp(70, 92)
            .toInt();
    final int? globalScoutingIndex =
        _intOrNullFromKeys(payload, _gsiKeys) ??
        _intOrNullFromKeys(_mapValue(payload['summary_json']), _gsiKeys) ??
        _intOrNullFromKeys(_mapValue(payload['summaryJson']), _gsiKeys) ??
        _intOrNullFromKeys(_mapValue(payload['metadata_json']), _gsiKeys) ??
        _intOrNullFromKeys(_mapValue(payload['metadataJson']), _gsiKeys);
    final int potential = (rating + 4 + (seed % 6)).clamp(rating, 95).toInt();
    final int age = (18 + (seed % 11)).clamp(18, 34).toInt();

    return Player(
      id: playerId,
      name: fullName,
      position: position,
      country: _stringValue(
        payload['current_club_name'],
        fallback: 'Open Market',
      ),
      age: age,
      rating: rating,
      potential: potential,
      valueInMillions:
          fallbackValueInMillions <= 0 ? 1 : fallbackValueInMillions,
      pace: _metricFromSeed(seed, 0),
      technique: _metricFromSeed(seed, 1),
      mentality: _metricFromSeed(seed, 2),
      image: 'assets/branding/gtex_icon.png',
      globalScoutingIndex: globalScoutingIndex,
      isHot: isHot,
    );
  }

  List<MarketBidEntry> _bidHistoryFromPayload(
    Map<String, Object?> listingPayload,
    Map<String, Object?> playerPayload, {
    required double fallbackAmount,
  }) {
    final List<Map<String, Object?>> bidders = _listValue(
      listingPayload['bidders'],
    ).map(_mapValue).toList(growable: false);
    if (bidders.isEmpty) {
      return <MarketBidEntry>[
        MarketBidEntry(
          clubName: _stringValue(
            playerPayload['current_club_name'],
            fallback: 'Opening bid',
          ),
          amountInMillions: fallbackAmount,
          isUser: false,
          tick: 0,
        ),
      ];
    }

    final List<Map<String, Object?>> sortedBidders =
        List<Map<String, Object?>>.from(bidders)
          ..sort((Map<String, Object?> left, Map<String, Object?> right) {
            final DateTime leftTime =
                _dateTimeValue(left['timestamp']) ??
                DateTime.fromMillisecondsSinceEpoch(0);
            final DateTime rightTime =
                _dateTimeValue(right['timestamp']) ??
                DateTime.fromMillisecondsSinceEpoch(0);
            final int byTime = leftTime.compareTo(rightTime);
            if (byTime != 0) {
              return byTime;
            }
            return _doubleValue(
              left['amount'],
            ).compareTo(_doubleValue(right['amount']));
          });

    return _dedupeBidHistory(
      sortedBidders
          .map((Map<String, Object?> bid) {
            final String clubName = _stringValue(
              bid['club_name'],
              fallback: _stringValue(bid['club_id'], fallback: 'Live bidder'),
            );
            final DateTime? timestamp = _dateTimeValue(bid['timestamp']);
            return MarketBidEntry(
              clubName: clubName,
              amountInMillions: _roundBid(_doubleValue(bid['amount'])),
              isUser: clubName == _userClubName,
              tick: timestamp?.millisecondsSinceEpoch ?? 0,
            );
          })
          .toList(growable: false),
    );
  }

  List<MarketBidEntry> _dedupeBidHistory(List<MarketBidEntry> history) {
    final Map<String, MarketBidEntry> unique = <String, MarketBidEntry>{};
    for (final MarketBidEntry entry in history) {
      unique['${entry.clubName}|${entry.amountInMillions.toStringAsFixed(1)}|${entry.tick}'] =
          entry;
    }
    final List<MarketBidEntry> deduped = unique.values.toList(growable: false);
    deduped.sort((MarketBidEntry left, MarketBidEntry right) {
      final int byTick = left.tick.compareTo(right.tick);
      if (byTick != 0) {
        return byTick;
      }
      return left.amountInMillions.compareTo(right.amountInMillions);
    });
    return deduped;
  }

  List<TransferMarketListing> _buildInitialListings(List<Player> players) {
    return players
        .asMap()
        .entries
        .map((MapEntry<int, Player> entry) {
          final int index = entry.key;
          final Player player = entry.value;
          final double openingBid = _roundBid(
            player.valueInMillions * (0.82 + (index * 0.03)),
          );
          final double increment = player.valueInMillions >= 30 ? 1.0 : 0.5;
          final String initialLeader = _rivalClubs[index % _rivalClubs.length];
          final String chasingClub =
              _rivalClubs[(index + 2) % _rivalClubs.length];

          return TransferMarketListing(
            id: 'fixture-listing-${player.id}',
            player: player,
            currentBidInMillions: openingBid,
            secondsRemaining: 54 + (index * 11),
            minimumIncrementInMillions: increment,
            watcherCount: 8 + (index * 3) + (player.isHot ? 4 : 0),
            bidHistory: <MarketBidEntry>[
              MarketBidEntry(
                clubName: chasingClub,
                amountInMillions: _roundBid(openingBid - increment),
                isUser: false,
                tick: 0,
              ),
              MarketBidEntry(
                clubName: initialLeader,
                amountInMillions: openingBid,
                isUser: false,
                tick: 0,
              ),
            ],
          );
        })
        .toList(growable: false);
  }

  TransferMarketListing _advanceListing({
    required TransferMarketListing listing,
    required int index,
    required int nextTick,
  }) {
    final int nextSeconds = math.max(0, listing.secondsRemaining - 1);
    TransferMarketListing next = listing.copyWith(
      secondsRemaining: nextSeconds,
      watcherCount: 6 + ((listing.watcherCount + index + nextTick) % 24),
    );

    final bool timerExpired = nextSeconds == 0;
    final bool periodicBid = (nextTick + index) % (4 + (index % 3)) == 0;

    if (timerExpired || periodicBid) {
      next = _withRivalBid(
        listing: next,
        index: index,
        nextTick: nextTick,
        forceBid: timerExpired,
      );
    }

    return next;
  }

  TransferMarketListing _withRivalBid({
    required TransferMarketListing listing,
    required int index,
    required int nextTick,
    required bool forceBid,
  }) {
    final bool userLeading = listing.userIsHighestBidder;
    final bool rivalCanLeap =
        forceBid || !userLeading || (nextTick + index) % 9 == 0;

    if (!rivalCanLeap) {
      return listing.copyWith(secondsRemaining: _resetTimer(index, nextTick));
    }

    final String rivalClub =
        _rivalClubs[(index + nextTick) % _rivalClubs.length];
    final double stepMultiplier = 1 + ((nextTick + index) % 2);
    final double newBid = _roundBid(
      listing.currentBidInMillions +
          (listing.minimumIncrementInMillions * stepMultiplier),
    );

    final List<MarketBidEntry> nextHistory = <MarketBidEntry>[
      ...listing.bidHistory,
      MarketBidEntry(
        clubName: rivalClub,
        amountInMillions: newBid,
        isUser: false,
        tick: nextTick,
      ),
    ];

    return listing.copyWith(
      currentBidInMillions: newBid,
      secondsRemaining: _resetTimer(index, nextTick),
      bidHistory: nextHistory,
      watcherCount: listing.watcherCount + 1 + (index % 3),
    );
  }

  int _resetTimer(int index, int tick) {
    return 30 + ((index * 7 + tick * 3) % 45);
  }

  double _metricFromSeed(int seed, int offset) {
    final int normalized = ((seed ~/ (offset + 1)) % 26) + 68;
    return normalized / 100;
  }

  int _stableSeed(String value) {
    return value.codeUnits.fold<int>(0, (int sum, int codeUnit) {
      return (sum * 31 + codeUnit) & 0x7fffffff;
    });
  }

  String _normalizePosition(String value) {
    final String position = value.trim().toUpperCase();
    if (position == 'MIDFIELDER') {
      return 'CM';
    }
    if (position == 'DEFENDER') {
      return 'CB';
    }
    if (position == 'FORWARD' || position == 'ATTACKER') {
      return 'ST';
    }
    if (position == 'GOALKEEPER') {
      return 'GK';
    }
    return position.isEmpty ? 'N/A' : position;
  }

  double _roundBid(double value) {
    return (value * 10).round() / 10;
  }
}

Map<String, Object?> _mapValue(Object? value) {
  if (value is Map<String, Object?>) {
    return value;
  }
  if (value is Map) {
    return value.map<String, Object?>(
      (Object? key, Object? item) => MapEntry(key.toString(), item),
    );
  }
  return const <String, Object?>{};
}

List<Object?> _listValue(Object? value) {
  if (value is List<Object?>) {
    return value;
  }
  if (value is List) {
    return value.cast<Object?>();
  }
  return const <Object?>[];
}

Map<String, Object?>? _decodeMessage(dynamic message) {
  if (message is String) {
    final String trimmed = message.trim();
    if (trimmed.isEmpty) {
      return null;
    }
    try {
      return _mapValue(jsonDecode(trimmed));
    } catch (_) {
      return null;
    }
  }
  if (message is Map) {
    return _mapValue(message);
  }
  return null;
}

String _stringValue(Object? value, {String fallback = ''}) {
  final String? parsed = _stringOrNull(value);
  return parsed ?? fallback;
}

String? _stringOrNull(Object? value) {
  if (value == null) {
    return null;
  }
  final String parsed = value.toString().trim();
  return parsed.isEmpty ? null : parsed;
}

double _doubleValue(Object? value, {double fallback = 0}) {
  if (value is num) {
    return value.toDouble();
  }
  return double.tryParse(value?.toString() ?? '') ?? fallback;
}

int _intValue(Object? value, {int fallback = 0}) {
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.round();
  }
  return int.tryParse(value?.toString() ?? '') ?? fallback;
}

const List<String> _gsiKeys = <String>[
  'global_scouting_index',
  'globalScoutingIndex',
  'gsi',
  'current_gsi',
  'currentGsi',
];

int? _intOrNullFromKeys(Map<String, Object?> payload, List<String> keys) {
  for (final String key in keys) {
    final Object? value = payload[key];
    if (value is int) {
      return value;
    }
    if (value is num) {
      return value.round();
    }
    final int? parsed = int.tryParse(value?.toString() ?? '');
    if (parsed != null) {
      return parsed;
    }
  }
  return null;
}

DateTime? _dateTimeValue(Object? value) {
  if (value is DateTime) {
    return value.toUtc();
  }
  return DateTime.tryParse(value?.toString() ?? '')?.toUtc();
}

int _secondsUntil(DateTime? timestamp) {
  if (timestamp == null) {
    return 0;
  }
  final int seconds = timestamp.difference(DateTime.now().toUtc()).inSeconds;
  return seconds < 0 ? 0 : seconds;
}

final NotifierProvider<TransferMarketNotifier, TransferMarketState>
transferProvider =
    NotifierProvider<TransferMarketNotifier, TransferMarketState>(
      TransferMarketNotifier.new,
    );
