import 'package:flutter/material.dart';

import '../../data/gte_authed_api.dart';
import '../../data/gte_api_repository.dart';
import '../../ui_gtex/ui_gtex.dart';
import 'launch_control_api.dart';
import 'launch_control_controller.dart';
import 'launch_control_models.dart';

class GtexFeatureFlagsLaunchControlScreenV2 extends StatefulWidget {
  const GtexFeatureFlagsLaunchControlScreenV2({
    super.key,
    required this.baseUrl,
    required this.accessToken,
    required this.backendMode,
    this.controller,
    this.authedApi,
  });

  final String baseUrl;
  final String? accessToken;
  final GteBackendMode backendMode;
  final GtexLaunchControlController? controller;
  final GteAuthedApi? authedApi;

  @override
  State<GtexFeatureFlagsLaunchControlScreenV2> createState() =>
      _GtexFeatureFlagsLaunchControlScreenV2State();
}

class _GtexFeatureFlagsLaunchControlScreenV2State
    extends State<GtexFeatureFlagsLaunchControlScreenV2> {
  late final GtexLaunchControlController _controller;
  late final bool _ownsController;

  @override
  void initState() {
    super.initState();
    _ownsController = widget.controller == null;
    _controller =
        widget.controller ??
        GtexLaunchControlController(
          api: GtexLaunchControlApi.standard(
            baseUrl: widget.baseUrl,
            accessToken: widget.accessToken,
            mode: widget.backendMode,
            client: widget.authedApi,
          ),
        );
    _controller.load();
  }

  @override
  void dispose() {
    if (_ownsController) {
      _controller.dispose();
    }
    super.dispose();
  }

  Future<void> _showGrantBetaDialog(GtexLaunchControlSnapshot snapshot) async {
    final List<GtexLaunchControlFlag> grantableFlags = snapshot.flags
        .where(
          (GtexLaunchControlFlag flag) =>
              flag.launchState == GtexLaunchState.beta || flag.betaOnly,
        )
        .toList(growable: false);
    final List<GtexLaunchControlFlag> flags =
        grantableFlags.isEmpty ? snapshot.flags : grantableFlags;
    if (flags.isEmpty) {
      return;
    }
    String selectedFeatureKey = flags.first.featureKey;
    final TextEditingController userController = TextEditingController();
    final TextEditingController notesController = TextEditingController();
    final _BetaGrantDraft? draft = await showDialog<_BetaGrantDraft>(
      context: context,
      builder: (BuildContext dialogContext) {
        return StatefulBuilder(
          builder: (BuildContext context, StateSetter setDialogState) {
            return AlertDialog(
              backgroundColor: GtexColors.panel,
              title: const Text('Grant Beta Access'),
              content: SizedBox(
                width: 440,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: <Widget>[
                    DropdownButtonFormField<String>(
                      value: selectedFeatureKey,
                      decoration: const InputDecoration(
                        labelText: 'Feature',
                        border: OutlineInputBorder(),
                      ),
                      items: flags
                          .map(
                            (GtexLaunchControlFlag flag) =>
                                DropdownMenuItem<String>(
                                  value: flag.featureKey,
                                  child: Text(flag.title),
                                ),
                          )
                          .toList(growable: false),
                      onChanged: (String? value) {
                        if (value == null) {
                          return;
                        }
                        setDialogState(() {
                          selectedFeatureKey = value;
                        });
                      },
                    ),
                    const SizedBox(height: GtexSpacing.md),
                    TextField(
                      controller: userController,
                      decoration: const InputDecoration(
                        labelText: 'User ID',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: GtexSpacing.md),
                    TextField(
                      controller: notesController,
                      maxLines: 2,
                      decoration: const InputDecoration(
                        labelText: 'Notes',
                        border: OutlineInputBorder(),
                      ),
                    ),
                  ],
                ),
              ),
              actions: <Widget>[
                TextButton(
                  onPressed: () => Navigator.of(dialogContext).pop(),
                  child: const Text('Cancel'),
                ),
                FilledButton.icon(
                  onPressed: () {
                    final String userId = userController.text.trim();
                    if (userId.isEmpty) {
                      return;
                    }
                    Navigator.of(dialogContext).pop(
                      _BetaGrantDraft(
                        featureKey: selectedFeatureKey,
                        userId: userId,
                        notes: notesController.text.trim(),
                      ),
                    );
                  },
                  icon: const Icon(Icons.person_add_alt_1_outlined),
                  label: const Text('Grant'),
                ),
              ],
            );
          },
        );
      },
    );
    userController.dispose();
    notesController.dispose();
    if (draft == null) {
      return;
    }
    await _controller.grantBetaAccess(
      featureKey: draft.featureKey,
      userId: draft.userId,
      notes: draft.notes.isEmpty ? null : draft.notes,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Theme(
      data: Theme.of(context).copyWith(
        scaffoldBackgroundColor: GtexColors.stadiumBlack,
        textTheme: Theme.of(context).textTheme.apply(
          bodyColor: GtexColors.text,
          displayColor: GtexColors.text,
        ),
      ),
      child: Scaffold(
        backgroundColor: GtexColors.stadiumBlack,
        body: SafeArea(
          child: AnimatedBuilder(
            animation: _controller,
            builder: (BuildContext context, _) {
              final GtexLaunchControlSnapshot? snapshot = _controller.snapshot;
              if (_controller.loading && snapshot == null) {
                return const Center(child: CircularProgressIndicator());
              }
              if (_controller.error != null && snapshot == null) {
                return _ErrorState(
                  message: _controller.error!,
                  onRetry: _controller.load,
                );
              }
              return RefreshIndicator(
                onRefresh: _controller.load,
                child: SingleChildScrollView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  padding: const EdgeInsets.all(GtexSpacing.lg),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      _Header(snapshot: snapshot, onRefresh: _controller.load),
                      const SizedBox(height: GtexSpacing.lg),
                      if (snapshot != null) ...<Widget>[
                        _MetricStrip(snapshot: snapshot),
                        const SizedBox(height: GtexSpacing.lg),
                        _FlagPanel(
                          flags: snapshot.flags,
                          actionBusy: _controller.actionLoading,
                          onToggleFlag: _controller.toggleFlag,
                          onToggleKillSwitch: _controller.toggleKillSwitch,
                          onChangeLaunchState: _controller.changeLaunchState,
                          onSetBetaOnly: _controller.setBetaOnly,
                        ),
                        const SizedBox(height: GtexSpacing.lg),
                        LayoutBuilder(
                          builder: (BuildContext context, BoxConstraints box) {
                            final bool wide = box.maxWidth >= 980;
                            if (!wide) {
                              return Column(
                                children: <Widget>[
                                  _ModuleHealthPanel(
                                    health: snapshot.moduleHealth,
                                  ),
                                  const SizedBox(height: GtexSpacing.lg),
                                  _CommandRouterPanel(
                                    routes: snapshot.commandRoutes,
                                  ),
                                  const SizedBox(height: GtexSpacing.lg),
                                  _AuditPanel(
                                    events: snapshot.recentAuditEvents,
                                    grants: snapshot.betaGrants,
                                    clientFlags: _controller.clientFlags,
                                    actionBusy: _controller.actionLoading,
                                    actionMessage: _controller.actionMessage,
                                    actionError: _controller.actionError,
                                    onGrantBeta:
                                        () => _showGrantBetaDialog(snapshot),
                                    onRevokeGrant: _controller.revokeBetaAccess,
                                  ),
                                ],
                              );
                            }
                            return Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: <Widget>[
                                Expanded(
                                  child: _ModuleHealthPanel(
                                    health: snapshot.moduleHealth,
                                  ),
                                ),
                                const SizedBox(width: GtexSpacing.lg),
                                Expanded(
                                  child: Column(
                                    children: <Widget>[
                                      _CommandRouterPanel(
                                        routes: snapshot.commandRoutes,
                                      ),
                                      const SizedBox(height: GtexSpacing.lg),
                                      _AuditPanel(
                                        events: snapshot.recentAuditEvents,
                                        grants: snapshot.betaGrants,
                                        clientFlags: _controller.clientFlags,
                                        actionBusy: _controller.actionLoading,
                                        actionMessage:
                                            _controller.actionMessage,
                                        actionError: _controller.actionError,
                                        onGrantBeta:
                                            () =>
                                                _showGrantBetaDialog(snapshot),
                                        onRevokeGrant:
                                            _controller.revokeBetaAccess,
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                            );
                          },
                        ),
                      ],
                    ],
                  ),
                ),
              );
            },
          ),
        ),
      ),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header({required this.snapshot, required this.onRefresh});

  final GtexLaunchControlSnapshot? snapshot;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    final GtexLaunchControlSnapshot? currentSnapshot = snapshot;
    return GtexPanel(
      accent: GtexColors.cyan,
      child: Row(
        children: <Widget>[
          Container(
            width: 52,
            height: 52,
            decoration: BoxDecoration(
              color: GtexColors.cyan.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
            ),
            child: const Icon(
              Icons.tune_outlined,
              color: GtexColors.cyan,
              size: 28,
            ),
          ),
          const SizedBox(width: GtexSpacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  'Launch Control',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    color: GtexColors.text,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: GtexSpacing.xxs),
                Text(
                  currentSnapshot == null
                      ? 'Loading Batch 34 rollout state'
                      : '${currentSnapshot.flags.length} flags | ${currentSnapshot.commandRoutes.length} command routes',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: GtexColors.textMuted,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          ),
          IconButton(
            onPressed: onRefresh,
            tooltip: 'Refresh',
            icon: const Icon(Icons.refresh_outlined, color: GtexColors.text),
          ),
        ],
      ),
    );
  }
}

class _MetricStrip extends StatelessWidget {
  const _MetricStrip({required this.snapshot});

  final GtexLaunchControlSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final bool compact = constraints.maxWidth < 720;
        final double tileWidth =
            compact ? constraints.maxWidth : (constraints.maxWidth - 36) / 4;
        return Wrap(
          spacing: GtexSpacing.sm,
          runSpacing: GtexSpacing.sm,
          children: <Widget>[
            SizedBox(
              width: tileWidth,
              child: GtexMetricTile(
                label: 'Flags',
                value: '${snapshot.flags.length}',
                helper: 'Registered',
                icon: Icons.flag_outlined,
                accent: GtexColors.cyan,
              ),
            ),
            SizedBox(
              width: tileWidth,
              child: GtexMetricTile(
                label: 'Enabled',
                value: '${snapshot.enabledCount}',
                helper: 'Effective',
                icon: Icons.check_circle_outline,
                accent: GtexColors.pitch,
              ),
            ),
            SizedBox(
              width: tileWidth,
              child: GtexMetricTile(
                label: 'Gated',
                value: '${snapshot.gatedCount}',
                helper: 'Internal/beta',
                icon: Icons.lock_outline,
                accent: GtexColors.gold,
              ),
            ),
            SizedBox(
              width: tileWidth,
              child: GtexMetricTile(
                label: 'Kill switches',
                value: '${snapshot.killSwitchCount}',
                helper: 'Active',
                icon: Icons.power_settings_new_outlined,
                accent:
                    snapshot.killSwitchCount == 0
                        ? GtexColors.pitch
                        : GtexColors.red,
              ),
            ),
          ],
        );
      },
    );
  }
}

