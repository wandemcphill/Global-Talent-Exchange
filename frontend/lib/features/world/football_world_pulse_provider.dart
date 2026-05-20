import 'dart:math' as math;

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/community_api.dart';
import '../../data/gte_api_repository.dart';
import '../../features/competitions/live_competitions_provider.dart';
import '../../features/shared/data/gte_feature_support.dart';
import '../../features/streamer_tournament_engine/data/streamer_tournament_engine_models.dart';
import '../../features/transfer_market/live_market_provider.dart';
import '../../models/community_models.dart';
import '../../models/competition_models.dart';
import '../../models/hosted_competition_models.dart';
import '../../shared/providers/auth_provider.dart';
import 'live_world_provider.dart';

class FootballWorldPulseData {
  const FootballWorldPulseData({
    required this.transferTicker,
    required this.globalActivity,
    required this.transferRoutes,
    required this.onlineClubs,
    required this.competitionCountdowns,
    required this.marketMovers,
    required this.discussionPreviews,
    required this.rivalryCards,
    required this.negotiations,
    required this.rankingMovements,
    required this.marketHeat,
    required this.userDensity,
  });

  final List<FootballPulseItem> transferTicker;
  final List<FootballPulseItem> globalActivity;
  final List<FootballPulseRoute> transferRoutes;
  final List<FootballPulseItem> onlineClubs;
  final List<FootballPulseItem> competitionCountdowns;
  final List<FootballPulseItem> marketMovers;
  final List<FootballPulseItem> discussionPreviews;
  final List<FootballPulseItem> rivalryCards;
  final List<FootballPulseItem> negotiations;
  final List<FootballPulseItem> rankingMovements;
  final double marketHeat;
  final double userDensity;

  static const FootballWorldPulseData empty = FootballWorldPulseData(
    transferTicker: <FootballPulseItem>[
      FootballPulseItem(
        label: 'Transfer desk',
        detail: 'Waiting for live listings',
        metric: 'SYNC',
        intensity: 0.24,
      ),
    ],
    globalActivity: <FootballPulseItem>[
      FootballPulseItem(
        label: 'World pulse',
        detail: 'Market, competitions, and scouting rails are online',
        metric: 'LIVE',
        intensity: 0.32,
      ),
    ],
    transferRoutes: <FootballPulseRoute>[],
    onlineClubs: <FootballPulseItem>[],
    competitionCountdowns: <FootballPulseItem>[],
    marketMovers: <FootballPulseItem>[],
    discussionPreviews: <FootballPulseItem>[],
    rivalryCards: <FootballPulseItem>[],
    negotiations: <FootballPulseItem>[],
    rankingMovements: <FootballPulseItem>[],
    marketHeat: 0.24,
    userDensity: 0.28,
  );
}

class FootballPulseItem {
  const FootballPulseItem({
    required this.label,
    required this.detail,
    required this.metric,
    required this.intensity,
  });

  final String label;
  final String detail;
  final String metric;
  final double intensity;
}

class FootballPulseRoute {
  const FootballPulseRoute({
    required this.source,
    required this.destination,
    required this.label,
    required this.intensity,
  });

  final String source;
  final String destination;
  final String label;
  final double intensity;
}

