import 'package:gte_frontend/features/match_center/models/match_event.dart';
import 'package:gte_frontend/features/match_center/models/match_timeline_frame.dart';
import 'package:gte_frontend/features/match_center/models/match_view_state.dart';
import 'broadcast_package_models.dart';

class BroadcastPackageRepository {
  const BroadcastPackageRepository();

  MatchPresentationPackage resolve(MatchViewState viewState) {
    final MatchPresentationPackage package =
        viewState.presentationPackage ?? _buildFallbackPackage(viewState);
    return MatchPresentationPackage(
      matchLabel: package.matchLabel,
      home: _mergeTeamIdentity(package.home, viewState.homeTeam),
      away: _mergeTeamIdentity(package.away, viewState.awayTeam),
      context: _normalizeContext(
        package.context,
        home: package.home,
        away: package.away,
      ),
      reactions: package.reactions,
      ratingLeaders: package.ratingLeaders,
      momentumNotes: package.momentumNotes,
      coachNotes: package.coachNotes,
      commentaryHighlights: package.commentaryHighlights,
    );
  }

  BroadcastPackageData resolveBroadcastData({
    required String matchKey,
    required MatchViewState viewState,
  }) {
    final MatchPresentationPackage package = resolve(viewState);
    return BroadcastPackageData(
      matchKey: matchKey,
      package: package,
      storylinePanel: _buildStorylinePanel(
        viewState: viewState,
        package: package,
        eventTimelineLocked: viewState.scoreRevealLocked,
      ),
    );
  }

  MatchPresentationPackage _buildFallbackPackage(MatchViewState viewState) {
    return MatchPresentationPackage(
      matchLabel:
          '${viewState.homeTeam.teamName} vs ${viewState.awayTeam.teamName}',
      home: _fallbackTeam(viewState, MatchViewerSide.home),
      away: _fallbackTeam(viewState, MatchViewerSide.away),
    );
  }

  MatchPresentationTeam _fallbackTeam(
    MatchViewState viewState,
    MatchViewerSide side,
  ) {
    final MatchViewerTeam team = viewState.teamForSide(side);
    final List<MatchViewerPlayerFrame> starters = _sortedPlayers(
      viewState: viewState,
      side: side,
    );
    return MatchPresentationTeam(
      teamId: team.teamId,
      teamName: team.teamName,
      shortName: team.shortName,
      formation: team.formation,
      primaryColorHex: team.primaryColorHex,
      secondaryColorHex: team.secondaryColorHex,
      accentColorHex: team.accentColorHex,
      goalkeeperColorHex: team.goalkeeperColorHex,
      starters: starters
          .map(
            (MatchViewerPlayerFrame player) => MatchPresentationPlayer(
              playerId: player.playerId,
              playerName: player.label,
              shirtNumber: player.shirtNumber,
              role: player.role.name,
              line: player.line.name,
              x: player.position.x,
              y: player.position.y,
            ),
          )
          .toList(growable: false),
    );
  }

  List<MatchViewerPlayerFrame> _sortedPlayers({
    required MatchViewState viewState,
    required MatchViewerSide side,
  }) {
    if (viewState.frames.isEmpty) {
      return const <MatchViewerPlayerFrame>[];
    }
    final List<MatchViewerPlayerFrame> players = viewState.frames.first.players
        .where((MatchViewerPlayerFrame player) => player.side == side)
        .toList(growable: false);
    players.sort((MatchViewerPlayerFrame left, MatchViewerPlayerFrame right) {
      final int lineOrder = _lineRank(
        left.line,
      ).compareTo(_lineRank(right.line));
      if (lineOrder != 0) {
        return lineOrder;
      }
      final int xOrder = left.position.x.compareTo(right.position.x);
      if (xOrder != 0) {
        return xOrder;
      }
      return left.position.y.compareTo(right.position.y);
    });
    return players;
  }

  int _lineRank(MatchPlayerLine value) {
    switch (value) {
      case MatchPlayerLine.goalkeeper:
        return 0;
      case MatchPlayerLine.defense:
        return 1;
      case MatchPlayerLine.midfield:
        return 2;
      case MatchPlayerLine.attack:
        return 3;
    }
  }

