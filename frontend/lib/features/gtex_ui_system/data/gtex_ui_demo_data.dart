import 'dart:math' as math;

import 'package:flutter/foundation.dart';

import '../../../core/gte_session_identity.dart';
import '../../../data/gte_exchange_models.dart';
import '../../../models/match_type.dart';
import '../../../providers/gte_exchange_controller.dart';

@immutable
class GtexClubSnapshot {
  const GtexClubSnapshot({
    required this.name,
    required this.leaguePosition,
    required this.points,
    required this.fanSentiment,
    required this.sentimentEmoji,
    required this.regionLabel,
  });

  final String name;
  final int leaguePosition;
  final int points;
  final int fanSentiment;
  final String sentimentEmoji;
  final String regionLabel;
}

@immutable
class GtexStoryCardData {
  const GtexStoryCardData({
    required this.id,
    required this.title,
    required this.subtitle,
    required this.kicker,
  });

  final String id;
  final String title;
  final String subtitle;
  final String kicker;
}

@immutable
class GtexTaskData {
  const GtexTaskData({
    required this.id,
    required this.title,
    required this.detail,
    required this.progress,
    required this.rewardLabel,
    this.isClaimed = false,
  });

  final String id;
  final String title;
  final String detail;
  final double progress;
  final String rewardLabel;
  final bool isClaimed;

  GtexTaskData copyWith({bool? isClaimed}) {
    return GtexTaskData(
      id: id,
      title: title,
      detail: detail,
      progress: progress,
      rewardLabel: rewardLabel,
      isClaimed: isClaimed ?? this.isClaimed,
    );
  }
}

@immutable
class GtexLiveMatchData {
  const GtexLiveMatchData({
    required this.id,
    required this.stageLabel,
    required this.homeClub,
    required this.awayClub,
    required this.homeScore,
    required this.awayScore,
    required this.minute,
    required this.possessionHome,
    required this.xgHome,
    required this.xgAway,
    required this.shotsHome,
    required this.shotsAway,
    required this.commentaryLine,
    required this.highlightPlayer,
    required this.highlightSummary,
    this.matchType = MatchType.userHosted,
    this.entryFee = 0,
  });

  final String id;
  final String stageLabel;
  final String homeClub;
  final String awayClub;
  final int homeScore;
  final int awayScore;
  final int minute;
  final int possessionHome;
  final double xgHome;
  final double xgAway;
  final int shotsHome;
  final int shotsAway;
  final String commentaryLine;
  final String highlightPlayer;
  final String highlightSummary;
  final MatchType matchType;
  final double entryFee;
}

@immutable
class GtexTransferAlertData {
  const GtexTransferAlertData({
    required this.id,
    required this.title,
    required this.summary,
    required this.tag,
  });

  final String id;
  final String title;
  final String summary;
  final String tag;
}

@immutable
class GtexOfferData {
  const GtexOfferData({
    required this.title,
    required this.valueLabel,
    required this.status,
  });

  final String title;
  final String valueLabel;
  final String status;
}

@immutable
class GtexPlayerCardData {
  const GtexPlayerCardData({
    required this.id,
    required this.name,
    required this.position,
    required this.country,
    required this.clubName,
    required this.age,
    required this.rating,
    required this.potential,
    required this.price,
    required this.bidStatus,
    required this.timerLabel,
    required this.badges,
    required this.attributes,
    required this.storyMoments,
    required this.careerMoments,
    required this.offers,
    this.globalScoutingIndex,
    this.liquidityLabel = 'High 🔥',
  });

  final String id;
  final String name;
  final String position;
  final String country;
  final String clubName;
  final int age;
  final int rating;
  final int potential;
  final double price;
  final String bidStatus;
  final String timerLabel;
  final List<String> badges;
  final Map<String, int> attributes;
  final List<String> storyMoments;
  final List<String> careerMoments;
  final List<GtexOfferData> offers;
  final int? globalScoutingIndex;
  final String liquidityLabel;

  double get rentalCost => price * 0.10;

  int get gsi => (globalScoutingIndex ?? rating).clamp(0, 100).toInt();

  String get gsiLabel => 'GSI $gsi';