class _FlagPanel extends StatelessWidget {
  const _FlagPanel({
    required this.flags,
    required this.actionBusy,
    required this.onToggleFlag,
    required this.onToggleKillSwitch,
    required this.onChangeLaunchState,
    required this.onSetBetaOnly,
  });

  final List<GtexLaunchControlFlag> flags;
  final bool actionBusy;
  final ValueChanged<GtexLaunchControlFlag> onToggleFlag;
  final ValueChanged<GtexLaunchControlFlag> onToggleKillSwitch;
  final void Function(GtexLaunchControlFlag flag, GtexLaunchState launchState)
  onChangeLaunchState;
  final void Function(GtexLaunchControlFlag flag, {required bool betaOnly})
  onSetBetaOnly;

  @override
  Widget build(BuildContext context) {
    return GtexPanel(
      title: 'Feature flags',
      subtitle: 'Canonical AdminFeatureFlag rollout state',
      accent: GtexColors.pitch,
      child: Column(
        children: flags
            .map((GtexLaunchControlFlag flag) {
              return Padding(
                padding: const EdgeInsets.only(bottom: GtexSpacing.sm),
                child: _FlagRow(
                  flag: flag,
                  actionBusy: actionBusy,
                  onToggleFlag: () => onToggleFlag(flag),
                  onToggleKillSwitch: () => onToggleKillSwitch(flag),
                  onChangeLaunchState:
                      (GtexLaunchState state) =>
                          onChangeLaunchState(flag, state),
                  onSetBetaOnly:
                      (bool betaOnly) =>
                          onSetBetaOnly(flag, betaOnly: betaOnly),
                ),
              );
            })
            .toList(growable: false),
      ),
    );
  }
}

