import 'dart:math';

import '../app/gte_app_config.dart';
import 'gte_api_repository.dart';
import 'gte_exchange_api_client.dart';
import 'gte_models.dart';
import '../models/player_avatar.dart';
import '../models/competition_models.dart';

enum LiveMatchPhase {
  preMatch,
  firstHalf,
  halftime,
  secondHalf,
  fullTime,
}

enum LiveMatchEventType {
  goal,
  card,
  substitution,
  incident,
}

class LiveMatchEvent {
  const LiveMatchEvent({
    required this.minute,
    required this.title,
    required this.detail,
    required this.team,
    required this.type,
    this.isKeyMoment = false,
  });

  final int minute;
  final String title;
  final String detail;
  final String team;
  final LiveMatchEventType type;
  final bool isKeyMoment;
}

class LiveMatchLineupPlayer {
  const LiveMatchLineupPlayer({
    required this.name,
    required this.position,
    required this.rating,
    this.captain = false,
    this.playerId,
    this.nationalityCode,
    this.avatarSeedToken,
    this.avatarDnaSeed,
    this.avatar,
  });

  final String name;
  final String position;
  final double rating;
  final bool captain;
  final String? playerId;
  final String? nationalityCode;
  final String? avatarSeedToken;
  final String? avatarDnaSeed;
  final PlayerAvatar? avatar;
}

class LiveMatchTacticalSuggestion {
  const LiveMatchTacticalSuggestion({
    required this.title,
    required this.detail,
    required this.impactLabel,
  });

  final String title;
  final String detail;
  final String impactLabel;
}

class LiveMatchHighlightClip {
  const LiveMatchHighlightClip({
    required this.id,
    required this.title,
    required this.minute,
    required this.durationLabel,
    required this.isPremium,
    required this.isArchived,
    required this.expiresAt,
    required this.downloadEligible,
  });

  final String id;
  final String title;
  final int minute;
  final String durationLabel;
  final bool isPremium;
  final bool isArchived;
  final DateTime expiresAt;
  final bool downloadEligible;
}

class LiveMatchSnapshot {
  const LiveMatchSnapshot({
    this.matchId,
    this.halftimeAnalyticsAvailable = false,
    this.highlightsAvailable = false,
    this.keyMomentsAvailable = false,
    required this.homeTeam,
    required this.awayTeam,
    required this.homeScore,
    required this.awayScore,
    required this.minute,
    required this.phase,
    required this.momentum,
    required this.commentary,
    required this.homeLineup,
    required this.awayLineup,
    required this.substitutions,
    required this.cards,
    required this.tacticalSuggestions,
    required this.keyMoments,
    required this.highlights,
    required this.standardHighlightExpiresAt,
    required this.premiumHighlightExpiresAt,
  });

  final String? matchId;
  final bool halftimeAnalyticsAvailable;
  final bool highlightsAvailable;
  final bool keyMomentsAvailable;
  final String homeTeam;
  final String awayTeam;
  final int homeScore;
  final int awayScore;
  final int minute;
  final LiveMatchPhase phase;
  final List<int> momentum;
  final List<LiveMatchEvent> commentary;
  final List<LiveMatchLineupPlayer> homeLineup;
  final List<LiveMatchLineupPlayer> awayLineup;
  final List<LiveMatchEvent> substitutions;
  final List<LiveMatchEvent> cards;
  final List<LiveMatchTacticalSuggestion> tacticalSuggestions;
  final List<LiveMatchHighlightClip> keyMoments;
  final List<LiveMatchHighlightClip> highlights;
  final DateTime standardHighlightExpiresAt;
  final DateTime premiumHighlightExpiresAt;

  bool get isLive =>
      phase == LiveMatchPhase.firstHalf || phase == LiveMatchPhase.secondHalf;

  bool get isHalftime => phase == LiveMatchPhase.halftime;

  bool get isFinal => phase == LiveMatchPhase.fullTime;
}

