import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:gte_frontend/features/formation/domain/formation_models.dart';
import 'package:gte_frontend/features/formation/presentation/widgets/tactical_pitch_board.dart';
import 'package:gte_frontend/features/formation/providers/formation_providers.dart';
import 'package:gte_frontend/shared/state/gtex_async_surface_state.dart';
import 'package:gte_frontend/shared/widgets/async_state_widget.dart';
import 'package:gte_frontend/shared/widgets/gtex_async_state_view.dart';

class FormationEditorScreen extends ConsumerStatefulWidget {
  const FormationEditorScreen({super.key, required this.clubId});

  final String clubId;

  @override
  ConsumerState<FormationEditorScreen> createState() =>
      _FormationEditorScreenState();
}

class _FormationEditorScreenState extends ConsumerState<FormationEditorScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(formationEditorProvider.notifier).load(widget.clubId);
    });
  }

  @override
  void didUpdateWidget(FormationEditorScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.clubId != widget.clubId) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        ref.read(formationEditorProvider.notifier).load(widget.clubId);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final FormationEditorState state = ref.watch(formationEditorProvider);
    final FormationPublishReadiness readiness = ref.watch(
      formationPublishReadyProvider,
    );
    final FormationEditorNotifier notifier = ref.read(
      formationEditorProvider.notifier,
    );

    return Scaffold(
      appBar: AppBar(
        title: const Text('Formation'),
        actions: <Widget>[
          TextButton.icon(
            key: const Key('formation-save-draft'),
            onPressed:
                state.hasDraft && !state.isPending
                    ? () => notifier.saveDraft()
                    : null,
            icon: const Icon(Icons.save_outlined),
            label: const Text('Save'),
          ),
          FilledButton.icon(
            key: const Key('formation-publish'),
            onPressed:
                readiness.canPublish ? () => notifier.requestPublish() : null,
            icon:
                state.isPending
                    ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                    : const Icon(Icons.publish_outlined),
            label: const Text('Publish'),
          ),
          const SizedBox(width: 12),
        ],
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: AsyncStateWidget<FormationDto>(
            state: state.surfaceState,
            onLoading:
                () => _FormationEditorLayout(
                  state: state,
                  readiness: readiness,
                  board: const TacticalPitchBoard(formation: null),
                ),
            onEmpty:
                (String? reason) => _FormationEditorLayout(
                  state: state,
                  readiness: readiness,
                  board: const TacticalPitchBoard(formation: null),
                  sidePanel: GtexAsyncStateView.empty(
                    title: reason ?? noActiveFormationMessage,
                    message: 'Backend returned no active tactical record.',
                    actionLabel: 'Create draft',
                    onAction: () => notifier.createDraft(),
                  ),
                ),
            onBlocked:
                (String reason, String? ctaRoute) => _FormationEditorLayout(
                  state: state,
                  readiness: readiness,
                  board: TacticalPitchBoard(
                    formation: state.boardFormation,
                    players: state.eligiblePlayers,
                    blockedReason: reason,
                  ),
                  sidePanel: GtexAsyncStateView.blocked(
                    title: 'Formation blocked',
                    message: reason,
                  ),
                ),
            onPending:
                (FormationDto? stale) => _FormationEditorLayout(
                  state: state,
                  readiness: readiness,
                  board: TacticalPitchBoard(
                    formation: stale ?? state.boardFormation,
                    players: state.eligiblePlayers,
                    pending: true,
                  ),
                ),
            onSyncing:
                (FormationDto current) => _FormationEditorLayout(
                  state: state,
                  readiness: readiness,
                  board: TacticalPitchBoard(
                    formation: current,
                    players: state.eligiblePlayers,
                  ),
                  sidePanel: const GtexAsyncStateView.syncing(
                    title: 'Syncing formation',
                    message: 'Backend formation update is being applied.',
                  ),
                ),
            onReconnecting:
                (
                  FormationDto? lastKnown,
                  int attempt,
                ) => _FormationEditorLayout(
                  state: state,
                  readiness: readiness,
                  board: TacticalPitchBoard(
                    formation: lastKnown ?? state.boardFormation,
                    players: state.eligiblePlayers,
                  ),
                  sidePanel: GtexAsyncStateView.reconnecting(
                    title: 'Realtime reconnecting',
                    message:
                        'Attempt $attempt is keeping last-known data visible.',
                  ),
                ),
            onDegraded:
                (FormationDto current, String warning) =>
                    _FormationEditorLayout(
                      state: state,
                      readiness: readiness,
                      board: TacticalPitchBoard(
                        formation: current,
                        players: state.eligiblePlayers,
                      ),
                      sidePanel: GtexAsyncStateView.degraded(
                        title: 'Chemistry warning',
                        message: warning,
                      ),
                    ),
            onConfirmed:
                (FormationDto data, String? auditRef) => _FormationEditorLayout(
                  state: state,
                  readiness: readiness,
                  board: TacticalPitchBoard(
                    formation: data,
                    players: state.eligiblePlayers,
                  ),
                  sidePanel: GtexAsyncStateView.confirmed(
                    title: 'Formation published',
                    message:
                        auditRef == null
                            ? 'Backend confirmed the formation.'
                            : 'Audit ref $auditRef',
                  ),
                ),
            onError:
                (String code, String message, VoidCallback retry) =>
                    _FormationEditorLayout(
                      state: state,
                      readiness: readiness,
                      board: TacticalPitchBoard(
                        formation: state.boardFormation,
                        players: state.eligiblePlayers,
                      ),
                      sidePanel: GtexAsyncStateView.error(
                        title: 'Formation unavailable',
                        message: message,
                        actionLabel: 'Retry',
                        onAction: () => notifier.load(widget.clubId),
                      ),
                    ),
            onData:
                (FormationDto data) => _FormationEditorLayout(
                  state: state,
                  readiness: readiness,
                  board: TacticalPitchBoard(
                    formation: state.boardFormation ?? data,
                    players: state.eligiblePlayers,
                  ),
                ),
          ),
        ),
      ),
    );
  }
}

