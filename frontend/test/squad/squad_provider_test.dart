import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/features/squad/domain/squad_models.dart';
import 'package:gte_frontend/features/squad/providers/squad_providers.dart';
import 'package:gte_frontend/shared/state/gtex_async_surface_state.dart';

void main() {
  test('availability matrix with zero players maps to GtexEmpty', () {
    const AvailabilityMatrix matrix = AvailabilityMatrix(
      players: <AvailabilityMatrixPlayer>[],
      fixtures: <AvailabilityFixture>[],
      cells: <AvailabilityCell>[],
    );

    final GtexSurfaceState<AvailabilityMatrix> state =
        squadAvailabilityMatrixSurfaceState(matrix);

    expect(state, isA<GtexEmpty<AvailabilityMatrix>>());
    expect(
      (state as GtexEmpty<AvailabilityMatrix>).reason,
      'No players in squad - availability matrix is empty.',
    );
  });

  test('selection-ready derived helper keeps only backend-ready players', () {
    const SquadOperationsSnapshot snapshot = SquadOperationsSnapshot(
      roster: <SquadPlayerDTO>[
        SquadPlayerDTO(
          id: 'ready',
          name: 'Ready Player',
          position: 'CM',
          availability: SquadAvailabilityStatus.available,
          morale: MoraleScore(score: 80, label: 'good'),
          chemistryFit: ChemistryFitDTO(
            overallScore: 80,
            positionFit: 80,
            teamFit: 80,
          ),
          contractStatus: ContractStatusDTO(weeksRemaining: 52),
          selectionReady: true,
          stats: PlayerStatsDTO(),
        ),
        SquadPlayerDTO(
          id: 'blocked',
          name: 'Blocked Player',
          position: 'CB',
          availability: SquadAvailabilityStatus.injured,
          morale: MoraleScore(score: 45, label: 'low'),
          chemistryFit: ChemistryFitDTO(
            overallScore: 50,
            positionFit: 55,
            teamFit: 48,
          ),
          contractStatus: ContractStatusDTO(weeksRemaining: 40),
          selectionReady: false,
          stats: PlayerStatsDTO(),
        ),
      ],
      availabilityMatrix: AvailabilityMatrix(
        players: <AvailabilityMatrixPlayer>[],
        fixtures: <AvailabilityFixture>[],
        cells: <AvailabilityCell>[],
      ),
      injuries: <InjuryDTO>[],
      chemistry: ChemistryReport(),
      contracts: <ContractStatusDTO>[],
      scoutingNotes: <ScoutingNoteDTO>[],
    );

    final List<SquadPlayerDTO> ready = squadSelectionReadyFromState(
      const GtexData<SquadOperationsSnapshot>(data: snapshot),
    );

    expect(ready, hasLength(1));
    expect(ready.single.id, 'ready');
  });

  test('contract warnings include weeksRemaining under 26', () {
    const SquadOperationsSnapshot snapshot = SquadOperationsSnapshot(
      roster: <SquadPlayerDTO>[],
      availabilityMatrix: AvailabilityMatrix(
        players: <AvailabilityMatrixPlayer>[],
        fixtures: <AvailabilityFixture>[],
        cells: <AvailabilityCell>[],
      ),
      injuries: <InjuryDTO>[],
      chemistry: ChemistryReport(),
      contracts: <ContractStatusDTO>[
        ContractStatusDTO(playerId: 'soon', weeksRemaining: 25),
        ContractStatusDTO(playerId: 'safe', weeksRemaining: 26),
      ],
      scoutingNotes: <ScoutingNoteDTO>[],
    );

    final List<ContractStatusDTO> warnings = squadContractWarnings(snapshot);

    expect(warnings, hasLength(1));
    expect(warnings.single.playerId, 'soon');
  });
}
