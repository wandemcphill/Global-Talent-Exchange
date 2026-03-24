import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/models/match_event.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';

enum MatchMode {
  quick,
  standard,
  cinematic,
}

MatchMode matchModeFromString(String? value) {
  switch (value?.trim().toLowerCase()) {
    case 'quick':
      return MatchMode.quick;
    case 'cinematic':
      return MatchMode.cinematic;
    default:
      return MatchMode.standard;
  }
}

extension MatchModeX on MatchMode {
  String get apiValue => name;

  String get label {
    switch (this) {
      case MatchMode.quick:
        return 'Quick';
      case MatchMode.standard:
        return 'Standard';
      case MatchMode.cinematic:
        return 'Cinematic';
    }
  }
}

enum MatchVerificationStatus {
  verified,
  unverified,
  tampered,
}

MatchVerificationStatus matchVerificationStatusFromString(String? value) {
  switch (value?.trim().toLowerCase()) {
    case 'verified':
      return MatchVerificationStatus.verified;
    case 'tampered':
      return MatchVerificationStatus.tampered;
    default:
      return MatchVerificationStatus.unverified;
  }
}

class MatchViewerTeam {
  const MatchViewerTeam({
    required this.teamId,
    required this.teamName,
    required this.shortName,
    required this.side,
    required this.formation,
    required this.primaryColorHex,
    required this.secondaryColorHex,
    required this.accentColorHex,
    required this.goalkeeperColorHex,
  });

  final String teamId;
  final String teamName;
  final String shortName;
  final MatchViewerSide side;
  final String formation;
  final String primaryColorHex;
  final String secondaryColorHex;
  final String accentColorHex;
  final String goalkeeperColorHex;

  MatchViewerTeam copyWith({
    String? teamName,
    String? shortName,
  }) {
    return MatchViewerTeam(
      teamId: teamId,
      teamName: teamName ?? this.teamName,
      shortName: shortName ?? this.shortName,
      side: side,
      formation: formation,
      primaryColorHex: primaryColorHex,
      secondaryColorHex: secondaryColorHex,
      accentColorHex: accentColorHex,
      goalkeeperColorHex: goalkeeperColorHex,
    );
  }

  factory MatchViewerTeam.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value, label: 'viewer team');
    return MatchViewerTeam(
      teamId: GteJson.string(json, <String>['team_id', 'teamId']),
      teamName: GteJson.string(json, <String>['team_name', 'teamName']),
      shortName: GteJson.string(json, <String>['short_name', 'shortName']),
      side: matchViewerSideFromString(
        GteJson.string(json, <String>['side']),
      ),
      formation: GteJson.string(json, <String>['formation'], fallback: '4-3-3'),
      primaryColorHex:
          GteJson.string(json, <String>['primary_color', 'primaryColor']),
      secondaryColorHex:
          GteJson.string(json, <String>['secondary_color', 'secondaryColor']),
      accentColorHex:
          GteJson.string(json, <String>['accent_color', 'accentColor']),
      goalkeeperColorHex: GteJson.string(
        json,
        <String>['goalkeeper_color', 'goalkeeperColor'],
      ),
    );
  }
}

class MatchFairnessIndicator {
  const MatchFairnessIndicator({
    this.status = MatchVerificationStatus.unverified,
    this.label = 'Fair Play Pending',
    this.message,
    this.noPayToWin = true,
    this.visualOnlyMonetization = true,
    this.serverAuthoritative = true,
    this.tournamentFairnessMode,
    this.homeSpendTier,
    this.awaySpendTier,
    this.squadBalancePolicy,
    this.softBalanceApplied = false,
  });

  final MatchVerificationStatus status;
  final String label;
  final String? message;
  final bool noPayToWin;
  final bool visualOnlyMonetization;
  final bool serverAuthoritative;
  final String? tournamentFairnessMode;
  final String? homeSpendTier;
  final String? awaySpendTier;
  final String? squadBalancePolicy;
  final bool softBalanceApplied;