Future<LiveMatchSnapshot> loadLiveMatchSnapshot(
  CompetitionSummary competition,
) async {
  await Future<void>.delayed(const Duration(milliseconds: 350));
  final LiveMatchSnapshot fallback =
      LiveMatchFixtures.buildSnapshot(competition);
  if (_matchApiConfig.backendMode == GteBackendMode.fixture) {
    return fallback;
  }
  try {
    final Map<String, Object?> livePayload =
        await _matchApiClient.fetchMatchLiveFeed(competition.id);
    LiveMatchSnapshot merged =
        _mergeLiveFeedSnapshot(fallback, livePayload, competition);
    try {
      final Map<String, Object?> highlightPayload =
          await _matchApiClient.fetchMatchHighlights(competition.id);
      merged = _mergeHighlightsSnapshot(merged, highlightPayload, competition);
    } catch (_) {
      return merged;
    }
    return merged;
  } catch (_) {
    return fallback;
  }
}

final GteAppConfig _matchApiConfig = GteAppConfig.fromEnvironment();
final GteExchangeApiClient _matchApiClient = GteExchangeApiClient.standard(
  baseUrl: _matchApiConfig.apiBaseUrl,
  mode: _matchApiConfig.backendMode,
);

LiveMatchSnapshot _mergeLiveFeedSnapshot(
  LiveMatchSnapshot fallback,
  Map<String, Object?> payload,
  CompetitionSummary competition,
) {
  final String matchId =
      GteJson.string(payload, <String>['match_id'], fallback: competition.id);
  final String homeTeam =
      GteJson.string(payload, <String>['home_team_name', 'homeTeamName']);
  final String awayTeam =
      GteJson.string(payload, <String>['away_team_name', 'awayTeamName']);
  final int homeScore =
      _requireInt(payload, <String>['home_score', 'homeScore'], 'home_score');
  final int awayScore =
      _requireInt(payload, <String>['away_score', 'awayScore'], 'away_score');
  final String status = GteJson.string(payload, <String>['status']);
  final String phaseLabel = GteJson.string(payload, <String>['phase']);
  final int? minute = _optionalInt(payload, <String>['minute']);
  final LiveMatchPhase phase =
      _phaseFromLiveFeed(phaseLabel, status, minute ?? fallback.minute);
  final List<LiveMatchEvent> commentary = _mapLiveFeedEvents(
    payload,
    fallback: fallback,
  );
  final List<LiveMatchEvent> substitutions = commentary
      .where((LiveMatchEvent event) =>
          event.type == LiveMatchEventType.substitution)
      .toList(growable: false);
  final List<LiveMatchEvent> cards = commentary
      .where((LiveMatchEvent event) => event.type == LiveMatchEventType.card)
      .toList(growable: false);

  final Map<String, Object?> availability = GteJson.map(
    GteJson.value(payload, <String>['availability']) ??
        const <String, Object?>{},
    label: 'match availability',
  );
  final bool halftimeAvailable = GteJson.boolean(
    availability,
    <String>['halftime_analytics_available', 'halftimeAnalyticsAvailable'],
    fallback: false,
  );
  final bool highlightsAvailable = GteJson.boolean(
    availability,
    <String>['highlights_available', 'highlightsAvailable'],
    fallback: commentary.isNotEmpty,
  );
  final bool keyMomentsAvailable = GteJson.boolean(
    availability,
    <String>['key_moments_available', 'keyMomentsAvailable'],
    fallback: commentary.isNotEmpty,
  );

  final DateTime now = DateTime.now().toUtc();
  final DateTime premiumExpiry = now.add(const Duration(hours: 3));
  final List<LiveMatchLineupPlayer>? homeLineup = _lineupFromPayload(
    GteJson.value(payload, <String>['home_lineup', 'homeLineup']),
  );
  final List<LiveMatchLineupPlayer>? awayLineup = _lineupFromPayload(
    GteJson.value(payload, <String>['away_lineup', 'awayLineup']),
  );
  final List<LiveMatchHighlightClip> keyMoments = keyMomentsAvailable
      ? _keyMomentsFromEvents(commentary, matchId, premiumExpiry)
      : const <LiveMatchHighlightClip>[];

  return LiveMatchSnapshot(
    matchId: matchId,
    halftimeAnalyticsAvailable: halftimeAvailable,
    highlightsAvailable: highlightsAvailable,
    keyMomentsAvailable: keyMomentsAvailable,
    homeTeam: homeTeam,
    awayTeam: awayTeam,
    homeScore: homeScore,
    awayScore: awayScore,
    minute: minute ?? fallback.minute,
    phase: phase,
    momentum: fallback.momentum,
    commentary: commentary,
    homeLineup: homeLineup ?? fallback.homeLineup,
    awayLineup: awayLineup ?? fallback.awayLineup,
    substitutions: substitutions,
    cards: cards,
    tacticalSuggestions: fallback.tacticalSuggestions,
    keyMoments: keyMoments,
    highlights: highlightsAvailable
        ? fallback.highlights
        : const <LiveMatchHighlightClip>[],
    standardHighlightExpiresAt: fallback.standardHighlightExpiresAt,
    premiumHighlightExpiresAt: fallback.premiumHighlightExpiresAt,
  );
}

