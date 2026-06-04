import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/formation/data/formation_repository.dart';
import 'package:gte_frontend/features/formation/domain/formation_models.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';
import 'package:gte_frontend/shared/state/gtex_async_surface_state.dart';

final Provider<IFormationRepository> formationRepositoryProvider =
    Provider<IFormationRepository>((Ref ref) {
      return FormationApiRepository(client: ref.watch(authedApiProvider));
    });

final Provider<String> formationUserRoleProvider = Provider<String>((Ref ref) {
  return ref.watch(currentUserRoleProvider);
});

final activeFormationProvider = StreamProvider.autoDispose.family<
  GtexSurfaceState<FormationDto>,
  String
>((Ref ref, String clubId) async* {
  final IFormationRepository repository = ref.watch(
    formationRepositoryProvider,
  );
  yield const GtexLoading<FormationDto>();
  FormationDto? current;
  try {
    current = await repository.getActiveFormation(clubId);
  } on Object catch (error) {
    yield GtexError<FormationDto>(
      code: 'formation.active.load_failed',
      message: _messageFor(error),
    );
    return;
  }
  if (current == null) {
    yield const GtexEmpty<FormationDto>(reason: noActiveFormationMessage);
  } else {
    yield GtexData<FormationDto>(data: current);
  }

  await for (final FormationWsEvent event in repository
      .subscribeToFormationEvents(clubId)) {
    switch (event) {
      case FormationActiveUpdated(:final formation):
        current = formation;
        yield GtexSyncing<FormationDto>(current: formation);
        yield GtexData<FormationDto>(data: formation);
      case FormationChemistryAlert(:final warnings):
        final FormationDto? lastKnown = current;
        if (lastKnown == null) {
          yield const GtexEmpty<FormationDto>(reason: noActiveFormationMessage);
        } else {
          final FormationDto updated = lastKnown.copyWith(warnings: warnings);
          current = updated;
          yield GtexDegraded<FormationDto>(
            current: updated,
            warning:
                warnings.isEmpty
                    ? 'Chemistry warnings cleared.'
                    : warnings.join(', '),
          );
        }
    }
  }
});

final formationHistoryProvider = FutureProvider.autoDispose
    .family<GtexSurfaceState<List<FormationHistoryItemDto>>, String>((
      Ref ref,
      String clubId,
    ) async {
      try {
        final List<FormationHistoryItemDto> history = await ref
            .watch(formationRepositoryProvider)
            .getFormationHistory(clubId);
        if (history.isEmpty) {
          return const GtexEmpty<List<FormationHistoryItemDto>>(
            reason: 'No saved formations returned by backend.',
          );
        }
        return GtexData<List<FormationHistoryItemDto>>(data: history);
      } on Object catch (error) {
        return GtexError<List<FormationHistoryItemDto>>(
          code: 'formation.history.load_failed',
          message: _messageFor(error),
        );
      }
    });

final formationDetailProvider = FutureProvider.autoDispose
    .family<GtexSurfaceState<FormationDto>, String>((
      Ref ref,
      String formationId,
    ) async {
      try {
        return GtexData<FormationDto>(
          data: await ref
              .watch(formationRepositoryProvider)
              .getFormationDetail(formationId),
        );
      } on Object catch (error) {
        return GtexError<FormationDto>(
          code: 'formation.detail.load_failed',
          message: _messageFor(error),
        );
      }
    });

final NotifierProvider<FormationEditorNotifier, FormationEditorState>
formationEditorProvider =
    NotifierProvider<FormationEditorNotifier, FormationEditorState>(
      FormationEditorNotifier.new,
    );

final Provider<FormationPublishReadiness> formationPublishReadyProvider =
    Provider<FormationPublishReadiness>((Ref ref) {
      final FormationEditorState state = ref.watch(formationEditorProvider);
      return FormationPublishReadiness.evaluate(
        draft: state.draft,
        eligiblePlayerCount: state.eligiblePlayers.length,
        role: state.role,
        pending: state.isPending,
      );
    });

class FormationEditorState {
  const FormationEditorState({
    required this.surfaceState,
    required this.eligiblePlayers,
    required this.role,
    this.clubId,
    this.activeFormation,
    this.draft,
    this.isDirty = false,
    this.pendingRestoreSourceId,
    this.restoreRequiresConfirmation = false,
  });