final FutureProvider<FootballWorldPulseData> footballWorldPulseProvider =
    FutureProvider<FootballWorldPulseData>((Ref ref) async {
      if (ref.watch(criticalBackendModeProvider) == GteBackendMode.fixture) {
        return FootballWorldPulseData.empty;
      }
      final Future<MarketDashboardData?> marketFuture = ref
          .watch(marketDashboardProvider.future)
          .then((MarketDashboardData data) => data, onError: (_, _) => null);
      final Future<WorldAggregateData?> worldFuture = ref
          .watch(worldAggregateProvider.future)
          .then((WorldAggregateData data) => data, onError: (_, _) => null);
      final Future<CompetitionHubData?> competitionsFuture = ref
          .watch(competitionHubProvider.future)
          .then((CompetitionHubData data) => data, onError: (_, _) => null);
      final Future<List<LiveThread>> discussionFuture = _loadCommunityThreads(
        ref,
        discussions: true,
      );
      final Future<List<LiveThread>> liveThreadFuture = _loadCommunityThreads(
        ref,
        discussions: false,
      );

      final List<Object?> payloads =
          await Future.wait<Object?>(<Future<Object?>>[
            marketFuture,
            worldFuture,
            competitionsFuture,
            discussionFuture,
            liveThreadFuture,
          ]);
      final MarketDashboardData? market = payloads[0] as MarketDashboardData?;
      final WorldAggregateData? world = payloads[1] as WorldAggregateData?;
      final CompetitionHubData? competitions =
          payloads[2] as CompetitionHubData?;
      final List<LiveThread> discussions =
          (payloads[3] as List<LiveThread>?) ?? const <LiveThread>[];
      final List<LiveThread> liveThreads =
          (payloads[4] as List<LiveThread>?) ?? const <LiveThread>[];

      return FootballWorldPulseData(
        transferTicker: _transferTicker(market),
        globalActivity: _globalActivity(world, competitions, liveThreads),
        transferRoutes: _transferRoutes(market),
        onlineClubs: _onlineClubIndicators(competitions),
        competitionCountdowns: _competitionCountdowns(competitions),
        marketMovers: _marketMovers(market, world),
        discussionPreviews: _discussionPreviews(discussions, liveThreads),
        rivalryCards: _rivalryCards(discussions, liveThreads),
        negotiations: _negotiations(market),
        rankingMovements: _rankingMovements(world),
        marketHeat: _marketHeat(market),
        userDensity: _userDensity(competitions, liveThreads),
      );
    });

Future<List<LiveThread>> _loadCommunityThreads(
  Ref ref, {
  required bool discussions,
}) async {
  try {
    final mode = ref.watch(criticalBackendModeProvider);
    final CommunityApi api = CommunityApi.standard(
      baseUrl: ref.watch(apiBaseUrlProvider),
      accessToken: ref.watch(authProvider)?.accessToken,
      mode: mode,
      transport: createModeAwareTransport(mode),
    );
    return discussions ? api.listDiscussionThreads() : api.listLiveThreads();
  } catch (_) {
    return const <LiveThread>[];
  }
}

List<FootballPulseItem> _transferTicker(MarketDashboardData? market) {
  final List<TransferListingSummary> listings =
      market?.transferListings ?? const <TransferListingSummary>[];
  final List<FootballPulseItem> items = listings
      .take(6)
      .map(
        (TransferListingSummary listing) => FootballPulseItem(
          label: listing.playerName,
          detail:
              '${listing.currentClubName ?? 'Open market'} - ${listing.marketSignal}',
          metric: _formatCoin(
            math.max(listing.currentHighestBid, listing.basePrice),
          ),
          intensity: _clamp01(
            (listing.bidCount + listing.watchlistCount + 1) / 18,
          ),
        ),
      )
      .toList(growable: false);
  return items.isEmpty ? FootballWorldPulseData.empty.transferTicker : items;
}

List<FootballPulseItem> _globalActivity(
  WorldAggregateData? world,
  CompetitionHubData? competitions,
  List<LiveThread> liveThreads,
) {
  final int scoutingCount = world?.scoutingFeed.length ?? 0;
  final int risingCount = world?.risingStars.length ?? 0;
  final int competitionCount =
      (competitions?.gtexCompetitions.length ?? 0) +
      (competitions?.userCompetitions.length ?? 0) +
      (competitions?.streamerTournaments.length ?? 0);
  final List<FootballPulseItem> items = <FootballPulseItem>[
    FootballPulseItem(
      label: 'Scouting desk',
      detail: '$scoutingCount notes moving through the global feed',
      metric: '$scoutingCount reports',
      intensity: _clamp01(scoutingCount / 12),
    ),
    FootballPulseItem(
      label: 'Regen market',
      detail: '$risingCount rising profiles tracked by the world desk',
      metric: '$risingCount movers',
      intensity: _clamp01(risingCount / 12),
    ),
    FootballPulseItem(
      label: 'Competition grid',
      detail: '$competitionCount live or scheduled competitions visible',
      metric: '$competitionCount lanes',
      intensity: _clamp01(competitionCount / 16),
    ),
    FootballPulseItem(
      label: 'Club rooms',
      detail: '${liveThreads.length} public football discussions active',
      metric: '${liveThreads.length} threads',
      intensity: _clamp01(liveThreads.length / 10),
    ),
  ];
  return items;
}

