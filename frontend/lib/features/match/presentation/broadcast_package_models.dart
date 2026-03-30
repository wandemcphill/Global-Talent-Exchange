import '../../../data/gte_models.dart';

class MatchPresentationPlayer {
  const MatchPresentationPlayer({
    this.playerId,
    required this.playerName,
    this.shirtNumber,
    this.role,
    this.line,
    this.x,
    this.y,
    this.rating,
  });

  final String? playerId;
  final String playerName;
  final int? shirtNumber;
  final String? role;
  final String? line;
  final double? x;
  final double? y;
  final double? rating;

  String get displayLabel {
    final String number =
        shirtNumber == null ? '' : '${shirtNumber.toString().padLeft(2, '0')} ';
    return '$number$playerName'.trim();
  }

  factory MatchPresentationPlayer.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'presentation player',
    );
    return MatchPresentationPlayer(
      playerId: GteJson.stringOrNull(json, <String>['player_id', 'playerId']),
      playerName: GteJson.string(
        json,
        <String>['player_name', 'playerName'],
        fallback: '?',
      ),
      shirtNumber: GteJson.integerOrNull(
        json,
        <String>['shirt_number', 'shirtNumber'],
      ),
      role: GteJson.stringOrNull(json, <String>['role']),
      line: GteJson.stringOrNull(json, <String>['line']),
      x: _numberOrNull(json, const <String>['x']),
      y: _numberOrNull(json, const <String>['y']),
      rating: _numberOrNull(json, const <String>['rating']),
    );
  }
}

class MatchPresentationTeam {
  const MatchPresentationTeam({
    required this.teamId,
    required this.teamName,
    required this.shortName,
    required this.formation,
    this.coachName,
    this.recentForm,
    this.mentality,
    this.instructionSummary = const <String>[],
    this.starters = const <MatchPresentationPlayer>[],
    this.bench = const <MatchPresentationPlayer>[],
  });

  final String teamId;
  final String teamName;
  final String shortName;
  final String formation;
  final String? coachName;
  final int? recentForm;
  final String? mentality;
  final List<String> instructionSummary;
  final List<MatchPresentationPlayer> starters;
  final List<MatchPresentationPlayer> bench;

  factory MatchPresentationTeam.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'presentation team',
    );
    return MatchPresentationTeam(
      teamId: GteJson.string(json, <String>['team_id', 'teamId']),
      teamName: GteJson.string(json, <String>['team_name', 'teamName']),
      shortName: GteJson.string(
        json,
        <String>['short_name', 'shortName'],
        fallback: '',
      ),
      formation: GteJson.string(json, <String>['formation'], fallback: '4-3-3'),
      coachName: GteJson.stringOrNull(json, <String>['coach_name', 'coachName']),
      recentForm: GteJson.integerOrNull(
        json,
        <String>['recent_form', 'recentForm'],
      ),
      mentality: GteJson.stringOrNull(json, <String>['mentality']),
      instructionSummary: _stringList(
        GteJson.value(
              json,
              <String>['instruction_summary', 'instructionSummary'],
            ) ??
            const <Object?>[],
      ),
      starters: _mapPlayers(
        GteJson.value(json, <String>['starters']) ?? const <Object?>[],
      ),
      bench: _mapPlayers(
        GteJson.value(json, <String>['bench']) ?? const <Object?>[],
      ),
    );
  }
}

class MatchStandingsEntry {
  const MatchStandingsEntry({
    this.teamId,
    required this.teamName,
    this.position,
    this.played,
    this.points,
    this.goalDifference,
    this.form,
  });

  final String? teamId;
  final String teamName;
  final int? position;
  final int? played;
  final int? points;
  final int? goalDifference;
  final String? form;

  factory MatchStandingsEntry.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'standings entry',
    );
    return MatchStandingsEntry(
      teamId: GteJson.stringOrNull(json, <String>['team_id', 'teamId']),
      teamName: GteJson.string(json, <String>['team_name', 'teamName']),
      position: GteJson.integerOrNull(json, <String>['position']),
      played: GteJson.integerOrNull(json, <String>['played']),
      points: GteJson.integerOrNull(json, <String>['points']),
      goalDifference: GteJson.integerOrNull(
        json,
        <String>['goal_difference', 'goalDifference'],
      ),
      form: GteJson.stringOrNull(json, <String>['form']),
    );
  }
}

class MatchContextBoard {
  const MatchContextBoard({
    this.competitionName,
    this.competitionStage,
    this.venueName,
    this.kickoffLabel,
    this.dateLabel,
    this.refereeName,
    this.matchSignificance,
    this.standings = const <MatchStandingsEntry>[],
    this.storylines = const <String>[],
  });

  final String? competitionName;
  final String? competitionStage;
  final String? venueName;
  final String? kickoffLabel;
  final String? dateLabel;
  final String? refereeName;
  final String? matchSignificance;
  final List<MatchStandingsEntry> standings;
  final List<String> storylines;

