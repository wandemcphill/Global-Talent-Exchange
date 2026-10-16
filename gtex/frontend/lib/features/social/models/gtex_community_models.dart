import 'package:flutter/foundation.dart';

import '../../../data/gte_exchange_models.dart';
import '../../../data/gte_models.dart';
import '../../../domain/ownership/gtex_ownership_models.dart';
import '../../../domain/value/gtex_value_models.dart';
import '../../club_redesign/models/gtex_club_ownership_models.dart';
import '../../regen_redesign/models/gtex_regen_wire_models.dart';
import '../data/gtex_community_social_models.dart';

/// The football object a community signal is about.
///
/// GTEX community is organised around football objects, not user profiles:
/// every signal names a player, a club, a challenge or a market event that
/// already exists in the economy.
enum GtexCommunityObject { player, club, challenge, market }

/// Why a signal is in front of this user.
///
/// [world] is what is happening in the GTEX economy at large and is visible
/// signed out. [yours] is activity on something the signed-in user owns or
/// follows.
enum GtexCommunityLane { world, yours }

/// What the user can do next about a signal.
///
/// A signal that implies an action must carry one of these; a signal with
/// [GtexCommunityAction.none] renders as a statement with no dead control.
enum GtexCommunityAction { none, openPlayer, openClub, openMarket, openRegens }

/// One thing that happened in the GTEX football economy.
///
/// Every field on a signal traces to a published backend value. There is no
/// synthesised popularity, no "trending" language over a weak proxy, and no
/// count that stands in for a number the backend did not send: when a count
/// is unknown [socialProof] is simply `null`, never `"0 owners"`.
@immutable
class GtexCommunitySignal {
  const GtexCommunitySignal({
    required this.id,
    required this.object,
    required this.lane,
    required this.headline,
    required this.detail,
    this.socialProof,
    this.action = GtexCommunityAction.none,
    this.playerId,
    this.clubId,
    this.movementPercent,
    this.occurredAt,
    this.isFollowable = false,
  });

  final String id;
  final GtexCommunityObject object;
  final GtexCommunityLane lane;

  /// What happened, in one line.
  final String headline;

  /// Why it matters, in one line.
  final String detail;

  /// A real backend quantity that shows the user they are not alone -
  /// a holder count, an owner count, a share-event count. `null` when the
  /// backend did not publish one.
  final String? socialProof;

  final GtexCommunityAction action;
  final String? playerId;
  final String? clubId;

  /// Signed day movement, when the signal is a market move. Used only for
  /// ordering and tone; the copy already carries the number.
  final double? movementPercent;

  final DateTime? occurredAt;

  /// Whether this signal names a football object the user can follow through
  /// the existing `/api/social/follows` contract.
  final bool isFollowable;

  /// The follow target for this signal, or `null` when it names no followable
  /// object.
  GtexCommunityFollowTarget? get followTarget {
    if (!isFollowable) {
      return null;
    }
    final String? player = playerId;
    if (player != null && player.isNotEmpty) {
      return GtexCommunityFollowTarget.player(player);
    }
    final String? club = clubId;
    if (club != null && club.isNotEmpty) {
      return GtexCommunityFollowTarget.club(club);
    }
    return null;
  }
}

/// A `(target_type, id)` pair addressing the existing social-follow contract.
@immutable
class GtexCommunityFollowTarget {
  const GtexCommunityFollowTarget._(this.targetType, this.id);

  factory GtexCommunityFollowTarget.player(String playerId) =>
      GtexCommunityFollowTarget._('player', playerId);

  factory GtexCommunityFollowTarget.club(String clubId) =>
      GtexCommunityFollowTarget._('club', clubId);

  final String targetType;
  final String id;

  String get key => '$targetType:$id';

  @override
  bool operator ==(Object other) =>
      other is GtexCommunityFollowTarget &&
      other.targetType == targetType &&
      other.id == id;

  @override
  int get hashCode => Object.hash(targetType, id);
}

/// How much of the community layer this session can actually see.
enum GtexCommunityAccess {
  /// Signed out: the world lane only, with an honest sign-in prompt.
  anonymous,

