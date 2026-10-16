import 'package:gte_frontend/models/match_event.dart';
import 'package:gte_frontend/models/match_view_state.dart';

enum MatchSimulationStyle {
  possession,
  counter,
  balanced,
  direct,
  wingPlay,
}

extension MatchSimulationStyleX on MatchSimulationStyle {
  String get label => switch (this) {
        MatchSimulationStyle.possession => 'Possession',
        MatchSimulationStyle.counter => 'Counter',
        MatchSimulationStyle.balanced => 'Balanced',
        MatchSimulationStyle.direct => 'Direct',
        MatchSimulationStyle.wingPlay => 'Wing play',
      };
}

enum MatchSimulationPressing {
  low,
  medium,
  high,
}

extension MatchSimulationPressingX on MatchSimulationPressing {
  String get label => switch (this) {
        MatchSimulationPressing.low => 'Low press',
        MatchSimulationPressing.medium => 'Mid press',
        MatchSimulationPressing.high => 'High press',
      };
}

enum MatchSimulationTempo {
  slow,
  medium,
  fast,
}

extension MatchSimulationTempoX on MatchSimulationTempo {
  String get label => switch (this) {
        MatchSimulationTempo.slow => 'Slow',
        MatchSimulationTempo.medium => 'Medium',
        MatchSimulationTempo.fast => 'Fast',
      };
}

enum MatchSimulationLineHeight {
  low,
  medium,
  high,
}

extension MatchSimulationLineHeightX on MatchSimulationLineHeight {
  String get label => switch (this) {
        MatchSimulationLineHeight.low => 'Low line',
        MatchSimulationLineHeight.medium => 'Mid line',
        MatchSimulationLineHeight.high => 'High line',
      };
}

enum MatchSimulationWidth {
  narrow,
  balanced,
  wide,
}

extension MatchSimulationWidthX on MatchSimulationWidth {
  String get label => switch (this) {
        MatchSimulationWidth.narrow => 'Narrow',
        MatchSimulationWidth.balanced => 'Balanced width',
        MatchSimulationWidth.wide => 'Wide',
      };
}

enum MatchSimulationRole {
  generic,
  poacher,
  finisher,
  playmaker,
  boxToBox,
  anchor,
  winger,
  fullback,
  stopper,
  sweeperKeeper,
}

extension MatchSimulationRoleX on MatchSimulationRole {
  String get label => switch (this) {
        MatchSimulationRole.generic => 'Generic',
        MatchSimulationRole.poacher => 'Poacher',
        MatchSimulationRole.finisher => 'Finisher',
        MatchSimulationRole.playmaker => 'Playmaker',
        MatchSimulationRole.boxToBox => 'Box to box',
        MatchSimulationRole.anchor => 'Anchor',
        MatchSimulationRole.winger => 'Winger',
        MatchSimulationRole.fullback => 'Fullback',
        MatchSimulationRole.stopper => 'Stopper',
        MatchSimulationRole.sweeperKeeper => 'Sweeper keeper',
      };
}

enum MatchSimulationImportance {
  friendly,
  quickMatch,
  tournament,
  finalMatch,
}

extension MatchSimulationImportanceX on MatchSimulationImportance {
  String get label => switch (this) {
        MatchSimulationImportance.friendly => 'Friendly',
        MatchSimulationImportance.quickMatch => 'Quick match',
        MatchSimulationImportance.tournament => 'Tournament',
        MatchSimulationImportance.finalMatch => 'Final',
      };
}

enum MatchFormTag {
  steady,
  inForm,
  outOfForm,
  risingTalent,
}

extension MatchFormTagX on MatchFormTag {
  String get label => switch (this) {
        MatchFormTag.steady => 'Steady',
        MatchFormTag.inForm => 'In Form',
        MatchFormTag.outOfForm => 'Out of Form',
        MatchFormTag.risingTalent => 'Rising Talent',
      };
}

class MatchSimulationTactics {
  const MatchSimulationTactics({
    required this.style,
    required this.pressing,
    required this.tempo,
    this.lineHeight = MatchSimulationLineHeight.medium,
    this.width = MatchSimulationWidth.balanced,
  });

  final MatchSimulationStyle style;
  final MatchSimulationPressing pressing;
  final MatchSimulationTempo tempo;
  final MatchSimulationLineHeight lineHeight;
  final MatchSimulationWidth width;