class _FlagRow extends StatelessWidget {
  const _FlagRow({
    required this.flag,
    required this.actionBusy,
    required this.onToggleFlag,
    required this.onToggleKillSwitch,
    required this.onChangeLaunchState,
    required this.onSetBetaOnly,
  });

  final GtexLaunchControlFlag flag;
  final bool actionBusy;
  final VoidCallback onToggleFlag;
  final VoidCallback onToggleKillSwitch;
  final ValueChanged<GtexLaunchState> onChangeLaunchState;
  final ValueChanged<bool> onSetBetaOnly;

  @override
  Widget build(BuildContext context) {
    final GtexStatusTone stateTone = _toneForState(flag.launchState);
    return Container(
      padding: const EdgeInsets.all(GtexSpacing.md),
      decoration: BoxDecoration(
        color: GtexColors.panelStrong.withValues(alpha: 0.58),
        borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
        border: Border.all(color: GtexColors.line.withValues(alpha: 0.72)),
      ),
      child: LayoutBuilder(
        builder: (BuildContext context, BoxConstraints constraints) {
          final bool compact = constraints.maxWidth < 760;
          final Widget titleBlock = Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                flag.title,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  color: GtexColors.text,
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: GtexSpacing.xxs),
              Text(
                flag.featureKey,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: GtexColors.textMuted,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          );
          final Widget chips = Wrap(
            spacing: GtexSpacing.xs,
            runSpacing: GtexSpacing.xs,
            children: <Widget>[
              GtexStatusChip(
                label: gtexLaunchStateLabel(flag.launchState),
                tone: stateTone,
                compact: true,
              ),
              GtexStatusChip(
                label: flag.enabled ? 'Enabled' : 'Off',
                tone:
                    flag.enabled
                        ? GtexStatusTone.success
                        : GtexStatusTone.neutral,
                compact: true,
              ),
              if (flag.killSwitchEnabled)
                const GtexStatusChip(
                  label: 'Kill switch',
                  tone: GtexStatusTone.danger,
                  compact: true,
                ),
              if (flag.betaOnly)
                const GtexStatusChip(
                  label: 'Beta grant',
                  tone: GtexStatusTone.warning,
                  compact: true,
                ),
            ],
          );
          final Widget actions = Wrap(
            spacing: GtexSpacing.xs,
            runSpacing: GtexSpacing.xs,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: <Widget>[
              _LaunchStateDropdown(
                value: flag.launchState,
                enabled: !actionBusy,
                onChanged: onChangeLaunchState,
              ),
              FilterChip(
                selected: flag.betaOnly,
                onSelected: actionBusy ? null : onSetBetaOnly,
                avatar: const Icon(Icons.group_add_outlined, size: 18),
                label: const Text('Beta'),
              ),
              FilledButton.tonalIcon(
                onPressed: actionBusy ? null : onToggleFlag,
                icon: Icon(
                  flag.enabled
                      ? Icons.visibility_off_outlined
                      : Icons.visibility_outlined,
                ),
                label: Text(flag.enabled ? 'Disable' : 'Enable'),
              ),
              OutlinedButton.icon(
                onPressed: actionBusy ? null : onToggleKillSwitch,
                icon: Icon(
                  flag.killSwitchEnabled
                      ? Icons.power_settings_new_outlined
                      : Icons.emergency_outlined,
                ),
                label: Text(
                  flag.killSwitchEnabled ? 'Clear switch' : 'Kill switch',
                ),
              ),
            ],
          );
          if (compact) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                titleBlock,
                const SizedBox(height: GtexSpacing.sm),
                chips,
                const SizedBox(height: GtexSpacing.sm),
                actions,
              ],
            );
          }
          return Row(
            children: <Widget>[
              Expanded(flex: 3, child: titleBlock),
              Expanded(flex: 3, child: chips),
              const SizedBox(width: GtexSpacing.sm),
              actions,
            ],
          );
        },
      ),
    );
  }
}