  String get gsiTierLabel {
    if (gsi >= 90) return 'Elite GSI';
    if (gsi >= 82) return 'High-grade GSI';
    if (gsi >= 74) return 'First-team GSI';
    if (gsi >= 66) return 'Developing GSI';
    return 'Prospect GSI';
  }
}

@immutable
class GtexTournamentCardData {
  const GtexTournamentCardData({
    required this.id,
    required this.name,
    required this.status,
    required this.rewardLabel,
    required this.themeLabel,
  });

  final String id;
  final String name;
  final String status;
  final String rewardLabel;
  final String themeLabel;
}

@immutable
class GtexFederationCardData {
  const GtexFederationCardData({
    required this.id,
    required this.name,
    required this.memberCount,
    required this.rulesSummary,
  });

  final String id;
  final String name;
  final int memberCount;
  final String rulesSummary;
}

@immutable
class GtexHistoryRecordData {
  const GtexHistoryRecordData({
    required this.id,
    required this.title,
    required this.holder,
    required this.context,
  });

  final String id;
  final String title;
  final String holder;
  final String context;
}

@immutable
class GtexActivityFeedItem {
  const GtexActivityFeedItem({
    required this.id,
    required this.body,
    required this.timeLabel,
  });

  final String id;
  final String body;
  final String timeLabel;
}

@immutable
class GtexFinanceMetric {
  const GtexFinanceMetric({
    required this.label,
    required this.value,
    required this.progress,
  });

  final String label;
  final double value;
  final double progress;
}

@immutable
class GtexFanReactionData {
  const GtexFanReactionData({
    required this.id,
    required this.author,
    required this.body,
  });

  final String id;
  final String author;
  final String body;
}

@immutable
class GtexUiUniverseData {
  const GtexUiUniverseData({
    required this.userName,
    required this.club,
    required this.coins,
    required this.notifications,
    required this.stories,
    required this.tasks,
    required this.liveMatches,
    required this.transferAlerts,
    required this.trendingRegens,
    required this.marketPlayers,
    required this.tournaments,
    required this.federations,
    required this.historyRecords,
    required this.profileFeed,
    required this.incomeStreams,
    required this.expenseStreams,
    required this.fanReactions,
    required this.freeNationalTeamPicks,
    required this.nationalBudget,
  });

  final String userName;
  final GtexClubSnapshot club;
  final int coins;
  final int notifications;
  final List<GtexStoryCardData> stories;
  final List<GtexTaskData> tasks;
  final List<GtexLiveMatchData> liveMatches;
  final List<GtexTransferAlertData> transferAlerts;
  final List<GtexPlayerCardData> trendingRegens;
  final List<GtexPlayerCardData> marketPlayers;
  final List<GtexTournamentCardData> tournaments;
  final List<GtexFederationCardData> federations;
  final List<GtexHistoryRecordData> historyRecords;
  final List<GtexActivityFeedItem> profileFeed;
  final List<GtexFinanceMetric> incomeStreams;
  final List<GtexFinanceMetric> expenseStreams;
  final List<GtexFanReactionData> fanReactions;
  final int freeNationalTeamPicks;
  final double nationalBudget;
}

class GtexUiUniverseFactory {
  const GtexUiUniverseFactory._();

