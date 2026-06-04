import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/core/theme/app_theme.dart';
import 'package:gte_frontend/features/squad/data/squad_repository.dart';
import 'package:gte_frontend/features/squad/domain/squad_models.dart';
import 'package:gte_frontend/features/squad/providers/squad_providers.dart';
import 'package:gte_frontend/features/squad/squad_screen.dart';

void main() {
  testWidgets(
    'renders empty availability matrix when backend has zero players',
    (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1280, 2200);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            squadRepositoryProvider.overrideWithValue(
              _FakeSquadRepository(_emptySquadSnapshot()),
            ),
          ],
          child: MaterialApp(
            theme: AppTheme.dark(),
            home: const Scaffold(
              body: SquadScreen(clubId: 'club-1', role: 'club.owner'),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Availability Matrix'), findsOneWidget);
      expect(
        find.text('No players in squad - availability matrix is empty.'),
        findsOneWidget,
      );
      expect(
        find.byKey(const Key('squad-empty-availability-matrix')),
        findsOneWidget,
      );
    },
  );

  testWidgets('renders chemistry warnings and short contract badge', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1280, 3000);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          squadRepositoryProvider.overrideWithValue(
            _FakeSquadRepository(_warningSquadSnapshot()),
          ),
        ],
        child: MaterialApp(
          theme: AppTheme.dark(),
          home: const Scaffold(
            body: SquadScreen(clubId: 'club-1', role: 'club.owner'),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(
      find.text('Chemistry warning: Left-sided overload needs balancing'),
      findsWidgets,
    );
    expect(find.byKey(const Key('contract-renewal-risk-p-1')), findsOneWidget);
    expect(find.textContaining('Renewal risk <26 weeks'), findsWidgets);
  });
}

class _FakeSquadRepository implements ISquadRepository {
  const _FakeSquadRepository(this.snapshot);

  final SquadOperationsSnapshot snapshot;

  @override
  Future<SquadOperationsSnapshot> fetchSquadOperations(String clubId) async =>
      snapshot;

  @override
  Future<AvailabilityMatrix> getAvailabilityMatrix(String clubId) async =>
      snapshot.availabilityMatrix;

  @override
  Future<ChemistryReport> getChemistryReport(String clubId) async =>
      snapshot.chemistry;

  @override
  Future<List<ContractStatusDTO>> getContracts(String clubId) async =>
      snapshot.contracts;

  @override
  Future<List<InjuryDTO>> getInjuries(String clubId) async => snapshot.injuries;

  @override
  Future<List<ScoutingNoteDTO>> getScoutingNotes(String clubId) async =>
      snapshot.scoutingNotes;

  @override
  Future<List<SquadPlayerDTO>> getSquadRoster(String clubId) async =>
      snapshot.roster;
}

SquadOperationsSnapshot _emptySquadSnapshot() {
  return const SquadOperationsSnapshot(
    roster: <SquadPlayerDTO>[],
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
}

SquadOperationsSnapshot _warningSquadSnapshot() {
  const SquadPlayerDTO player = SquadPlayerDTO(
    id: 'p-1',
    name: 'Ibrahim Sane',
    position: 'LW',
    age: 22,
    nationality: 'Senegal',
    availability: SquadAvailabilityStatus.available,
    morale: MoraleScore(score: 74, label: 'good', trend: 'stable'),
    chemistryFit: ChemistryFitDTO(
      overallScore: 61,
      positionFit: 68,
      teamFit: 57,
      warnings: <String>['Left-sided overload needs balancing'],
    ),
    contractStatus: ContractStatusDTO(
      playerId: 'p-1',
      playerName: 'Ibrahim Sane',
      status: 'active',
      weeksRemaining: 12,
    ),
    selectionReady: true,
    scoutingNotes: <ScoutingNoteDTO>[
      ScoutingNoteDTO(
        playerId: 'p-1',
        authorId: 'scout-1',
        content: 'Needs right-side chemistry support',
      ),
    ],
    stats: PlayerStatsDTO(appearances: 16, rating: 7.1),
  );

  return const SquadOperationsSnapshot(
    roster: <SquadPlayerDTO>[player],
    availabilityMatrix: AvailabilityMatrix(
      players: <AvailabilityMatrixPlayer>[
        AvailabilityMatrixPlayer(
          playerId: 'p-1',
          name: 'Ibrahim Sane',
          position: 'LW',
        ),
      ],
      fixtures: <AvailabilityFixture>[
        AvailabilityFixture(fixtureId: 'fx-1', label: 'vs Meridian'),
      ],
      cells: <AvailabilityCell>[
        AvailabilityCell(
          playerId: 'p-1',
          fixtureId: 'fx-1',
          status: SquadAvailabilityStatus.available,
        ),
      ],
    ),
    injuries: <InjuryDTO>[],
    chemistry: ChemistryReport(
      overallScore: 64,
      warnings: <String>['Left-sided overload needs balancing'],
    ),
    contracts: <ContractStatusDTO>[
      ContractStatusDTO(
        playerId: 'p-1',
        playerName: 'Ibrahim Sane',
        status: 'active',
        weeksRemaining: 12,
      ),
    ],
    scoutingNotes: <ScoutingNoteDTO>[],
  );
}
