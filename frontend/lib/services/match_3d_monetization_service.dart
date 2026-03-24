import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:gte_frontend/models/match_event.dart';
import 'package:gte_frontend/models/match_viewer_presentation.dart';

enum RenderMode {
  auto,
  twoD,
  threeD,
}

enum Match3dCameraPreset {
  broadcast,
  sideline,
  goalbox,
}

enum Match3dPaidInteraction {
  slowMotionReplay,
  alternateCameraAngle,
  highlightNextAttack,
}

enum Match3dReaction {
  fire,
  applause,
  hype,
}

enum Match3dPurchaseKind {
  threeDUnlock,
  tournamentBoost,
  coinGift,
  slowMotionReplay,
  alternateCameraAngle,
  highlightNextAttack,
}

enum Match3dPromptMoment {
  preMatch,
  halftime,
  bigMoment,
}

enum Match3dFailureReason {
  cancelled,
  entitlementFailed,
  insufficientBalance,
  performanceDrop,
  unavailable,
}

class Match3dMatchContext {
  const Match3dMatchContext({
    required this.matchId,
    required this.competitionId,
    required this.isFinal,
    required this.isMajorMatch,
    required this.isSpectator,
    required this.presentationMode,
    this.performanceSafe = true,
  });

  final String matchId;
  final String competitionId;
  final bool isFinal;
  final bool isMajorMatch;
  final bool isSpectator;
  final MatchViewerPresentationMode presentationMode;
  final bool performanceSafe;

  bool get auto3dEligible => isFinal || isMajorMatch;

  Match3dMatchContext copyWith({
    String? matchId,
    String? competitionId,
    bool? isFinal,
    bool? isMajorMatch,
    bool? isSpectator,
    MatchViewerPresentationMode? presentationMode,
    bool? performanceSafe,
  }) {
    return Match3dMatchContext(
      matchId: matchId ?? this.matchId,
      competitionId: competitionId ?? this.competitionId,
      isFinal: isFinal ?? this.isFinal,
      isMajorMatch: isMajorMatch ?? this.isMajorMatch,
      isSpectator: isSpectator ?? this.isSpectator,
      presentationMode: presentationMode ?? this.presentationMode,
      performanceSafe: performanceSafe ?? this.performanceSafe,
    );
  }
}

class Match3dUserEntitlement {
  const Match3dUserEntitlement({
    this.isPremiumUser = false,
    this.availableCoins = 0,
    this.premiumCameraAccess = false,
    this.fastReplayAccess = false,
    this.unlockedMatchIds = const <String>{},
    this.tournamentBoostCompetitionIds = const <String>{},
  });

  const Match3dUserEntitlement.proManager({
    this.availableCoins = 0,
    this.unlockedMatchIds = const <String>{},
    this.tournamentBoostCompetitionIds = const <String>{},
  })  : isPremiumUser = true,
        premiumCameraAccess = true,
        fastReplayAccess = true;

  final bool isPremiumUser;
  final double availableCoins;
  final bool premiumCameraAccess;
  final bool fastReplayAccess;
  final Set<String> unlockedMatchIds;
  final Set<String> tournamentBoostCompetitionIds;

  bool hasUnlockedMatch(String matchId) => unlockedMatchIds.contains(matchId);

  bool hasTournamentBoost(String competitionId) =>
      tournamentBoostCompetitionIds.contains(competitionId);

  Match3dUserEntitlement copyWith({
    bool? isPremiumUser,
    double? availableCoins,
    bool? premiumCameraAccess,
    bool? fastReplayAccess,
    Set<String>? unlockedMatchIds,
    Set<String>? tournamentBoostCompetitionIds,
  }) {
    return Match3dUserEntitlement(
      isPremiumUser: isPremiumUser ?? this.isPremiumUser,
      availableCoins: availableCoins ?? this.availableCoins,
      premiumCameraAccess: premiumCameraAccess ?? this.premiumCameraAccess,
      fastReplayAccess: fastReplayAccess ?? this.fastReplayAccess,
      unlockedMatchIds: unlockedMatchIds ?? this.unlockedMatchIds,
      tournamentBoostCompetitionIds:
          tournamentBoostCompetitionIds ?? this.tournamentBoostCompetitionIds,
    );
  }
}

