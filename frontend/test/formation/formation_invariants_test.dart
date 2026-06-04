import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/features/formation/formation.dart';
import 'package:gte_frontend/shared/state/gtex_async_surface_state.dart';

void main() {
  test('formation editor blocks fewer than 11 eligible players', () {
    final FormationEditorBlock? block = evaluateFormationEditorBlock(
      eligiblePlayerCount: 10,
      role: 'club.owner',
    );

    expect(block, isNotNull);
    expect(block!.reason, insufficientEligiblePlayersMessage);
  });

  test('publish readiness blocks pending publish and incomplete XI', () {
    final FormationPublishReadiness readiness =
        FormationPublishReadiness.evaluate(
          draft: _formation(filledSlots: 10),
          eligiblePlayerCount: 11,
          role: 'club.manager',
          pending: true,
        );

    expect(readiness.canPublish, isFalse);
    expect(
      readiness.blockedReasons,
      contains('Publish requires 11 filled formation slots.'),
    );
    expect(
      readiness.blockedReasons,
      contains('Publish is already pending backend confirmation.'),
    );
  });

  test(
    'formation editor provider loads blocked state from backend eligibility',
    () async {
      final ProviderContainer container = ProviderContainer(
        overrides: [
          formationRepositoryProvider.overrideWithValue(
            _FormationRepositoryStub(eligibleCount: 10),
          ),
          formationUserRoleProvider.overrideWithValue('club.owner'),
        ],
      );
      addTearDown(container.dispose);

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
}

FormationDto _formation({required int filledSlots}) {
  final DateTime now = DateTime.utc(2026, 1, 1);
  return FormationDto(
    id: 'formation-1',
    clubId: 'club-1',
    name: '4-3-3 draft',
    scheme: '4-3-3',
    slots: List<FormationSlotDto>.generate(11, (int index) {
      final bool filled = index < filledSlots;
      return FormationSlotDto(
        slotId: 'slot-$index',
        position: 'P$index',
        x: 0.5,
        y: 0.5,
        role: 'balanced',
        filled: filled,
        assignedPlayerId: filled ? 'p$index' : null,
      );
    }, growable: false),
    chemistryScore: 70,
    warnings: const <String>[],
    status: FormationStatus.draft,
    createdAt: now,
    updatedAt: now,
  );
}

class _FormationRepositoryStub implements IFormationRepository {
  const _FormationRepositoryStub({required this.eligibleCount});

  final int eligibleCount;

  @override
  Future<FormationDto?> getActiveFormation(String clubId) async {
    return _formation(filledSlots: 11);
  }

  @override
  Future<List<FormationSelectionReadyPlayerDto>> getSelectionReadyPlayers(
    String clubId,
  ) async {
    return List<FormationSelectionReadyPlayerDto>.generate(
      eligibleCount,
      (int index) => FormationSelectionReadyPlayerDto(
        id: 'p$index',
        name: 'Player $index',
        position: 'CM',
        eligible: true,
      ),
      growable: false,
    );
  }

  @override
  Future<FormationDto> getFormationDetail(String formationId) {
    throw UnimplementedError();
  }

  @override
  Future<List<FormationHistoryItemDto>> getFormationHistory(String clubId) {
    throw UnimplementedError();
  }

  @override
  Future<FormationDto> publishFormation(String clubId, String formationId) {
    throw UnimplementedError();
  }

  @override
  Future<FormationDto> restoreFormationDraft(
    String clubId,
    String sourceFormationId,
  ) {
    throw UnimplementedError();
  }

  @override
  Future<FormationDto> saveFormationDraft(
    String clubId,
    FormationSaveRequest request,
  ) {
    throw UnimplementedError();
  }

  @override
  Stream<FormationWsEvent> subscribeToFormationEvents(String clubId) {
    return const Stream<FormationWsEvent>.empty();
  }
}
