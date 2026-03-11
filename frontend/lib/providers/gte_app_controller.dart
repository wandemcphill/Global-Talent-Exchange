import 'package:flutter/foundation.dart';

import 'gte_mock_api.dart';

class GteAppController extends ChangeNotifier {
  GteAppController({
    GteMockApi? api,
  }) : _api = api ?? const GteMockApi();

  final GteMockApi _api;

  int currentTabIndex = 0;
  bool isBootstrapping = false;
  bool isRefreshingMarket = false;
  String? errorMessage;

  List<PlayerSnapshot> players = <PlayerSnapshot>[];
  MarketPulse? marketPulse;
  PlayerProfile? selectedProfile;

  List<PlayerSnapshot> get featuredPlayers => players;

  List<PlayerSnapshot> get watchlistPlayers => players
      .where((PlayerSnapshot player) => player.isWatchlisted)
      .toList(growable: false);

  List<PlayerSnapshot> get shortlistPlayers => players
      .where((PlayerSnapshot player) => player.isShortlisted)
      .toList(growable: false);

  List<PlayerSnapshot> get transferRoomPlayers => players
      .where((PlayerSnapshot player) => player.inTransferRoom)
      .toList(growable: false);

  Future<void> bootstrap() async {
    if (isBootstrapping) {
      return;
    }

    isBootstrapping = true;
    errorMessage = null;
    notifyListeners();

    try {
      final List<dynamic> payload = await Future.wait<dynamic>(<Future<dynamic>>[
        _api.fetchPlayers(),
        _api.fetchMarketPulse(),
      ]);

      players = payload[0] as List<PlayerSnapshot>;
      final MarketPulse fetchedPulse = payload[1] as MarketPulse;
      marketPulse = _decorateMarketPulse(fetchedPulse);
    } catch (error) {
      errorMessage = error.toString();
    } finally {
      isBootstrapping = false;
      notifyListeners();
    }
  }

  void switchTab(int index) {
    if (currentTabIndex == index) {
      return;
    }

    currentTabIndex = index;
    notifyListeners();
  }

  Future<void> openPlayer(String playerId) async {
    try {
      final PlayerProfile profile = await _api.fetchPlayerProfile(playerId);
      selectedProfile = _mergeProfileWithPlayerState(profile);
      notifyListeners();
    } catch (error) {
      errorMessage = error.toString();
      notifyListeners();
    }
  }

  void closePlayer() {
    if (selectedProfile == null) {
      return;
    }

    selectedProfile = null;
    notifyListeners();
  }

  Future<void> refreshMarket() async {
    if (isRefreshingMarket) {
      return;
    }

    isRefreshingMarket = true;
    notifyListeners();

    try {
      final MarketPulse fetched = await _api.fetchMarketPulse();
      marketPulse = _decorateMarketPulse(fetched);
    } catch (error) {
      errorMessage = error.toString();
    } finally {
      isRefreshingMarket = false;
      notifyListeners();
    }
  }

  void toggleFollow(String playerId) {
    _updatePlayer(
      playerId,
      (PlayerSnapshot player) => player.copyWith(isFollowed: !player.isFollowed),
    );
  }

  void toggleWatchlist(String playerId) {
    _updatePlayer(
      playerId,
      (PlayerSnapshot player) => player.copyWith(
        isWatchlisted: !player.isWatchlisted,
        isShortlisted: player.isWatchlisted ? false : player.isShortlisted,
      ),
    );
  }

  void toggleShortlist(String playerId) {
    _updatePlayer(
      playerId,
      (PlayerSnapshot player) {
        final bool nextShortlist = !player.isShortlisted;
        return player.copyWith(
          isShortlisted: nextShortlist,
          isWatchlisted: nextShortlist ? true : player.isWatchlisted,
        );
      },
    );
  }

  void toggleTransferRoom(String playerId) {
    _updatePlayer(
      playerId,
      (PlayerSnapshot player) {
        final bool nextTransferRoom = !player.inTransferRoom;
        return player.copyWith(
          inTransferRoom: nextTransferRoom,
          isShortlisted: nextTransferRoom ? true : player.isShortlisted,
          isWatchlisted: nextTransferRoom ? true : player.isWatchlisted,
        );
      },
    );
  }

  void cycleNotificationIntensity(String playerId) {
    _updatePlayer(
      playerId,
      (PlayerSnapshot player) => player.copyWith(
        notificationIntensity: _nextNotificationIntensity(
          player.notificationIntensity,
        ),
      ),
    );
  }

  void _updatePlayer(
    String playerId,
    PlayerSnapshot Function(PlayerSnapshot player) transform,
  ) {
    players = players.map((PlayerSnapshot player) {
      if (player.id != playerId) {
        return player;
      }
      return transform(player);
    }).toList(growable: false);

    if (selectedProfile != null && selectedProfile!.snapshot.id == playerId) {
      final PlayerSnapshot snapshot = players.firstWhere(
        (PlayerSnapshot player) => player.id == playerId,
      );
      selectedProfile = selectedProfile!.copyWith(snapshot: snapshot);
    }

    if (marketPulse != null) {
      marketPulse = _decorateMarketPulse(marketPulse!);
    }

    notifyListeners();
  }

  PlayerProfile _mergeProfileWithPlayerState(PlayerProfile profile) {
    final PlayerSnapshot player = players.firstWhere(
      (PlayerSnapshot snapshot) => snapshot.id == profile.snapshot.id,
      orElse: () => profile.snapshot,
    );

    return profile.copyWith(snapshot: player);
  }

  MarketPulse _decorateMarketPulse(MarketPulse pulse) {
    return pulse.copyWith(
      activeWatchers: watchlistPlayers.length * 73 + 131,
      liveDeals: transferRoomPlayers.length + pulse.transferRoom.length,
    );
  }
}

NotificationIntensity _nextNotificationIntensity(
  NotificationIntensity current,
) {
  switch (current) {
    case NotificationIntensity.light:
      return NotificationIntensity.standard;
    case NotificationIntensity.standard:
      return NotificationIntensity.scoutMode;
    case NotificationIntensity.scoutMode:
      return NotificationIntensity.light;
  }
}
