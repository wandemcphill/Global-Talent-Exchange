import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/models/match_event.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';

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
  });

  final String matchId;
  final String source;
  final bool supportsOffside;
  final int? deterministicSeed;
  final int durationSeconds;
  final MatchViewerTeam homeTeam;
  final MatchViewerTeam awayTeam;
  final List<MatchEvent> events;
  final List<MatchTimelineFrame> frames;

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