  factory MatchContextBoard.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value ?? const <String, Object?>{},
      label: 'context board',
    );
    return MatchContextBoard(
      competitionName: GteJson.stringOrNull(
        json,
        <String>['competition_name', 'competitionName'],
      ),
      competitionStage: GteJson.stringOrNull(
        json,
        <String>['competition_stage', 'competitionStage'],
      ),
      venueName: GteJson.stringOrNull(
        json,
        <String>['venue_name', 'venueName'],
      ),
      kickoffLabel: GteJson.stringOrNull(
        json,
        <String>['kickoff_label', 'kickoffLabel'],
      ),
      dateLabel: GteJson.stringOrNull(
        json,
        <String>['date_label', 'dateLabel'],
      ),
      refereeName: GteJson.stringOrNull(
        json,
        <String>['referee_name', 'refereeName'],
      ),
      matchSignificance: GteJson.stringOrNull(
        json,
        <String>['match_significance', 'matchSignificance'],
      ),
      standings: _mapStandings(
        GteJson.value(json, <String>['standings']) ?? const <Object?>[],
      ),
      storylines: _stringList(
        GteJson.value(json, <String>['storylines']) ?? const <Object?>[],
      ),
    );
  }
}

class MatchReactionCard {
  const MatchReactionCard({
    required this.source,
    required this.headline,
    required this.detail,
    this.sentiment,
    this.tag,
  });

  final String source;
  final String headline;
  final String detail;
  final String? sentiment;
  final String? tag;

  factory MatchReactionCard.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'reaction card',
    );
    return MatchReactionCard(
      source: GteJson.string(json, <String>['source']),
      headline: GteJson.string(json, <String>['headline']),
      detail: GteJson.string(json, <String>['detail']),
      sentiment: GteJson.stringOrNull(json, <String>['sentiment']),
      tag: GteJson.stringOrNull(json, <String>['tag']),
    );
  }
}

class MatchPresentationPackage {
  const MatchPresentationPackage({
    required this.matchLabel,
    required this.home,
    required this.away,
    this.context = const MatchContextBoard(),
    this.reactions = const <MatchReactionCard>[],
    this.ratingLeaders = const <MatchPresentationPlayer>[],
    this.momentumNotes = const <String>[],
    this.coachNotes = const <String>[],
    this.commentaryHighlights = const <String>[],
  });

  final String matchLabel;
  final MatchPresentationTeam home;
  final MatchPresentationTeam away;
  final MatchContextBoard context;
  final List<MatchReactionCard> reactions;
  final List<MatchPresentationPlayer> ratingLeaders;
  final List<String> momentumNotes;
  final List<String> coachNotes;
  final List<String> commentaryHighlights;

  factory MatchPresentationPackage.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'presentation package',
    );
    return MatchPresentationPackage(
      matchLabel: GteJson.string(
        json,
        <String>['match_label', 'matchLabel'],
        fallback: 'Matchday package',
      ),
      home: MatchPresentationTeam.fromJson(
        GteJson.value(json, <String>['home']),
      ),
      away: MatchPresentationTeam.fromJson(
        GteJson.value(json, <String>['away']),
      ),
      context: MatchContextBoard.fromJson(
        GteJson.value(json, <String>['context']),
      ),
      reactions: _mapReactions(
        GteJson.value(json, <String>['reactions']) ?? const <Object?>[],
      ),
      ratingLeaders: _mapPlayers(
        GteJson.value(
              json,
              <String>['rating_leaders', 'ratingLeaders'],
            ) ??
            const <Object?>[],
      ),
      momentumNotes: _stringList(
        GteJson.value(
              json,
              <String>['momentum_notes', 'momentumNotes'],
            ) ??
            const <Object?>[],
      ),
      coachNotes: _stringList(
        GteJson.value(json, <String>['coach_notes', 'coachNotes']) ??
            const <Object?>[],
      ),
      commentaryHighlights: _stringList(
        GteJson.value(
              json,
              <String>['commentary_highlights', 'commentaryHighlights'],
            ) ??
            const <Object?>[],
      ),
    );
  }
}

double? _numberOrNull(Map<String, Object?> json, List<String> keys) {
  final Object? raw = GteJson.value(json, keys);
  if (raw == null) {
    return null;
  }
  if (raw is num) {
    return raw.toDouble();
  }
  return double.tryParse(raw.toString());
}

List<String> _stringList(Object? value) {
  final List<Object?> raw = GteJson.list(
    value ?? const <Object?>[],
    label: 'string list',
  );
  return raw
      .map((Object? item) => item?.toString().trim() ?? '')
      .where((String item) => item.isNotEmpty)
      .toList(growable: false);
}

List<MatchPresentationPlayer> _mapPlayers(Object? value) {
  final List<Object?> raw = GteJson.list(
    value ?? const <Object?>[],
    label: 'presentation players',
  );
  return raw
      .map(MatchPresentationPlayer.fromJson)
      .toList(growable: false);
}

List<MatchStandingsEntry> _mapStandings(Object? value) {
  final List<Object?> raw = GteJson.list(
    value ?? const <Object?>[],
    label: 'standings entries',
  );
  return raw.map(MatchStandingsEntry.fromJson).toList(growable: false);
}

List<MatchReactionCard> _mapReactions(Object? value) {
  final List<Object?> raw = GteJson.list(
    value ?? const <Object?>[],
    label: 'reaction cards',
  );
  return raw.map(MatchReactionCard.fromJson).toList(growable: false);
}