class _FormationEditorLayout extends StatelessWidget {
  const _FormationEditorLayout({
    required this.state,
    required this.readiness,
    required this.board,
    this.sidePanel,
  });

  final FormationEditorState state;
  final FormationPublishReadiness readiness;
  final Widget board;
  final Widget? sidePanel;

  @override
  Widget build(BuildContext context) {
    final Widget resolvedSidePanel =
        sidePanel ?? _FormationSidePanel(state: state, readiness: readiness);

    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        if (constraints.maxWidth < 760) {
          return SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                board,
                const SizedBox(height: 16),
                resolvedSidePanel,
              ],
            ),
          );
        }
        return Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 520),
              child: board,
            ),
            const SizedBox(width: 16),
            Expanded(child: resolvedSidePanel),
          ],
        );
      },
    );
  }
}

class _FormationSidePanel extends StatelessWidget {
  const _FormationSidePanel({required this.state, required this.readiness});

  final FormationEditorState state;
  final FormationPublishReadiness readiness;

  @override
  Widget build(BuildContext context) {
    final FormationDto? formation = state.boardFormation;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        _InfoPanel(
          title: formation?.name ?? 'No backend formation',
          subtitle:
              formation == null
                  ? noActiveFormationMessage
                  : '${formation.scheme} - ${formation.status.name}',
        ),
        const SizedBox(height: 12),
        _InfoPanel(
          title: 'Eligible players',
          subtitle: '${state.eligiblePlayers.length} backend selection-ready',
        ),
        if (formation?.warnings.isNotEmpty ?? false) ...<Widget>[
          const SizedBox(height: 12),
          _InfoPanel(
            title: 'Chemistry warnings',
            subtitle: formation!.warnings.join('\n'),
            warning: true,
          ),
        ],
        if (readiness.blockedReasons.isNotEmpty) ...<Widget>[
          const SizedBox(height: 12),
          _InfoPanel(
            title: 'Publish gate',
            subtitle: readiness.blockedReasons.join('\n'),
            warning: true,
          ),
        ],
      ],
    );
  }
}

class _InfoPanel extends StatelessWidget {
  const _InfoPanel({
    required this.title,
    required this.subtitle,
    this.warning = false,
  });

  final String title;
  final String subtitle;
  final bool warning;

  @override
  Widget build(BuildContext context) {
    final Color borderColor =
        warning
            ? Theme.of(context).colorScheme.error
            : Theme.of(context).colorScheme.outlineVariant;
    return DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: borderColor),
        color: Theme.of(context).colorScheme.surface,
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(title, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 6),
            Text(subtitle),
          ],
        ),
      ),
    );
  }
}