  static GtexUiUniverseData fromController(
    GteExchangeController controller, {
    Set<String> claimedTaskIds = const <String>{},
  }) {
    final GteSessionIdentity identity =
        GteSessionIdentity.fromExchangeController(controller);
    final String userName =
        identity.userName?.trim().isNotEmpty == true
            ? identity.userName!.trim()
            : 'Manager Pulse';
    final String clubName =
        identity.clubName?.trim().isNotEmpty == true
            ? identity.clubName!.trim()
            : 'Lagos Pulse FC';
    final List<GtexPlayerCardData> sourcePlayers = _playersFromController(
      controller,
    );
    final List<GtexPlayerCardData> marketPlayers = sourcePlayers
        .take(8)
        .toList(growable: false);
    final List<GtexPlayerCardData> regenPlayers = sourcePlayers.reversed
        .take(6)
        .toList(growable: false);
    final List<GtexTaskData> tasks = _baseTasks
        .map(
          (GtexTaskData task) =>
              claimedTaskIds.contains(task.id)
                  ? task.copyWith(isClaimed: true)
                  : task,
        )
        .toList(growable: false);
    final GtexPlayerCardData featurePlayer =
        (marketPlayers.isNotEmpty
            ? marketPlayers.first
            : _fallbackPlayers.first);
    return GtexUiUniverseData(
      userName: userName,
      club: GtexClubSnapshot(
        name: clubName,
        leaguePosition: 3,
        points: 58,
        fanSentiment: 84,
        sentimentEmoji: '🔥',
        regionLabel: 'West Africa Elite Ladder',
      ),
      coins: controller.walletSummary?.availableBalance.round() ?? 1840,
      notifications: 3,
      stories: <GtexStoryCardData>[
        GtexStoryCardData(
          id: 'story-underdog-run',
          title: 'Underdog Run',
          subtitle: '$clubName just shocked the semi-final bracket.',
          kicker: 'Storyline',
        ),
        GtexStoryCardData(
          id: 'story-regen-surge',
          title: 'Regen Surge',
          subtitle:
              '${featurePlayer.name} is now trending across three markets.',
          kicker: 'Scouting',
        ),
        const GtexStoryCardData(
          id: 'story-fan-fever',
          title: 'Fan Fever',
          subtitle: 'Supporters are demanding a high press before the derby.',
          kicker: 'Fans',
        ),
        const GtexStoryCardData(
          id: 'story-federation-shift',
          title: 'Federation Vote',
          subtitle: 'A new cross-border youth rule is moving into debate.',
          kicker: 'World',
        ),
      ],
      tasks: tasks,
      liveMatches: <GtexLiveMatchData>[
        GtexLiveMatchData(
          id: 'match-1',
          stageLabel: 'League Night',
          homeClub: clubName,
          awayClub: 'Kano Meteors',
          homeScore: 2,
          awayScore: 1,
          minute: 68,
          possessionHome: 58,
          xgHome: 1.9,
          xgAway: 0.8,
          shotsHome: 11,
          shotsAway: 6,
          commentaryLine:
              '${featurePlayer.name} bursts through the half-space again.',
          highlightPlayer: featurePlayer.name,
          highlightSummary: '7.8 match rating and the winning assist so far.',
          matchType: MatchType.gtexHosted,
          entryFee: 0,
        ),
        GtexLiveMatchData(
          id: 'match-2',
          stageLabel: 'Fast Cup',
          homeClub: 'Abuja Arrows',
          awayClub: 'Cape Comets',
          homeScore: 3,
          awayScore: 3,
          minute: 82,
          possessionHome: 46,
          xgHome: 2.4,
          xgAway: 2.2,
          shotsHome: 14,
          shotsAway: 12,
          commentaryLine:
              'Chaos in stoppage prep. Both sides are trading blows.',
          highlightPlayer: 'Neo Kaze',
          highlightSummary:
              'Two goals, one rebound poach, one outrageous trivela.',
          matchType: MatchType.fastMatch,
          entryFee: 35,
        ),
        GtexLiveMatchData(
          id: 'match-3',
          stageLabel: 'Continental Qualifier',
          homeClub: 'Dakar Surge',
          awayClub: 'Luanda Engines',
          homeScore: 0,
          awayScore: 0,
          minute: 33,
          possessionHome: 51,
          xgHome: 0.7,
          xgAway: 0.5,
          shotsHome: 5,
          shotsAway: 4,
          commentaryLine:
              'Tactical stalemate. The next pressing trap will decide it.',
          highlightPlayer: 'Sami Okoro',
          highlightSummary:
              'Already won 6 duels and reset the midfield rhythm.',
          matchType: MatchType.userHosted,
          entryFee: 12,
        ),
      ],
      transferAlerts: <GtexTransferAlertData>[
        GtexTransferAlertData(
          id: 'alert-1',
          title: 'Rival bid incoming',
          summary:
              'Northport Union is preparing a late move for ${featurePlayer.name}.',
          tag: 'Market heat',
        ),
        const GtexTransferAlertData(
          id: 'alert-2',
          title: 'Loan window opens in 2h',
          summary: 'Young depth pieces can be rented at 10% of market value.',
          tag: 'Ops',
        ),
        const GtexTransferAlertData(
          id: 'alert-3',
          title: 'Scouting report refreshed',
          summary: 'Three elite regens crossed the 90-potential threshold.',
          tag: 'Academy',
        ),
      ],
      trendingRegens: regenPlayers,
      marketPlayers: marketPlayers,
      tournaments: const <GtexTournamentCardData>[
        GtexTournamentCardData(
          id: 'tournament-1',
          name: 'Neon Champions Cup',
          status: 'Registration open',
          rewardLabel: 'Prize pool: 4.8M',
          themeLabel: 'Broadcast prime',
        ),
        GtexTournamentCardData(
          id: 'tournament-2',
          name: 'Global Regen Clash',
          status: 'Seeding live',
          rewardLabel: 'Youth prestige boost',
          themeLabel: 'Future stars',
        ),
        GtexTournamentCardData(
          id: 'tournament-3',
          name: 'Federation Masters',
          status: 'Knockouts ready',
          rewardLabel: 'Legacy banner',
          themeLabel: 'Historic nights',
        ),
      ],
      federations: const <GtexFederationCardData>[
        GtexFederationCardData(
          id: 'federation-1',
          name: 'Atlantic Coaches Guild',
          memberCount: 1482,
          rulesSummary:
              'Open scouting, two youth locks, one emergency loan spot.',
        ),
        GtexFederationCardData(
          id: 'federation-2',
          name: 'Pan-Africa Talent Council',
          memberCount: 2199,
          rulesSummary:
              'Cross-border cups, regen sharing windows, hard salary caps.',
        ),
        GtexFederationCardData(
          id: 'federation-3',
          name: 'Future Football Assembly',
          memberCount: 876,
          rulesSummary:
              'Experimental formats, creator rights, flexible academy quotas.',
        ),
      ],
      historyRecords: const <GtexHistoryRecordData>[
        GtexHistoryRecordData(
          id: 'record-1',
          title: 'Most goals in a season',
          holder: 'Kaito Mensah',
          context: '41 goals for Coastline Rovers, 2025.',
        ),
        GtexHistoryRecordData(
          id: 'record-2',
          title: 'Greatest club ever',
          holder: 'Sahara Royals',
          context: 'Seven league crowns and three continental titles.',
        ),
        GtexHistoryRecordData(
          id: 'record-3',
          title: 'Youngest Ballon Regen',
          holder: 'Ayo Silva',
          context: 'Won at age 18 after a 94-potential breakout.',
        ),
        GtexHistoryRecordData(
          id: 'record-4',
          title: 'Longest unbeaten run',
          holder: 'Port Valiants',
          context: '33 matches without defeat across two competitions.',
        ),
      ],
      profileFeed: <GtexActivityFeedItem>[
        GtexActivityFeedItem(
          id: 'feed-1',
          body: '$userName signed a wonderkid winger for deadline day.',
          timeLabel: '12m ago',
        ),
        GtexActivityFeedItem(
          id: 'feed-2',
          body: '$clubName moved into the top three after a comeback win.',
          timeLabel: '1h ago',
        ),
        const GtexActivityFeedItem(
          id: 'feed-3',
          body: 'Joined a federation debate on youth residency rules.',
          timeLabel: '3h ago',
        ),
        const GtexActivityFeedItem(
          id: 'feed-4',
          body: 'Won the weekly live-broadcast engagement streak.',
          timeLabel: 'Yesterday',
        ),
      ],
      incomeStreams: const <GtexFinanceMetric>[
        GtexFinanceMetric(label: 'Broadcast', value: 3.8, progress: 0.76),
        GtexFinanceMetric(label: 'Matchday', value: 2.6, progress: 0.52),
        GtexFinanceMetric(label: 'Sponsorship', value: 1.8, progress: 0.36),
      ],
      expenseStreams: const <GtexFinanceMetric>[
        GtexFinanceMetric(label: 'Wages', value: 2.4, progress: 0.48),
        GtexFinanceMetric(label: 'Facilities', value: 1.2, progress: 0.24),
        GtexFinanceMetric(label: 'Scouting', value: 0.9, progress: 0.18),
      ],
      fanReactions: const <GtexFanReactionData>[
        GtexFanReactionData(
          id: 'fan-1',
          author: '@stadiumnorth',
          body: 'Keep the press high. This badge finally looks fearless.',
        ),
        GtexFanReactionData(
          id: 'fan-2',
          author: '@regenwatch',
          body: 'Do not sell the academy striker unless the offer is absurd.',
        ),
        GtexFanReactionData(
          id: 'fan-3',
          author: '@ultrawire',
          body: 'The identity score is rising. The fans can feel the plan now.',
        ),
      ],
      freeNationalTeamPicks: 5,
      nationalBudget: 4.2,
    );
  }