  factory MatchFairnessIndicator.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value ?? const <String, Object?>{},
      label: 'fairness indicator',
    );
    return MatchFairnessIndicator(
      status: matchVerificationStatusFromString(
        GteJson.stringOrNull(json, <String>['status']),
      ),
      label: GteJson.string(
        json,
        <String>['label'],
        fallback: 'Fair Play Pending',
      ),
      message: GteJson.stringOrNull(json, <String>['message']),
      noPayToWin: GteJson.boolean(
        json,
        <String>['no_pay_to_win', 'noPayToWin'],
        fallback: true,
      ),
      visualOnlyMonetization: GteJson.boolean(
        json,
        <String>['visual_only_monetization', 'visualOnlyMonetization'],
        fallback: true,
      ),
      serverAuthoritative: GteJson.boolean(
        json,
        <String>['server_authoritative', 'serverAuthoritative'],
        fallback: true,
      ),
      tournamentFairnessMode: GteJson.stringOrNull(
        json,
        <String>['tournament_fairness_mode', 'tournamentFairnessMode'],
      ),
      homeSpendTier: GteJson.stringOrNull(
        json,
        <String>['home_spend_tier', 'homeSpendTier'],
      ),
      awaySpendTier: GteJson.stringOrNull(
        json,
        <String>['away_spend_tier', 'awaySpendTier'],
      ),
      squadBalancePolicy: GteJson.stringOrNull(
        json,
        <String>['squad_balance_policy', 'squadBalancePolicy'],
      ),
      softBalanceApplied: GteJson.boolean(
        json,
        <String>['soft_balance_applied', 'softBalanceApplied'],
        fallback: false,
      ),
    );
  }
}

class MatchTimelineProof {
  const MatchTimelineProof({
    this.status = MatchVerificationStatus.unverified,
    this.matchHash = '',
    this.timelineHash = '',
    this.visibleTimelineHash = '',
    this.signed = true,
    this.revealedThroughSeconds = 0,
  });

  final MatchVerificationStatus status;
  final String matchHash;
  final String timelineHash;
  final String visibleTimelineHash;
  final bool signed;
  final int revealedThroughSeconds;

  factory MatchTimelineProof.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value ?? const <String, Object?>{},
      label: 'timeline proof',
    );
    return MatchTimelineProof(
      status: matchVerificationStatusFromString(
        GteJson.stringOrNull(json, <String>['status']),
      ),
      matchHash: GteJson.string(
        json,
        <String>['match_hash', 'matchHash'],
        fallback: '',
      ),
      timelineHash: GteJson.string(
        json,
        <String>['timeline_hash', 'timelineHash'],
        fallback: '',
      ),
      visibleTimelineHash: GteJson.string(
        json,
        <String>['visible_timeline_hash', 'visibleTimelineHash'],
        fallback: '',
      ),
      signed: GteJson.boolean(
        json,
        <String>['signed'],
        fallback: true,
      ),
      revealedThroughSeconds: GteJson.integer(
        json,
        <String>['revealed_through_seconds', 'revealedThroughSeconds'],
        fallback: 0,
      ),
    );
  }
}

class MatchViewState {
  const MatchViewState({
    required this.matchId,
    required this.source,
    required this.supportsOffside,
    required this.durationSeconds,
    required this.homeTeam,
    required this.awayTeam,
    required this.events,
    required this.frames,
    this.deterministicSeed,
    this.matchMode = MatchMode.standard,
    this.fairnessIndicator = const MatchFairnessIndicator(),
    this.timelineProof = const MatchTimelineProof(),
    this.scoreRevealLocked = false,
    this.segmentStartSeconds = 0,
    this.segmentEndSeconds = 0,
    this.hasMoreSegments = false,
    this.nextSegmentToken,
  });

  final String matchId;
  final String source;
  final bool supportsOffside;
  final int? deterministicSeed;
  final MatchMode matchMode;
  final int durationSeconds;
  final MatchViewerTeam homeTeam;
  final MatchViewerTeam awayTeam;
  final List<MatchEvent> events;
  final List<MatchTimelineFrame> frames;
  final MatchFairnessIndicator fairnessIndicator;
  final MatchTimelineProof timelineProof;
  final bool scoreRevealLocked;
  final int segmentStartSeconds;
  final int segmentEndSeconds;
  final bool hasMoreSegments;
  final String? nextSegmentToken;