LiveMatchSnapshot _mergeHighlightsSnapshot(
  LiveMatchSnapshot base,
  Map<String, Object?> payload,
  CompetitionSummary competition,
) {
  final List<Object?> rawHighlights = GteJson.list(
    GteJson.value(payload, <String>['highlights']) ?? const <Object?>[],
    label: 'highlights',
  );
  final DateTime now = DateTime.now().toUtc();
  final DateTime standardExpiry = now.add(const Duration(minutes: 10));
  final DateTime premiumExpiry = now.add(const Duration(hours: 3));

  final List<LiveMatchHighlightClip> highlights = <LiveMatchHighlightClip>[];
  final List<LiveMatchHighlightClip> keyMoments = <LiveMatchHighlightClip>[];

  for (int index = 0; index < rawHighlights.length; index += 1) {
    final Map<String, Object?> item =
        GteJson.map(rawHighlights[index], label: 'highlight item');
    final String highlightId = GteJson.string(
      item,
      <String>['highlight_id', 'highlightId'],
      fallback: '${competition.id}-clip-$index',
    );
    final String title =
        GteJson.string(item, <String>['title'], fallback: 'Highlight');
    final String eventType =
        GteJson.string(item, <String>['event_type', 'eventType'], fallback: '');
    final int minute = GteJson.integer(item, <String>['minute'], fallback: 0);
    final String accessState = GteJson.string(
      item,
      <String>['access_state', 'accessState'],
      fallback: 'available',
    );
    final bool archiveAvailable = GteJson.boolean(
      item,
      <String>['archive_available', 'archiveAvailable'],
      fallback: false,
    );
    final bool downloadAvailable = GteJson.boolean(
      item,
      <String>['download_available', 'downloadAvailable'],
      fallback: false,
    );
    final bool isKeyMoment = _isKeyMoment(eventType);
    final bool isPremium = isKeyMoment || accessState != 'available';
    final LiveMatchHighlightClip clip = LiveMatchHighlightClip(
      id: highlightId,
      title: title,
      minute: minute,
      durationLabel: '${isKeyMoment ? 18 : 22} sec',
      isPremium: isPremium,
      isArchived: archiveAvailable,
      expiresAt: isPremium ? premiumExpiry : standardExpiry,
      downloadEligible: downloadAvailable,
    );
    if (isKeyMoment) {
      keyMoments.add(clip);
    } else {
      highlights.add(clip);
    }
  }

  return LiveMatchSnapshot(
    matchId: base.matchId,
    halftimeAnalyticsAvailable: base.halftimeAnalyticsAvailable,
    highlightsAvailable: highlights.isNotEmpty,
    keyMomentsAvailable: keyMoments.isNotEmpty,
    homeTeam: base.homeTeam,
    awayTeam: base.awayTeam,
    homeScore: base.homeScore,
    awayScore: base.awayScore,
    minute: base.minute,
    phase: base.phase,
    momentum: base.momentum,
    commentary: base.commentary,
    homeLineup: base.homeLineup,
    awayLineup: base.awayLineup,
    substitutions: base.substitutions,
    cards: base.cards,
    tacticalSuggestions: base.tacticalSuggestions,
    keyMoments: keyMoments,
    highlights: highlights,
    standardHighlightExpiresAt: standardExpiry,
    premiumHighlightExpiresAt: premiumExpiry,
  );
}

