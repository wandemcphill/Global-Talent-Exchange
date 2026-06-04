import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/formation/formation.dart';
import 'package:gte_frontend/shared/state/gtex_async_surface_state.dart';

import 'formation_test_fixtures.dart';

void main() {
  ProviderContainer containerFor(FakeFormationRepository repository) {
    final ProviderContainer container = ProviderContainer(
      overrides: [
        formationRepositoryProvider.overrideWithValue(repository),
        formationUserRoleProvider.overrideWithValue('club.owner'),
      ],
    );
    addTearDown(container.dispose);
    return container;
  }

  test(
    'load enters blocked state when backend eligible count is below 11',
    () async {
      final FakeFormationRepository repository = FakeFormationRepository(
        activeFormation: fixtureFormation(),
        eligiblePlayers: fixtureEligiblePlayers(10),
      );
      final ProviderContainer container = containerFor(repository);

      await container.read(formationEditorProvider.notifier).load('club-1');

      final FormationEditorState state = container.read(
        formationEditorProvider,
      );
      expect(state.surfaceState, isA<GtexBlocked<FormationDto>>());
      expect(
        (state.surfaceState as GtexBlocked<FormationDto>).reason,
        insufficientEligiblePlayersMessage,
      );
    },
  );

  test('publish is pending until backend confirms with audit ref', () async {
    final Completer<FormationDto> publishCompleter = Completer<FormationDto>();
    final FakeFormationRepository repository = FakeFormationRepository(
      activeFormation: fixtureFormation(status: FormationStatus.draft),
    )..publishCompleter = publishCompleter;
    final ProviderContainer container = containerFor(repository);
    final FormationEditorNotifier notifier = container.read(
      formationEditorProvider.notifier,
    );

    await notifier.load('club-1');
    final Future<FormationDto?> publishFuture = notifier.requestPublish();

    expect(
      container.read(formationEditorProvider).surfaceState,
      isA<GtexPending<FormationDto>>(),
    );
    expect(container.read(formationPublishReadyProvider).canPublish, isFalse);

    publishCompleter.complete(
      fixtureFormation(
        id: 'formation-1',
        status: FormationStatus.published,
        auditRef: 'audit-publish-123',
      ),
    );
    await publishFuture;

    final GtexSurfaceState<FormationDto> surfaceState =
        container.read(formationEditorProvider).surfaceState;
    expect(surfaceState, isA<GtexConfirmed<FormationDto>>());
    expect(
      (surfaceState as GtexConfirmed<FormationDto>).auditRef,
      'audit-publish-123',
    );
  });

  test('restore requires confirmation and creates a new draft', () async {
    final FormationDto active = fixtureFormation(
      id: 'active-formation',
      status: FormationStatus.published,
    );
    final FormationDto restored = fixtureFormation(
      id: 'restored-new-draft',
      status: FormationStatus.draft,
      auditRef: 'audit-restore-456',
    );
    final FakeFormationRepository repository = FakeFormationRepository(
      activeFormation: active,
      restoredDraft: restored,
    );
    final ProviderContainer container = containerFor(repository);
    final FormationEditorNotifier notifier = container.read(
      formationEditorProvider.notifier,
    );

    await notifier.load('club-1');
    notifier.requestRestore('history-formation');

    FormationEditorState state = container.read(formationEditorProvider);
    expect(state.restoreRequiresConfirmation, isTrue);
    expect(state.draft, isNull);
    expect(repository.restoreCalls, 0);

    await notifier.confirmRestore();

    state = container.read(formationEditorProvider);
    expect(repository.restoreCalls, 1);
    expect(state.activeFormation?.id, 'active-formation');
    expect(state.draft?.id, 'restored-new-draft');
    expect(state.draft?.status, FormationStatus.draft);
    expect(state.surfaceState, isA<GtexConfirmed<FormationDto>>());
  });
}