  factory MatchViewState.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'match view state');
    final List<Object?> rawEvents = GteJson.list(
      GteJson.value(json, <String>['events']) ?? const <Object?>[],
      label: 'match events',
    );
    final List<Object?> rawFrames = GteJson.list(
      GteJson.value(json, <String>['frames']) ?? const <Object?>[],
      label: 'match frames',
    );
    final List<MatchTimelineFrame> frames = rawFrames
        .map(MatchTimelineFrame.fromJson)
        .toList(growable: false)
      ..sort((MatchTimelineFrame left, MatchTimelineFrame right) =>
          left.timeSeconds.compareTo(right.timeSeconds));
    return MatchViewState(
      matchId: GteJson.string(json, <String>['match_id', 'matchId']),
      source: GteJson.string(json, <String>['source'], fallback: 'unknown'),
      supportsOffside: GteJson.boolean(
        json,
        <String>['supports_offside', 'supportsOffside'],
        fallback: false,
      ),
      deterministicSeed: GteJson.integerOrNull(
          json, <String>['deterministic_seed', 'deterministicSeed']),
      matchMode: matchModeFromString(
        GteJson.stringOrNull(json, <String>['match_mode', 'matchMode']),
      ),
      durationSeconds: GteJson.integer(
        json,
        <String>['duration_seconds', 'durationSeconds'],
        fallback: frames.isEmpty ? 0 : frames.last.timeSeconds.ceil(),
      ),
      homeTeam: MatchViewerTeam.fromJson(
        GteJson.value(json, <String>['home_team', 'homeTeam']),
      ),
      awayTeam: MatchViewerTeam.fromJson(
        GteJson.value(json, <String>['away_team', 'awayTeam']),
      ),
      events: rawEvents.map(MatchEvent.fromJson).toList(growable: false),
      frames: frames,
      fairnessIndicator: MatchFairnessIndicator.fromJson(
        GteJson.value(
          json,
          <String>['fairness_indicator', 'fairnessIndicator'],
        ),
      ),
      timelineProof: MatchTimelineProof.fromJson(
        GteJson.value(json, <String>['timeline_proof', 'timelineProof']),
      ),
      scoreRevealLocked: GteJson.boolean(
        json,
        <String>['score_reveal_locked', 'scoreRevealLocked'],
        fallback: false,
      ),
      segmentStartSeconds: GteJson.integer(
        json,
        <String>['segment_start_seconds', 'segmentStartSeconds'],
        fallback: 0,
      ),
      segmentEndSeconds: GteJson.integer(
        json,
        <String>['segment_end_seconds', 'segmentEndSeconds'],
        fallback: frames.isEmpty ? 0 : frames.last.timeSeconds.ceil(),
      ),
      hasMoreSegments: GteJson.boolean(
        json,
        <String>['has_more_segments', 'hasMoreSegments'],
        fallback: false,
      ),
      nextSegmentToken: GteJson.stringOrNull(
        json,
        <String>['next_segment_token', 'nextSegmentToken'],
      ),
    );
  }

  MatchViewState copyWith({
    String? source,
    bool? supportsOffside,
    int? deterministicSeed,
    MatchMode? matchMode,
    int? durationSeconds,
    MatchViewerTeam? homeTeam,
    MatchViewerTeam? awayTeam,
    List<MatchEvent>? events,
    List<MatchTimelineFrame>? frames,
    MatchFairnessIndicator? fairnessIndicator,
    MatchTimelineProof? timelineProof,
    bool? scoreRevealLocked,
    int? segmentStartSeconds,
    int? segmentEndSeconds,
    bool? hasMoreSegments,
    String? nextSegmentToken,
  }) {
    return MatchViewState(
      matchId: matchId,
      source: source ?? this.source,
      supportsOffside: supportsOffside ?? this.supportsOffside,
      deterministicSeed: deterministicSeed ?? this.deterministicSeed,
      matchMode: matchMode ?? this.matchMode,
      durationSeconds: durationSeconds ?? this.durationSeconds,
      homeTeam: homeTeam ?? this.homeTeam,
      awayTeam: awayTeam ?? this.awayTeam,
      events: events ?? this.events,
      frames: frames ?? this.frames,
      fairnessIndicator: fairnessIndicator ?? this.fairnessIndicator,
      timelineProof: timelineProof ?? this.timelineProof,
      scoreRevealLocked: scoreRevealLocked ?? this.scoreRevealLocked,
      segmentStartSeconds: segmentStartSeconds ?? this.segmentStartSeconds,
      segmentEndSeconds: segmentEndSeconds ?? this.segmentEndSeconds,
      hasMoreSegments: hasMoreSegments ?? this.hasMoreSegments,
      nextSegmentToken: nextSegmentToken ?? this.nextSegmentToken,
    );
  }

  MatchTimelineFrame get firstFrame => frames.first;

  MatchTimelineFrame get lastFrame => frames.last;

  MatchEvent? eventById(String? id) {
    if (id == null) {
      return null;
    }
    for (final MatchEvent event in events) {
      if (event.id == id) {
        return event;
      }
    }
    return null;
  }

  MatchViewerTeam teamForSide(MatchViewerSide side) {
    return side == MatchViewerSide.home ? homeTeam : awayTeam;
  }
}