  MatchPresentationTeam _mergeTeamIdentity(
    MatchPresentationTeam packageTeam,
    MatchViewerTeam sourceTeam,
  ) {
    return MatchPresentationTeam(
      teamId: packageTeam.teamId,
      teamName: packageTeam.teamName,
      shortName: packageTeam.shortName,
      formation: packageTeam.formation,
      crest: packageTeam.crest,
      primaryColorHex:
          packageTeam.primaryColorHex ?? sourceTeam.primaryColorHex,
      secondaryColorHex:
          packageTeam.secondaryColorHex ?? sourceTeam.secondaryColorHex,
      accentColorHex: packageTeam.accentColorHex ?? sourceTeam.accentColorHex,
      goalkeeperColorHex:
          packageTeam.goalkeeperColorHex ?? sourceTeam.goalkeeperColorHex,
      coachName: packageTeam.coachName,
      recentForm: packageTeam.recentForm,
      mentality: packageTeam.mentality,
      instructionSummary: packageTeam.instructionSummary,
      starters: packageTeam.starters,
      bench: packageTeam.bench,
    );
  }

  MatchContextBoard _normalizeContext(
    MatchContextBoard context, {
    required MatchPresentationTeam home,
    required MatchPresentationTeam away,
  }) {
    if (context.matchSignificance != null &&
        context.matchSignificance!.trim().isNotEmpty) {
      return context;
    }
    final MatchStandingsEntry? homeStanding = _standingForTeam(
      context.standings,
      home,
    );
    final MatchStandingsEntry? awayStanding = _standingForTeam(
      context.standings,
      away,
    );
    final String? homeRank = _ordinal(homeStanding?.position);
    final String? awayRank = _ordinal(awayStanding?.position);
    if (homeStanding == null ||
        awayStanding == null ||
        homeRank == null ||
        awayRank == null) {
      return context;
    }
    return MatchContextBoard(
      competitionName: context.competitionName,
      competitionStage: context.competitionStage,
      competitionContext: context.competitionContext,
      venueName: context.venueName,
      kickoffLabel: context.kickoffLabel,
      dateLabel: context.dateLabel,
      refereeName: context.refereeName,
      matchSignificance:
          '$homeRank ${home.teamName} versus $awayRank ${away.teamName} in the table.',
      standings: context.standings,
      storylines: context.storylines,
    );
  }

  MatchStandingsEntry? _standingForTeam(
    List<MatchStandingsEntry> standings,
    MatchPresentationTeam team,
  ) {
    for (final MatchStandingsEntry entry in standings) {
      if (entry.teamId != null && entry.teamId == team.teamId) {
        return entry;
      }
      if (entry.teamName.trim().toLowerCase() ==
          team.teamName.trim().toLowerCase()) {
        return entry;
      }
    }
    return null;
  }

  String? _ordinal(int? value) {
    if (value == null) {
      return null;
    }
    final int mod100 = value % 100;
    if (mod100 >= 11 && mod100 <= 13) {
      return '${value}th';
    }
    switch (value % 10) {
      case 1:
        return '${value}st';
      case 2:
        return '${value}nd';
      case 3:
        return '${value}rd';
      default:
        return '${value}th';
    }
  }

