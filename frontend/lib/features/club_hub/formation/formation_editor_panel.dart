import 'package:flutter/material.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';
import 'package:gte_frontend/features/shell/shell.dart' as shell;
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

import 'formation_editor_models.dart';
import 'formation_editor_provider.dart';

class FormationEditorPanel extends StatefulWidget {
  const FormationEditorPanel({
    super.key,
    required this.clubId,
    this.clubName,
    this.navigationDependencies,
  });

  final String clubId;
  final String? clubName;
  final GteNavigationDependencies? navigationDependencies;

  @override
  State<FormationEditorPanel> createState() => _FormationEditorPanelState();
}

class _FormationEditorPanelState extends State<FormationEditorPanel> {
  FormationEditorController? _controller;

  @override
  void initState() {
    super.initState();
    _mountController();
  }

  @override
  void didUpdateWidget(FormationEditorPanel oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.clubId != widget.clubId ||
        oldWidget.navigationDependencies?.apiBaseUrl !=
            widget.navigationDependencies?.apiBaseUrl ||
        oldWidget.navigationDependencies?.accessToken !=
            widget.navigationDependencies?.accessToken) {
      _controller?.dispose();
      _mountController();
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  void _mountController() {
    final GteNavigationDependencies? dependencies =
        widget.navigationDependencies;
    if (dependencies == null) {
      _controller = null;
      return;
    }
    final FormationEditorController controller = FormationEditorController(
      clubId: widget.clubId,
      baseUrl: dependencies.apiBaseUrl,
      accessToken: dependencies.accessToken,
    );
    _controller = controller;
    controller.load();
  }

  @override
  Widget build(BuildContext context) {
    final FormationEditorController? controller = _controller;
    if (controller == null) {
      return const GteStatePanel(
        key: Key('formation-editor-blocked'),
        eyebrow: 'FORMATION',
        title: 'Formation editor is blocked',
        message:
            'No club-scoped backend provider is mounted on this route, so tactical data cannot be loaded or edited.',
        icon: Icons.block_outlined,
      );
    }
    return AnimatedBuilder(
      animation: controller,
      builder: (BuildContext context, Widget? child) {
        return Column(
          key: const Key('formation-editor-panel'),
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            _FormationHeader(controller: controller),
            const SizedBox(height: 18),
            _FormationBody(controller: controller),
          ],
        );
      },
    );
  }
}

class FormationHealthSignal extends StatefulWidget {
  const FormationHealthSignal({
    super.key,
    required this.clubId,
    this.navigationDependencies,
  });

  final String clubId;
  final GteNavigationDependencies? navigationDependencies;

  @override
  State<FormationHealthSignal> createState() => _FormationHealthSignalState();
}

class _FormationHealthSignalState extends State<FormationHealthSignal> {
  FormationEditorController? _controller;

  @override
  void initState() {
    super.initState();
    _mountController();
  }