List<FootballPulseRoute> _transferRoutes(MarketDashboardData? market) {
  final List<TransferListingSummary> listings =
      market?.transferListings ?? const <TransferListingSummary>[];
  return listings
      .take(5)
      .map(
        (TransferListingSummary listing) => FootballPulseRoute(
          source: listing.currentClubName ?? 'Open pool',
          destination:
              listing.channel.trim().isEmpty
                  ? 'Transfer room'
                  : listing.channel,
          label: listing.playerName,
          intensity: _clamp01(
            (listing.bidCount + listing.watchlistCount + 1) / 16,
          ),
        ),
      )
      .toList(growable: false);
}

List<FootballPulseItem> _onlineClubIndicators(
  CompetitionHubData? competitions,
) {
  final List<CompetitionSummary> online = <CompetitionSummary>[
    ...?competitions?.gtexCompetitions.where(
      (CompetitionSummary item) => item.onlineNow,
    ),
    ...?competitions?.userCompetitions.where(
      (CompetitionSummary item) => item.onlineNow,
    ),
  ];
  return online
      .take(4)
      .map(
        (CompetitionSummary item) => FootballPulseItem(
          label: item.name,
          detail: '${item.participantCount}/${item.capacity} clubs present',
          metric: 'ONLINE',
          intensity: _clamp01(
            item.participantCount / math.max(1, item.capacity),
          ),
        ),
      )
      .toList(growable: false);
}

List<FootballPulseItem> _competitionCountdowns(CompetitionHubData? data) {
  final List<FootballPulseItem> items = <FootballPulseItem>[
    ...?data?.gtexCompetitions.map(_competitionCountdownItem),
    ...?data?.userCompetitions.map(_competitionCountdownItem),
    ...?data?.hostedCompetitions.map(_hostedCountdownItem),
    ...?data?.streamerTournaments.map(_streamerCountdownItem),
  ];
  items.sort(
    (FootballPulseItem left, FootballPulseItem right) =>
        right.intensity.compareTo(left.intensity),
  );
  return items.take(5).toList(growable: false);
}

FootballPulseItem _competitionCountdownItem(CompetitionSummary item) {
  final DateTime? target = item.scheduledStartAt ?? item.registrationDeadline;
  return FootballPulseItem(
    label: item.name,
    detail:
        '${item.participantCount}/${item.capacity} clubs - ${item.status.name}',
    metric: _relativeTime(target),
    intensity: _countdownIntensity(
      target,
      item.participantCount,
      item.capacity,
    ),
  );
}

FootballPulseItem _hostedCountdownItem(HostedCompetition item) {
  final int expectedClubs = math.max(1, item.maxParticipants);
  return FootballPulseItem(
    label: item.title,
    detail: '$expectedClubs club slots - ${item.status}',
    metric: _relativeTime(item.startsAt),
    intensity: _countdownIntensity(item.startsAt, 1, expectedClubs),
  );
}

FootballPulseItem _streamerCountdownItem(StreamerTournament item) {
  final int entrants = item.entries.length;
  final int capacity = math.max(1, item.maxParticipants);
  return FootballPulseItem(
    label: item.title,
    detail: '$entrants/$capacity creator clubs - ${item.status}',
    metric: _relativeTime(item.startsAt),
    intensity: _countdownIntensity(item.startsAt, entrants, capacity),
  );
}

