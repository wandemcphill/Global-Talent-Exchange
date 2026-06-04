import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/formation/formation.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

import 'formation_test_fixtures.dart';

void main() {
  testWidgets('tactical pitch board renders backend formation slots', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _TestApp(
        child: TacticalPitchBoard(
          formation: fixtureFormation(),
          players: fixtureEligiblePlayers(11),
        ),
      ),
    );

    expect(find.byKey(const Key('formation-slot-slot-1')), findsOneWidget);
    expect(find.text('GK'), findsOneWidget);
    expect(find.text('Player 1'), findsOneWidget);
  });

  testWidgets(
    'editor blocks publish when backend eligible players are below 11',
    (WidgetTester tester) async {
      final FakeFormationRepository repository = FakeFormationRepository(
        activeFormation: fixtureFormation(),
        eligiblePlayers: fixtureEligiblePlayers(10),
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            formationRepositoryProvider.overrideWithValue(repository),
            formationUserRoleProvider.overrideWithValue('club.owner'),
          ],
          child: const _TestApp(child: FormationEditorScreen(clubId: 'club-1')),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text(insufficientEligiblePlayersMessage), findsWidgets);
      final FilledButton publishButton = tester.widget<FilledButton>(
        find.byKey(const Key('formation-publish')),
      );
      expect(publishButton.onPressed, isNull);
    },
  );

  testWidgets('history renders backend formations, not local editor drafts', (
    WidgetTester tester,
  ) async {
    final FakeFormationRepository repository = FakeFormationRepository(
      activeFormation: fixtureFormation(status: FormationStatus.published),
      history: <FormationHistoryItemDto>[
        FormationHistoryItemDto(
          id: 'backend-history',
          name: 'Backend Archive',
          scheme: '4-2-3-1',
          publishedAt: fixtureNow,
          chemistryScore: 88,
          status: FormationStatus.published,
        ),
      ],
    );
    final ProviderContainer container = ProviderContainer(
      overrides: [
        formationRepositoryProvider.overrideWithValue(repository),
        formationUserRoleProvider.overrideWithValue('club.owner'),
      ],
    );
    addTearDown(container.dispose);
    await container.read(formationEditorProvider.notifier).load('club-1');
    container.read(formationEditorProvider.notifier).createDraft();

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: const _TestApp(child: FormationHistoryScreen(clubId: 'club-1')),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Backend Archive'), findsOneWidget);
    expect(find.text('4-3-3 draft'), findsNothing);
  });
}

class _TestApp extends StatelessWidget {
  const _TestApp({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(theme: GteShellTheme.build(), home: child);
  }
}
