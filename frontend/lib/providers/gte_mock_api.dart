import 'dart:async';

enum NotificationIntensity {
  light,
  standard,
  scoutMode,
}

class TrendPoint {
  const TrendPoint({
    required this.label,
    required this.value,
  });

  final String label;
  final double value;
}

class PlayerSnapshot {
  const PlayerSnapshot({
    required this.id,
    required this.name,
    required this.club,
    required this.nation,
    required this.position,
    required this.age,
    required this.marketCredits,
    required this.gsi,
    required this.formRating,
    required this.valueDeltaPct,
    required this.valueTrend,
    required this.recentHighlights,
    this.isFollowed = false,
    this.isWatchlisted = false,
    this.isShortlisted = false,
    this.inTransferRoom = false,
    this.notificationIntensity = NotificationIntensity.standard,
  });

  final String id;
  final String name;
  final String club;
  final String nation;
  final String position;
  final int age;
  final int marketCredits;
  final int gsi;
  final double formRating;
  final double valueDeltaPct;
  final List<TrendPoint> valueTrend;
  final List<String> recentHighlights;
  final bool isFollowed;
  final bool isWatchlisted;
  final bool isShortlisted;
  final bool inTransferRoom;
  final NotificationIntensity notificationIntensity;

  PlayerSnapshot copyWith({
    String? id,
    String? name,
    String? club,
    String? nation,
    String? position,
    int? age,
    int? marketCredits,
    int? gsi,
    double? formRating,
    double? valueDeltaPct,
    List<TrendPoint>? valueTrend,
    List<String>? recentHighlights,
    bool? isFollowed,
    bool? isWatchlisted,
    bool? isShortlisted,
    bool? inTransferRoom,
    NotificationIntensity? notificationIntensity,
  }) {
    return PlayerSnapshot(
      id: id ?? this.id,
      name: name ?? this.name,
      club: club ?? this.club,
      nation: nation ?? this.nation,
      position: position ?? this.position,
      age: age ?? this.age,
      marketCredits: marketCredits ?? this.marketCredits,
      gsi: gsi ?? this.gsi,
      formRating: formRating ?? this.formRating,
      valueDeltaPct: valueDeltaPct ?? this.valueDeltaPct,
      valueTrend: valueTrend ?? this.valueTrend,
      recentHighlights: recentHighlights ?? this.recentHighlights,
      isFollowed: isFollowed ?? this.isFollowed,
      isWatchlisted: isWatchlisted ?? this.isWatchlisted,
      isShortlisted: isShortlisted ?? this.isShortlisted,
      inTransferRoom: inTransferRoom ?? this.inTransferRoom,
      notificationIntensity: notificationIntensity ?? this.notificationIntensity,
    );
  }
}

class PlayerProfile {
  const PlayerProfile({
    required this.snapshot,
    required this.gsiTrend,
    required this.awards,
    required this.statBlocks,
    required this.scoutingReport,
    required this.transferSignal,
  });

  final PlayerSnapshot snapshot;
  final List<TrendPoint> gsiTrend;
  final List<String> awards;
  final List<String> statBlocks;
  final String scoutingReport;
  final String transferSignal;

  PlayerProfile copyWith({
    PlayerSnapshot? snapshot,
    List<TrendPoint>? gsiTrend,
    List<String>? awards,
    List<String>? statBlocks,
    String? scoutingReport,
    String? transferSignal,
  }) {
    return PlayerProfile(
      snapshot: snapshot ?? this.snapshot,
      gsiTrend: gsiTrend ?? this.gsiTrend,
      awards: awards ?? this.awards,
      statBlocks: statBlocks ?? this.statBlocks,
      scoutingReport: scoutingReport ?? this.scoutingReport,
      transferSignal: transferSignal ?? this.transferSignal,
    );
  }
}

class TransferRoomEntry {
  const TransferRoomEntry({
    required this.id,
    required this.headline,
    required this.lane,
    required this.marketCredits,
    required this.activity,
    required this.timestamp,
  });