List<FootballPulseItem> _marketMovers(
  MarketDashboardData? market,
  WorldAggregateData? world,
) {
  final List<PlayerShareSummary> players =
      market?.tradablePlayerShares ?? const <PlayerShareSummary>[];
  final List<PlayerShareSummary> sorted = List<PlayerShareSummary>.of(players)
    ..sort(
      (PlayerShareSummary left, PlayerShareSummary right) =>
          (right.marketInterestScore ?? 0).compareTo(
            left.marketInterestScore ?? 0,
          ),
    );
  final List<FootballPulseItem> items = sorted
      .take(4)
      .map(
        (PlayerShareSummary player) => FootballPulseItem(
          label: player.playerName,
          detail:
              '${player.currentClubName ?? 'Club syncing'} - ${player.marketMessage}',
          metric:
              player.sharePriceCoin == null
                  ? '${player.marketInterestScore ?? 0} heat'
                  : _formatCoin(player.sharePriceCoin!),
          intensity: _clamp01((player.marketInterestScore ?? 0) / 100),
        ),
      )
      .toList(growable: true);
  if (items.isEmpty) {
    items.addAll(
      (world?.risingStars ?? const <JsonMap>[])
          .take(4)
          .map(
            (JsonMap item) => FootballPulseItem(
              label: _jsonLabel(item, const <String>[
                'player_name',
                'playerName',
                'name',
              ], fallback: 'Rising regen'),
              detail: _jsonLabel(item, const <String>[
                'position',
                'nationality',
                'club_name',
              ], fallback: 'World scouting movement'),
              metric: 'TREND',
              intensity: 0.48,
            ),
          ),
    );
  }
  return items.take(4).toList(growable: false);
}

List<FootballPulseItem> _discussionPreviews(
  List<LiveThread> discussions,
  List<LiveThread> liveThreads,
) {
  final List<LiveThread> threads = <LiveThread>[...discussions, ...liveThreads]
    ..sort(
      (LiveThread left, LiveThread right) =>
          (right.lastMessageAt ?? right.updatedAt).compareTo(
            left.lastMessageAt ?? left.updatedAt,
          ),
    );
  return threads
      .take(4)
      .map(
        (LiveThread thread) => FootballPulseItem(
          label: thread.title,
          detail:
              '${thread.category} - ${thread.status.toUpperCase()} - ${_relativeTime(thread.lastMessageAt)}',
          metric: thread.trendScore > 0 ? '+${thread.trendScore}' : 'LIVE',
          intensity: _clamp01(
            (thread.trendScore + (thread.pinned ? 8 : 0)) / 24,
          ),
        ),
      )
      .toList(growable: false);
}

List<FootballPulseItem> _rivalryCards(
  List<LiveThread> discussions,
  List<LiveThread> liveThreads,
) {
  final List<LiveThread> rivalryThreads = <LiveThread>[
        ...discussions,
        ...liveThreads,
      ]
      .where((LiveThread thread) {
        final String text =
            '${thread.title} ${thread.body} ${thread.threadKey} ${thread.category}'
                .toLowerCase();
        return text.contains('derby') ||
            text.contains('rival') ||
            text.contains('matchday');
      })
      .toList(growable: false);
  return rivalryThreads
      .take(3)
      .map(
        (LiveThread thread) => FootballPulseItem(
          label: thread.title,
          detail:
              thread.body.trim().isEmpty
                  ? 'Rivalry activity lane'
                  : thread.body,
          metric: thread.pinned ? 'PINNED' : 'ACTIVE',
          intensity: _clamp01((thread.trendScore + 8) / 24),
        ),
      )
      .toList(growable: false);
}

List<FootballPulseItem> _negotiations(MarketDashboardData? market) {
  final List<TransferListingSummary> listings =
      market?.transferListings ?? const <TransferListingSummary>[];
  final List<TransferListingSummary> sorted = List<TransferListingSummary>.of(
    listings,
  )..sort(
    (TransferListingSummary left, TransferListingSummary right) =>
        (right.bidCount + right.watchlistCount).compareTo(
          left.bidCount + left.watchlistCount,
        ),
  );
  return sorted
      .take(4)
      .map(
        (TransferListingSummary listing) => FootballPulseItem(
          label: listing.playerName,
          detail:
              '${listing.bidCount} bids - ${listing.watchlistCount} watchlists - ${listing.status}',
          metric: _relativeSeconds(listing.timeRemaining),
          intensity: _clamp01((listing.bidCount + listing.watchlistCount) / 18),
        ),
      )
      .toList(growable: false);
}