bool canAccess3D(
  Match3dMatchContext matchContext,
  Match3dUserEntitlement userEntitlement,
) {
  return userEntitlement.isPremiumUser ||
      userEntitlement.hasTournamentBoost(matchContext.competitionId) ||
      userEntitlement.hasUnlockedMatch(matchContext.matchId);
}

typedef Match3dEntitlementProvider = Match3dUserEntitlement? Function();

typedef Match3dPurchaseIntentHandler = Future<Match3dPurchaseDecision> Function(
  Match3dPurchaseRequest request,
);

class Match3dPurchaseRequest {
  const Match3dPurchaseRequest({
    required this.kind,
    required this.cost,
    required this.matchId,
    required this.competitionId,
    this.reaction,
    this.giftAmount,
  });

  final Match3dPurchaseKind kind;
  final double cost;
  final String matchId;
  final String competitionId;
  final Match3dReaction? reaction;
  final double? giftAmount;
}

class Match3dPurchaseDecision {
  const Match3dPurchaseDecision({
    required this.approved,
    this.consumeLocalBalance = true,
    this.message,
  });

  const Match3dPurchaseDecision.approved({
    this.consumeLocalBalance = true,
    this.message,
  }) : approved = true;

  const Match3dPurchaseDecision.denied({
    this.message,
  })  : approved = false,
        consumeLocalBalance = false;

  final bool approved;
  final bool consumeLocalBalance;
  final String? message;
}

class Match3dOverlayBurst {
  const Match3dOverlayBurst({
    required this.id,
    required this.label,
    required this.emoji,
    required this.accentColor,
    this.coinAmount,
  });

  final String id;
  final String label;
  final String emoji;
  final Color accentColor;
  final double? coinAmount;
}

class Match3dActionResult {
  const Match3dActionResult({
    required this.success,
    this.message,
    this.failureReason,
    this.overlayBurst,
  });

  const Match3dActionResult.success({
    this.message,
    this.overlayBurst,
  })  : success = true,
        failureReason = null;

  const Match3dActionResult.failure({
    this.message,
    this.failureReason,
  })  : success = false,
        overlayBurst = null;

  final bool success;
  final String? message;
  final Match3dFailureReason? failureReason;
  final Match3dOverlayBurst? overlayBurst;
}

class Match3dMonetizationService extends ChangeNotifier {
  Match3dMonetizationService({
    Match3dUserEntitlement? entitlement,
    RenderMode initialRenderMode = RenderMode.twoD,
    Match3dPurchaseIntentHandler? onPurchaseIntent,
    this.tournamentBoostPrice,
  })  : _baseEntitlement = entitlement ?? const Match3dUserEntitlement(),
        _selectedRenderMode = initialRenderMode,
        _onPurchaseIntent = onPurchaseIntent;

  static const double threeDUnlockPrice = 0.2;
  static const double slowMotionReplayPrice = 0.05;
  static const double alternateCameraAnglePrice = 0.02;
  static const double highlightNextAttackPrice = 0.05;
  static const List<double> giftAmounts = <double>[0.1, 0.2, 0.5];
  static const List<double> _standardSpeedOptions = <double>[1, 2, 4];
  static const List<double> _premiumSpeedOptions = <double>[1, 2, 4, 6];

  Match3dUserEntitlement _baseEntitlement;
  final Match3dPurchaseIntentHandler? _onPurchaseIntent;
  RenderMode _selectedRenderMode;
  Match3dCameraPreset _cameraPreset = Match3dCameraPreset.broadcast;
  double _coinsSpentLocally = 0;
  int _burstSequence = 0;

  final Set<String> _sessionUnlockedMatchIds = <String>{};
  final Set<String> _sessionBoostedCompetitionIds = <String>{};
  final Map<String, Set<Match3dPaidInteraction>> _interactionUnlocksByMatch =
      <String, Set<Match3dPaidInteraction>>{};
  final Map<String, Set<String>> _promptTokensByMatch = <String, Set<String>>{};