  factory FormationEditorState.initial({required String role}) {
    return FormationEditorState(
      surfaceState: const GtexLoading<FormationDto>(),
      eligiblePlayers: const <FormationSelectionReadyPlayerDto>[],
      role: role,
    );
  }

  final String? clubId;
  final GtexSurfaceState<FormationDto> surfaceState;
  final FormationDto? activeFormation;
  final FormationDto? draft;
  final List<FormationSelectionReadyPlayerDto> eligiblePlayers;
  final String role;
  final bool isDirty;
  final String? pendingRestoreSourceId;
  final bool restoreRequiresConfirmation;

  FormationDto? get boardFormation => draft ?? activeFormation;
  bool get isPending => surfaceState is GtexPending<FormationDto>;
  bool get hasDraft => draft != null;

  FormationEditorState copyWith({
    Object? clubId = _unset,
    GtexSurfaceState<FormationDto>? surfaceState,
    Object? activeFormation = _unset,
    Object? draft = _unset,
    List<FormationSelectionReadyPlayerDto>? eligiblePlayers,
    String? role,
    bool? isDirty,
    Object? pendingRestoreSourceId = _unset,
    bool? restoreRequiresConfirmation,
  }) {
    return FormationEditorState(
      clubId: clubId == _unset ? this.clubId : clubId as String?,
      surfaceState: surfaceState ?? this.surfaceState,
      activeFormation:
          activeFormation == _unset
              ? this.activeFormation
              : activeFormation as FormationDto?,
      draft: draft == _unset ? this.draft : draft as FormationDto?,
      eligiblePlayers: eligiblePlayers ?? this.eligiblePlayers,
      role: role ?? this.role,
      isDirty: isDirty ?? this.isDirty,
      pendingRestoreSourceId:
          pendingRestoreSourceId == _unset
              ? this.pendingRestoreSourceId
              : pendingRestoreSourceId as String?,
      restoreRequiresConfirmation:
          restoreRequiresConfirmation ?? this.restoreRequiresConfirmation,
    );
  }
}

class FormationEditorNotifier extends Notifier<FormationEditorState> {
  @override
  FormationEditorState build() {
    return FormationEditorState.initial(
      role: ref.watch(formationUserRoleProvider),
    );
  }

  Future<void> load(String clubId) async {
    final IFormationRepository repository = ref.read(
      formationRepositoryProvider,
    );
    final String role = ref.read(formationUserRoleProvider);
    state = state.copyWith(
      clubId: clubId,
      role: role,
      surfaceState: const GtexLoading<FormationDto>(),
      pendingRestoreSourceId: null,
      restoreRequiresConfirmation: false,
    );
    try {
      final List<FormationSelectionReadyPlayerDto> eligiblePlayers =
          await repository.getSelectionReadyPlayers(clubId);
      final FormationEditorBlock? block = evaluateFormationEditorBlock(
        eligiblePlayerCount: eligiblePlayers.length,
        role: role,
      );
      if (block != null) {
        state = state.copyWith(
          eligiblePlayers: eligiblePlayers,
          surfaceState: GtexBlocked<FormationDto>(
            reason: block.reason,
            ctaRoute: block.ctaRoute,
          ),
        );
        return;
      }
      final FormationDto? active = await repository.getActiveFormation(clubId);
      if (active == null) {
        state = state.copyWith(
          eligiblePlayers: eligiblePlayers,
          activeFormation: null,
          draft: null,
          isDirty: false,
          surfaceState: const GtexEmpty<FormationDto>(
            reason: noActiveFormationMessage,
          ),
        );
        return;
      }
      state = state.copyWith(
        eligiblePlayers: eligiblePlayers,
        activeFormation: active,
        draft: active.status == FormationStatus.draft ? active : null,
        isDirty: false,
        surfaceState: GtexData<FormationDto>(data: active),
      );
    } on Object catch (error) {
      state = state.copyWith(
        surfaceState: GtexError<FormationDto>(
          code: 'formation.editor.load_failed',
          message: _messageFor(error),
        ),
      );
    }
  }