  BroadcastStorylinePanelData _buildStorylinePanel({
    required MatchViewState viewState,
    required MatchPresentationPackage package,
    required bool eventTimelineLocked,
  }) {
    final List<String> staffNotes = _uniqueStrings(<String>[
      ...package.coachNotes,
      ..._instructionNotes(package.home),
      ..._instructionNotes(package.away),
    ]);
    final List<String> pressRoundup = _reactionLines(
      package.reactions.where(
        (MatchReactionCard card) => card.source.trim().toLowerCase() == 'press',
      ),
    );
    final List<String> socialRoundup = _reactionLines(
      package.reactions.where(
        (MatchReactionCard card) => <String>{
          'fans',
          'social',
          'alerts',
        }.contains(card.source.trim().toLowerCase()),
      ),
    );
    final List<String> lineupChanges = _uniqueStrings(<String>[
      ..._reactionLines(
        package.reactions.where(
          (MatchReactionCard card) => _containsAny(
            '${card.headline} ${card.detail} ${card.tag ?? ''}',
            const <String>['lineup', 'line-up', 'starting xi', 'bench'],
          ),
        ),
      ),
      if (!eventTimelineLocked)
        ..._eventLines(
          viewState.events.where(
            (MatchEvent event) =>
                event.type == MatchViewerEventType.substitution,
          ),
        ),
    ]);
    final List<String> injuries =
        eventTimelineLocked
            ? const <String>[]
            : _eventLines(
              viewState.events.where(
                (MatchEvent event) => event.type == MatchViewerEventType.injury,
              ),
            );
    final List<String> suspensions =
        eventTimelineLocked
            ? const <String>[]
            : _eventLines(
              viewState.events.where(
                (MatchEvent event) =>
                    event.type == MatchViewerEventType.redCard,
              ),
            );
    final List<String> talkingPoints = _uniqueStrings(<String>[
      if (package.context.matchSignificance != null)
        package.context.matchSignificance!,
      ...package.context.storylines,
      ..._reactionLines(
        package.reactions.where(
          (MatchReactionCard card) =>
              card.source.trim().toLowerCase() == 'match desk',
        ),
      ),
    ]);
    return BroadcastStorylinePanelData(
      staffNotes: staffNotes,
      pressRoundup: pressRoundup,
      socialRoundup: socialRoundup,
      injuries: injuries,
      suspensions: suspensions,
      lineupChanges: lineupChanges,
      talkingPoints: talkingPoints,
    );
  }

  List<String> _instructionNotes(MatchPresentationTeam team) {
    if (team.instructionSummary.isEmpty) {
      return const <String>[];
    }
    return team.instructionSummary
        .map((String item) => '${team.teamName}: $item')
        .toList(growable: false);
  }

  List<String> _reactionLines(Iterable<MatchReactionCard> cards) {
    return _uniqueStrings(
      cards.map(_reactionLine).where((String item) => item.isNotEmpty),
    );
  }

  String _reactionLine(MatchReactionCard card) {
    final String headline = card.headline.trim();
    final String detail = card.detail.trim();
    if (headline.isEmpty) {
      return detail;
    }
    if (detail.isEmpty ||
        detail.toLowerCase().startsWith(headline.toLowerCase())) {
      return headline;
    }
    return '$headline. $detail';
  }

  List<String> _eventLines(Iterable<MatchEvent> events) {
    return _uniqueStrings(
      events.map(_eventLine).where((String item) => item.isNotEmpty),
    );
  }

  String _eventLine(MatchEvent event) {
    final String clock = event.clockLabel.trim();
    final String team = event.teamName?.trim() ?? '';
    final String primary = event.primaryPlayerName?.trim() ?? '';
    final String secondary = event.secondaryPlayerName?.trim() ?? '';
    switch (event.type) {
      case MatchViewerEventType.substitution:
        if (primary.isNotEmpty && secondary.isNotEmpty) {
          return '$clock ${team.isEmpty ? '' : '$team: '}$secondary on for $primary'
              .trim();
        }
        break;
      case MatchViewerEventType.injury:
        if (primary.isNotEmpty) {
          return '$clock ${team.isEmpty ? '' : '$team: '}$primary injury setback'
              .trim();
        }
        break;
      case MatchViewerEventType.redCard:
        if (primary.isNotEmpty) {
          return '$clock ${team.isEmpty ? '' : '$team: '}$primary sent off'
              .trim();
        }
        break;
      default:
        break;
    }
    final String commentary = event.commentary.trim();
    if (commentary.isNotEmpty) {
      return '$clock $commentary'.trim();
    }
    return '$clock ${event.bannerText}'.trim();
  }

  bool _containsAny(String source, List<String> tokens) {
    final String normalized = source.trim().toLowerCase();
    for (final String token in tokens) {
      if (normalized.contains(token)) {
        return true;
      }
    }
    return false;
  }

  List<String> _uniqueStrings(Iterable<String> items) {
    final Set<String> seen = <String>{};
    final List<String> output = <String>[];
    for (final String item in items) {
      final String normalized = item.trim();
      if (normalized.isEmpty || !seen.add(normalized)) {
        continue;
      }
      output.add(normalized);
    }
    return output;
  }
}