  final String id;
  final String headline;
  final String lane;
  final int marketCredits;
  final String activity;
  final DateTime timestamp;
}

class MarketPulse {
  const MarketPulse({
    required this.marketMomentum,
    required this.dailyVolumeCredits,
    required this.activeWatchers,
    required this.liveDeals,
    required this.hottestLeague,
    required this.tickers,
    required this.transferRoom,
  });

  final double marketMomentum;
  final int dailyVolumeCredits;
  final int activeWatchers;
  final int liveDeals;
  final String hottestLeague;
  final List<String> tickers;
  final List<TransferRoomEntry> transferRoom;

  MarketPulse copyWith({
    double? marketMomentum,
    int? dailyVolumeCredits,
    int? activeWatchers,
    int? liveDeals,
    String? hottestLeague,
    List<String>? tickers,
    List<TransferRoomEntry>? transferRoom,
  }) {
    return MarketPulse(
      marketMomentum: marketMomentum ?? this.marketMomentum,
      dailyVolumeCredits: dailyVolumeCredits ?? this.dailyVolumeCredits,
      activeWatchers: activeWatchers ?? this.activeWatchers,
      liveDeals: liveDeals ?? this.liveDeals,
      hottestLeague: hottestLeague ?? this.hottestLeague,
      tickers: tickers ?? this.tickers,
      transferRoom: transferRoom ?? this.transferRoom,
    );
  }
}

class GteMockApi {
  const GteMockApi({
    this.latency = const Duration(milliseconds: 250),
  });

  final Duration latency;

  Future<List<PlayerSnapshot>> fetchPlayers() async {
    await Future<void>.delayed(latency);
    return _catalog
        .map(
          (PlayerSnapshot player) => player.copyWith(
            valueTrend: List<TrendPoint>.from(player.valueTrend),
            recentHighlights: List<String>.from(player.recentHighlights),
          ),
        )
        .toList(growable: false);
  }

  Future<PlayerProfile> fetchPlayerProfile(String id) async {
    await Future<void>.delayed(latency);
    final PlayerProfile? profile = _profiles[id];
    if (profile == null) {
      throw StateError('Unknown player id: $id');
    }
    return profile.copyWith(
      snapshot: profile.snapshot.copyWith(
        valueTrend: List<TrendPoint>.from(profile.snapshot.valueTrend),
        recentHighlights: List<String>.from(profile.snapshot.recentHighlights),
      ),
      gsiTrend: List<TrendPoint>.from(profile.gsiTrend),
      awards: List<String>.from(profile.awards),
      statBlocks: List<String>.from(profile.statBlocks),
    );
  }

  Future<MarketPulse> fetchMarketPulse() async {
    await Future<void>.delayed(latency);
    return _marketPulse.copyWith(
      tickers: List<String>.from(_marketPulse.tickers),
      transferRoom: List<TransferRoomEntry>.from(_marketPulse.transferRoom),
    );
  }
}