List<LiveMatchLineupPlayer>? _lineupFromPayload(Object? value) {
  if (value is! List<Object?> || value.isEmpty) {
    return null;
  }
  return value.map((Object? item) {
    final Map<String, Object?> json = GteJson.map(
      item,
      label: 'live match lineup player',
    );
    return LiveMatchLineupPlayer(
      playerId: GteJson.stringOrNull(json, <String>['player_id', 'playerId']),
      name: GteJson.string(
        json,
        <String>['player_name', 'playerName', 'name'],
        fallback: 'Unnamed player',
      ),
      position: GteJson.string(json, <String>['position'], fallback: 'UNK'),
      rating: GteJson.number(json, <String>['rating'], fallback: 6.5),
      captain: GteJson.boolean(json, <String>['captain'], fallback: false),
      nationalityCode: GteJson.stringOrNull(
        json,
        <String>['nationality_code', 'nationalityCode'],
      ),
      avatarSeedToken: GteJson.stringOrNull(
        json,
        <String>['avatar_seed_token', 'avatarSeedToken'],
      ),
      avatarDnaSeed: GteJson.stringOrNull(
        json,
        <String>['avatar_dna_seed', 'avatarDnaSeed'],
      ),
      avatar:
          PlayerAvatar.fromJsonOrNull(GteJson.value(json, <String>['avatar'])),
    );
  }).toList(growable: false);
}

int _requireInt(Map<String, Object?> payload, List<String> keys, String label) {
  if (GteJson.value(payload, keys) == null) {
    throw GteParsingException('Missing required $label', payload);
  }
  return GteJson.integer(payload, keys);
}

int? _optionalInt(Map<String, Object?> payload, List<String> keys) {
  if (GteJson.value(payload, keys) == null) {
    return null;
  }
  return GteJson.integer(payload, keys);
}

LiveMatchPhase _phaseFromLiveFeed(
  String phase,
  String status,
  int minute,
) {
  final String normalizedPhase = phase.trim().toLowerCase();
  final String normalizedStatus = status.trim().toLowerCase();
  if (normalizedPhase == 'scheduled' || normalizedStatus == 'scheduled') {
    return LiveMatchPhase.preMatch;
  }
  if (normalizedPhase == 'paused') {
    return LiveMatchPhase.halftime;
  }
  if (normalizedPhase == 'fulltime' || normalizedStatus == 'completed') {
    return LiveMatchPhase.fullTime;
  }
  if (minute >= 45) {
    return LiveMatchPhase.secondHalf;
  }
  return LiveMatchPhase.firstHalf;
}