  @override
  void didUpdateWidget(FormationHealthSignal oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.clubId != widget.clubId ||
        oldWidget.navigationDependencies?.apiBaseUrl !=
            widget.navigationDependencies?.apiBaseUrl) {
      _controller?.dispose();
      _mountController();
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  void _mountController() {
    final GteNavigationDependencies? dependencies =
        widget.navigationDependencies;
    if (dependencies == null) {
      _controller = null;
      return;
    }
    final FormationEditorController controller = FormationEditorController(
      clubId: widget.clubId,
      baseUrl: dependencies.apiBaseUrl,
      accessToken: dependencies.accessToken,
    );
    _controller = controller;
    controller.load();
  }

  @override
  Widget build(BuildContext context) {
    final FormationEditorController? controller = _controller;
    if (controller == null) {
      return const FormationSignalTile(
        title: 'Formation health',
        value: 'BLOCKED',
        state: shell.GtexSurfaceState.blocked,
        message: 'No formation provider is mounted for this club route.',
        icon: Icons.grid_view_outlined,
      );
    }
    return AnimatedBuilder(
      animation: controller,
      builder: (BuildContext context, Widget? child) {
        final FormationEditorSnapshot? snapshot = controller.snapshot;
        return FormationSignalTile(
          title: 'Formation health',
          value: _healthValue(controller),
          state: _surfaceState(controller.state),
          message: _healthMessage(controller, snapshot),
          icon: Icons.grid_view_outlined,
        );
      },
    );
  }

  static String _healthValue(FormationEditorController controller) {
    final FormationEditorSnapshot? snapshot = controller.snapshot;
    if (snapshot?.health.score != null) {
      return '${snapshot!.health.score}';
    }
    switch (controller.state) {
      case FormationEditorLoadState.blocked:
        return 'BLOCKED';
      case FormationEditorLoadState.syncing:
        return 'SYNCING';
      case FormationEditorLoadState.empty:
        return 'EMPTY';
      case FormationEditorLoadState.degraded:
        return 'DEGRADED';
      case FormationEditorLoadState.error:
        return 'ERROR';
      case FormationEditorLoadState.ready:
        return snapshot?.shape ?? 'READY';
    }
  }

  static String _healthMessage(
    FormationEditorController controller,
    FormationEditorSnapshot? snapshot,
  ) {
    if (controller.errorMessage != null) {
      return controller.errorMessage!;
    }
    if (snapshot == null) {
      return 'Formation sync is waiting for the backend snapshot.';
    }
    if (snapshot.health.blockers.isNotEmpty) {
      return snapshot.health.blockers.first;
    }
    if (snapshot.health.warnings.isNotEmpty) {
      return snapshot.health.warnings.first;
    }
    if (!snapshot.hasBoardData) {
      return 'The backend returned no tactical board slots for this club.';
    }
    return 'Formation slots, roles, and health are confirmed by the backend.';
  }
}

class FormationSignalTile extends StatelessWidget {
  const FormationSignalTile({
    super.key,
    required this.title,
    required this.value,
    required this.state,
    required this.message,
    required this.icon,
  });

  final String title;
  final String value;
  final shell.GtexSurfaceState state;
  final String message;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    final Color color = _colorFor(state);
    return Container(
      key: const Key('formation-health-signal'),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: color.withValues(alpha: 0.24)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Icon(icon, color: color, size: 18),
              const SizedBox(width: 8),
              Text(
                state.name.toUpperCase(),
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: color,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(title, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          Text(value, style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 8),
          Text(message, style: Theme.of(context).textTheme.bodyMedium),
        ],
      ),
    );
  }
}

class _FormationHeader extends StatelessWidget {
  const _FormationHeader({required this.controller});

  final FormationEditorController controller;

  @override
  Widget build(BuildContext context) {
    final FormationEditorSnapshot? snapshot = controller.snapshot;
    return GteSurfacePanel(
      emphasized: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      'Tactical board',
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Formation, roles, health, and publish history are loaded from the club backend.',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              FilledButton.tonalIcon(
                onPressed:
                    controller.state == FormationEditorLoadState.syncing
                        ? null
                        : controller.load,
                icon: const Icon(Icons.sync_outlined),
                label: const Text('Sync'),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: <Widget>[
              _StatusPill(label: _stateLabel(controller.state)),
              if (snapshot?.shape != null) _StatusPill(label: snapshot!.shape!),
              if (snapshot?.version != null)
                _StatusPill(label: 'v${snapshot!.version}'),
              if (snapshot?.publishedAt != null)
                const _StatusPill(label: 'Published'),
            ],
          ),
        ],
      ),
    );
  }
}

class _FormationBody extends StatelessWidget {
  const _FormationBody({required this.controller});

  final FormationEditorController controller;