List<FootballPulseItem> _rankingMovements(WorldAggregateData? world) {
  final List<JsonMap> candidates = <JsonMap>[
    ...?world?.risingStars,
    ...?world?.hallOfFame,
  ];
  return candidates
      .take(4)
      .map(
        (JsonMap item) => FootballPulseItem(
          label: _jsonLabel(item, const <String>[
            'player_name',
            'playerName',
            'name',
          ], fallback: 'Tracked profile'),
          detail: _jsonLabel(item, const <String>[
            'position',
            'nationality',
            'legacy_tier',
          ], fallback: 'Ranking movement'),
          metric: _jsonLabel(item, const <String>[
            'rank_delta',
            'movement',
            'rank',
          ], fallback: '+1'),
          intensity: 0.5,
        ),
      )
      .toList(growable: false);
}

double _marketHeat(MarketDashboardData? market) {
  final int listingPressure = (market?.transferListings ??
          const <TransferListingSummary>[])
      .fold<int>(0, (int total, TransferListingSummary item) {
        return total + item.bidCount + item.watchlistCount;
      });
  final int playerPressure = (market?.tradablePlayerShares ??
          const <PlayerShareSummary>[])
      .fold<int>(0, (int total, PlayerShareSummary item) {
        return total + (item.marketInterestScore ?? 0);
      });
  return _clamp01((listingPressure / 42) + (playerPressure / 600));
}

double _userDensity(
  CompetitionHubData? competitions,
  List<LiveThread> threads,
) {
  final int participants =
      (competitions?.gtexCompetitions ?? const <CompetitionSummary>[])
          .fold<int>(
            0,
            (int total, CompetitionSummary item) =>
                total + item.participantCount,
          ) +
      (competitions?.userCompetitions ?? const <CompetitionSummary>[])
          .fold<int>(
            0,
            (int total, CompetitionSummary item) =>
                total + item.participantCount,
          ) +
      (competitions?.streamerTournaments ?? const <StreamerTournament>[])
          .fold<int>(
            0,
            (int total, StreamerTournament item) => total + item.entries.length,
          );
  return _clamp01((participants / 96) + (threads.length / 16));
}

String _jsonLabel(JsonMap item, List<String> keys, {required String fallback}) {
  for (final String key in keys) {
    final String value = stringValue(item[key]);
    if (value.isNotEmpty) {
      return value;
    }
  }
  return fallback;
}

String _formatCoin(double value) {
  if (value <= 0) {
    return 'opening';
  }
  final String formatted =
      value >= 100
          ? value.toStringAsFixed(0)
          : value.toStringAsFixed(value == value.roundToDouble() ? 0 : 1);
  return '$formatted GTEX Coin';
}

String _relativeSeconds(int seconds) {
  if (seconds <= 0) {
    return 'closing';
  }
  if (seconds < 3600) {
    return '${(seconds / 60).ceil()}m';
  }
  return '${(seconds / 3600).ceil()}h';
}

String _relativeTime(DateTime? value) {
  if (value == null) {
    return 'live';
  }
  final Duration delta = value.toUtc().difference(DateTime.now().toUtc());
  if (delta.inSeconds.abs() < 60) {
    return 'now';
  }
  if (delta.isNegative) {
    final Duration ago = delta.abs();
    if (ago.inHours < 24) {
      return '${ago.inHours.clamp(1, 23)}h ago';
    }
    return '${ago.inDays}d ago';
  }
  if (delta.inHours < 24) {
    return 'T-${delta.inHours.clamp(1, 23)}h';
  }
  return 'T-${delta.inDays}d';
}

double _countdownIntensity(DateTime? value, int participants, int capacity) {
  final double fill = participants / math.max(1, capacity);
  if (value == null) {
    return _clamp01(fill);
  }
  final int hours = value.toUtc().difference(DateTime.now().toUtc()).inHours;
  final double urgency = hours <= 0 ? 0.6 : 1 / math.max(1, hours);
  return _clamp01(fill + urgency);
}

double _clamp01(double value) => value.clamp(0.0, 1.0).toDouble();