const List<PlayerSnapshot> _catalog = <PlayerSnapshot>[
  PlayerSnapshot(
    id: 'lamine-yamal',
    name: 'Lamine Yamal',
    club: 'Barcelona',
    nation: 'Spain',
    position: 'RW',
    age: 18,
    marketCredits: 1180,
    gsi: 96,
    formRating: 9.2,
    valueDeltaPct: 7.8,
    valueTrend: <TrendPoint>[
      TrendPoint(label: 'W1', value: 67),
      TrendPoint(label: 'W2', value: 71),
      TrendPoint(label: 'W3', value: 76),
      TrendPoint(label: 'W4', value: 82),
      TrendPoint(label: 'W5', value: 88),
    ],
    recentHighlights: <String>[
      '2 goals in the last 3 matches',
      'Final-third chance creation up 18%',
      'Transfer room activity accelerated this week',
    ],
    isFollowed: true,
    isWatchlisted: true,
  ),
  PlayerSnapshot(
    id: 'jude-bellingham',
    name: 'Jude Bellingham',
    club: 'Real Madrid',
    nation: 'England',
    position: 'CM',
    age: 22,
    marketCredits: 1260,
    gsi: 94,
    formRating: 8.9,
    valueDeltaPct: 4.6,
    valueTrend: <TrendPoint>[
      TrendPoint(label: 'W1', value: 70),
      TrendPoint(label: 'W2', value: 73),
      TrendPoint(label: 'W3', value: 79),
      TrendPoint(label: 'W4', value: 84),
      TrendPoint(label: 'W5', value: 87),
    ],
    recentHighlights: <String>[
      'Tournament influence tier: elite',
      'Shortlist demand remains stable',
      'Midfield duel win rate above 64%',
    ],
    isShortlisted: true,
  ),
  PlayerSnapshot(
    id: 'jamal-musiala',
    name: 'Jamal Musiala',
    club: 'Bayern Munich',
    nation: 'Germany',
    position: 'AM',
    age: 23,
    marketCredits: 1095,
    gsi: 91,
    formRating: 8.7,
    valueDeltaPct: 3.9,
    valueTrend: <TrendPoint>[
      TrendPoint(label: 'W1', value: 61),
      TrendPoint(label: 'W2', value: 65),
      TrendPoint(label: 'W3', value: 69),
      TrendPoint(label: 'W4', value: 74),
      TrendPoint(label: 'W5', value: 79),
    ],
    recentHighlights: <String>[
      'Line-breaking carries trending upward',
      'Scout Mode alerts active across 14 clubs',
      'Ball progression profile improved',
    ],
    isFollowed: true,
    notificationIntensity: NotificationIntensity.scoutMode,
  ),
  PlayerSnapshot(
    id: 'victor-osimhen',
    name: 'Victor Osimhen',
    club: 'Galatasaray',
    nation: 'Nigeria',
    position: 'ST',
    age: 27,
    marketCredits: 920,
    gsi: 88,
    formRating: 8.4,
    valueDeltaPct: 6.1,
    valueTrend: <TrendPoint>[
      TrendPoint(label: 'W1', value: 55),
      TrendPoint(label: 'W2', value: 58),
      TrendPoint(label: 'W3', value: 62),
      TrendPoint(label: 'W4', value: 69),
      TrendPoint(label: 'W5', value: 75),
    ],
    recentHighlights: <String>[
      'Transfer signal upgraded to active',
      'Shot volume back above 4.2 per 90',
      'Platform market demand rose after last matchday',
    ],
    inTransferRoom: true,
  ),
];