class _LaunchStateDropdown extends StatelessWidget {
  const _LaunchStateDropdown({
    required this.value,
    required this.enabled,
    required this.onChanged,
  });

  final GtexLaunchState value;
  final bool enabled;
  final ValueChanged<GtexLaunchState> onChanged;

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: 'Launch state',
      child: Container(
        width: 162,
        height: 42,
        padding: const EdgeInsets.symmetric(horizontal: GtexSpacing.sm),
        decoration: BoxDecoration(
          color: GtexColors.panel.withValues(alpha: 0.78),
          borderRadius: BorderRadius.circular(GtexSpacing.radiusSm),
          border: Border.all(color: GtexColors.line.withValues(alpha: 0.72)),
        ),
        child: DropdownButtonHideUnderline(
          child: DropdownButton<GtexLaunchState>(
            value: value,
            isExpanded: true,
            dropdownColor: GtexColors.panel,
            iconEnabledColor: GtexColors.textMuted,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: GtexColors.text,
              fontWeight: FontWeight.w800,
            ),
            onChanged:
                enabled
                    ? (GtexLaunchState? nextValue) {
                      if (nextValue != null) {
                        onChanged(nextValue);
                      }
                    }
                    : null,
            items: GtexLaunchState.values
                .map(
                  (GtexLaunchState state) => DropdownMenuItem<GtexLaunchState>(
                    value: state,
                    child: Text(gtexLaunchStateLabel(state)),
                  ),
                )
                .toList(growable: false),
          ),
        ),
      ),
    );
  }
}