  static List<GtexPlayerCardData> _playersFromController(
    GteExchangeController controller,
  ) {
    if (controller.players.isEmpty) {
      return _fallbackPlayers;
    }
    return controller.players
        .asMap()
        .entries
        .map(
          (MapEntry<int, GteMarketPlayerListItem> entry) =>
              _fromMarketPlayer(entry.value, entry.key),
        )
        .toList(growable: false);
  }

  static GtexPlayerCardData _fromMarketPlayer(
    GteMarketPlayerListItem item,
    int index,
  ) {
    final int gsi =
        (item.globalScoutingIndex ?? item.trendScore ?? 74)
            .round()
            .clamp(50, 99)
            .toInt();
    final int rating = gsi;
    final int age = item.age ?? 18;
    final int potential = math.min(
      99,
      rating + 5 + (index % 6) + (age < 22 ? 4 : 0),
    );
    final double price = item.currentValueCredits ?? (1.6 + index) * 1000000;
    final List<String> badges = <String>[
      if (potential >= 90) '🌟',
      if ((item.movementPct ?? 0) > 3) '🔥',
      if (age <= 21) '🧬',
    ];
    final Map<String, int> attributes = <String, int>{
      'Pace': _scaledStat(rating, 6 + index),
      'Technique': _scaledStat(rating, 9 + index),
      'Power': _scaledStat(rating, 2 + index),
      'Vision': _scaledStat(rating, 11 + index),
      'Duels': _scaledStat(rating, 4 + index),
      'Flair': _scaledStat(rating, 13 + index),
    };
    final String playerName =
        item.playerName.trim().isEmpty
            ? 'Unnamed Talent'
            : item.playerName.trim();
    final String clubName =
        item.currentClubName?.trim().isNotEmpty == true
            ? item.currentClubName!.trim()
            : 'Open Market';
    final String position =
        item.position?.trim().isNotEmpty == true
            ? item.position!.trim().toUpperCase()
            : 'CF';
    final String country =
        item.nationality?.trim().isNotEmpty == true
            ? item.nationality!.trim()
            : 'Nigeria';
    return GtexPlayerCardData(
      id: item.playerId,
      name: playerName,
      position: position,
      country: country,
      clubName: clubName,
      age: age,
      rating: rating,
      potential: potential,
      price: price,
      bidStatus: item.isAvailable ? 'Open for bids' : item.availabilityLabel,
      timerLabel: '${4 + (index % 5)}h left',
      badges: badges.isEmpty ? const <String>['🎯'] : badges,
      attributes: attributes,
      storyMoments: <String>[
        'Breakout match against coastal rivals with a late winner.',
        'Won the weekly regen spotlight after a double-digit rating spike.',
        'Became the hottest asset on the board in ${country.toUpperCase()}.',
      ],
      careerMoments: <String>[
        'Academy rise at $clubName.',
        'Senior debut at age ${math.max(16, age - 2)}.',
        'Current market value surged after three elite scouting reports.',
      ],
      offers: <GtexOfferData>[
        GtexOfferData(
          title: 'Highest bid',
          valueLabel: _currencyLabel(price * 1.02),
          status: 'Live',
        ),
        GtexOfferData(
          title: 'Contract package',
          valueLabel: '${_currencyLabel(price * 0.25)}/yr',
          status: 'Negotiating',
        ),
      ],
      globalScoutingIndex: gsi,
      liquidityLabel: _liquidityLabel(item, index),
    );
  }