List<LiveMatchEvent> _mapLiveFeedEvents(
  Map<String, Object?> payload, {
  required LiveMatchSnapshot fallback,
}) {
  final List<Object?> rawEvents = GteJson.list(
    GteJson.value(payload, <String>['timeline_events', 'timelineEvents']) ??
        const <Object?>[],
    label: 'timeline events',
  );
  return rawEvents.map((Object? rawEvent) {
    final Map<String, Object?> json =
        GteJson.map(rawEvent, label: 'timeline event');
    final String eventType =
        GteJson.string(json, <String>['event_type', 'eventType'], fallback: '');
    final int minute = GteJson.integer(json, <String>['minute'], fallback: 0);
    final String? teamName = GteJson.stringOrNull(
      json,
      <String>['team_name', 'teamName', 'club_name', 'clubName'],
    );
    final String? playerName =
        GteJson.stringOrNull(json, <String>['player_name', 'playerName']);
    final String? secondaryPlayerName = GteJson.stringOrNull(
      json,
      <String>['secondary_player_name', 'secondaryPlayerName'],
    );
    final String? description =
        GteJson.stringOrNull(json, <String>['description', 'commentary']);
    final int homeScore = GteJson.integer(
      json,
      <String>['home_score', 'homeScore'],
      fallback: fallback.homeScore,
    );
    final int awayScore = GteJson.integer(
      json,
      <String>['away_score', 'awayScore'],
      fallback: fallback.awayScore,
    );
    final bool isKeyMoment = _isKeyMoment(eventType);
    final LiveMatchEventType mappedType = _mapEventType(eventType);
    final String resolvedTeamName = teamName ?? '';
    final String title = _eventTitle(eventType, playerName, teamName);
    final String detail = description ??
        _eventDetail(
          eventType,
          playerName,
          secondaryPlayerName,
          resolvedTeamName,
          homeScore,
          awayScore,
        );
    return LiveMatchEvent(
      minute: minute,
      title: title,
      detail: detail,
      team: teamName ?? '',
      type: mappedType,
      isKeyMoment: isKeyMoment,
    );
  }).toList(growable: false);
}

LiveMatchEventType _mapEventType(String eventType) {
  switch (eventType) {
    case 'goals':
    case 'penalties':
      return LiveMatchEventType.goal;
    case 'yellow_cards':
    case 'red_cards':
      return LiveMatchEventType.card;
    case 'substitutions':
      return LiveMatchEventType.substitution;
    default:
      return LiveMatchEventType.incident;
  }
}

bool _isKeyMoment(String eventType) {
  return eventType == 'goals' ||
      eventType == 'penalties' ||
      eventType == 'red_cards';
}

String _eventTitle(String eventType, String? playerName, String? teamName) {
  final String label = _eventLabel(eventType);
  if (playerName != null && playerName.isNotEmpty) {
    return '$label - $playerName';
  }
  if (teamName != null && teamName.isNotEmpty) {
    return '$label - $teamName';
  }
  return label;
}

String _eventDetail(
  String eventType,
  String? playerName,
  String? secondaryPlayerName,
  String teamName,
  int homeScore,
  int awayScore,
) {
  final String label = _eventLabel(eventType);
  final String resolvedTeam = teamName.isNotEmpty ? teamName : 'the match';
  if (playerName != null && secondaryPlayerName != null) {
    return '$playerName with support from $secondaryPlayerName for $resolvedTeam.';
  }
  if (playerName != null) {
    return '$playerName for $resolvedTeam. $label (${homeScore}-${awayScore}).';
  }
  return '$label for $resolvedTeam.';
}

String _eventLabel(String eventType) {
  switch (eventType) {
    case 'goals':
      return 'Goal';
    case 'assists':
      return 'Assist';
    case 'missed_chances':
      return 'Chance';
    case 'yellow_cards':
      return 'Yellow card';
    case 'red_cards':
      return 'Red card';
    case 'substitutions':
      return 'Substitution';
    case 'injuries':
      return 'Injury';
    case 'penalties':
      return 'Penalty';
    default:
      return 'Match moment';
  }
}

List<LiveMatchHighlightClip> _keyMomentsFromEvents(
  List<LiveMatchEvent> events,
  String matchId,
  DateTime expiry,
) {
  final List<LiveMatchEvent> keyMoments =
      events.where((LiveMatchEvent event) => event.isKeyMoment).toList();
  return keyMoments.asMap().entries.map((MapEntry<int, LiveMatchEvent> entry) {
    final LiveMatchEvent event = entry.value;
    return LiveMatchHighlightClip(
      id: '$matchId-key-${entry.key}',
      title: event.title,
      minute: event.minute,
      durationLabel: '${18 + entry.key * 3} sec',
      isPremium: true,
      isArchived: false,
      expiresAt: expiry,
      downloadEligible: false,
    );
  }).toList(growable: false);
}