class _ModuleHealthPanel extends StatelessWidget {
  const _ModuleHealthPanel({required this.health});

  final List<GtexModuleHealth> health;

  @override
  Widget build(BuildContext context) {
    return GtexPanel(
      title: 'Module health',
      subtitle: 'Launch posture by command module',
      accent: GtexColors.gold,
      child: Column(
        children: health
            .map((GtexModuleHealth item) {
              return _KeyValueLine(
                title: item.moduleKey,
                subtitle: item.detail,
                trailing: GtexStatusChip(
                  label: item.status,
                  tone: _toneForHealth(item.status),
                  compact: true,
                ),
              );
            })
            .toList(growable: false),
      ),
    );
  }
}

class _CommandRouterPanel extends StatelessWidget {
  const _CommandRouterPanel({required this.routes});

  final List<GtexAdminCommandRoute> routes;

  @override
  Widget build(BuildContext context) {
    return GtexPanel(
      title: 'Command router',
      subtitle: 'Admin deep links registered for Batch 34',
      accent: GtexColors.cyan,
      child: Column(
        children: routes
            .map((GtexAdminCommandRoute route) {
              return _KeyValueLine(
                title: route.title,
                subtitle: route.route,
                trailing: Icon(
                  route.enabled
                      ? Icons.check_circle_outline
                      : Icons.radio_button_unchecked_outlined,
                  color:
                      route.enabled ? GtexColors.pitch : GtexColors.textMuted,
                ),
              );
            })
            .toList(growable: false),
      ),
    );
  }
}

class _AuditPanel extends StatelessWidget {
  const _AuditPanel({
    required this.events,
    required this.grants,
    required this.clientFlags,
    required this.actionBusy,
    required this.actionMessage,
    required this.actionError,
    required this.onGrantBeta,
    required this.onRevokeGrant,
  });

  final List<GtexFeatureFlagAuditEvent> events;
  final List<GtexBetaAccessGrant> grants;
  final List<GtexClientFeatureFlag> clientFlags;
  final bool actionBusy;
  final String? actionMessage;
  final String? actionError;
  final VoidCallback onGrantBeta;
  final ValueChanged<GtexBetaAccessGrant> onRevokeGrant;

