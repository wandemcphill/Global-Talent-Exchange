import 'dart:math' as math;

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/player.dart';

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
    required this.player,
    required this.currentBidInMillions,
    required this.secondsRemaining,
    required this.minimumIncrementInMillions,
    required this.watcherCount,
    required this.bidHistory,
  });

  final Player player;
  final double currentBidInMillions;
  final int secondsRemaining;
  final double minimumIncrementInMillions;
  final int watcherCount;
  final List<MarketBidEntry> bidHistory;

  MarketBidEntry get leadingBidder {
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
      }.contains(player.position),
      TransferMarketFilter.defenders => <String>{
        'CB',
        'LB',
        'RB',
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
  }) {
    return TransferMarketListing(
      player: player ?? this.player,
      currentBidInMillions: currentBidInMillions ?? this.currentBidInMillions,
      secondsRemaining: secondsRemaining ?? this.secondsRemaining,
      minimumIncrementInMillions:
          minimumIncrementInMillions ?? this.minimumIncrementInMillions,
      watcherCount: watcherCount ?? this.watcherCount,
      bidHistory: bidHistory ?? this.bidHistory,
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
    return listings.where((TransferMarketListing listing) {
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
    }).toList();
  }

  List<Player> get filteredPlayers {
    return filteredListings
        .map((TransferMarketListing listing) => listing.player)
        .toList();
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

  static const String userClubName = 'GTEX United';

  @override
  TransferMarketState build() {
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

  void setSearchQuery(String value) {
    state = state.copyWith(searchQuery: value);
  }

  void setFilter(TransferMarketFilter filter) {
    state = state.copyWith(activeFilter: filter);
  }

  void toggleShortlist(String playerId) {
    final Set<String> next = <String>{...state.shortlistedIds};
    if (!next.add(playerId)) {
      next.remove(playerId);
    }
    state = state.copyWith(shortlistedIds: next);
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

    final List<TransferMarketListing> updatedListings =
        state.listings.map((TransferMarketListing current) {
          if (current.player.id != playerId) {
            return current;
          }

          final List<MarketBidEntry> nextHistory = <MarketBidEntry>[
            ...current.bidHistory,
            MarketBidEntry(
              clubName: userClubName,
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
        }).toList();

    final Set<String> nextShortlist = <String>{
      ...state.shortlistedIds,
      playerId,
    };

    state = state.copyWith(
      listings: updatedListings,
      shortlistedIds: nextShortlist,
    );

    return placedBid;
  }

  void tickSimulation() {
    final int nextTick = state.simulationTick + 1;
    final List<TransferMarketListing> nextListings =
        state.listings.asMap().entries.map((
          MapEntry<int, TransferMarketListing> entry,
        ) {
          return _advanceListing(
            listing: entry.value,
            index: entry.key,
            nextTick: nextTick,
          );
        }).toList();

    state = state.copyWith(listings: nextListings, simulationTick: nextTick);
  }

  List<TransferMarketListing> _buildInitialListings(List<Player> players) {
    return players.asMap().entries.map((MapEntry<int, Player> entry) {
      final int index = entry.key;
      final Player player = entry.value;
      final double openingBid = _roundBid(
        player.valueInMillions * (0.82 + (index * 0.03)),
      );
      final double increment = player.valueInMillions >= 30 ? 1.0 : 0.5;
      final String initialLeader = _rivalClubs[index % _rivalClubs.length];
      final String chasingClub = _rivalClubs[(index + 2) % _rivalClubs.length];

      return TransferMarketListing(
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
    }).toList();
  }

  TransferMarketListing _advanceListing({
    required TransferMarketListing listing,
    required int index,
    required int nextTick,
  }) {
    int nextSeconds = math.max(0, listing.secondsRemaining - 1);
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

  double _roundBid(double value) {
    return (value * 10).round() / 10;
  }
}

final NotifierProvider<TransferMarketNotifier, TransferMarketState>
transferProvider =
    NotifierProvider<TransferMarketNotifier, TransferMarketState>(
      TransferMarketNotifier.new,
    );