  void createDraft({String scheme = '4-3-3'}) {
    final String? clubId = state.clubId;
    if (clubId == null) {
      state = state.copyWith(
        surfaceState: const GtexBlocked<FormationDto>(
          reason: 'A club must be selected before creating a formation draft.',
        ),
      );
      return;
    }
    final FormationEditorBlock? block = evaluateFormationEditorBlock(
      eligiblePlayerCount: state.eligiblePlayers.length,
      role: state.role,
    );
    if (block != null) {
      state = state.copyWith(
        surfaceState: GtexBlocked<FormationDto>(
          reason: block.reason,
          ctaRoute: block.ctaRoute,
        ),
      );
      return;
    }
    final DateTime now = DateTime.now().toUtc();
    final FormationDto draft = FormationDto(
      id: 'local-draft',
      clubId: clubId,
      name: '$scheme draft',
      scheme: scheme,
      slots: defaultSlotsForScheme(scheme),
      chemistryScore: 0,
      warnings: const <String>[],
      status: FormationStatus.draft,
      createdAt: now,
      updatedAt: now,
    );
    state = state.copyWith(
      draft: draft,
      isDirty: true,
      surfaceState: GtexData<FormationDto>(data: draft),
    );
  }

  void assignPlayerToSlot(String slotId, String playerId) {
    final FormationDto? draft = _editableDraft();
    if (draft == null) {
      return;
    }
    if (!state.eligiblePlayers.any(
      (FormationSelectionReadyPlayerDto player) => player.id == playerId,
    )) {
      return;
    }
    _updateDraftSlots(
      draft.slots
          .map((FormationSlotDto slot) {
            if (slot.slotId != slotId) {
              return slot;
            }
            return slot.copyWith(assignedPlayerId: playerId, filled: true);
          })
          .toList(growable: false),
    );
  }

  void assignSlotRole(String slotId, String role) {
    final FormationDto? draft = _editableDraft();
    if (draft == null) {
      return;
    }
    _updateDraftSlots(
      draft.slots
          .map((FormationSlotDto slot) {
            if (slot.slotId != slotId) {
              return slot;
            }
            return slot.copyWith(role: role.trim().isEmpty ? 'balanced' : role);
          })
          .toList(growable: false),
    );
  }

  Future<FormationDto?> saveDraft() async {
    final FormationDto? draft = state.draft;
    final String? clubId = state.clubId;
    if (draft == null || clubId == null || state.isPending) {
      return null;
    }
    final FormationEditorBlock? block = evaluateFormationEditorBlock(
      eligiblePlayerCount: state.eligiblePlayers.length,
      role: state.role,
    );
    if (block != null) {
      state = state.copyWith(
        surfaceState: GtexBlocked<FormationDto>(
          reason: block.reason,
          ctaRoute: block.ctaRoute,
        ),
      );
      return null;
    }
    state = state.copyWith(
      surfaceState: GtexPending<FormationDto>(stale: draft),
    );
    try {
      final FormationDto saved = await ref
          .read(formationRepositoryProvider)
          .saveFormationDraft(clubId, FormationSaveRequest.fromDraft(draft));
      state = state.copyWith(
        draft: saved,
        isDirty: false,
        surfaceState: GtexConfirmed<FormationDto>(
          data: saved,
          auditRef: saved.auditRef,
        ),
      );
      return saved;
    } on Object catch (error) {
      state = state.copyWith(
        surfaceState: GtexError<FormationDto>(
          code: 'formation.draft.save_failed',
          message: _messageFor(error),
        ),
      );
      return null;
    }
  }