  /// Signed in with a live session: both lanes.
  authenticated,
}

/// The composed community surface.
///
/// A source that failed contributes a line to [warnings] and nothing else -
/// it never blanks the sources that did load, and it never degrades into a
/// zero.
@immutable
class GtexCommunityPulse {
  const GtexCommunityPulse({
    required this.access,
    required this.headline,
    this.worldSignals = const <GtexCommunitySignal>[],
    this.yourSignals = const <GtexCommunitySignal>[],
    this.followedTargets = const <GtexCommunityFollowTarget>{},
    this.warnings = const <String>[],
  });

  factory GtexCommunityPulse.anonymous({
    List<GtexCommunitySignal> worldSignals = const <GtexCommunitySignal>[],
    List<String> warnings = const <String>[],
  }) {
    return GtexCommunityPulse(
      access: GtexCommunityAccess.anonymous,
      headline: buildGtexCommunityHeadline(
        access: GtexCommunityAccess.anonymous,
        worldSignals: worldSignals,
        yourSignals: const <GtexCommunitySignal>[],
      ),
      worldSignals: worldSignals,
      warnings: warnings,
    );
  }

  final GtexCommunityAccess access;
  final String headline;
  final List<GtexCommunitySignal> worldSignals;
  final List<GtexCommunitySignal> yourSignals;
  final Set<GtexCommunityFollowTarget> followedTargets;
  final List<String> warnings;

  bool get isAuthenticated => access == GtexCommunityAccess.authenticated;

  bool get isEmpty => worldSignals.isEmpty && yourSignals.isEmpty;

  bool follows(GtexCommunityFollowTarget? target) =>
      target != null && followedTargets.contains(target);
}

/// Hard bounds on how much a single community load may render.
///
/// The community surface is a bounded digest, not an infinite feed: the
/// backing endpoints publish no cursor, so paging would have to be faked.
const int gtexCommunityWorldSignalLimit = 8;
const int gtexCommunityYourSignalLimit = 10;

/// How many owned players get an individual holder-count / form lookup.
/// Kept small so the surface never becomes an N+1 over a whole portfolio.
const int gtexCommunityPlayerLookupLimit = 3;

/// How many of the user's club holdings are asked for challenge activity.
const int gtexCommunityClubLookupLimit = 3;

/// A real owner count, or `null` when the backend published none.
///
/// `null` here means *unknown*, and callers must render it as absence rather
/// than as `0 owners` - the difference between "nobody holds this" and "we
/// were not told" is the difference between a fact and a fabrication.
String? gtexCommunityHolderProof(int? holderCount, {required String noun}) {
  if (holderCount == null || holderCount <= 0) {
    return null;
  }
  return '$holderCount $noun${holderCount == 1 ? '' : 's'}';
}

/// The world lane: what is moving in the GTEX market right now.
///
/// Built only from `GET /api/market/movers`, which is public, so this lane is
/// identical signed in and signed out. Movers are deduplicated by player -
/// the same footballer can appear in gainers, trending and most-traded at
/// once - and ordered by the size of the real day move.
List<GtexCommunitySignal> buildGtexCommunityWorldSignals(
  GteMarketMovers movers, {
  Map<String, int?> holderCountByPlayerId = const <String, int?>{},
  int limit = gtexCommunityWorldSignalLimit,
}) {
  final Map<String, GteMarketMoverItem> deduped =
      <String, GteMarketMoverItem>{};
  for (final GteMarketMoverItem item in <GteMarketMoverItem>[
    ...movers.topGainers,
    ...movers.topLosers,
    ...movers.mostTraded,
    ...movers.trending,
  ]) {
    deduped.putIfAbsent(item.playerId, () => item);
  }
  final List<GteMarketMoverItem> ordered = deduped.values.toList()
    ..sort(
      (GteMarketMoverItem a, GteMarketMoverItem b) =>
          b.dayChangePercent.abs().compareTo(a.dayChangePercent.abs()),
    );

  return ordered
      .where((GteMarketMoverItem item) => item.dayChangePercent != 0)
      .take(limit)
      .map(
        (GteMarketMoverItem item) => GtexCommunitySignal(
          id: 'world-market-${item.playerId}',
          object: GtexCommunityObject.market,
          lane: GtexCommunityLane.world,
          headline:
              '${item.playerName} moved ${gtexCommunitySignedPercent(item.dayChangePercent)}',
          detail: 'Player market value, last 24 hours.',
          socialProof: gtexCommunityHolderProof(
            holderCountByPlayerId[item.playerId],
            noun: 'owner',
          ),
          action: GtexCommunityAction.openPlayer,
          playerId: item.playerId,
          movementPercent: item.dayChangePercent,
          isFollowable: true,
        ),
      )
      .toList(growable: false);
}

