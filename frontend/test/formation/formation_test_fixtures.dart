import 'dart:async';

import 'package:gte_frontend/features/formation/formation.dart';

final DateTime fixtureNow = DateTime.utc(2026, 6, 2, 12);

FormationDto fixtureFormation({
  String id = 'formation-1',
  String clubId = 'club-1',
  FormationStatus status = FormationStatus.draft,
  String? auditRef,
  bool filled = true,
}) {
  return FormationDto(
    id: id,
    clubId: clubId,
    name: 'Atlas Press',
    scheme: '4-3-3',
    slots: List<FormationSlotDto>.generate(11, (int index) {
      return FormationSlotDto(
        slotId: 'slot-${index + 1}',
        position: index == 0 ? 'GK' : 'P$index',
        assignedPlayerId: filled ? 'player-${index + 1}' : null,
        x: 0.1 + (index % 4) * 0.24,
        y: 0.1 + (index ~/ 4) * 0.24,
        role: 'balanced',
        filled: filled,
      );
    }, growable: false),
    chemistryScore: 82,
    warnings: const <String>[],
    status: status,
    createdAt: fixtureNow,
    updatedAt: fixtureNow,
    publishedAt: status == FormationStatus.published ? fixtureNow : null,
    auditRef: auditRef,
  );
}

List<FormationSelectionReadyPlayerDto> fixtureEligiblePlayers(int count) {
  return List<FormationSelectionReadyPlayerDto>.generate(count, (int index) {
    return FormationSelectionReadyPlayerDto(
      id: 'player-${index + 1}',
      name: 'Player ${index + 1}',
      position: index == 0 ? 'GK' : 'MID',
      eligible: true,
    );
  }, growable: false);
}

class FakeFormationRepository implements IFormationRepository {
  FakeFormationRepository({
    this.activeFormation,
    List<FormationSelectionReadyPlayerDto>? eligiblePlayers,
    List<FormationHistoryItemDto>? history,
    this.restoredDraft,
    this.publishedFormation,
  }) : eligiblePlayers = eligiblePlayers ?? fixtureEligiblePlayers(11),
       history = history ?? const <FormationHistoryItemDto>[];

  FormationDto? activeFormation;
  List<FormationSelectionReadyPlayerDto> eligiblePlayers;
  List<FormationHistoryItemDto> history;
  FormationDto? restoredDraft;
  FormationDto? publishedFormation;
  Completer<FormationDto>? publishCompleter;
  int restoreCalls = 0;

  @override
  Future<FormationDto?> getActiveFormation(String clubId) async {
    return activeFormation;
  }

  @override
  Future<List<FormationSelectionReadyPlayerDto>> getSelectionReadyPlayers(
    String clubId,
  ) async {
    return eligiblePlayers;
  }

  @override
  Future<FormationDto> saveFormationDraft(
    String clubId,
    FormationSaveRequest request,
  ) async {
    return fixtureFormation(
      id: 'saved-draft',
      clubId: clubId,
      status: FormationStatus.draft,
      auditRef: 'audit-draft',
    );
  }

  @override
  Future<FormationDto> publishFormation(String clubId, String formationId) {
    final Completer<FormationDto>? completer = publishCompleter;
    if (completer != null) {
      return completer.future;
    }
    return Future<FormationDto>.value(
      publishedFormation ??
          fixtureFormation(
            id: formationId,
            clubId: clubId,
            status: FormationStatus.published,
            auditRef: 'audit-publish',
          ),
    );
  }

  @override
  Future<List<FormationHistoryItemDto>> getFormationHistory(
    String clubId,
  ) async {
    return history;
  }

  @override
  Future<FormationDto> getFormationDetail(String formationId) async {
    return activeFormation ?? fixtureFormation(id: formationId);
  }

  @override
  Future<FormationDto> restoreFormationDraft(
    String clubId,
    String sourceFormationId,
  ) async {
    restoreCalls += 1;
    return restoredDraft ??
        fixtureFormation(
          id: 'restored-draft',
          clubId: clubId,
          status: FormationStatus.draft,
          auditRef: 'audit-restore',
        );
  }

  @override
  Stream<FormationWsEvent> subscribeToFormationEvents(String clubId) {
    return const Stream<FormationWsEvent>.empty();
  }
}