  @override
  Widget build(BuildContext context) {
    switch (controller.state) {
      case FormationEditorLoadState.blocked:
        return GteStatePanel(
          key: const Key('formation-editor-blocked-state'),
          eyebrow: 'FORMATION',
          title: 'Formation endpoint is blocked',
          message:
              controller.errorMessage ??
              'The backend has not exposed a club formation endpoint.',
          icon: Icons.block_outlined,
        );
      case FormationEditorLoadState.syncing:
        return const GteStatePanel(
          key: Key('formation-editor-syncing-state'),
          eyebrow: 'FORMATION',
          title: 'Syncing formation',
          message: 'Waiting for backend tactical board data.',
          icon: Icons.sync_outlined,
        );
      case FormationEditorLoadState.error:
        return GteStatePanel(
          key: const Key('formation-editor-error-state'),
          eyebrow: 'FORMATION',
          title: 'Formation sync failed',
          message:
              controller.errorMessage ??
              'The formation provider returned an error.',
          icon: Icons.error_outline,
          actionLabel: 'Retry',
          onAction: controller.load,
        );
      case FormationEditorLoadState.empty:
        return const GteStatePanel(
          key: Key('formation-editor-empty-state'),
          eyebrow: 'FORMATION',
          title: 'No formation published',
          message:
              'The backend returned no tactical board slots, roles, or publish audit for this club.',
          icon: Icons.grid_off_outlined,
        );
      case FormationEditorLoadState.degraded:
      case FormationEditorLoadState.ready:
        final FormationEditorSnapshot? snapshot = controller.snapshot;
        if (snapshot == null) {
          return const GteStatePanel(
            eyebrow: 'FORMATION',
            title: 'Formation snapshot unavailable',
            message: 'The backend response did not include a usable snapshot.',
            icon: Icons.error_outline,
          );
        }
        return _FormationSnapshotView(
          snapshot: snapshot,
          controller: controller,
        );
    }
  }
}

class _FormationSnapshotView extends StatelessWidget {
  const _FormationSnapshotView({
    required this.snapshot,
    required this.controller,
  });

  final FormationEditorSnapshot snapshot;
  final FormationEditorController controller;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        LayoutBuilder(
          builder: (BuildContext context, BoxConstraints constraints) {
            final bool wide = constraints.maxWidth >= 820;
            final Widget board = _FormationBoard(snapshot: snapshot);
            final Widget side = _FormationSidePanel(
              snapshot: snapshot,
              controller: controller,
            );
            if (wide) {
              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Expanded(flex: 7, child: board),
                  const SizedBox(width: 18),
                  Expanded(flex: 4, child: side),
                ],
              );
            }
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[board, const SizedBox(height: 18), side],
            );
          },
        ),
        const SizedBox(height: 18),
        _FormationAuditTrail(snapshot: snapshot),
      ],
    );
  }
}

class _FormationBoard extends StatelessWidget {
  const _FormationBoard({required this.snapshot});