class LiveMatchFixtures {
  static LiveMatchSnapshot buildSnapshot(CompetitionSummary competition) {
    final int seed = competition.id.hashCode.abs();
    final Random rng = Random(seed);
    final List<String> teams = List<String>.from(_teamNames, growable: false);
    teams.shuffle(rng);
    final String homeTeam = teams.first;
    final String awayTeam = teams.length > 1 ? teams[1] : 'GTEX Select';

    final LiveMatchPhase phase = _phaseForCompetition(competition);
    final int minute = _minuteForPhase(rng, phase);
    final int homeScore = _scoreForSide(rng, phase, isHome: true);
    final int awayScore = _scoreForSide(rng, phase, isHome: false);

    final List<LiveMatchEvent> commentary = _buildCommentary(
      rng,
      homeTeam: homeTeam,
      awayTeam: awayTeam,
      minute: minute,
    );
    final List<LiveMatchEvent> substitutions = commentary
        .where((LiveMatchEvent event) =>
            event.type == LiveMatchEventType.substitution)
        .toList(growable: false);
    final List<LiveMatchEvent> cards = commentary
        .where((LiveMatchEvent event) => event.type == LiveMatchEventType.card)
        .toList(growable: false);
    final List<LiveMatchHighlightClip> keyMoments = _buildKeyMoments(
        competition,
        commentary
            .where((LiveMatchEvent event) => event.isKeyMoment)
            .toList(growable: false));

    final DateTime now = DateTime.now().toUtc();
    final DateTime standardExpiry = now.add(const Duration(minutes: 10));
    final DateTime premiumExpiry = now.add(const Duration(hours: 3));
    final List<LiveMatchHighlightClip> highlights = _buildHighlights(
        competition, commentary, standardExpiry, premiumExpiry);

    return LiveMatchSnapshot(
      matchId: competition.id,
      halftimeAnalyticsAvailable: false,
      highlightsAvailable: highlights.isNotEmpty,
      keyMomentsAvailable: keyMoments.isNotEmpty,
      homeTeam: homeTeam,
      awayTeam: awayTeam,
      homeScore: homeScore,
      awayScore: awayScore,
      minute: minute,
      phase: phase,
      momentum: List<int>.generate(12, (int index) => rng.nextInt(7) - 3),
      commentary: commentary,
      homeLineup: _buildLineup(rng, homeTeam, captainSeed: seed),
      awayLineup: _buildLineup(rng, awayTeam, captainSeed: seed + 8),
      substitutions: substitutions,
      cards: cards,
      tacticalSuggestions: _buildSuggestions(rng),
      keyMoments: keyMoments,
      highlights: highlights,
      standardHighlightExpiresAt: standardExpiry,
      premiumHighlightExpiresAt: premiumExpiry,
    );
  }

  static LiveMatchPhase _phaseForCompetition(CompetitionSummary competition) {
    switch (competition.status) {
      case CompetitionStatus.inProgress:
        return LiveMatchPhase.firstHalf;
      case CompetitionStatus.completed:
        return LiveMatchPhase.fullTime;
      case CompetitionStatus.locked:
      case CompetitionStatus.filled:
        return LiveMatchPhase.preMatch;
      case CompetitionStatus.published:
      case CompetitionStatus.openForJoin:
        return LiveMatchPhase.preMatch;
      default:
        return LiveMatchPhase.preMatch;
    }
  }

  static int _minuteForPhase(Random rng, LiveMatchPhase phase) {
    switch (phase) {
      case LiveMatchPhase.firstHalf:
        return 18 + rng.nextInt(27);
      case LiveMatchPhase.halftime:
        return 45;
      case LiveMatchPhase.secondHalf:
        return 52 + rng.nextInt(35);
      case LiveMatchPhase.fullTime:
        return 90;
      case LiveMatchPhase.preMatch:
      default:
        return 0;
    }
  }

