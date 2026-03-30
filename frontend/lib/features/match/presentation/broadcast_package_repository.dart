import '../../../models/match_timeline_frame.dart';
import '../../../models/match_view_state.dart';
import 'broadcast_package_models.dart';

class BroadcastPackageRepository {
  const BroadcastPackageRepository();

  MatchPresentationPackage resolve(MatchViewState viewState) {
    final MatchPresentationPackage? package = viewState.presentationPackage;
    if (package != null) {
      return package;
    }
    return MatchPresentationPackage(
      matchLabel:
          '${viewState.homeTeam.teamName} vs ${viewState.awayTeam.teamName}',
      home: _fallbackTeam(viewState, MatchViewerSide.home),
      away: _fallbackTeam(viewState, MatchViewerSide.away),
      context: MatchContextBoard(
        competitionName: viewState.source.replaceAll('_', ' ').toUpperCase(),
        matchSignificance:
            'Live match-viewer contract active. Expanded package data is not present on this payload.',
      ),
    );
  }

  MatchPresentationTeam _fallbackTeam(
    MatchViewState viewState,
    MatchViewerSide side,
  ) {
    final MatchViewerTeam team = viewState.teamForSide(side);
    final List<MatchViewerPlayerFrame> starters =
        viewState.frames.isEmpty
            ? const <MatchViewerPlayerFrame>[]
            : viewState.frames.first.players
                .where((MatchViewerPlayerFrame player) => player.side == side)
                .toList(growable: false);
    return MatchPresentationTeam(
      teamId: team.teamId,
      teamName: team.teamName,
      shortName: team.shortName,
      formation: team.formation,
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
}
