import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:gte_frontend/features/formation/domain/formation_models.dart';
import 'package:gte_frontend/features/formation/providers/formation_providers.dart';
import 'package:gte_frontend/shared/state/gtex_async_surface_state.dart';
import 'package:gte_frontend/shared/widgets/async_state_widget.dart';
import 'package:gte_frontend/shared/widgets/gtex_async_state_view.dart';

class FormationHistoryScreen extends ConsumerWidget {
  const FormationHistoryScreen({super.key, required this.clubId});

  final String clubId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AsyncValue<GtexSurfaceState<List<FormationHistoryItemDto>>> history =
        ref.watch(formationHistoryProvider(clubId));
    return Scaffold(
      appBar: AppBar(title: const Text('Formation History')),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: history.when(
            loading:
                () => const GtexAsyncStateView.loading(
                  title: 'Loading formation history',
                ),
            error:
                (Object error, StackTrace stackTrace) =>
                    GtexAsyncStateView.error(message: error.toString()),
            data:
                (
                  GtexSurfaceState<List<FormationHistoryItemDto>> state,
                ) => AsyncStateWidget<List<FormationHistoryItemDto>>(
                  state: state,
                  onLoading: () => const GtexAsyncStateView.loading(),
                  onEmpty:
                      (String? reason) => GtexAsyncStateView.empty(
                        title: reason ?? 'No saved formations',
                        message: 'Backend returned no saved formation history.',
                      ),
                  onBlocked:
                      (String reason, String? ctaRoute) =>
                          GtexAsyncStateView.blocked(message: reason),
                  onPending:
                      (List<FormationHistoryItemDto>? stale) => _HistoryList(
                        items: stale ?? const <FormationHistoryItemDto>[],
                      ),
                  onSyncing:
                      (List<FormationHistoryItemDto> current) =>
                          _HistoryList(items: current),
                  onReconnecting:
                      (List<FormationHistoryItemDto>? lastKnown, int attempt) =>
                          _HistoryList(
                            items:
                                lastKnown ?? const <FormationHistoryItemDto>[],
                          ),
                  onDegraded:
                      (List<FormationHistoryItemDto> current, String warning) =>
                          _HistoryList(items: current),
                  onConfirmed:
                      (List<FormationHistoryItemDto> data, String? auditRef) =>
                          _HistoryList(items: data),
                  onError:
                      (String code, String message, VoidCallback retry) =>
                          GtexAsyncStateView.error(
                            title: 'Formation history unavailable',
                            message: message,
                          ),
                  onData:
                      (List<FormationHistoryItemDto> data) =>
                          _HistoryList(items: data),
                ),
          ),
        ),
      ),
    );
  }
}

class _HistoryList extends ConsumerWidget {
  const _HistoryList({required this.items});

  final List<FormationHistoryItemDto> items;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final FormationEditorState editorState = ref.watch(formationEditorProvider);
    final FormationEditorNotifier notifier = ref.read(
      formationEditorProvider.notifier,
    );
    return ListView.separated(
      itemCount:
          items.length + (editorState.restoreRequiresConfirmation ? 1 : 0),
      separatorBuilder:
          (BuildContext context, int index) => const SizedBox(height: 12),
      itemBuilder: (BuildContext context, int index) {
        if (editorState.restoreRequiresConfirmation && index == 0) {
          return _RestoreConfirmationCard(
            sourceFormationId: editorState.pendingRestoreSourceId ?? '',
            onCancel: notifier.cancelRestore,
            onConfirm: () => notifier.confirmRestore(),
          );
        }
        final int itemIndex =
            editorState.restoreRequiresConfirmation ? index - 1 : index;
        final FormationHistoryItemDto item = items[itemIndex];
        return _FormationHistoryCard(
          item: item,
          onRestore: () => notifier.requestRestore(item.id),
        );
      },
    );
  }
}

class _FormationHistoryCard extends StatelessWidget {
  const _FormationHistoryCard({required this.item, required this.onRestore});

  final FormationHistoryItemDto item;
  final VoidCallback onRestore;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Row(
          children: <Widget>[
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    item.name,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '${item.scheme} - ${item.status.name} - Chemistry ${item.chemistryScore.toStringAsFixed(0)}',
                  ),
                ],
              ),
            ),
            TextButton.icon(
              key: Key('formation-restore-${item.id}'),
              onPressed: onRestore,
              icon: const Icon(Icons.restore_outlined),
              label: const Text('Restore'),
            ),
          ],
        ),
      ),
    );
  }
}

class _RestoreConfirmationCard extends StatelessWidget {
  const _RestoreConfirmationCard({
    required this.sourceFormationId,
    required this.onCancel,
    required this.onConfirm,
  });

  final String sourceFormationId;
  final VoidCallback onCancel;
  final VoidCallback onConfirm;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.secondaryContainer,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Row(
          children: <Widget>[
            Expanded(
              child: Text(
                'Restore $sourceFormationId as a new draft?',
                style: Theme.of(context).textTheme.titleSmall,
              ),
            ),
            TextButton(onPressed: onCancel, child: const Text('Cancel')),
            FilledButton.icon(
              key: const Key('formation-confirm-restore'),
              onPressed: onConfirm,
              icon: const Icon(Icons.add_to_photos_outlined),
              label: const Text('Create draft'),
            ),
          ],
        ),
      ),
    );
  }
}