  static int _scoreForSide(Random rng, LiveMatchPhase phase,
      {required bool isHome}) {
    if (phase == LiveMatchPhase.preMatch) {
      return 0;
    }
    final int base = rng.nextInt(3);
    if (isHome && phase == LiveMatchPhase.firstHalf) {
      return base;
    }
    if (!isHome && phase == LiveMatchPhase.firstHalf) {
      return max(0, base - 1);
    }
    if (phase == LiveMatchPhase.fullTime) {
      return base + rng.nextInt(2);
    }
    return base;
  }

  static List<LiveMatchLineupPlayer> _buildLineup(
    Random rng,
    String team, {
    required int captainSeed,
  }) {
    final List<String> names = List<String>.from(_playerNames, growable: false);
    names.shuffle(rng);
    final int captainIndex = captainSeed % 11;
    return List<LiveMatchLineupPlayer>.generate(11, (int index) {
      final String player = names[index];
      return LiveMatchLineupPlayer(
        name: player,
        position: _positions[index % _positions.length],
        rating: 6.2 + rng.nextDouble() * 2.2,
        captain: index == captainIndex,
      );
    });
  }

  static List<LiveMatchEvent> _buildCommentary(
    Random rng, {
    required String homeTeam,
    required String awayTeam,
    required int minute,
  }) {
    final List<LiveMatchEvent> events = <LiveMatchEvent>[
      LiveMatchEvent(
        minute: 2,
        title: 'Opening tempo',
        detail: '$homeTeam press immediately and win the first second-ball.',
        team: homeTeam,
        type: LiveMatchEventType.incident,
      ),
      LiveMatchEvent(
        minute: 9,
        title: 'Early warning',
        detail: '$awayTeam switch the flank to stretch the back line.',
        team: awayTeam,
        type: LiveMatchEventType.incident,
      ),
      LiveMatchEvent(
        minute: 18,
        title: 'First shot on target',
        detail: '$homeTeam force a low save after a diagonal cutback.',
        team: homeTeam,
        type: LiveMatchEventType.incident,
      ),
      LiveMatchEvent(
        minute: 24,
        title: 'Yellow card',
        detail: 'Late pressure foul as $awayTeam breaks the press.',
        team: awayTeam,
        type: LiveMatchEventType.card,
      ),
      LiveMatchEvent(
        minute: 33,
        title: 'Key moment',
        detail: '$homeTeam finish a three-pass transition for the opener.',
        team: homeTeam,
        type: LiveMatchEventType.goal,
        isKeyMoment: true,
      ),
      LiveMatchEvent(
        minute: 41,
        title: 'Momentum swing',
        detail: '$awayTeam answer with an aggressive corner routine.',
        team: awayTeam,
        type: LiveMatchEventType.incident,
      ),
      LiveMatchEvent(
        minute: 56,
        title: 'Substitution',
        detail: '$awayTeam bring on a fresh winger to isolate the fullback.',
        team: awayTeam,
        type: LiveMatchEventType.substitution,
      ),
      LiveMatchEvent(
        minute: 64,
        title: 'Key moment',
        detail: '$awayTeam pull level after a rebound falls in the box.',
        team: awayTeam,
        type: LiveMatchEventType.goal,
        isKeyMoment: true,
      ),
      LiveMatchEvent(
        minute: 71,
        title: 'Tactical reset',
        detail: '$homeTeam shift into a 4-2-3-1 to regain midfield control.',
        team: homeTeam,
        type: LiveMatchEventType.incident,
      ),
      LiveMatchEvent(
        minute: 78,
        title: 'Substitution',
        detail: '$homeTeam add a second striker and stretch the line.',
        team: homeTeam,
        type: LiveMatchEventType.substitution,
      ),
      LiveMatchEvent(
        minute: max(82, minute),
        title: 'Key moment',
        detail: '$homeTeam fire wide after a late cut-in.',
        team: homeTeam,
        type: LiveMatchEventType.incident,
        isKeyMoment: true,
      ),
    ];
    return events
        .where((LiveMatchEvent event) => event.minute <= max(90, minute))
        .toList(growable: false);
  }