final Map<String, PlayerProfile> _profiles = <String, PlayerProfile>{
  'lamine-yamal': PlayerProfile(
    snapshot: _catalog[0],
    gsiTrend: const <TrendPoint>[
      TrendPoint(label: 'M1', value: 72),
      TrendPoint(label: 'M2', value: 77),
      TrendPoint(label: 'M3', value: 83),
      TrendPoint(label: 'M4', value: 89),
      TrendPoint(label: 'M5', value: 96),
    ],
    awards: const <String>[
      'Golden Boy shortlist',
      'Matchday MVP x3',
      'Continental semifinal decisive contribution',
    ],
    statBlocks: const <String>[
      'xA 0.42',
      'Dribbles won 5.7',
      'Progressive carries 7.3',
      'Final-third receptions 13.8',
    ],
    scoutingReport:
        'Explosive right-sided creator with elite manipulation of space and accelerating end product. Breakout profile still carries upside headroom.',
    transferSignal:
        'Untouchable unless a record-setting move materializes. Watchlist and shortlist activity remains the strongest in the catalog.',
  ),
  'jude-bellingham': PlayerProfile(
    snapshot: _catalog[1],
    gsiTrend: const <TrendPoint>[
      TrendPoint(label: 'M1', value: 70),
      TrendPoint(label: 'M2', value: 75),
      TrendPoint(label: 'M3', value: 81),
      TrendPoint(label: 'M4', value: 87),
      TrendPoint(label: 'M5', value: 94),
    ],
    awards: const <String>[
      'Player of the season finalist',
      'Continental final-winning moment',
      'Best XI selection',
    ],
    statBlocks: const <String>[
      'Press resistance 95th pct',
      'Box arrivals 6.1',
      'Shot-creating actions 5.0',
      'Duel win rate 63%',
    ],
    scoutingReport:
        'Complete midfield controller with premium ball-carrying, duel dominance, and high-leverage scoring output. Low-risk elite asset.',
    transferSignal:
        'Market remains premium and supply-constrained. Acquisition scenario is improbable, but his card drives benchmark pricing.',
  ),
  'jamal-musiala': PlayerProfile(
    snapshot: _catalog[2],
    gsiTrend: const <TrendPoint>[
      TrendPoint(label: 'M1', value: 66),
      TrendPoint(label: 'M2', value: 71),
      TrendPoint(label: 'M3', value: 76),
      TrendPoint(label: 'M4', value: 84),
      TrendPoint(label: 'M5', value: 91),
    ],
    awards: const <String>[
      'Young player of the month',
      'Tournament breakout watch',
      'Domestic title race accelerator',
    ],
    statBlocks: const <String>[
      'Carries into box 3.8',
      'Touches in zone 14: 11.2',
      'Turn resistance 92nd pct',
      'Progressive passes received 14.6',
    ],
    scoutingReport:
        'Hybrid creator-finisher with elite change of direction and close-control gravity. Best deployed with freedom between lines.',
    transferSignal:
        'Scout Mode traffic is heavy. Price is climbing steadily without the volatility seen in pure hype-driven movers.',
  ),
  'victor-osimhen': PlayerProfile(
    snapshot: _catalog[3],
    gsiTrend: const <TrendPoint>[
      TrendPoint(label: 'M1', value: 61),
      TrendPoint(label: 'M2', value: 66),
      TrendPoint(label: 'M3', value: 69),
      TrendPoint(label: 'M4', value: 82),
      TrendPoint(label: 'M5', value: 88),
    ],
    awards: const <String>[
      'League golden boot race contender',
      'Transfer room headline striker',
      'Match-winning brace spotlight',
    ],
    statBlocks: const <String>[
      'Shots 4.4',
      'Aerial wins 3.2',
      'Penalty-box touches 8.9',
      'Goals per shot 0.23',
    ],
    scoutingReport:
        'Vertical striker with premium penalty-box occupation, elite separation bursts, and immediate transfer-market gravity.',
    transferSignal:
        'Transfer room remains live. Featured on both platform deal boards and user market chatter after the latest valuation jump.',
  ),
};

final MarketPulse _marketPulse = MarketPulse(
  marketMomentum: 8.4,
  dailyVolumeCredits: 18340,
  activeWatchers: 642,
  liveDeals: 21,
  hottestLeague: 'UEFA Club Championship',
  tickers: const <String>[
    'Yamal +7.8%',
    'Osimhen +6.1%',
    'Musiala Scout Mode spike',
    'Transfer room volume +14%',
  ],
  transferRoom: <TransferRoomEntry>[
    TransferRoomEntry(
      id: 'tr-1',
      headline: 'Platform Deal: Victor Osimhen demand surge',
      lane: 'Platform Deals',
      marketCredits: 920,
      activity: '22 shortlist moves in 24h',
      timestamp: DateTime(2026, 3, 11, 10, 30),
    ),
    TransferRoomEntry(
      id: 'tr-2',
      headline: 'User Market Deal: Musiala premium listing filled',
      lane: 'User Market Deals',
      marketCredits: 1110,
      activity: 'Cleared in 6 minutes',
      timestamp: DateTime(2026, 3, 11, 9, 50),
    ),
    TransferRoomEntry(
      id: 'tr-3',
      headline: 'Announcement: Jude benchmark pricing reset',
      lane: 'Announcements',
      marketCredits: 1260,
      activity: 'Market cap ceiling updated',
      timestamp: DateTime(2026, 3, 11, 8, 45),
    ),
  ],
);