  final double? tournamentBoostPrice;

  Match3dUserEntitlement get baseEntitlement => _baseEntitlement;

  Match3dUserEntitlement get effectiveEntitlement {
    return _baseEntitlement.copyWith(
      availableCoins: availableCoinBalance,
      unlockedMatchIds: <String>{
        ..._baseEntitlement.unlockedMatchIds,
        ..._sessionUnlockedMatchIds,
      },
      tournamentBoostCompetitionIds: <String>{
        ..._baseEntitlement.tournamentBoostCompetitionIds,
        ..._sessionBoostedCompetitionIds,
      },
    );
  }

  RenderMode get selectedRenderMode => _selectedRenderMode;

  Match3dCameraPreset get cameraPreset => _cameraPreset;

  double get availableCoinBalance =>
      math.max(0, _baseEntitlement.availableCoins - _coinsSpentLocally);

  void updateEntitlement(Match3dUserEntitlement? entitlement) {
    _baseEntitlement = entitlement ?? const Match3dUserEntitlement();
    notifyListeners();
  }

  void selectRenderMode(RenderMode mode) {
    if (_selectedRenderMode == mode) {
      return;
    }
    _selectedRenderMode = mode;
    notifyListeners();
  }

  void setCameraPreset(
    Match3dCameraPreset preset,
    Match3dMatchContext context,
  ) {
    if (preset != Match3dCameraPreset.broadcast &&
        !canUsePremiumCamera(context)) {
      return;
    }
    if (_cameraPreset == preset) {
      return;
    }
    _cameraPreset = preset;
    notifyListeners();
  }

  RenderMode effectiveRenderModeFor(Match3dMatchContext context) {
    if (!context.performanceSafe) {
      return RenderMode.twoD;
    }
    switch (_selectedRenderMode) {
      case RenderMode.twoD:
        return RenderMode.twoD;
      case RenderMode.auto:
        return context.auto3dEligible &&
                canAccess3D(context, effectiveEntitlement)
            ? RenderMode.threeD
            : RenderMode.twoD;
      case RenderMode.threeD:
        return canAccess3D(context, effectiveEntitlement)
            ? RenderMode.threeD
            : RenderMode.twoD;
    }
  }

  bool wantsThreeD(Match3dMatchContext context) {
    switch (_selectedRenderMode) {
      case RenderMode.twoD:
        return false;
      case RenderMode.auto:
        return context.auto3dEligible;
      case RenderMode.threeD:
        return true;
    }
  }

  bool needsThreeDUnlock(Match3dMatchContext context) {
    return wantsThreeD(context) && !canAccess3D(context, effectiveEntitlement);
  }

  bool shouldOfferPrompt({
    required Match3dPromptMoment moment,
    required Match3dMatchContext context,
    String? dedupeKey,
  }) {
    if (!needsThreeDUnlock(context)) {
      return false;
    }
    final String token = '${moment.name}:${dedupeKey ?? moment.name}';
    final Set<String> prompted = _promptTokensByMatch.putIfAbsent(
      context.matchId,
      () => <String>{},
    );
    if (prompted.contains(token)) {
      return false;
    }
    prompted.add(token);
    return true;
  }

  bool hasTournamentBoost(Match3dMatchContext context) {
    return effectiveEntitlement.hasTournamentBoost(context.competitionId);
  }

  bool canUsePremiumCamera(Match3dMatchContext context) {
    final Match3dUserEntitlement entitlement = effectiveEntitlement;
    return entitlement.isPremiumUser ||
        entitlement.premiumCameraAccess ||
        hasTournamentBoost(context) ||
        hasInteraction(
          context.matchId,
          Match3dPaidInteraction.alternateCameraAngle,
        );
  }

  bool canUseFastReplay(Match3dMatchContext context) {
    final Match3dUserEntitlement entitlement = effectiveEntitlement;
    return entitlement.isPremiumUser ||
        entitlement.fastReplayAccess ||
        hasTournamentBoost(context);
  }