  static List<LiveMatchTacticalSuggestion> _buildSuggestions(Random rng) {
    final List<LiveMatchTacticalSuggestion> suggestions =
        <LiveMatchTacticalSuggestion>[
      const LiveMatchTacticalSuggestion(
        title: 'Shift press to the right channel',
        detail:
            'Their build-up overloads the left side. Force turnovers toward the touchline to compress space.',
        impactLabel: 'High press +8',
      ),
      const LiveMatchTacticalSuggestion(
        title: 'Trigger early fullback overlap',
        detail:
            'Opposition winger is staying high. Overlap quickly to create 2v1s on the outside.',
        impactLabel: 'Width +12',
      ),
      const LiveMatchTacticalSuggestion(
        title: 'Rotate the striker',
        detail: 'Stagger the forward line to pull a center-back out of shape.',
        impactLabel: 'Shot quality +6',
      ),
    ];
    suggestions.shuffle(rng);
    return suggestions.take(2).toList(growable: false);
  }

  static List<LiveMatchHighlightClip> _buildKeyMoments(
    CompetitionSummary competition,
    List<LiveMatchEvent> keyMoments,
  ) {
    final DateTime now = DateTime.now().toUtc();
    return keyMoments
        .asMap()
        .entries
        .map((MapEntry<int, LiveMatchEvent> entry) {
      final LiveMatchEvent event = entry.value;
      return LiveMatchHighlightClip(
        id: '${competition.id}-key-${entry.key}',
        title: event.title,
        minute: event.minute,
        durationLabel: '${18 + entry.key * 3} sec',
        isPremium: true,
        isArchived: false,
        expiresAt: now.add(const Duration(hours: 3)),
        downloadEligible: true,
      );
    }).toList(growable: false);
  }

  static List<LiveMatchHighlightClip> _buildHighlights(
    CompetitionSummary competition,
    List<LiveMatchEvent> commentary,
    DateTime standardExpiry,
    DateTime premiumExpiry,
  ) {
    final List<LiveMatchEvent> shortlist = commentary
        .where((LiveMatchEvent event) =>
            event.type == LiveMatchEventType.goal || event.isKeyMoment)
        .take(4)
        .toList(growable: false);
    if (shortlist.isEmpty) {
      shortlist.addAll(commentary.take(3));
    }
    return shortlist.asMap().entries.map((MapEntry<int, LiveMatchEvent> entry) {
      final LiveMatchEvent event = entry.value;
      final bool premium = entry.key.isEven;
      return LiveMatchHighlightClip(
        id: '${competition.id}-clip-${entry.key}',
        title: event.detail,
        minute: event.minute,
        durationLabel: '${22 + entry.key * 4} sec',
        isPremium: premium,
        isArchived: false,
        expiresAt: premium ? premiumExpiry : standardExpiry,
        downloadEligible: premium,
      );
    }).toList(growable: false);
  }
}

const List<String> _teamNames = <String>[
  'GTEX United',
  'Atlas City',
  'Solar FC',
  'Northbridge',
  'Lumen SC',
  'Tidehold',
  'Copperlane',
  'Aster Athletic',
];

const List<String> _playerNames = <String>[
  'Adebayo Musa',
  'Kofi Mensah',
  'Jasper Hale',
  'Ibrahim Diallo',
  'Luca Moretti',
  'Noah Rivers',
  'Theo Martins',
  'Samir Keita',
  'Emeka Odion',
  'Bastien Clarke',
  'Rene Savic',
  'Marcos Silva',
  'Jude Akin',
  'Elias Hart',
  'Dario Lopez',
  'Victor Nwosu',
  'Hugo Lane',
  'Felix Morel',
  'Amir Kone',
  'Liam Okoro',
  'Omar Suazo',
  'Nico Patel',
  'Sergio Quinn',
  'Jonah Brandt',
];

const List<String> _positions = <String>[
  'GK',
  'RB',
  'CB',
  'CB',
  'LB',
  'DM',
  'CM',
  'CM',
  'RW',
  'ST',
  'LW',
];