  static int _scaledStat(int base, int variance) {
    final int raw = base + (variance % 9) - 4;
    return raw.clamp(60, 99);
  }

  static String _currencyLabel(double value) {
    if (value >= 1000000) {
      return '${(value / 1000000).toStringAsFixed(1)}M';
    }
    if (value >= 1000) {
      return '${(value / 1000).toStringAsFixed(0)}K';
    }
    return value.toStringAsFixed(0);
  }

  static String _liquidityLabel(GteMarketPlayerListItem item, int index) {
    final double movement = item.movementPct ?? 0;
    if (movement >= 4.5 || index <= 1) {
      return 'High 🔥';
    }
    if (movement >= 1.5 || index <= 4) {
      return 'Medium';
    }
    return 'Low';
  }

  static const List<GtexTaskData> _baseTasks = <GtexTaskData>[
    GtexTaskData(
      id: 'task-match',
      title: 'Win your next live match',
      detail: 'Secure three points to keep the title push alive.',
      progress: 0.72,
      rewardLabel: '+120 coins',
    ),
    GtexTaskData(
      id: 'task-transfer',
      title: 'Place two transfer bids',
      detail: 'Keep your recruitment board active before midnight.',
      progress: 0.45,
      rewardLabel: '+80 scouting XP',
    ),
    GtexTaskData(
      id: 'task-fans',
      title: 'Lift fan sentiment above 90',
      detail: 'Positive identity actions compound your streak multiplier.',
      progress: 0.88,
      rewardLabel: '+1.5x streak',
    ),
  ];