  final FormationEditorSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    if (!snapshot.hasBoardData) {
      return const GteStatePanel(
        title: 'Tactical board is empty',
        message:
            'No backend slots were returned, so no lineup, role, or coordinate is displayed.',
        icon: Icons.grid_off_outlined,
      );
    }
    return GteSurfacePanel(
      key: const Key('formation-tactical-board'),
      accentColor: GteShellTheme.accentClub,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Pitch roles', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 12),
          AspectRatio(
            aspectRatio: 0.74,
            child: Container(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(8),
                gradient: const LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: <Color>[Color(0xFF113A32), Color(0xFF0B2521)],
                ),
                border: Border.all(color: Colors.white24),
              ),
              child: Stack(
                children: <Widget>[
                  Positioned.fill(child: CustomPaint(painter: _PitchPainter())),
                  ...snapshot.positionedSlots.map(
                    (FormationBoardSlot slot) => Positioned(
                      left: 0,
                      right: 0,
                      top: 0,
                      bottom: 0,
                      child: Align(
                        alignment: Alignment(
                          ((slot.x!.clamp(0, 100) / 50) - 1).toDouble(),
                          ((slot.y!.clamp(0, 100) / 50) - 1).toDouble(),
                        ),
                        child: _RoleMarker(slot: slot),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          if (snapshot.unpositionedSlots.isNotEmpty) ...<Widget>[
            const SizedBox(height: 14),
            Text(
              'Unpositioned roles',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            ...snapshot.unpositionedSlots.map(
              (FormationBoardSlot slot) => _RoleListTile(slot: slot),
            ),
          ],
        ],
      ),
    );
  }
}

class _FormationSidePanel extends StatelessWidget {
  const _FormationSidePanel({required this.snapshot, required this.controller});

  final FormationEditorSnapshot snapshot;
  final FormationEditorController controller;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      key: const Key('formation-health-panel'),
      accentColor:
          snapshot.health.isBlocked
              ? GteShellTheme.negative
              : snapshot.health.warnings.isNotEmpty
              ? GteShellTheme.warning
              : GteShellTheme.positive,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Formation health',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 10),
          Text(
            snapshot.health.score == null
                ? 'Health score pending'
                : '${snapshot.health.score} / 100',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 12),
          if (snapshot.health.blockers.isEmpty &&
              snapshot.health.warnings.isEmpty)
            Text(
              'No blockers or warnings were returned with this snapshot.',
              style: Theme.of(context).textTheme.bodyMedium,
            )
          else ...<Widget>[
            ...snapshot.health.blockers.map(
              (String blocker) => _HealthLine(
                icon: Icons.block_outlined,
                text: blocker,
                color: GteShellTheme.negative,
              ),
            ),
            ...snapshot.health.warnings.map(
              (String warning) => _HealthLine(
                icon: Icons.warning_amber_outlined,
                text: warning,
                color: GteShellTheme.warning,
              ),
            ),
          ],
          const SizedBox(height: 16),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: <Widget>[
              FilledButton.tonalIcon(
                onPressed:
                    snapshot.canSaveDraft && !controller.isSaving
                        ? controller.saveDraft
                        : null,
                icon: const Icon(Icons.save_outlined),
                label: Text(controller.isSaving ? 'Saving' : 'Save draft'),
              ),
              FilledButton.icon(
                onPressed:
                    snapshot.canPublish && !controller.isPublishing
                        ? controller.publish
                        : null,
                icon: const Icon(Icons.publish_outlined),
                label: Text(controller.isPublishing ? 'Publishing' : 'Publish'),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            'Save and publish are disabled until the backend grants those actions.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }
}

class _FormationAuditTrail extends StatelessWidget {
  const _FormationAuditTrail({required this.snapshot});

  final FormationEditorSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    if (!snapshot.hasPublishAudit) {
      return const GteStatePanel(
        key: Key('formation-audit-empty'),
        eyebrow: 'AUDIT',
        title: 'No formation audit trail',
        message:
            'The backend returned no save, publish, or sync history for this formation.',
        icon: Icons.history_toggle_off_outlined,
      );
    }
    return GteSurfacePanel(
      key: const Key('formation-audit-trail'),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Save and publish audit',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 12),
          if (snapshot.publishedAt != null)
            _AuditLine(
              title: 'Published',
              subtitle: snapshot.publishedBy ?? 'Backend actor not provided',
              value: _dateLabel(snapshot.publishedAt!),
            ),
          ...snapshot.auditTrail.map(
            (FormationAuditEvent event) => _AuditLine(
              title: event.action,
              subtitle: event.note ?? event.actor ?? 'No audit note provided',
              value:
                  event.occurredAt == null
                      ? 'Time pending'
                      : _dateLabel(event.occurredAt!),
            ),
          ),
        ],
      ),
    );
  }
}

class _RoleMarker extends StatelessWidget {
  const _RoleMarker({required this.slot});

  final FormationBoardSlot slot;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 112,
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: Colors.black.withValues(alpha: 0.58),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: Colors.white30),
        ),
        child: Padding(
          padding: const EdgeInsets.all(8),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              Text(
                slot.displayRole,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                slot.displayPlayer,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(
                  context,
                ).textTheme.bodySmall?.copyWith(color: Colors.white70),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _RoleListTile extends StatelessWidget {
  const _RoleListTile({required this.slot});

  final FormationBoardSlot slot;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: <Widget>[
          const Icon(Icons.radio_button_unchecked, size: 16),
          const SizedBox(width: 8),
          Expanded(child: Text(slot.displayRole)),
          const SizedBox(width: 8),
          Text(slot.displayPlayer),
        ],
      ),
    );
  }
}

class _HealthLine extends StatelessWidget {
  const _HealthLine({
    required this.icon,
    required this.text,
    required this.color,
  });