  @override
  Widget build(BuildContext context) {
    return GtexPanel(
      title: 'Audit, beta and client flags',
      subtitle:
          '${events.length} recent audit events | ${grants.length} grants | ${clientFlags.length} client flags',
      accent: GtexColors.purple,
      trailing: FilledButton.tonalIcon(
        onPressed: actionBusy ? null : onGrantBeta,
        icon: const Icon(Icons.person_add_alt_1_outlined),
        label: const Text('Grant beta'),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          if (actionMessage != null || actionError != null) ...<Widget>[
            _InlineNotice(
              message: actionError ?? actionMessage!,
              isError: actionError != null,
            ),
            const SizedBox(height: GtexSpacing.sm),
          ],
          const _SectionLabel('Beta grants'),
          if (grants.isEmpty)
            const _EmptyPanelLine('No beta grants yet.')
          else
            ...grants.take(6).map((GtexBetaAccessGrant grant) {
              return _KeyValueLine(
                title: grant.userId,
                subtitle:
                    '${grant.featureKey}${grant.notes == null ? '' : ' | ${grant.notes}'}',
                trailing:
                    grant.active
                        ? OutlinedButton.icon(
                          onPressed:
                              actionBusy ? null : () => onRevokeGrant(grant),
                          icon: const Icon(Icons.block_outlined, size: 18),
                          label: const Text('Revoke'),
                        )
                        : const GtexStatusChip(
                          label: 'Revoked',
                          tone: GtexStatusTone.neutral,
                          compact: true,
                        ),
              );
            }),
          const SizedBox(height: GtexSpacing.md),
          const _SectionLabel('Client flags'),
          if (clientFlags.isEmpty)
            const _EmptyPanelLine('No client-visible flags for this session.')
          else
            ...clientFlags.take(6).map((GtexClientFeatureFlag flag) {
              return _KeyValueLine(
                title: flag.title,
                subtitle: '${flag.featureKey} | ${flag.route ?? 'No route'}',
                trailing: GtexStatusChip(
                  label:
                      flag.enabled
                          ? gtexLaunchStateLabel(flag.launchState)
                          : 'Blocked',
                  tone:
                      flag.enabled
                          ? _toneForState(flag.launchState)
                          : GtexStatusTone.danger,
                  compact: true,
                ),
              );
            }),
          const SizedBox(height: GtexSpacing.md),
          const _SectionLabel('Recent audit'),
          if (events.isEmpty)
            const _EmptyPanelLine('No launch-control audit events yet.')
          else
            ...events.take(4).map((GtexFeatureFlagAuditEvent event) {
              return _KeyValueLine(
                title: event.featureKey,
                subtitle: event.action,
                trailing: const Icon(
                  Icons.history_outlined,
                  color: GtexColors.purple,
                ),
              );
            }),
        ],
      ),
    );
  }
}

class _SectionLabel extends StatelessWidget {
  const _SectionLabel(this.label);

  final String label;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: GtexSpacing.sm),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelLarge?.copyWith(
          color: GtexColors.text,
          fontWeight: FontWeight.w900,
        ),
      ),
    );
  }
}

class _EmptyPanelLine extends StatelessWidget {
  const _EmptyPanelLine(this.message);

  final String message;

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Text(
        message,
        style: Theme.of(context).textTheme.bodySmall?.copyWith(
          color: GtexColors.textMuted,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

class _InlineNotice extends StatelessWidget {
  const _InlineNotice({required this.message, required this.isError});

  final String message;
  final bool isError;

  @override
  Widget build(BuildContext context) {
    final Color accent = isError ? GtexColors.red : GtexColors.pitch;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(GtexSpacing.sm),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(GtexSpacing.radiusSm),
        border: Border.all(color: accent.withValues(alpha: 0.42)),
      ),
      child: Text(
        message,
        style: Theme.of(context).textTheme.bodySmall?.copyWith(
          color: GtexColors.text,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }
}

class _BetaGrantDraft {
  const _BetaGrantDraft({
    required this.featureKey,
    required this.userId,
    required this.notes,
  });

  final String featureKey;
  final String userId;
  final String notes;
}

class _KeyValueLine extends StatelessWidget {
  const _KeyValueLine({
    required this.title,
    required this.subtitle,
    required this.trailing,
  });

  final String title;
  final String subtitle;
  final Widget trailing;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: GtexSpacing.sm),
      child: Row(
        children: <Widget>[
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    color: GtexColors.text,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: GtexSpacing.xxs),
                Text(
                  subtitle,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: GtexColors.textMuted,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: GtexSpacing.sm),
          trailing,
        ],
      ),
    );
  }
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.message, required this.onRetry});

  final String message;
  final Future<void> Function() onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: GtexPanel(
        accent: GtexColors.red,
        title: 'Launch control unavailable',
        subtitle: message,
        child: FilledButton.icon(
          onPressed: onRetry,
          icon: const Icon(Icons.refresh_outlined),
          label: const Text('Retry'),
        ),
      ),
    );
  }
}

GtexStatusTone _toneForState(GtexLaunchState state) {
  return switch (state) {
    GtexLaunchState.public => GtexStatusTone.success,
    GtexLaunchState.beta || GtexLaunchState.internal => GtexStatusTone.warning,
    GtexLaunchState.paused ||
    GtexLaunchState.maintenance => GtexStatusTone.warning,
    GtexLaunchState.hidden || GtexLaunchState.disabled => GtexStatusTone.danger,
  };
}

GtexStatusTone _toneForHealth(String status) {
  return switch (status.trim().toLowerCase()) {
    'online' => GtexStatusTone.success,
    'gated' || 'maintenance' || 'paused' || 'off' => GtexStatusTone.warning,
    'kill_switch' || 'disabled' || 'hidden' => GtexStatusTone.danger,
    _ => GtexStatusTone.neutral,
  };
}