  String get summary =>
      '${style.label} | ${pressing.label} | ${tempo.label} tempo';

  String get detailSummary => '$summary | ${lineHeight.label} | ${width.label}';
}

class MatchSimulationPlayer {
  const MatchSimulationPlayer({
    required this.id,
    required this.name,
    required this.position,
    required this.overall,
    required this.age,
    required this.baseValueCredits,
    required this.finishing,
    required this.creativity,
    required this.defending,
    required this.goalkeeping,
    required this.pace,
    required this.workRate,
    this.role = MatchSimulationRole.generic,
  });

  final String id;
  final String name;
  final String position;
  final int overall;
  final int age;
  final double baseValueCredits;
  final int finishing;
  final int creativity;
  final int defending;
  final int goalkeeping;
  final int pace;
  final int workRate;
  final MatchSimulationRole role;

  bool get isGoalkeeper => _normalizedPosition(position) == 'GK';

  bool get isDefender {
    final String normalized = _normalizedPosition(position);
    return normalized == 'CB' ||
        normalized == 'RB' ||
        normalized == 'LB' ||
        normalized == 'RWB' ||
        normalized == 'LWB';
  }

  bool get isMidfielder {
    final String normalized = _normalizedPosition(position);
    return normalized == 'DM' ||
        normalized == 'CM' ||
        normalized == 'AM' ||
        normalized == 'RM' ||
        normalized == 'LM';
  }

  bool get isForward {
    final String normalized = _normalizedPosition(position);
    return normalized == 'ST' ||
        normalized == 'CF' ||
        normalized == 'RW' ||
        normalized == 'LW';
  }

  bool get isWidePlayer {
    final String normalized = _normalizedPosition(position);
    return normalized == 'RW' ||
        normalized == 'LW' ||
        normalized == 'RB' ||
        normalized == 'LB' ||
        normalized == 'RWB' ||
        normalized == 'LWB' ||
        normalized == 'RM' ||
        normalized == 'LM';
  }
}

class MatchSimulationTeam {
  const MatchSimulationTeam({
    required this.id,
    required this.name,
    required this.shortName,
    required this.formation,
    required this.primaryColorHex,
    required this.secondaryColorHex,
    required this.accentColorHex,
    required this.goalkeeperColorHex,
    required this.attack,
    required this.midfield,
    required this.defense,
    required this.goalkeeper,
    required this.tactics,
    required this.players,
  });

  final String id;
  final String name;
  final String shortName;
  final String formation;
  final String primaryColorHex;
  final String secondaryColorHex;
  final String accentColorHex;
  final String goalkeeperColorHex;
  final int attack;
  final int midfield;
  final int defense;
  final int goalkeeper;
  final MatchSimulationTactics tactics;
  final List<MatchSimulationPlayer> players;
}

class MatchSimulationRequest {
  const MatchSimulationRequest({
    required this.matchId,
    required this.homeTeam,
    required this.awayTeam,
    required this.seed,
    this.importance = MatchSimulationImportance.quickMatch,
    this.durationMinutes = 90,
    this.playbackDurationSeconds = 90,
  });

  final String matchId;
  final MatchSimulationTeam homeTeam;
  final MatchSimulationTeam awayTeam;
  final int seed;
  final MatchSimulationImportance importance;
  final int durationMinutes;
  final int playbackDurationSeconds;
}

class MatchSimulationTeamStats {
  const MatchSimulationTeamStats({
    required this.teamId,
    required this.teamName,
    required this.possessionPct,
    required this.shots,
    required this.shotsOnTarget,
    required this.expectedGoals,
    required this.bigChances,
    required this.turnoversForced,
    this.averageStaminaPct = 100,
    this.recoveries = 0,
    this.successfulPresses = 0,
  });

  final String teamId;
  final String teamName;
  final int possessionPct;
  final int shots;
  final int shotsOnTarget;
  final double expectedGoals;
  final int bigChances;
  final int turnoversForced;
  final int averageStaminaPct;
  final int recoveries;
  final int successfulPresses;
}

