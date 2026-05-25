import 'package:flutter/foundation.dart';

enum GtexMatchPhase {
  scheduled,
  firstHalf,
  halfTime,
  secondHalf,
  extraTime,
  penalties,
  fullTime,
}

enum GtexPitchEventType {
  kickoff,
  shot,
  goal,
  pass,
  tackle,
  save,
  foul,
  yellowCard,
  redCard,
  substitution,
  tacticalChange,
}

@immutable
class GtexLiveMatchState {
  const GtexLiveMatchState({
    required this.matchId,
    required this.home,
    required this.away,
    required this.minute,
    required this.phase,
    required this.pitchPlayers,
    required this.timeline,
    required this.stats,
    required this.highlights,
    this.homeMomentumPercent,
    this.economyImpacts = const <GtexMatchEconomyImpact>[],
    this.selectedPlayerId,
    this.isWatchedByOwner = false,
  });

  final String matchId;
  final GtexMatchTeam home;
  final GtexMatchTeam away;
  final int minute;
  final GtexMatchPhase phase;
  final List<GtexPitchPlayer> pitchPlayers;
  final List<GtexMatchTimelineEvent> timeline;
  final GtexMatchStats stats;
  final List<GtexMatchHighlight> highlights;
  final int? homeMomentumPercent;
  final List<GtexMatchEconomyImpact> economyImpacts;
  final String? selectedPlayerId;
  final bool isWatchedByOwner;

  bool get isLive =>
      phase != GtexMatchPhase.scheduled && phase != GtexMatchPhase.fullTime;

  GtexLiveMatchState copyWith({
    String? selectedPlayerId,
    int? minute,
    GtexMatchPhase? phase,
    List<GtexMatchTimelineEvent>? timeline,
  }) {
    return GtexLiveMatchState(
      matchId: matchId,
      home: home,
      away: away,
      minute: minute ?? this.minute,
      phase: phase ?? this.phase,
      pitchPlayers: pitchPlayers,
      timeline: timeline ?? this.timeline,
      stats: stats,
      highlights: highlights,
      homeMomentumPercent: homeMomentumPercent,
      economyImpacts: economyImpacts,
      selectedPlayerId: selectedPlayerId ?? this.selectedPlayerId,
      isWatchedByOwner: isWatchedByOwner,
    );
  }
}

@immutable
class GtexMatchEconomyImpact {
  const GtexMatchEconomyImpact({
    required this.playerName,
    this.teamId,
    this.currentValueLabel,
    this.deltaLabel,
    this.deltaPercent,
  });

  final String playerName;
  final String? teamId;
  final String? currentValueLabel;
  final String? deltaLabel;
  final double? deltaPercent;
}

@immutable
class GtexMatchTeam {
  const GtexMatchTeam({
    required this.id,
    required this.name,
    required this.shortName,
    required this.score,
    required this.formation,
    required this.players,
    this.badgeUrl,
    this.primaryColorHex,
  });

  final String id;
  final String name;
  final String shortName;
  final int score;
  final String formation;
  final List<GtexLineupPlayer> players;
  final String? badgeUrl;
  final String? primaryColorHex;
}

@immutable
class GtexLineupPlayer {
  const GtexLineupPlayer({
    required this.id,
    required this.name,
    required this.position,
    required this.shirtNumber,
    required this.rating,
    this.imageUrl,
    this.isRegen = false,
  });

  final String id;
  final String name;
  final String position;
  final int shirtNumber;
  final double rating;
  final String? imageUrl;
  final bool isRegen;
}

@immutable
class GtexPitchPlayer {
  const GtexPitchPlayer({
    required this.playerId,
    required this.teamId,
    required this.name,
    required this.shirtNumber,
    required this.x,
    required this.y,
    required this.isHome,
    this.hasBall = false,
  });

  final String playerId;
  final String teamId;
  final String name;
  final int shirtNumber;
  final double x;
  final double y;
  final bool isHome;
  final bool hasBall;
}

@immutable
class GtexMatchTimelineEvent {
  const GtexMatchTimelineEvent({
    required this.minute,
    required this.type,
    required this.title,
    required this.description,
    this.teamId,
    this.playerName,
  });

  final int minute;
  final GtexPitchEventType type;
  final String title;
  final String description;
  final String? teamId;
  final String? playerName;
}

@immutable
class GtexMatchStats {
  const GtexMatchStats({
    required this.homePossession,
    required this.awayPossession,
    required this.homeShots,
    required this.awayShots,
    required this.homeShotsOnTarget,
    required this.awayShotsOnTarget,
    required this.homePassAccuracy,
    required this.awayPassAccuracy,
    required this.homeExpectedGoals,
    required this.awayExpectedGoals,
  });

  final int homePossession;
  final int awayPossession;
  final int homeShots;
  final int awayShots;
  final int homeShotsOnTarget;
  final int awayShotsOnTarget;
  final int homePassAccuracy;
  final int awayPassAccuracy;
  final double homeExpectedGoals;
  final double awayExpectedGoals;
}

@immutable
class GtexMatchHighlight {
  const GtexMatchHighlight({
    required this.minute,
    required this.title,
    required this.summary,
    required this.importance,
  });

  final int minute;
  final String title;
  final String summary;
  final int importance;
}

@immutable
class GtexTacticalInstruction {
  const GtexTacticalInstruction({
    required this.pressIntensity,
    required this.defensiveLine,
    required this.tempo,
    required this.riskLevel,
  });

  final int pressIntensity;
  final int defensiveLine;
  final int tempo;
  final int riskLevel;
}
