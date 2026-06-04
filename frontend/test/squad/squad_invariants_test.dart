import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/features/squad/squad.dart';
import 'package:gte_frontend/shared/state/gtex_async_surface_state.dart';

void main() {
  test('selection ready provider uses backend selectionReady flags', () {
    final SquadOperationsSnapshot snapshot = SquadOperationsSnapshot(
      roster: <SquadPlayerDTO>[
        _player('p1', selectionReady: true),
        _player('p2', selectionReady: false),
      ],
      availabilityMatrix: const AvailabilityMatrix(rows: <AvailabilityRow>[]),
      injuries: const <InjuryDTO>[],
      chemistry: const ChemistryReport(),
      contracts: const <ContractStatusDTO>[],
      scoutingNotes: const <ScoutingNoteDTO>[],
    );

    final List<SquadPlayerDTO> ready = squadSelectionReadyFromState(
      GtexData<SquadOperationsSnapshot>(data: snapshot),
    );

    expect(ready.map((SquadPlayerDTO player) => player.id), <String>['p1']);
  });

  test('empty availability matrix renders empty surface state', () {
    final GtexSurfaceState<AvailabilityMatrix> state =
        squadAvailabilityMatrixSurfaceState(
          const AvailabilityMatrix(rows: <AvailabilityRow>[]),
        );

    expect(state, isA<GtexEmpty<AvailabilityMatrix>>());
  });

  test('contract warnings use weeks remaining below 26', () {
    final SquadOperationsSnapshot snapshot = SquadOperationsSnapshot(
      roster: <SquadPlayerDTO>[
        _player('p1', weeksRemaining: 25),
        _player('p2', weeksRemaining: 30),
      ],
      availabilityMatrix: const AvailabilityMatrix(rows: <AvailabilityRow>[]),
      injuries: const <InjuryDTO>[],
      chemistry: const ChemistryReport(),
      contracts: const <ContractStatusDTO>[],
      scoutingNotes: const <ScoutingNoteDTO>[],
    );

    expect(squadContractWarnings(snapshot), hasLength(1));
    expect(squadContractWarnings(snapshot).single.playerId, 'p1');
  });
}

SquadPlayerDTO _player(
  String id, {
  bool selectionReady = true,
  int weeksRemaining = 52,
}) {
  return SquadPlayerDTO(
    id: id,
    name: 'Player $id',
    position: 'CM',
    availability: SquadAvailabilityStatus.available,
    morale: const MoraleScore(score: 80, label: 'steady'),
    chemistryFit: const ChemistryFitDTO(
      overallScore: 70,
      positionFit: 70,
      teamFit: 70,
    ),
    contractStatus: ContractStatusDTO(
      playerId: id,
      weeksRemaining: weeksRemaining,
    ),
    selectionReady: selectionReady,
    stats: const PlayerStatsDTO(),
  );
}
