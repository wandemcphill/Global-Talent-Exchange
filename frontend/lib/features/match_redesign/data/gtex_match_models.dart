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
class GtexPitchBall {
  const GtexPitchBall({
    required this.x,
    required this.y,
    this.z = 0.0,
    this.ownerPlayerId,
    this.state = 'rolling',
  });

  final double x;
  final double y;
  final double z;
  final String? ownerPlayerId;
  final String state;

  bool get isInFlight => state == 'in_flight' || z > 0.05;
}

@immutable
class GtexKeyDuel {
  const GtexKeyDuel({
    required this.homePlayerName,
    required this.homePlayerRole,
    required this.homePlayerRating,
    required this.awayPlayerName,
    required this.awayPlayerRole,
    required this.awayPlayerRating,
    required this.description,
    this.available = true,
    this.homePlayerRatingAvailable = true,
    this.awayPlayerRatingAvailable = true,
  });

  final String homePlayerName;
  final String homePlayerRole;
  final double homePlayerRating;
  final String awayPlayerName;
  final String awayPlayerRole;
  final double awayPlayerRating;
  final String description;
  final bool available;
  final bool homePlayerRatingAvailable;
  final bool awayPlayerRatingAvailable;
}

@immutable
class GtexPreMatchPackage {
  const GtexPreMatchPackage({
    required this.homeForm,
    required this.awayForm,
    required this.homeWinRate,
    required this.awayWinRate,
    required this.h2hTotal,
    required this.h2hHomeWins,
    required this.h2hDraws,
    required this.h2hAwayWins,
    required this.h2hLastMeeting,
    required this.homeWinPct,
    required this.drawPct,
    required this.awayWinPct,
    required this.totalVotes,
    this.keyDuel,
    this.storyline,
    this.homeFormAvailable = true,
    this.awayFormAvailable = true,
    this.h2hAvailable = true,
    this.probabilityAvailable = true,
    this.votesAvailable = true,
    this.homeWinRateAvailable = true,
    this.awayWinRateAvailable = true,
  });

  final List<String> homeForm;
  final List<String> awayForm;
  final int homeWinRate;
  final int awayWinRate;
  final int h2hTotal;
  final int h2hHomeWins;
  final int h2hDraws;
  final int h2hAwayWins;
  final String h2hLastMeeting;
  final int homeWinPct;
  final int drawPct;
  final int awayWinPct;
  final int totalVotes;
  final GtexKeyDuel? keyDuel;
  final String? storyline;
  final bool homeFormAvailable;
  final bool awayFormAvailable;
  final bool h2hAvailable;
  final bool probabilityAvailable;
  final bool votesAvailable;
  final bool homeWinRateAvailable;
  final bool awayWinRateAvailable;
}

@immutable
class GtexShotMapEntry {
  const GtexShotMapEntry({
    required this.minute,
    required this.isHome,
    required this.x,
    required this.y,
    required this.xg,
    required this.outcome,
    required this.playerName,
  });

  final int minute;
  final bool isHome;
  final double x;
  final double y;
  final double xg;
  final String outcome; // 'goal', 'saved', 'missed', 'blocked'
  final String playerName;

  bool get isGoal => outcome == 'goal';
}

@immutable
class GtexPlayerOfTheMatch {
  const GtexPlayerOfTheMatch({
    required this.playerName,
    required this.teamName,
    required this.shirtNumber,
    required this.rating,
    required this.goals,
    required this.assists,
    required this.keyPasses,
    required this.passAcc,
    required this.summary,
    this.available = true,
    this.ratingAvailable = true,
    this.assistsAvailable = true,
    this.keyPassesAvailable = true,
    this.passAccAvailable = true,
  });

  final String playerName;
  final String teamName;
  final int shirtNumber;
  final double rating;
  final int goals;
  final int assists;
  final int keyPasses;
  final int passAcc;
  final String summary;
  final bool available;
  final bool ratingAvailable;
  final bool assistsAvailable;
  final bool keyPassesAvailable;
  final bool passAccAvailable;
}

@immutable
class GtexMomentumPoint {
  const GtexMomentumPoint({
    required this.minute,
    required this.value,
  });

  final int minute;
  final int value;
}

@immutable
class GtexPlayerRatingItem {
  const GtexPlayerRatingItem({
    required this.playerId,
    required this.name,
    required this.shirtNumber,
    required this.position,
    required this.rating,
    required this.isHome,
    this.badges = const <String>[],
  });

  final String playerId;
  final String name;
  final int shirtNumber;
  final String position;
  final double rating;
  final bool isHome;
  final List<String> badges;
}

@immutable
class GtexPostMatchPackage {
  const GtexPostMatchPackage({
    required this.motm,
    required this.shotMap,
    required this.momentum,
    required this.ratings,
    required this.shareSummary,
  });

  final GtexPlayerOfTheMatch motm;
  final List<GtexShotMapEntry> shotMap;
  final List<GtexMomentumPoint> momentum;
  final List<GtexPlayerRatingItem> ratings;
  final String shareSummary;
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
    this.ball,
    this.preMatch,
    this.postMatch,
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
  final GtexPitchBall? ball;
  final GtexPreMatchPackage? preMatch;
  final GtexPostMatchPackage? postMatch;
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
    GtexPitchBall? ball,
    GtexPreMatchPackage? preMatch,
    GtexPostMatchPackage? postMatch,
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
      ball: ball ?? this.ball,
      preMatch: preMatch ?? this.preMatch,
      postMatch: postMatch ?? this.postMatch,
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
    this.playerId,
    this.teamId,
    this.currentValueLabel,
    this.deltaLabel,
    this.deltaPercent,
  });

  final String playerName;
  final String? playerId;
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
    this.managerName,
    this.recentFormPercent,
    this.mentality,
    this.instructionSummary = const <String>[],
    this.bench = const <GtexLineupPlayer>[],
  });

  final String id;
  final String name;
  final String shortName;
  final int score;
  final String formation;
  final List<GtexLineupPlayer> players;
  final String? badgeUrl;
  final String? primaryColorHex;
  final String? managerName;
  final int? recentFormPercent;
  final String? mentality;
  final List<String> instructionSummary;
  final List<GtexLineupPlayer> bench;
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
    this.formLabel,
    this.fitnessPct,
  });

  final String id;
  final String name;
  final String position;
  final int shirtNumber;
  final double rating;
  final String? imageUrl;
  final bool isRegen;
  final String? formLabel;
  final double? fitnessPct;
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
    this.role,
    this.state = 'idle',
    this.animationState = 'idle',
    this.staminaPct = 100.0,
  });

  final String playerId;
  final String teamId;
  final String name;
  final int shirtNumber;
  final double x;
  final double y;
  final bool isHome;
  final bool hasBall;
  final String? role;
  final String state;
  final String animationState;
  final double staminaPct;
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
    this.shotsAvailable = true,
    this.possessionAvailable = true,
    this.passingAvailable = true,
    this.expectedGoalsAvailable = true,
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
  final bool shotsAvailable;
  final bool possessionAvailable;
  final bool passingAvailable;
  final bool expectedGoalsAvailable;
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
    this.formation,
    this.mentality,
    this.side,
    this.substitutions,
  });

  final int pressIntensity;
  final int defensiveLine;
  final int tempo;
  final int riskLevel;
  final String? formation;
  final String? mentality;
  final String? side;
  final List<Map<String, dynamic>>? substitutions;
}