  bool hasInteraction(String matchId, Match3dPaidInteraction interaction) {
    return _interactionUnlocksByMatch[matchId]?.contains(interaction) ?? false;
  }

  bool shouldHighlightNextAttack(String matchId) {
    return hasInteraction(matchId, Match3dPaidInteraction.highlightNextAttack);
  }

  void consumeHighlightNextAttack(String matchId) {
    final Set<Match3dPaidInteraction>? unlocked =
        _interactionUnlocksByMatch[matchId];
    if (unlocked == null ||
        !unlocked.remove(Match3dPaidInteraction.highlightNextAttack)) {
      return;
    }
    notifyListeners();
  }

  List<double> speedOptionsFor(Match3dMatchContext context) {
    final List<double> options = canUseFastReplay(context)
        ? _premiumSpeedOptions
        : _standardSpeedOptions;
    if (hasInteraction(
      context.matchId,
      Match3dPaidInteraction.slowMotionReplay,
    )) {
      return <double>[0.5, ...options];
    }
    return List<double>.of(options, growable: false);
  }

  Future<Match3dActionResult> unlockThreeDForMatch(
    Match3dMatchContext context,
  ) async {
    final Match3dActionResult result = await _processPurchase(
      request: Match3dPurchaseRequest(
        kind: Match3dPurchaseKind.threeDUnlock,
        cost: threeDUnlockPrice,
        matchId: context.matchId,
        competitionId: context.competitionId,
      ),
      successMessage: '3D unlocked for this match session.',
    );
    if (result.success) {
      _sessionUnlockedMatchIds.add(context.matchId);
      notifyListeners();
    }
    return result;
  }

  Future<Match3dActionResult> upgradeTournamentExperience(
    Match3dMatchContext context,
  ) async {
    final double? price = tournamentBoostPrice;
    if (price == null) {
      return const Match3dActionResult.failure(
        message: 'Tournament boost is not configured for this session.',
        failureReason: Match3dFailureReason.unavailable,
      );
    }
    final Match3dActionResult result = await _processPurchase(
      request: Match3dPurchaseRequest(
        kind: Match3dPurchaseKind.tournamentBoost,
        cost: price,
        matchId: context.matchId,
        competitionId: context.competitionId,
      ),
      successMessage: 'Tournament experience upgraded for this competition.',
    );
    if (result.success) {
      _sessionBoostedCompetitionIds.add(context.competitionId);
      notifyListeners();
    }
    return result;
  }

  Future<Match3dActionResult> unlockInteraction(
    Match3dPaidInteraction interaction,
    Match3dMatchContext context,
  ) async {
    if (interaction == Match3dPaidInteraction.alternateCameraAngle &&
        canUsePremiumCamera(context)) {
      return const Match3dActionResult.success(
        message: 'Premium camera angles are already available.',
      );
    }

    final Match3dPurchaseKind kind;
    final double cost;
    final String successMessage;
    switch (interaction) {
      case Match3dPaidInteraction.slowMotionReplay:
        kind = Match3dPurchaseKind.slowMotionReplay;
        cost = slowMotionReplayPrice;
        successMessage = 'Slow motion replay unlocked for this match.';
      case Match3dPaidInteraction.alternateCameraAngle:
        kind = Match3dPurchaseKind.alternateCameraAngle;
        cost = alternateCameraAnglePrice;
        successMessage = 'Alternate 3D camera unlocked for this match.';
      case Match3dPaidInteraction.highlightNextAttack:
        kind = Match3dPurchaseKind.highlightNextAttack;
        cost = highlightNextAttackPrice;
        successMessage = 'The next attack will be highlighted.';
    }

    final Match3dActionResult result = await _processPurchase(
      request: Match3dPurchaseRequest(
        kind: kind,
        cost: cost,
        matchId: context.matchId,
        competitionId: context.competitionId,
      ),
      successMessage: successMessage,
    );
    if (result.success) {
      final Set<Match3dPaidInteraction> unlocked =
          _interactionUnlocksByMatch.putIfAbsent(
        context.matchId,
        () => <Match3dPaidInteraction>{},
      );
      unlocked.add(interaction);
      notifyListeners();
    }
    return result;
  }

