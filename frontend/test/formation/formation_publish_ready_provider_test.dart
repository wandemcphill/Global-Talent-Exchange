import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/formation/formation.dart';

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
    'publish readiness blocks drafts with unfilled required slots',
    () async {
      final FakeFormationRepository repository = FakeFormationRepository(
        activeFormation: fixtureFormation(
          status: FormationStatus.draft,
          filled: false,
        ),
      );
      final ProviderContainer container = containerFor(repository);

      await container.read(formationEditorProvider.notifier).load('club-1');

      final FormationPublishReadiness readiness = container.read(
        formationPublishReadyProvider,
      );
      expect(readiness.canPublish, isFalse);
      expect(
        readiness.blockedReasons,
        contains('Publish requires 11 filled formation slots.'),
      );
    },
  );

  test(
    'publish readiness allows filled owner draft from backend data',
    () async {
      final FakeFormationRepository repository = FakeFormationRepository(
        activeFormation: fixtureFormation(status: FormationStatus.draft),
      );
      final ProviderContainer container = containerFor(repository);

      await container.read(formationEditorProvider.notifier).load('club-1');

      final FormationPublishReadiness readiness = container.read(
        formationPublishReadyProvider,
      );
      expect(readiness.canPublish, isTrue);
      expect(readiness.blockedReasons, isEmpty);
    },
  );
}