/// The "your community" lane: activity on football objects this user owns or
/// follows.
///
/// Ordering is deterministic and product-led rather than chronological,
/// because the sources publish incompatible clocks: owned-player market moves
/// first (largest move first), then matchday form, then clubs, then club
/// challenges, then regens, then settled ownership changes.
List<GtexCommunitySignal> buildGtexCommunityYourSignals({
  required GtexOwnershipBook ownership,
  required GteMarketMovers movers,
  Map<String, int?> holderCountByPlayerId = const <String, int?>{},
  Map<String, GtexPlayerForm> formByPlayerId =
      const <String, GtexPlayerForm>{},
  List<GtexClubShareHolding> clubHoldings = const <GtexClubShareHolding>[],
  List<GtexClubChallengeCard> challenges = const <GtexClubChallengeCard>[],
  List<RegenRankingEntry> regenRankings = const <RegenRankingEntry>[],
  GteOrderListView? orders,
  Set<GtexCommunityFollowTarget> followedTargets =
      const <GtexCommunityFollowTarget>{},
  int limit = gtexCommunityYourSignalLimit,
}) {
  final List<GtexCommunitySignal> signals = <GtexCommunitySignal>[];

  signals.addAll(
    _ownedMarketSignals(
      ownership: ownership,
      movers: movers,
      holderCountByPlayerId: holderCountByPlayerId,
      followedTargets: followedTargets,
    ),
  );
  signals.addAll(
    _matchdayFormSignals(
      ownership: ownership,
      formByPlayerId: formByPlayerId,
      holderCountByPlayerId: holderCountByPlayerId,
    ),
  );
  signals.addAll(_clubSignals(clubHoldings));
  signals.addAll(_challengeSignals(challenges));
  signals.addAll(_regenSignals(ownership: ownership, rankings: regenRankings));
  if (orders != null) {
    signals.addAll(
      _ownershipChangeSignals(orders: orders, ownership: ownership),
    );
  }

  final Set<String> seen = <String>{};
  return signals
      .where((GtexCommunitySignal signal) => seen.add(signal.id))
      .take(limit)
      .toList(growable: false);
}

List<GtexCommunitySignal> _ownedMarketSignals({
  required GtexOwnershipBook ownership,
  required GteMarketMovers movers,
  required Map<String, int?> holderCountByPlayerId,
  required Set<GtexCommunityFollowTarget> followedTargets,
}) {
  final Map<String, GteMarketMoverItem> deduped =
      <String, GteMarketMoverItem>{};
  for (final GteMarketMoverItem item in <GteMarketMoverItem>[
    ...movers.topGainers,
    ...movers.topLosers,
    ...movers.mostTraded,
    ...movers.trending,
  ]) {
    deduped.putIfAbsent(item.playerId, () => item);
  }
  final List<GteMarketMoverItem> relevant = deduped.values
      .where(
        (GteMarketMoverItem item) =>
            item.dayChangePercent != 0 &&
            (ownership.owns(item.playerId) ||
                followedTargets.contains(
                  GtexCommunityFollowTarget.player(item.playerId),
                )),
      )
      .toList()
    ..sort(
      (GteMarketMoverItem a, GteMarketMoverItem b) =>
          b.dayChangePercent.abs().compareTo(a.dayChangePercent.abs()),
    );

  return relevant.map((GteMarketMoverItem item) {
    final bool owned = ownership.owns(item.playerId);
    final GtexOwnershipStake? stake = ownership.stakeFor(item.playerId);
    return GtexCommunitySignal(
      id: 'yours-market-${item.playerId}',
      object: GtexCommunityObject.player,
      lane: GtexCommunityLane.yours,
      headline:
          '${stake?.playerName ?? item.playerName} moved '
          '${gtexCommunitySignedPercent(item.dayChangePercent)}',
      detail: owned
          ? (stake == null ? 'A player you own.' : '${stake.ownershipLabel}.')
          : 'A player you follow.',
      socialProof: gtexCommunityHolderProof(
        holderCountByPlayerId[item.playerId],
        noun: 'owner',
      ),
      action: GtexCommunityAction.openPlayer,
      playerId: item.playerId,
      movementPercent: item.dayChangePercent,
      isFollowable: true,
    );
  }).toList(growable: false);
}