  Future<Match3dActionResult> sendCoinGift(
    double amount,
    Match3dMatchContext context,
  ) async {
    if (!giftAmounts.contains(amount)) {
      return const Match3dActionResult.failure(
        message: 'Unsupported gift amount.',
        failureReason: Match3dFailureReason.unavailable,
      );
    }
    return _processPurchase(
      request: Match3dPurchaseRequest(
        kind: Match3dPurchaseKind.coinGift,
        cost: amount,
        matchId: context.matchId,
        competitionId: context.competitionId,
        giftAmount: amount,
      ),
      successMessage: 'Gift sent.',
      overlayBurst: Match3dOverlayBurst(
        id: 'gift-${_burstSequence++}',
        label: '${amount.toStringAsFixed(1)} coin gift',
        emoji: '\u{1F381}',
        accentColor: const Color(0xFFFDB022),
        coinAmount: amount,
      ),
    );
  }

  Match3dActionResult sendReaction(
    Match3dReaction reaction,
    Match3dMatchContext context,
  ) {
    final ({String emoji, String label, Color accent}) burst =
        switch (reaction) {
      Match3dReaction.fire => (
          emoji: '\u{1F525}',
          label: 'Fire reaction',
          accent: const Color(0xFFF97066),
        ),
      Match3dReaction.applause => (
          emoji: '\u{1F44F}',
          label: 'Applause reaction',
          accent: const Color(0xFF53B1FD),
        ),
      Match3dReaction.hype => (
          emoji: '\u{26A1}',
          label: 'Hype reaction',
          accent: const Color(0xFF17B26A),
        ),
    };
    return Match3dActionResult.success(
      message: burst.label,
      overlayBurst: Match3dOverlayBurst(
        id: 'reaction-${context.matchId}-${_burstSequence++}',
        label: burst.label,
        emoji: burst.emoji,
        accentColor: burst.accent,
      ),
    );
  }

  void fallbackToTwoD({
    Match3dFailureReason reason = Match3dFailureReason.entitlementFailed,
  }) {
    _selectedRenderMode = RenderMode.twoD;
    _cameraPreset = Match3dCameraPreset.broadcast;
    notifyListeners();
  }

  Future<Match3dActionResult> _processPurchase({
    required Match3dPurchaseRequest request,
    required String successMessage,
    Match3dOverlayBurst? overlayBurst,
  }) async {
    if (request.cost > 0 && availableCoinBalance + 0.0001 < request.cost) {
      return const Match3dActionResult.failure(
        message: 'Not enough coins for this upgrade.',
        failureReason: Match3dFailureReason.insufficientBalance,
      );
    }
    final Match3dPurchaseDecision decision =
        await _onPurchaseIntent?.call(request) ??
            const Match3dPurchaseDecision.approved();
    if (!decision.approved) {
      return Match3dActionResult.failure(
        message: decision.message ?? 'Purchase cancelled.',
        failureReason: Match3dFailureReason.cancelled,
      );
    }
    if (decision.consumeLocalBalance && request.cost > 0) {
      _coinsSpentLocally += request.cost;
    }
    notifyListeners();
    return Match3dActionResult.success(
      message: decision.message ?? successMessage,
      overlayBurst: overlayBurst,
    );
  }
}

bool match3dEventCountsAsBigMoment(MatchEvent? event) {
  if (event == null) {
    return false;
  }
  return event.type == MatchViewerEventType.goal ||
      event.type == MatchViewerEventType.save ||
      event.type == MatchViewerEventType.penalty ||
      event.type == MatchViewerEventType.redCard;
}

bool match3dEventCountsAsAttack(MatchEvent? event) {
  if (event == null) {
    return false;
  }
  return event.type == MatchViewerEventType.attack ||
      event.type == MatchViewerEventType.setPiece ||
      event.type == MatchViewerEventType.penalty ||
      event.type == MatchViewerEventType.goal ||
      event.type == MatchViewerEventType.miss;
}