class MatchSimulationPlayerPerformance {
  const MatchSimulationPlayerPerformance({
    required this.player,
    required this.teamId,
    required this.teamName,
    required this.rating,
    required this.goals,
    required this.assists,
    required this.keyPasses,
    required this.shots,
    required this.shotsOnTarget,
    required this.saves,
    required this.turnoversWon,
    required this.mistakes,
    required this.cleanSheet,
    required this.isMvp,
    required this.formTag,
    required this.previousValueCredits,
    required this.nextValueCredits,
    required this.valueDeltaPct,
  });

  final MatchSimulationPlayer player;
  final String teamId;
  final String teamName;
  final double rating;
  final int goals;
  final int assists;
  final int keyPasses;
  final int shots;
  final int shotsOnTarget;
  final int saves;
  final int turnoversWon;
  final int mistakes;
  final bool cleanSheet;
  final bool isMvp;
  final MatchFormTag formTag;
  final double previousValueCredits;
  final double nextValueCredits;
  final double valueDeltaPct;

  double get valueDeltaCredits => nextValueCredits - previousValueCredits;

  MatchSimulationPlayerPerformance copyWith({
    double? rating,
    int? goals,
    int? assists,
    int? keyPasses,
    int? shots,
    int? shotsOnTarget,
    int? saves,
    int? turnoversWon,
    int? mistakes,
    bool? cleanSheet,
    bool? isMvp,
    MatchFormTag? formTag,
    double? previousValueCredits,
    double? nextValueCredits,
    double? valueDeltaPct,
  }) {
    return MatchSimulationPlayerPerformance(
      player: player,
      teamId: teamId,
      teamName: teamName,
      rating: rating ?? this.rating,
      goals: goals ?? this.goals,
      assists: assists ?? this.assists,
      keyPasses: keyPasses ?? this.keyPasses,
      shots: shots ?? this.shots,
      shotsOnTarget: shotsOnTarget ?? this.shotsOnTarget,
      saves: saves ?? this.saves,
      turnoversWon: turnoversWon ?? this.turnoversWon,
      mistakes: mistakes ?? this.mistakes,
      cleanSheet: cleanSheet ?? this.cleanSheet,
      isMvp: isMvp ?? this.isMvp,
      formTag: formTag ?? this.formTag,
      previousValueCredits: previousValueCredits ?? this.previousValueCredits,
      nextValueCredits: nextValueCredits ?? this.nextValueCredits,
      valueDeltaPct: valueDeltaPct ?? this.valueDeltaPct,
    );
  }
}

class MatchSimulationResult {
  const MatchSimulationResult({
    required this.request,
    required this.viewState,
    required this.homeStats,
    required this.awayStats,
    required this.playerPerformances,
  });

  final MatchSimulationRequest request;
  final MatchViewState viewState;
  final MatchSimulationTeamStats homeStats;
  final MatchSimulationTeamStats awayStats;
  final List<MatchSimulationPlayerPerformance> playerPerformances;

  int get homeScore => viewState.lastFrame.homeScore;

  int get awayScore => viewState.lastFrame.awayScore;

  List<MatchEvent> get timelineEvents => viewState.events;

  MatchSimulationPlayerPerformance? get mvp {
    for (final MatchSimulationPlayerPerformance item in playerPerformances) {
      if (item.isMvp) {
        return item;
      }
    }
    return null;
  }
}

String _normalizedPosition(String value) {
  final String upper = value.trim().toUpperCase();
  if (upper.contains('GK')) {
    return 'GK';
  }
  if (upper.contains('RWB')) {
    return 'RWB';
  }
  if (upper.contains('LWB')) {
    return 'LWB';
  }
  if (upper.contains('RB')) {
    return 'RB';
  }
  if (upper.contains('LB')) {
    return 'LB';
  }
  if (upper.contains('CB')) {
    return 'CB';
  }
  if (upper.contains('DM')) {
    return 'DM';
  }
  if (upper.contains('AM')) {
    return 'AM';
  }
  if (upper.contains('CM')) {
    return 'CM';
  }
  if (upper.contains('RM')) {
    return 'RM';
  }
  if (upper.contains('LM')) {
    return 'LM';
  }
  if (upper.contains('RW')) {
    return 'RW';
  }
  if (upper.contains('LW')) {
    return 'LW';
  }
  if (upper.contains('CF')) {
    return 'CF';
  }
  if (upper.contains('ST')) {
    return 'ST';
  }
  return upper;
}