  final IconData icon;
  final String text;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(icon, color: color, size: 18),
          const SizedBox(width: 8),
          Expanded(child: Text(text)),
        ],
      ),
    );
  }
}

class _AuditLine extends StatelessWidget {
  const _AuditLine({
    required this.title,
    required this.subtitle,
    required this.value,
  });

  final String title;
  final String subtitle;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const Icon(Icons.history_outlined, size: 18),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(title, style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 4),
                Text(subtitle, style: Theme.of(context).textTheme.bodyMedium),
              ],
            ),
          ),
          const SizedBox(width: 10),
          Text(value, style: Theme.of(context).textTheme.bodySmall),
        ],
      ),
    );
  }
}

class _StatusPill extends StatelessWidget {
  const _StatusPill({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: GteShellTheme.accentClub.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(
          color: GteShellTheme.accentClub.withValues(alpha: 0.24),
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
        child: Text(label, style: Theme.of(context).textTheme.labelLarge),
      ),
    );
  }
}

class _PitchPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final Paint paint =
        Paint()
          ..color = Colors.white.withValues(alpha: 0.18)
          ..strokeWidth = 2
          ..style = PaintingStyle.stroke;
    final Rect rect = (Offset.zero & size).deflate(18);
    canvas.drawRect(rect, paint);
    canvas.drawLine(
      Offset(rect.left, size.height / 2),
      Offset(rect.right, size.height / 2),
      paint,
    );
    canvas.drawCircle(Offset(size.width / 2, size.height / 2), 42, paint);
    canvas.drawRect(
      Rect.fromCenter(
        center: Offset(size.width / 2, rect.top + 58),
        width: size.width * 0.46,
        height: 92,
      ),
      paint,
    );
    canvas.drawRect(
      Rect.fromCenter(
        center: Offset(size.width / 2, rect.bottom - 58),
        width: size.width * 0.46,
        height: 92,
      ),
      paint,
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

shell.GtexSurfaceState _surfaceState(FormationEditorLoadState state) {
  switch (state) {
    case FormationEditorLoadState.blocked:
      return shell.GtexSurfaceState.blocked;
    case FormationEditorLoadState.syncing:
      return shell.GtexSurfaceState.syncing;
    case FormationEditorLoadState.ready:
      return shell.GtexSurfaceState.confirmed;
    case FormationEditorLoadState.empty:
      return shell.GtexSurfaceState.empty;
    case FormationEditorLoadState.degraded:
      return shell.GtexSurfaceState.degraded;
    case FormationEditorLoadState.error:
      return shell.GtexSurfaceState.error;
  }
}

Color _colorFor(shell.GtexSurfaceState state) {
  switch (state) {
    case shell.GtexSurfaceState.confirmed:
      return GteShellTheme.positive;
    case shell.GtexSurfaceState.blocked:
    case shell.GtexSurfaceState.error:
      return GteShellTheme.negative;
    case shell.GtexSurfaceState.pending:
    case shell.GtexSurfaceState.degraded:
      return GteShellTheme.warning;
    case shell.GtexSurfaceState.loading:
    case shell.GtexSurfaceState.syncing:
    case shell.GtexSurfaceState.reconnecting:
      return GteShellTheme.accentClub;
    case shell.GtexSurfaceState.empty:
      return GteShellTheme.textMuted;
  }
}

String _stateLabel(FormationEditorLoadState state) {
  switch (state) {
    case FormationEditorLoadState.blocked:
      return 'Blocked';
    case FormationEditorLoadState.syncing:
      return 'Syncing';
    case FormationEditorLoadState.ready:
      return 'Ready';
    case FormationEditorLoadState.empty:
      return 'Empty';
    case FormationEditorLoadState.degraded:
      return 'Degraded';
    case FormationEditorLoadState.error:
      return 'Error';
  }
}

String _dateLabel(DateTime value) {
  final DateTime utc = value.toUtc();
  return '${utc.year}-${utc.month.toString().padLeft(2, '0')}-${utc.day.toString().padLeft(2, '0')}';
}
