import 'package:flutter/foundation.dart';

/// How much of GTEX's ownership economy the signed-in user actually holds.
///
/// Home uses this to decide what to lead with (Step 3 of the Phase 4F
/// contract): a user with nothing owned gets discovery content, an owner
/// gets their world; nobody gets pretend portfolio activity.
enum GtexHomeUserState { newUser, playerOwner, clubOwner, regenInvestor, multiAsset }

/// One owned player, enriched with movement and matchday signal where the
/// backend actually provides them.
///
/// [formTrendLabel] is only ever non-null when PHASE4-E's backend signal is
/// genuinely `applied` on this player - Home never claims a form-to-value
/// link the backend has not made (Phase 4E honesty rule, §9.2).
@immutable
class GtexHomePlayerHighlight {
  const GtexHomePlayerHighlight({
    required this.playerId,
    required this.playerName,
    required this.quantityLabel,
    required this.priceLabel,
    this.clubName,
    this.unrealizedPlPercent,
    this.formTrendLabel,
    this.matchdayNote,
  });

  final String playerId;
  final String playerName;
  final String? clubName;
  final String quantityLabel;
  final String priceLabel;

  /// `null` — never `0` — when there is no cost basis behind the position.
  final double? unrealizedPlPercent;

  /// e.g. `"Form +0.4"`. Only set when the matchday signal is applied.
  final String? formTrendLabel;

  /// e.g. `"Played 78 minutes last matchday"`. Presence-only note, never a
  /// value-causality claim beyond what [formTrendLabel] already states.
  final String? matchdayNote;

  bool get hasMovement => (unrealizedPlPercent ?? 0) != 0;

  String get movementLabel {
    final double? pct = unrealizedPlPercent;
    if (pct == null) {
      return 'Unknown movement';
    }
    final String sign = pct >= 0 ? '+' : '';
    return '$sign${pct.toStringAsFixed(1)}%';
  }
}

/// A market mover (real `day_change_percent` from `/api/market/movers`),
/// labelled with whether the signed-in user owns it.
@immutable
class GtexHomeMoverHighlight {
  const GtexHomeMoverHighlight({
    required this.playerId,
    required this.playerName,
    required this.dayChangePercent,
    required this.isOwned,
  });

  final String playerId;
  final String playerName;
  final double dayChangePercent;
  final bool isOwned;

  bool get isRising => dayChangePercent > 0;

  String get movementLabel {
    final String sign = dayChangePercent >= 0 ? '+' : '';
    return '$sign${dayChangePercent.toStringAsFixed(1)}%';
  }
}

/// One club the user holds ownership shares in.
@immutable
class GtexHomeClubHighlight {
  const GtexHomeClubHighlight({
    required this.clubId,
    required this.clubName,
    required this.sharesLabel,
    required this.sharePriceLabel,
    required this.plLabel,
    required this.isInProfit,
    required this.hasPerformanceHistory,
  });

  final String clubId;
  final String clubName;
  final String sharesLabel;
  final String sharePriceLabel;
  final String plLabel;
  final bool isInProfit;

  /// True only when the club has a settled-match performance history behind
  /// its share price (PHASE4-D's `hasPerformanceHistory`). Gates whether the
  /// UI may say the price reflects club form at all.
  final bool hasPerformanceHistory;
}

/// One regen prospect the user owns, found on the live regen leaderboard.
///
/// Home never fabricates a potential tier or scout confidence — it shows the
/// real ranking rows PHASE4-C's backend returned for an owned player, and
/// nothing else.
@immutable
class GtexHomeRegenHighlight {
  const GtexHomeRegenHighlight({
    required this.playerId,
    required this.playerName,
    required this.rank,
    required this.category,
  });

  final String playerId;
  final String playerName;
  final int rank;
  final String category;

  String get rankLabel => '#$rank';
}

/// A single "what needs your attention" action. Every item routes somewhere
/// real (Step 9) - never a dead affordance.
@immutable
class GtexHomeAttentionItem {
  const GtexHomeAttentionItem({
    required this.id,
    required this.label,
    required this.routeLocation,
    this.useGo = false,
    this.playerId,
  });

  final String id;
  final String label;
  final String routeLocation;
  final bool useGo;

  /// Set when the action opens a specific player via the canonical navigator
  /// rather than a route location.
  final String? playerId;
}

/// One line of "I am building something" — a settled ownership change.
@immutable
class GtexHomeActivityItem {
  const GtexHomeActivityItem({
    required this.id,
    required this.label,
    required this.timestampLabel,
    this.playerId,
  });

  final String id;
  final String label;
  final String timestampLabel;
  final String? playerId;
}

/// The whole personalized Home composition: a presentation aggregation over
/// PHASE4-B (ownership), PHASE4-A (movers), PHASE4-D (club holdings),
/// PHASE4-C (regen rankings) and PHASE4-E (matchday form). Home computes
/// none of the underlying numbers; it only selects, filters and labels them.
@immutable
class GtexHomeDigest {
  const GtexHomeDigest({
    required this.userState,
    required this.headline,
    required this.ownedPlayers,
    required this.yourMoversToday,
    required this.opportunityMovers,
    required this.clubs,
    required this.regens,
    required this.attentionItems,
    required this.recentActivity,
    required this.warnings,
  });

  factory GtexHomeDigest.empty() => const GtexHomeDigest(
    userState: GtexHomeUserState.newUser,
    headline: 'Sign in to see what changed in your GTEX world.',
    ownedPlayers: <GtexHomePlayerHighlight>[],
    yourMoversToday: <GtexHomeMoverHighlight>[],
    opportunityMovers: <GtexHomeMoverHighlight>[],
    clubs: <GtexHomeClubHighlight>[],
    regens: <GtexHomeRegenHighlight>[],
    attentionItems: <GtexHomeAttentionItem>[],
    recentActivity: <GtexHomeActivityItem>[],
    warnings: <String>[],
  );

  final GtexHomeUserState userState;
  final String headline;
  final List<GtexHomePlayerHighlight> ownedPlayers;
  final List<GtexHomeMoverHighlight> yourMoversToday;
  final List<GtexHomeMoverHighlight> opportunityMovers;
  final List<GtexHomeClubHighlight> clubs;
  final List<GtexHomeRegenHighlight> regens;
  final List<GtexHomeAttentionItem> attentionItems;
  final List<GtexHomeActivityItem> recentActivity;

  /// Per-source failures that did not stop the digest from composing (a
  /// club-portfolio sync failure never hides the player squad, etc). Home
  /// renders these as soft notices, never as a blank section.
  final List<String> warnings;

  bool get hasAnyOwnership =>
      ownedPlayers.isNotEmpty || clubs.isNotEmpty || regens.isNotEmpty;

  bool get isQuiet => hasAnyOwnership && yourMoversToday.isEmpty;
}