List<GtexCommunitySignal> _matchdayFormSignals({
  required GtexOwnershipBook ownership,
  required Map<String, GtexPlayerForm> formByPlayerId,
  required Map<String, int?> holderCountByPlayerId,
}) {
  final List<GtexCommunitySignal> signals = <GtexCommunitySignal>[];
  for (final MapEntry<String, GtexPlayerForm> entry
      in formByPlayerId.entries) {
    final GtexPlayerForm form = entry.value;
    final GtexMatchdaySignal? signal = form.signal;
    // Only a *applied* valuation signal is a football event worth telling an
    // owner about. An unapplied signal is Phase 4E saying "not enough
    // football yet", which is not news.
    if (signal == null || !signal.applied) {
      continue;
    }
    final GtexOwnershipStake? stake = ownership.stakeFor(entry.key);
    signals.add(
      GtexCommunitySignal(
        id: 'yours-form-${entry.key}',
        object: GtexCommunityObject.player,
        lane: GtexCommunityLane.yours,
        headline:
            '${stake?.playerName ?? entry.key} matchday form '
            '${gtexCommunitySignedPercent(signal.adjustmentPct)}',
        detail:
            '${signal.matchesCounted} match'
            '${signal.matchesCounted == 1 ? '' : 'es'} counted across '
            '${signal.competitionsCounted} competition'
            '${signal.competitionsCounted == 1 ? '' : 's'}.',
        socialProof: gtexCommunityHolderProof(
          holderCountByPlayerId[entry.key],
          noun: 'owner',
        ),
        action: GtexCommunityAction.openPlayer,
        playerId: entry.key,
        isFollowable: true,
      ),
    );
  }
  signals.sort(
    (GtexCommunitySignal a, GtexCommunitySignal b) =>
        a.headline.compareTo(b.headline),
  );
  return signals;
}

List<GtexCommunitySignal> _clubSignals(
  List<GtexClubShareHolding> holdings,
) {
  return holdings.map((GtexClubShareHolding holding) {
    final String movement = holding.unrealizedPlPercent == null
        ? 'Share position open'
        : 'Your position ${gtexCommunitySignedPercent(holding.unrealizedPlPercent!)}';
    // `hasPerformanceHistory` is PHASE4-D's own honesty flag: without it the
    // club has not played enough GTEX football for a form read, and claiming
    // one would be an invention.
    final String performance = holding.hasPerformanceHistory
        ? 'Club form is feeding the share price.'
        : 'No club match history yet, so no performance signal.';
    return GtexCommunitySignal(
      id: 'yours-club-${holding.clubId}',
      object: GtexCommunityObject.club,
      lane: GtexCommunityLane.yours,
      headline: '${holding.clubName}: $movement',
      detail: performance,
      socialProof: gtexCommunityHolderProof(
        holding.holderCount,
        noun: 'owner',
      ),
      action: GtexCommunityAction.openClub,
      clubId: holding.clubId,
      movementPercent: holding.unrealizedPlPercent,
      isFollowable: true,
    );
  }).toList(growable: false);
}