  static const List<GtexPlayerCardData> _fallbackPlayers = <GtexPlayerCardData>[
    GtexPlayerCardData(
      id: 'regen-zuri',
      name: 'Zuri Adamu',
      position: 'RW',
      country: 'Nigeria',
      clubName: 'Lagos Pulse FC',
      age: 19,
      rating: 86,
      potential: 94,
      price: 2400000,
      bidStatus: 'Open for bids',
      timerLabel: '3h left',
      badges: <String>['🧬', '🔥', '🌟'],
      attributes: <String, int>{
        'Pace': 93,
        'Technique': 88,
        'Power': 77,
        'Vision': 84,
        'Duels': 72,
        'Flair': 95,
      },
      storyMoments: <String>[
        'Breakout hat-trick on continental debut.',
        'Won Golden Regen after a viral solo goal.',
        'Triggered a seven-club bidding war in one weekend.',
      ],
      careerMoments: <String>[
        'Rose from academy wildcard to first-team starter.',
        'Captured youth league MVP at age 17.',
        'Now leads the broadcast highlight reel in dribble volume.',
      ],
      offers: <GtexOfferData>[
        GtexOfferData(title: 'Highest bid', valueLabel: '2.6M', status: 'Live'),
        GtexOfferData(
          title: 'Contract package',
          valueLabel: '700K/yr',
          status: 'Review',
        ),
      ],
    ),
    GtexPlayerCardData(
      id: 'regen-mika',
      name: 'Mika Toure',
      position: 'CM',
      country: 'Senegal',
      clubName: 'Dakar Surge',
      age: 20,
      rating: 84,
      potential: 92,
      price: 2100000,
      bidStatus: 'Highest bid placed',
      timerLabel: '5h left',
      badges: <String>['🧬', '🎯'],
      attributes: <String, int>{
        'Pace': 80,
        'Technique': 89,
        'Power': 78,
        'Vision': 91,
        'Duels': 84,
        'Flair': 82,
      },
      storyMoments: <String>[
        'Controlled a cup final with 94% pass completion.',
        'Turned a title race with a stoppage-time through ball.',
        'Shortlisted by every federation scouting cell.',
      ],
      careerMoments: <String>[
        'Signed from local youth circuits.',
        'Became vice captain at age 19.',
        'Anchored the best midfield in the west bracket.',
      ],
      offers: <GtexOfferData>[
        GtexOfferData(title: 'Highest bid', valueLabel: '2.3M', status: 'Live'),
        GtexOfferData(
          title: 'Contract package',
          valueLabel: '620K/yr',
          status: 'Negotiating',
        ),
      ],
    ),
    GtexPlayerCardData(
      id: 'regen-sori',
      name: 'Sori Baptiste',
      position: 'CB',
      country: 'Cameroon',
      clubName: 'Port Valiants',
      age: 21,
      rating: 82,
      potential: 90,
      price: 1750000,
      bidStatus: 'Scout report pending',
      timerLabel: '7h left',
      badges: <String>['🧬', '🛡️'],
      attributes: <String, int>{
        'Pace': 76,
        'Technique': 74,
        'Power': 90,
        'Vision': 72,
        'Duels': 92,
        'Flair': 69,
      },
      storyMoments: <String>[
        'Won 13 aerial duels in a derby.',
        'Locked down the tournament top scorer in the semi.',
        'Scouts now rate him as an elite defender ceiling.',
      ],
      careerMoments: <String>[
        'Converted from defensive midfielder at 18.',
        'Named best defender in the federation shield.',
        'Now fronting every tactical set-piece briefing.',
      ],
      offers: <GtexOfferData>[
        GtexOfferData(title: 'Highest bid', valueLabel: '1.9M', status: 'Live'),
        GtexOfferData(
          title: 'Contract package',
          valueLabel: '500K/yr',
          status: 'Prepared',
        ),
      ],
    ),
    GtexPlayerCardData(
      id: 'regen-lia',
      name: 'Lia Costa',
      position: 'SS',
      country: 'Angola',
      clubName: 'Luanda Engines',
      age: 18,
      rating: 80,
      potential: 91,
      price: 1600000,
      bidStatus: 'Open for bids',
      timerLabel: '2h left',
      badges: <String>['🧬', '🔥'],
      attributes: <String, int>{
        'Pace': 88,
        'Technique': 86,
        'Power': 71,
        'Vision': 83,
        'Duels': 68,
        'Flair': 92,
      },
      storyMoments: <String>[
        'Scored on debut from outside the box.',
        'Won Young Storyline of the Month.',
        'Set the community hub on fire with a solo clip.',
      ],
      careerMoments: <String>[
        'Fast-tracked through the national youth camp.',
        'Became the youngest scorer in club history.',
        'Now carries a two-competition highlight streak.',
      ],
      offers: <GtexOfferData>[
        GtexOfferData(title: 'Highest bid', valueLabel: '1.8M', status: 'Live'),
        GtexOfferData(
          title: 'Contract package',
          valueLabel: '410K/yr',
          status: 'Drafted',
        ),
      ],
    ),
    GtexPlayerCardData(
      id: 'regen-kofi',
      name: 'Kofi Mensimah',
      position: 'LB',
      country: 'Ghana',
      clubName: 'Cape Comets',
      age: 22,
      rating: 81,
      potential: 88,
      price: 1450000,
      bidStatus: 'Interest rising',
      timerLabel: '9h left',
      badges: <String>['🔥', '⚡'],
      attributes: <String, int>{
        'Pace': 87,
        'Technique': 79,
        'Power': 80,
        'Vision': 78,
        'Duels': 85,
        'Flair': 75,
      },
      storyMoments: <String>[
        'Pocketed an elite winger in a cup upset.',
        'Turned a replay with a last-ditch recovery tackle.',
        'Popularity jumped after a viral touchline sprint.',
      ],
      careerMoments: <String>[
        'Rebuilt as an inverted fullback.',
        'Earned team of the season honors last year.',
        'Now attracts live-market alerts every night.',
      ],
      offers: <GtexOfferData>[
        GtexOfferData(title: 'Highest bid', valueLabel: '1.6M', status: 'Live'),
        GtexOfferData(
          title: 'Contract package',
          valueLabel: '360K/yr',
          status: 'Review',
        ),
      ],
    ),
    GtexPlayerCardData(
      id: 'regen-ibra',
      name: 'Ibra Diallo',
      position: 'GK',
      country: 'Mali',
      clubName: 'Sahara Royals',
      age: 23,
      rating: 79,
      potential: 87,
      price: 1320000,
      bidStatus: 'Contract only',
      timerLabel: '1d left',
      badges: <String>['🧤', '🌟'],
      attributes: <String, int>{
        'Pace': 62,
        'Technique': 72,
        'Power': 83,
        'Vision': 79,
        'Duels': 88,
        'Flair': 64,
      },
      storyMoments: <String>[
        'Saved two penalties in a title decider.',
        'Posted the league’s best post-shot xG prevention mark.',
        'Became a fan hero after a stoppage-time double save.',
      ],
      careerMoments: <String>[
        'Promoted from backup after an injury crisis.',
        'Now leads the clean-sheet table.',
        'Listed as the safest long-term keeper asset.',
      ],
      offers: <GtexOfferData>[
        GtexOfferData(title: 'Highest bid', valueLabel: '1.4M', status: 'Live'),
        GtexOfferData(
          title: 'Contract package',
          valueLabel: '330K/yr',
          status: 'Negotiating',
        ),
      ],
    ),
  ];
}