  Future<FormationDto?> requestPublish() async {
    final FormationDto? draft = state.draft;
    final String? clubId = state.clubId;
    if (draft == null || clubId == null || state.isPending) {
      return null;
    }
    final FormationPublishReadiness readiness =
        FormationPublishReadiness.evaluate(
          draft: draft,
          eligiblePlayerCount: state.eligiblePlayers.length,
          role: state.role,
          pending: state.isPending,
        );
    if (!readiness.canPublish) {
      state = state.copyWith(
        surfaceState: GtexBlocked<FormationDto>(
          reason: readiness.blockedReasons.first,
        ),
      );
      return null;
    }
    state = state.copyWith(
      surfaceState: GtexPending<FormationDto>(stale: draft),
    );
    try {
      final FormationDto published = await ref
          .read(formationRepositoryProvider)
          .publishFormation(clubId, draft.id);
      state = state.copyWith(
        activeFormation: published,
        draft: null,
        isDirty: false,
        surfaceState: GtexConfirmed<FormationDto>(
          data: published,
          auditRef: published.auditRef,
        ),
      );
      ref.invalidate(formationHistoryProvider(clubId));
      return published;
    } on Object catch (error) {
      state = state.copyWith(
        surfaceState: GtexError<FormationDto>(
          code: 'formation.publish_failed',
          message: _messageFor(error),
        ),
      );
      return null;
    }
  }

  void requestRestore(String sourceFormationId) {
    state = state.copyWith(
      pendingRestoreSourceId: sourceFormationId,
      restoreRequiresConfirmation: true,
    );
  }

  Future<FormationDto?> confirmRestore() async {
    final String? clubId = state.clubId;
    final String? sourceFormationId = state.pendingRestoreSourceId;
    if (clubId == null || sourceFormationId == null || state.isPending) {
      return null;
    }
    final FormationDto? stale = state.boardFormation;
    state = state.copyWith(
      surfaceState: GtexPending<FormationDto>(stale: stale),
    );
    try {
      final FormationDto restored = await ref
          .read(formationRepositoryProvider)
          .restoreFormationDraft(clubId, sourceFormationId);
      state = state.copyWith(
        draft: restored,
        isDirty: false,
        pendingRestoreSourceId: null,
        restoreRequiresConfirmation: false,
        surfaceState: GtexConfirmed<FormationDto>(
          data: restored,
          auditRef: restored.auditRef,
        ),
      );
      return restored;
    } on Object catch (error) {
      state = state.copyWith(
        surfaceState: GtexError<FormationDto>(
          code: 'formation.restore_failed',
          message: _messageFor(error),
        ),
      );
      return null;
    }
  }

  void cancelRestore() {
    state = state.copyWith(
      pendingRestoreSourceId: null,
      restoreRequiresConfirmation: false,
    );
  }

  FormationDto? _editableDraft() {
    final FormationDto? draft = state.draft;
    if (draft == null || state.isPending) {
      return null;
    }
    final FormationEditorBlock? block = evaluateFormationEditorBlock(
      eligiblePlayerCount: state.eligiblePlayers.length,
      role: state.role,
    );
    if (block != null) {
      return null;
    }
    return draft;
  }

  void _updateDraftSlots(List<FormationSlotDto> slots) {
    final FormationDto? draft = state.draft;
    if (draft == null) {
      return;
    }
    final FormationDto updated = draft.copyWith(
      slots: slots,
      updatedAt: DateTime.now().toUtc(),
    );
    state = state.copyWith(
      draft: updated,
      isDirty: true,
      surfaceState: GtexData<FormationDto>(data: updated),
    );
  }
}

List<FormationSlotDto> defaultSlotsForScheme(String scheme) {
  final List<String> positions = <String>[
    'GK',
    'LB',
    'CB',
    'CB2',
    'RB',
    'CM',
    'CM2',
    'CM3',
    'LW',
    'ST',
    'RW',
  ];
  final List<double> x = <double>[
    0.5,
    0.18,
    0.38,
    0.62,
    0.82,
    0.28,
    0.5,
    0.72,
    0.2,
    0.5,
    0.8,
  ];
  final List<double> y = <double>[
    0.9,
    0.7,
    0.72,
    0.72,
    0.7,
    0.48,
    0.44,
    0.48,
    0.2,
    0.14,
    0.2,
  ];
  return List<FormationSlotDto>.generate(positions.length, (int index) {
    return FormationSlotDto(
      slotId: 'slot-${index + 1}',
      position: positions[index],
      x: x[index],
      y: y[index],
      role: 'balanced',
      filled: false,
    );
  }, growable: false);
}

String _messageFor(Object error) {
  if (error is GteApiException) {
    return error.message;
  }
  return error.toString();
}

const Object _unset = Object();