List<GtexCommunitySignal> _challengeSignals(
  List<GtexClubChallengeCard> challenges,
) {
  return challenges.map((GtexClubChallengeCard card) {
    final String opponent = card.opponentClubName ?? 'an open opponent';
    return GtexCommunitySignal(
      id: 'yours-challenge-${card.challengeId}',
      object: GtexCommunityObject.challenge,
      lane: GtexCommunityLane.yours,
      headline: '${card.issuingClubName} challenged $opponent',
      detail: card.stakesText == null || card.stakesText!.trim().isEmpty
          ? '${card.title} - ${card.status}.'
          : '${card.title} - ${card.status}. Stakes: ${card.stakesText}.',
      socialProof: gtexCommunityHolderProof(card.shareCount, noun: 'share'),
      action: GtexCommunityAction.openClub,
      clubId: card.issuingClubId,
    );
  }).toList(growable: false);
}

List<GtexCommunitySignal> _regenSignals({
  required GtexOwnershipBook ownership,
  required List<RegenRankingEntry> rankings,
}) {
  final List<RegenRankingEntry> owned = rankings
      .where((RegenRankingEntry entry) => ownership.owns(entry.playerId))
      .toList()
    ..sort(
      (RegenRankingEntry a, RegenRankingEntry b) => a.rank.compareTo(b.rank),
    );
  return owned
      .map(
        (RegenRankingEntry entry) => GtexCommunitySignal(
          id: 'yours-regen-${entry.playerId}',
          object: GtexCommunityObject.player,
          lane: GtexCommunityLane.yours,
          headline:
              '${entry.playerName} is ranked #${entry.rank} in ${entry.category}',
          detail: 'A regen you own is on the Regen World board.',
          action: GtexCommunityAction.openRegens,
          playerId: entry.playerId,
          isFollowable: true,
        ),
      )
      .toList(growable: false);
}

List<GtexCommunitySignal> _ownershipChangeSignals({
  required GteOrderListView orders,
  required GtexOwnershipBook ownership,
}) {
  final List<GteOrderRecord> settled = orders.items
      .where(
        (GteOrderRecord order) =>
            order.status == GteOrderStatus.filled ||
            order.status == GteOrderStatus.partiallyFilled,
      )
      .toList()
    ..sort((GteOrderRecord a, GteOrderRecord b) {
      final DateTime? aWhen = _orderTimestamp(a);
      final DateTime? bWhen = _orderTimestamp(b);
      if (aWhen == null || bWhen == null) {
        return 0;
      }
      return bWhen.compareTo(aWhen);
    });
  return settled.take(3).map((GteOrderRecord order) {
    final String label =
        ownership.stakeFor(order.playerId)?.playerName ?? order.playerId;
    final String verb = order.side == GteOrderSide.buy ? 'took' : 'released';
    return GtexCommunitySignal(
      id: 'yours-order-${order.id}',
      object: GtexCommunityObject.player,
      lane: GtexCommunityLane.yours,
      headline: 'You $verb a position in $label',
      detail: 'Settled ownership change.',
      action: GtexCommunityAction.openPlayer,
      playerId: order.playerId,
      occurredAt: _orderTimestamp(order),
      isFollowable: true,
    );
  }).toList(growable: false);
}

DateTime? _orderTimestamp(GteOrderRecord order) =>
    order.executionSummary.lastExecutedAt ?? order.updatedAt ?? order.createdAt;

/// `+4.2%` / `-1.8%`, with the sign always present so a move is never
/// mistaken for a level.
String gtexCommunitySignedPercent(double value) {
  return '${value >= 0 ? '+' : ''}${value.toStringAsFixed(1)}%';
}

/// The one-line answer to "am I alone in this football economy?".
String buildGtexCommunityHeadline({
  required GtexCommunityAccess access,
  required List<GtexCommunitySignal> worldSignals,
  required List<GtexCommunitySignal> yourSignals,
}) {
  if (access == GtexCommunityAccess.anonymous) {
    if (worldSignals.isEmpty) {
      return 'The GTEX football economy is quiet right now.';
    }
    return 'Sign in to see what is happening to the players and clubs you own.';
  }
  if (yourSignals.isEmpty && worldSignals.isEmpty) {
    return 'Nothing has happened in the GTEX football economy yet.';
  }
  if (yourSignals.isEmpty) {
    return 'Nothing has moved around your football yet. The wider economy is still live.';
  }
  final int count = yourSignals.length;
  return '$count thing${count == 1 ? '' : 's'} happened around your football.';
}
