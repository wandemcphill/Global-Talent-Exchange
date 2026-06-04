import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:gte_frontend/features/match_center/data/live_match_fixtures.dart';
import 'package:gte_frontend/features/match_center/data/match_center_models.dart';
import 'package:gte_frontend/features/match_center/realtime/live_match_realtime_models.dart';
import 'package:gte_frontend/widgets/gte_metric_chip.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

class MatchCenterSurface extends StatefulWidget {
  const MatchCenterSurface({
    super.key,
    required this.match,
    this.feedDegraded = false,
    this.initialOverlayMode = LiveMatchOverlayMode.shape,
    this.scoreClockAuthoritative = true,
    this.timelineVerified = true,
    this.unverifiedRealtimeState = MatchCenterSurfaceState.syncing,
    this.realtimeIssueMessage,
  });

  factory MatchCenterSurface.fromRealtimeFrame({
    Key? key,
    required LiveMatchRealtimeFrame frame,
    LiveMatchOverlayMode initialOverlayMode = LiveMatchOverlayMode.shape,
  }) {
    final MatchCenterSurfaceState unverifiedState = _surfaceStateForRealtime(
      frame,
    );
    return MatchCenterSurface(
      key: key,
      match: frame.snapshot,
      feedDegraded:
          frame.status == LiveMatchRealtimeStatus.reconnecting ||
          frame.status == LiveMatchRealtimeStatus.degraded,
      initialOverlayMode: initialOverlayMode,
      scoreClockAuthoritative: frame.isUsable,
      timelineVerified: frame.isUsable,
      unverifiedRealtimeState: unverifiedState,
      realtimeIssueMessage:
          frame.issue?.message ?? _fallbackRealtimeMessage(frame.status),
    );
  }

  final LiveMatchSnapshot match;
  final bool feedDegraded;
  final LiveMatchOverlayMode initialOverlayMode;
  final bool scoreClockAuthoritative;
  final bool timelineVerified;
  final MatchCenterSurfaceState unverifiedRealtimeState;
  final String? realtimeIssueMessage;

  @override
  State<MatchCenterSurface> createState() => _MatchCenterSurfaceState();
}

class _MatchCenterSurfaceState extends State<MatchCenterSurface> {
  late LiveMatchOverlayMode _selectedOverlayMode = widget.initialOverlayMode;

  @override
  void didUpdateWidget(covariant MatchCenterSurface oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.initialOverlayMode != widget.initialOverlayMode) {
      _selectedOverlayMode = widget.initialOverlayMode;
    }
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final Widget main = Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            MatchCenterScorebug(
              match: widget.match,
              feedDegraded: widget.feedDegraded,
              scoreClockAuthoritative: widget.scoreClockAuthoritative,
              unverifiedRealtimeState: widget.unverifiedRealtimeState,
              realtimeIssueMessage: widget.realtimeIssueMessage,
            ),
            const SizedBox(height: 14),
            MatchCenterPitchShell(
              match: widget.match,
              selectedMode: _selectedOverlayMode,
              feedDegraded: widget.feedDegraded,
              onModeChanged:
                  (LiveMatchOverlayMode mode) =>
                      setState(() => _selectedOverlayMode = mode),
            ),
          ],
        );
        final Widget rail = MatchCenterInspectorRail(
          match: widget.match,
          feedDegraded: widget.feedDegraded,
          scoreClockAuthoritative: widget.scoreClockAuthoritative,
          timelineVerified: widget.timelineVerified,
          unverifiedRealtimeState: widget.unverifiedRealtimeState,
          realtimeIssueMessage: widget.realtimeIssueMessage,
        );
        if (constraints.maxWidth >= 980) {
          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Expanded(flex: 7, child: main),
              const SizedBox(width: 16),
              Expanded(flex: 4, child: rail),
            ],
          );
        }
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[main, const SizedBox(height: 16), rail],
        );
      },
    );
  }
}

class MatchCenterScorebug extends StatelessWidget {
  const MatchCenterScorebug({
    super.key,
    required this.match,
    this.feedDegraded = false,
    this.scoreClockAuthoritative = true,
    this.unverifiedRealtimeState = MatchCenterSurfaceState.syncing,
    this.realtimeIssueMessage,
  });

  final LiveMatchSnapshot match;
  final bool feedDegraded;
  final bool scoreClockAuthoritative;
  final MatchCenterSurfaceState unverifiedRealtimeState;
  final String? realtimeIssueMessage;

  @override
  Widget build(BuildContext context) {
    final MatchCenterReadiness readiness = MatchCenterReadiness.fromSnapshot(
      match,
      feedDegraded: feedDegraded,
      scoreClockAuthoritative: scoreClockAuthoritative,
      unverifiedRealtimeState: unverifiedRealtimeState,
      scoreClockDetail: realtimeIssueMessage,
    );
    final Color tone = _stateColor(context, readiness.scorebug);
    final tokens = GteShellTheme.tokensOf(context);
    final String phaseLabel =
        scoreClockAuthoritative
            ? matchCenterPhaseLabel(match)
            : _pendingRealtimeLabel(readiness.scorebug);
    final String clockLabel =
        scoreClockAuthoritative ? matchCenterClockLabel(match) : '--';
    final String scoreLabel =
        scoreClockAuthoritative
            ? '${match.homeScore} - ${match.awayScore}'
            : '-- - --';
    return Container(
      key: const Key('match-center-scorebug'),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: tokens.panelStrong.withValues(alpha: 0.96),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: tone.withValues(alpha: 0.34)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Row(
            children: <Widget>[
              MatchCenterStateBadge(state: readiness.scorebug),
              const SizedBox(width: 10),
              Text(
                phaseLabel,
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: tone,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 0,
                ),
              ),
              const Spacer(),
              Text(
                clockLabel,
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  color: tokens.textPrimary,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Row(
            children: <Widget>[
              Expanded(child: _ScorebugTeam(name: match.homeTeam)),
              Container(
                constraints: const BoxConstraints(minWidth: 92),
                padding: const EdgeInsets.symmetric(
                  horizontal: 14,
                  vertical: 10,
                ),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.06),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                    color: Colors.white.withValues(alpha: 0.14),
                  ),
                ),
                child: Text(
                  scoreLabel,
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    color: tokens.textPrimary,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
              Expanded(child: _ScorebugTeam(name: match.awayTeam, end: true)),
            ],
          ),
          if (!scoreClockAuthoritative) ...<Widget>[
            const SizedBox(height: 12),
            MatchCenterStatePanel(
              state: readiness.scorebug,
              title: 'Scorebug ${readiness.scorebug.name}',
              message:
                  realtimeIssueMessage ??
                  'Awaiting a backend-authored score and clock frame before showing match state.',
              icon: _realtimeStateIcon(readiness.scorebug),
            ),
          ],
          if (!matchCenterHasText(match.matchId)) ...<Widget>[
            const SizedBox(height: 12),
            MatchCenterStatePanel(
              state: MatchCenterSurfaceState.blocked,
              title: 'Match id blocked',
              message:
                  'A canonical match id is required before linked live ops actions can attach to this scorebug.',
              icon: Icons.lock_outline,
            ),
          ],
        ],
      ),
    );
  }
}

class MatchCenterPitchShell extends StatelessWidget {
  const MatchCenterPitchShell({
    super.key,
    required this.match,
    required this.selectedMode,
    required this.onModeChanged,
    this.feedDegraded = false,
  });

  final LiveMatchSnapshot match;
  final LiveMatchOverlayMode selectedMode;
  final ValueChanged<LiveMatchOverlayMode> onModeChanged;
  final bool feedDegraded;

  @override
  Widget build(BuildContext context) {
    final MatchCenterOverlayAvailability selectedOverlay =
        MatchCenterOverlayAvailability.fromSnapshot(
          match,
          selectedMode,
          feedDegraded: feedDegraded,
        );
    final bool hasLineups =
        match.homeLineup.isNotEmpty || match.awayLineup.isNotEmpty;
    final tokens = GteShellTheme.tokensOf(context);
    return Container(
      key: const Key('match-center-pitch-shell'),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: tokens.panel.withValues(alpha: 0.96),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: tokens.stroke.withValues(alpha: 0.88)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          Row(
            children: <Widget>[
              const Icon(Icons.grid_4x4_outlined, size: 20),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  '2D pitch shell',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
              MatchCenterStateBadge(state: selectedOverlay.state),
            ],
          ),
          const SizedBox(height: 12),
          MatchCenterOverlayModeSelector(
            match: match,
            selectedMode: selectedMode,
            feedDegraded: feedDegraded,
            onModeChanged: onModeChanged,
          ),
          const SizedBox(height: 12),
          if (!hasLineups)
            const MatchCenterStatePanel(
              state: MatchCenterSurfaceState.empty,
              title: 'Pitch shell waiting for lineups',
              message:
                  'The shell renders only after the snapshot includes home or away lineup records.',
              icon: Icons.grid_off_outlined,
            )
          else
            AspectRatio(
              aspectRatio: 16 / 10,
              child: DecoratedBox(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                    color: Colors.white.withValues(alpha: 0.14),
                  ),
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: CustomPaint(
                    painter: _MatchCenterPitchPainter(
                      mode: selectedMode,
                      stats: match.stats,
                    ),
                    child: _PitchMarkerLayer(match: match),
                  ),
                ),
              ),
            ),
          const SizedBox(height: 12),
          if (selectedOverlay.state == MatchCenterSurfaceState.confirmed ||
              selectedOverlay.state == MatchCenterSurfaceState.degraded)
            _OverlaySummary(overlay: selectedOverlay)
          else
            MatchCenterStatePanel(
              state: selectedOverlay.state,
              title:
                  '${selectedOverlay.label} overlay ${selectedOverlay.state.name}',
              message: selectedOverlay.detail,
              icon: _overlayIcon(selectedOverlay.mode),
            ),
        ],
      ),
    );
  }
}

class MatchCenterOverlayModeSelector extends StatelessWidget {
  const MatchCenterOverlayModeSelector({
    super.key,
    required this.match,
    required this.selectedMode,
    required this.onModeChanged,
    this.feedDegraded = false,
  });

  final LiveMatchSnapshot match;
  final LiveMatchOverlayMode selectedMode;
  final ValueChanged<LiveMatchOverlayMode> onModeChanged;
  final bool feedDegraded;

  @override
  Widget build(BuildContext context) {
    final List<MatchCenterOverlayAvailability> overlays =
        matchCenterOverlayStates(match, feedDegraded: feedDegraded);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: SegmentedButton<LiveMatchOverlayMode>(
            showSelectedIcon: false,
            segments: overlays
                .map(
                  (MatchCenterOverlayAvailability overlay) =>
                      ButtonSegment<LiveMatchOverlayMode>(
                        value: overlay.mode,
                        icon: Icon(_overlayIcon(overlay.mode), size: 18),
                        label: Text(overlay.label),
                        tooltip: overlay.detail,
                      ),
                )
                .toList(growable: false),
            selected: <LiveMatchOverlayMode>{selectedMode},
            onSelectionChanged:
                (Set<LiveMatchOverlayMode> value) => onModeChanged(value.first),
          ),
        ),
        const SizedBox(height: 10),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: overlays
              .map(
                (MatchCenterOverlayAvailability overlay) =>
                    _OverlayStatusChip(overlay: overlay),
              )
              .toList(growable: false),
        ),
      ],
    );
  }
}

class MatchCenterInspectorRail extends StatelessWidget {
  const MatchCenterInspectorRail({
    super.key,
    required this.match,
    this.feedDegraded = false,
    this.scoreClockAuthoritative = true,
    this.timelineVerified = true,
    this.unverifiedRealtimeState = MatchCenterSurfaceState.syncing,
    this.realtimeIssueMessage,
  });

  final LiveMatchSnapshot match;
  final bool feedDegraded;
  final bool scoreClockAuthoritative;
  final bool timelineVerified;
  final MatchCenterSurfaceState unverifiedRealtimeState;
  final String? realtimeIssueMessage;

  @override
  Widget build(BuildContext context) {
    final MatchCenterReadiness readiness = MatchCenterReadiness.fromSnapshot(
      match,
      feedDegraded: feedDegraded,
      scoreClockAuthoritative: scoreClockAuthoritative,
      timelineVerified: timelineVerified,
      unverifiedRealtimeState: unverifiedRealtimeState,
      scoreClockDetail: realtimeIssueMessage,
      timelineDetail: realtimeIssueMessage,
    );
    final tokens = GteShellTheme.tokensOf(context);
    return Container(
      key: const Key('match-center-inspector-rail'),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: tokens.panelStrong.withValues(alpha: 0.96),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: tokens.stroke.withValues(alpha: 0.88)),
      ),
      child: DefaultTabController(
        length: 2,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            Text(
              'Inspector rail',
              style: Theme.of(
                context,
              ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: readiness.items
                  .map((MatchCenterReadinessItem item) {
                    return _ReadinessTile(item: item);
                  })
                  .toList(growable: false),
            ),
            const SizedBox(height: 14),
            MatchCenterLiveIntelligencePanel(
              match: match,
              feedDegraded: feedDegraded,
            ),
            const SizedBox(height: 14),
            const TabBar(
              tabs: <Widget>[Tab(text: 'Timeline'), Tab(text: 'Stats')],
            ),
            const SizedBox(height: 12),
            SizedBox(
              height: 320,
              child: TabBarView(
                children: <Widget>[
                  MatchCenterTimelineTab(
                    match: match,
                    timelineVerified: timelineVerified,
                    unverifiedRealtimeState: unverifiedRealtimeState,
                    realtimeIssueMessage: realtimeIssueMessage,
                  ),
                  MatchCenterStatsTab(match: match, feedDegraded: feedDegraded),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class MatchCenterLiveIntelligencePanel extends StatelessWidget {
  const MatchCenterLiveIntelligencePanel({
    super.key,
    required this.match,
    this.feedDegraded = false,
  });

  final LiveMatchSnapshot match;
  final bool feedDegraded;

  @override
  Widget build(BuildContext context) {
    final LiveMatchLiveIntelligence? intelligence = match.liveIntelligence;
    final MatchCenterSurfaceState state =
        MatchCenterReadiness.fromSnapshot(
          match,
          feedDegraded: feedDegraded,
        ).liveIntelligence;
    if (intelligence == null) {
      return const MatchCenterStatePanel(
        state: MatchCenterSurfaceState.empty,
        title: 'Live intelligence empty',
        message: 'No live intelligence payload was attached to this snapshot.',
        icon: Icons.psychology_alt_outlined,
      );
    }
    final tokens = GteShellTheme.tokensOf(context);
    return Container(
      key: const Key('match-center-live-intelligence'),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: _stateColor(context, state).withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: _stateColor(context, state).withValues(alpha: 0.24),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              const Icon(Icons.psychology_alt_outlined, size: 20),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Live intelligence',
                  style: Theme.of(
                    context,
                  ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800),
                ),
              ),
              MatchCenterStateBadge(state: state),
            ],
          ),
          if (matchCenterHasText(intelligence.summary)) ...<Widget>[
            const SizedBox(height: 8),
            Text(
              intelligence.summary!,
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: tokens.textPrimary),
            ),
          ],
          if (intelligence.updatedAt != null) ...<Widget>[
            const SizedBox(height: 8),
            Text(
              'Updated ${intelligence.updatedAt!.toUtc().toIso8601String()}',
              style: Theme.of(
                context,
              ).textTheme.labelSmall?.copyWith(color: tokens.textMuted),
            ),
          ],
          const SizedBox(height: 10),
          if (intelligence.signals.isEmpty)
            Text(
              'Status: ${intelligence.status}',
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: tokens.textMuted),
            )
          else
            Column(
              children: intelligence.signals
                  .map(
                    (LiveMatchIntelligenceSignal signal) =>
                        _IntelligenceSignalTile(signal: signal),
                  )
                  .toList(growable: false),
            ),
        ],
      ),
    );
  }
}

class MatchCenterTimelineTab extends StatelessWidget {
  const MatchCenterTimelineTab({
    super.key,
    required this.match,
    this.timelineVerified = true,
    this.unverifiedRealtimeState = MatchCenterSurfaceState.syncing,
    this.realtimeIssueMessage,
  });

  final LiveMatchSnapshot match;
  final bool timelineVerified;
  final MatchCenterSurfaceState unverifiedRealtimeState;
  final String? realtimeIssueMessage;

  @override
  Widget build(BuildContext context) {
    if (!timelineVerified) {
      return MatchCenterStatePanel(
        state: unverifiedRealtimeState,
        title: 'Timeline ${unverifiedRealtimeState.name}',
        message:
            realtimeIssueMessage ??
            'Timeline events are withheld until the backend score and clock snapshot confirms this match state.',
        icon: _realtimeStateIcon(unverifiedRealtimeState),
      );
    }
    if (match.commentary.isEmpty) {
      return const MatchCenterStatePanel(
        state: MatchCenterSurfaceState.empty,
        title: 'Timeline empty',
        message:
            'Goals, cards, substitutions, and incidents appear after verified events arrive.',
        icon: Icons.timeline_outlined,
      );
    }
    return ListView.separated(
      key: const Key('match-center-timeline-tab'),
      itemCount: match.commentary.length,
      separatorBuilder: (_, __) => const SizedBox(height: 10),
      itemBuilder: (BuildContext context, int index) {
        return _TimelineTile(event: match.commentary[index]);
      },
    );
  }
}

class MatchCenterStatsTab extends StatelessWidget {
  const MatchCenterStatsTab({
    super.key,
    required this.match,
    this.feedDegraded = false,
  });

  final LiveMatchSnapshot match;
  final bool feedDegraded;

  @override
  Widget build(BuildContext context) {
    final LiveMatchStatsSnapshot? stats = match.stats;
    if (stats == null) {
      return const MatchCenterStatePanel(
        key: Key('match-center-stats-blocked-panel'),
        state: MatchCenterSurfaceState.blocked,
        title: 'Stats payload blocked',
        message: 'No stats payload is attached to the current match snapshot.',
        icon: Icons.query_stats_outlined,
      );
    }
    final List<Widget> rows = <Widget>[
      if (stats.possession != null)
        _StatPairRow(label: 'Possession', pair: stats.possession!),
      if (stats.shots != null) _StatPairRow(label: 'Shots', pair: stats.shots!),
      if (stats.shotsOnTarget != null)
        _StatPairRow(label: 'Shots on target', pair: stats.shotsOnTarget!),
      if (stats.expectedGoals != null)
        _StatPairRow(
          label: 'Expected goals',
          pair: stats.expectedGoals!,
          decimals: 2,
        ),
      if (stats.territory != null)
        _StatPairRow(label: 'Territory', pair: stats.territory!),
      if (stats.pressure != null)
        _StatPairRow(label: 'Pressure', pair: stats.pressure!),
      if (matchCenterHasText(stats.marketSignal) ||
          matchCenterHasText(stats.marketDetail))
        _MarketContextBlock(stats: stats),
    ];
    if (rows.isEmpty) {
      return const MatchCenterStatePanel(
        state: MatchCenterSurfaceState.empty,
        title: 'Stats payload empty',
        message: 'The stats payload did not include renderable match metrics.',
        icon: Icons.query_stats_outlined,
      );
    }
    final List<Widget> children = <Widget>[
      if (feedDegraded)
        const MatchCenterStatePanel(
          state: MatchCenterSurfaceState.degraded,
          title: 'Stats feed degraded',
          message:
              'Stats are present, but the caller marked the active feed as degraded.',
          icon: Icons.signal_wifi_statusbar_connected_no_internet_4,
        ),
      ...rows,
    ];
    return SingleChildScrollView(
      key: const Key('match-center-stats-tab'),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: children
            .expand(
              (Widget child) => <Widget>[child, const SizedBox(height: 10)],
            )
            .toList(growable: false),
      ),
    );
  }
}

class MatchCenterStatePanel extends StatelessWidget {
  const MatchCenterStatePanel({
    super.key,
    required this.state,
    required this.title,
    required this.message,
    required this.icon,
  });

  final MatchCenterSurfaceState state;
  final String title;
  final String message;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    final Color tone = _stateColor(context, state);
    return Container(
      key: ValueKey<String>('match-center-state-${state.name}'),
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: tone.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: tone.withValues(alpha: 0.24)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(icon, color: tone, size: 22),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Row(
                  children: <Widget>[
                    Expanded(
                      child: Text(
                        title,
                        style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                    MatchCenterStateBadge(state: state),
                  ],
                ),
                const SizedBox(height: 6),
                Text(message, style: Theme.of(context).textTheme.bodySmall),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class MatchCenterStateBadge extends StatelessWidget {
  const MatchCenterStateBadge({super.key, required this.state});

  final MatchCenterSurfaceState state;

  @override
  Widget build(BuildContext context) {
    final Color tone = _stateColor(context, state);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: tone.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: tone.withValues(alpha: 0.32)),
      ),
      child: Text(
        state.label,
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
          color: tone,
          fontWeight: FontWeight.w800,
          letterSpacing: 0,
        ),
      ),
    );
  }
}

class _ScorebugTeam extends StatelessWidget {
  const _ScorebugTeam({required this.name, this.end = false});

  final String name;
  final bool end;

  @override
  Widget build(BuildContext context) {
    return Text(
      name,
      maxLines: 2,
      overflow: TextOverflow.ellipsis,
      textAlign: end ? TextAlign.end : TextAlign.start,
      style: Theme.of(context).textTheme.titleMedium?.copyWith(
        fontWeight: FontWeight.w900,
        letterSpacing: 0,
      ),
    );
  }
}

class _OverlaySummary extends StatelessWidget {
  const _OverlaySummary({required this.overlay});

  final MatchCenterOverlayAvailability overlay;

  @override
  Widget build(BuildContext context) {
    final Color tone = _stateColor(context, overlay.state);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: tone.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: tone.withValues(alpha: 0.24)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Icon(_overlayIcon(overlay.mode), color: tone, size: 22),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      '${overlay.label} overlay ${overlay.state.name}',
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      overlay.detail,
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
              MatchCenterStateBadge(state: overlay.state),
            ],
          ),
          if (overlay.metrics.isNotEmpty) ...<Widget>[
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: overlay.metrics
                  .map(
                    (MatchCenterMetric metric) => GteMetricChip(
                      label: metric.label,
                      value: metric.value,
                      positive: metric.positive,
                    ),
                  )
                  .toList(growable: false),
            ),
          ],
        ],
      ),
    );
  }
}

class _OverlayStatusChip extends StatelessWidget {
  const _OverlayStatusChip({required this.overlay});

  final MatchCenterOverlayAvailability overlay;

  @override
  Widget build(BuildContext context) {
    final Color tone = _stateColor(context, overlay.state);
    return Tooltip(
      message: overlay.detail,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
        decoration: BoxDecoration(
          color: tone.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: tone.withValues(alpha: 0.24)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Icon(_overlayIcon(overlay.mode), color: tone, size: 16),
            const SizedBox(width: 6),
            Text(
              '${overlay.label}: ${overlay.state.label}',
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: tone,
                fontWeight: FontWeight.w800,
                letterSpacing: 0,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PitchMarkerLayer extends StatelessWidget {
  const _PitchMarkerLayer({required this.match});

  final LiveMatchSnapshot match;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        return Stack(
          children: <Widget>[
            ..._markers(
              match.homeLineup,
              homeSide: true,
              size: constraints.biggest,
            ),
            ..._markers(
              match.awayLineup,
              homeSide: false,
              size: constraints.biggest,
            ),
          ],
        );
      },
    );
  }

  List<Widget> _markers(
    List<LiveMatchLineupPlayer> players, {
    required bool homeSide,
    required Size size,
  }) {
    return players
        .take(11)
        .toList(growable: false)
        .asMap()
        .entries
        .map((MapEntry<int, LiveMatchLineupPlayer> entry) {
          final Offset position = _formationOffset(
            entry.key,
            homeSide: homeSide,
          );
          return Positioned(
            left: position.dx * size.width,
            top: position.dy * size.height,
            child: FractionalTranslation(
              translation: const Offset(-0.5, -0.5),
              child: _PitchPlayerMarker(
                player: entry.value,
                homeSide: homeSide,
              ),
            ),
          );
        })
        .toList(growable: false);
  }

  Offset _formationOffset(int index, {required bool homeSide}) {
    const List<Offset> shape = <Offset>[
      Offset(0.08, 0.50),
      Offset(0.20, 0.18),
      Offset(0.20, 0.38),
      Offset(0.20, 0.62),
      Offset(0.20, 0.82),
      Offset(0.38, 0.30),
      Offset(0.42, 0.50),
      Offset(0.38, 0.70),
      Offset(0.58, 0.24),
      Offset(0.64, 0.50),
      Offset(0.58, 0.76),
    ];
    final int safeIndex = index.clamp(0, shape.length - 1).toInt();
    final Offset base = shape[safeIndex];
    return Offset(homeSide ? base.dx : 1 - base.dx, base.dy);
  }
}

class _PitchPlayerMarker extends StatelessWidget {
  const _PitchPlayerMarker({required this.player, required this.homeSide});

  final LiveMatchLineupPlayer player;
  final bool homeSide;

  @override
  Widget build(BuildContext context) {
    final Color tone =
        homeSide ? GteShellTheme.accentArena : GteShellTheme.accentWarm;
    return SizedBox(
      width: 34,
      height: 34,
      child: Tooltip(
        message: player.name,
        child: DecoratedBox(
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: tone.withValues(alpha: 0.88),
            border: Border.all(color: Colors.white.withValues(alpha: 0.76)),
          ),
          child: Center(
            child: Text(
              player.position,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: Colors.black,
                fontWeight: FontWeight.w900,
                letterSpacing: 0,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _MatchCenterPitchPainter extends CustomPainter {
  const _MatchCenterPitchPainter({required this.mode, required this.stats});

  final LiveMatchOverlayMode mode;
  final LiveMatchStatsSnapshot? stats;

  @override
  void paint(Canvas canvas, Size size) {
    final Rect bounds = Offset.zero & size;
    final Paint turf =
        Paint()
          ..shader = const LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: <Color>[Color(0xFF0F5132), Color(0xFF0A3825)],
          ).createShader(bounds);
    canvas.drawRect(bounds, turf);

    final Paint stripe = Paint()..color = Colors.white.withValues(alpha: 0.035);
    for (int index = 0; index < 8; index += 1) {
      if (index.isEven) {
        canvas.drawRect(
          Rect.fromLTWH(
            0,
            size.height / 8 * index,
            size.width,
            size.height / 8,
          ),
          stripe,
        );
      }
    }

    final Rect pitch = bounds.deflate(12);
    _paintDataOverlay(canvas, size, pitch);

    final Paint line =
        Paint()
          ..color = Colors.white.withValues(alpha: 0.62)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.4;
    canvas.drawRect(pitch, line);
    canvas.drawLine(
      Offset(size.width / 2, pitch.top),
      Offset(size.width / 2, pitch.bottom),
      line,
    );
    canvas.drawCircle(Offset(size.width / 2, size.height / 2), 34, line);
    canvas.drawRect(
      Rect.fromLTWH(
        pitch.left,
        size.height * 0.32,
        size.width * 0.13,
        size.height * 0.36,
      ),
      line,
    );
    canvas.drawRect(
      Rect.fromLTWH(
        pitch.right - size.width * 0.13,
        size.height * 0.32,
        size.width * 0.13,
        size.height * 0.36,
      ),
      line,
    );
  }

  void _paintDataOverlay(Canvas canvas, Size size, Rect pitch) {
    switch (mode) {
      case LiveMatchOverlayMode.shape:
        _paintShapeGuides(canvas, size);
        break;
      case LiveMatchOverlayMode.pressure:
        _paintSplitZones(
          canvas,
          pitch,
          stats?.pressure,
          GteShellTheme.accentWarm,
        );
        break;
      case LiveMatchOverlayMode.territory:
        _paintSplitZones(
          canvas,
          pitch,
          stats?.territory,
          GteShellTheme.accentArena,
        );
        break;
      case LiveMatchOverlayMode.shots:
      case LiveMatchOverlayMode.xg:
        _paintShotMap(canvas, size, mode == LiveMatchOverlayMode.xg);
        break;
      case LiveMatchOverlayMode.market:
        _paintMarketBand(canvas, pitch);
        break;
    }
  }

  void _paintShapeGuides(Canvas canvas, Size size) {
    final Paint guide =
        Paint()
          ..color = Colors.white.withValues(alpha: 0.2)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.1;
    final Path home =
        Path()
          ..moveTo(size.width * 0.20, size.height * 0.18)
          ..lineTo(size.width * 0.42, size.height * 0.50)
          ..lineTo(size.width * 0.58, size.height * 0.24)
          ..moveTo(size.width * 0.20, size.height * 0.82)
          ..lineTo(size.width * 0.42, size.height * 0.50)
          ..lineTo(size.width * 0.58, size.height * 0.76);
    final Path away =
        Path()
          ..moveTo(size.width * 0.80, size.height * 0.18)
          ..lineTo(size.width * 0.58, size.height * 0.50)
          ..lineTo(size.width * 0.42, size.height * 0.24)
          ..moveTo(size.width * 0.80, size.height * 0.82)
          ..lineTo(size.width * 0.58, size.height * 0.50)
          ..lineTo(size.width * 0.42, size.height * 0.76);
    canvas.drawPath(home, guide);
    canvas.drawPath(
      away,
      guide..color = GteShellTheme.accentWarm.withValues(alpha: 0.2),
    );
  }

  void _paintSplitZones(
    Canvas canvas,
    Rect pitch,
    LiveMatchStatPair? pair,
    Color tone,
  ) {
    if (pair == null) {
      return;
    }
    final double homeWidth = pitch.width * pair.homeShare;
    canvas.drawRect(
      Rect.fromLTWH(pitch.left, pitch.top, homeWidth, pitch.height),
      Paint()..color = tone.withValues(alpha: 0.18),
    );
    canvas.drawRect(
      Rect.fromLTWH(
        pitch.left + homeWidth,
        pitch.top,
        pitch.width - homeWidth,
        pitch.height,
      ),
      Paint()..color = GteShellTheme.accentWarm.withValues(alpha: 0.14),
    );
  }

  void _paintShotMap(Canvas canvas, Size size, bool scaleByXg) {
    final List<LiveMatchShotMarker> shots =
        stats?.shotMap ?? const <LiveMatchShotMarker>[];
    for (final LiveMatchShotMarker marker in shots) {
      final Color tone =
          marker.isHome ? GteShellTheme.accentArena : GteShellTheme.accentWarm;
      final double radius = scaleByXg ? 5 + marker.xg.clamp(0, 1) * 18 : 8;
      final Offset center = Offset(
        marker.x * size.width,
        marker.y * size.height,
      );
      canvas.drawCircle(
        center,
        radius,
        Paint()..color = tone.withValues(alpha: 0.26),
      );
      canvas.drawCircle(
        center,
        radius,
        Paint()
          ..color = tone.withValues(alpha: 0.82)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.2,
      );
    }
  }

  void _paintMarketBand(Canvas canvas, Rect pitch) {
    if (stats?.hasMarketContext != true) {
      return;
    }
    final Paint paint =
        Paint()
          ..shader = LinearGradient(
            colors: <Color>[
              const Color(0xFF8FB3FF).withValues(alpha: 0.16),
              const Color(0xFFC7A24A).withValues(alpha: 0.16),
            ],
          ).createShader(pitch);
    canvas.drawRRect(
      RRect.fromRectAndRadius(pitch.deflate(24), const Radius.circular(8)),
      paint,
    );
  }

  @override
  bool shouldRepaint(covariant _MatchCenterPitchPainter oldDelegate) {
    return oldDelegate.mode != mode || oldDelegate.stats != stats;
  }
}

class _ReadinessTile extends StatelessWidget {
  const _ReadinessTile({required this.item});

  final MatchCenterReadinessItem item;

  @override
  Widget build(BuildContext context) {
    final Color tone = _stateColor(context, item.state);
    return Container(
      width: 150,
      constraints: const BoxConstraints(minHeight: 104),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: tone.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: tone.withValues(alpha: 0.22)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            item.label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(
              context,
            ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 8),
          MatchCenterStateBadge(state: item.state),
          const SizedBox(height: 8),
          Text(
            item.detail,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }
}

class _IntelligenceSignalTile extends StatelessWidget {
  const _IntelligenceSignalTile({required this.signal});

  final LiveMatchIntelligenceSignal signal;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.04),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.white.withValues(alpha: 0.1)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Wrap(
            spacing: 8,
            runSpacing: 6,
            children: <Widget>[
              Text(
                signal.title,
                style: Theme.of(
                  context,
                ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800),
              ),
              if (matchCenterHasText(signal.severity))
                _TextChip(label: signal.severity!),
              if (matchCenterHasText(signal.source))
                _TextChip(label: signal.source!),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            signal.detail,
            style: Theme.of(
              context,
            ).textTheme.bodySmall?.copyWith(color: tokens.textMuted),
          ),
        ],
      ),
    );
  }
}

class _TimelineTile extends StatelessWidget {
  const _TimelineTile({required this.event});

  final LiveMatchEvent event;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.04),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.white.withValues(alpha: 0.1)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          SizedBox(
            width: 44,
            child: Text(
              '${event.minute}\'',
              style: Theme.of(
                context,
              ).textTheme.labelLarge?.copyWith(fontWeight: FontWeight.w900),
            ),
          ),
          Icon(
            _eventIcon(event.type),
            color: _eventColor(event.type),
            size: 20,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  event.title,
                  style: Theme.of(
                    context,
                  ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800),
                ),
                const SizedBox(height: 4),
                Text(
                  event.detail,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _StatPairRow extends StatelessWidget {
  const _StatPairRow({
    required this.label,
    required this.pair,
    this.decimals = 0,
  });

  final String label;
  final LiveMatchStatPair pair;
  final int decimals;

  @override
  Widget build(BuildContext context) {
    final double homeShare = pair.homeShare;
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.04),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.white.withValues(alpha: 0.1)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Text(
                  label,
                  style: Theme.of(
                    context,
                  ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800),
                ),
              ),
              Text(
                '${pair.homeLabel(decimals: decimals)} / '
                '${pair.awayLabel(decimals: decimals)}',
                style: Theme.of(context).textTheme.labelLarge,
              ),
            ],
          ),
          const SizedBox(height: 10),
          ClipRRect(
            borderRadius: BorderRadius.circular(999),
            child: SizedBox(
              height: 8,
              child: Row(
                children: <Widget>[
                  Expanded(
                    flex: math.max(1, (homeShare * 100).round()),
                    child: ColoredBox(color: GteShellTheme.accentArena),
                  ),
                  Expanded(
                    flex: math.max(1, ((1 - homeShare) * 100).round()),
                    child: ColoredBox(color: GteShellTheme.accentWarm),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _MarketContextBlock extends StatelessWidget {
  const _MarketContextBlock({required this.stats});

  final LiveMatchStatsSnapshot stats;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: tokens.panel.withValues(alpha: 0.7),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: tokens.stroke.withValues(alpha: 0.72)),
      ),
      child: Wrap(
        spacing: 8,
        runSpacing: 8,
        children: <Widget>[
          if (matchCenterHasText(stats.marketSignal))
            GteMetricChip(label: 'Market signal', value: stats.marketSignal!),
          if (matchCenterHasText(stats.marketDetail))
            GteMetricChip(label: 'Market context', value: stats.marketDetail!),
        ],
      ),
    );
  }
}

class _TextChip extends StatelessWidget {
  const _TextChip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: tokens.accentWarm.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: tokens.accentWarm.withValues(alpha: 0.24)),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
          color: tokens.accentWarm,
          fontWeight: FontWeight.w800,
          letterSpacing: 0,
        ),
      ),
    );
  }
}

Color _stateColor(BuildContext context, MatchCenterSurfaceState state) {
  final tokens = GteShellTheme.tokensOf(context);
  switch (state) {
    case MatchCenterSurfaceState.confirmed:
      return tokens.positive;
    case MatchCenterSurfaceState.empty:
      return tokens.textMuted;
    case MatchCenterSurfaceState.blocked:
      return tokens.warning;
    case MatchCenterSurfaceState.degraded:
      return tokens.accentCapital;
    case MatchCenterSurfaceState.syncing:
      return GteShellTheme.accentClub;
  }
}

MatchCenterSurfaceState _surfaceStateForRealtime(LiveMatchRealtimeFrame frame) {
  switch (frame.status) {
    case LiveMatchRealtimeStatus.blocked:
    case LiveMatchRealtimeStatus.error:
      return MatchCenterSurfaceState.blocked;
    case LiveMatchRealtimeStatus.reconnecting:
    case LiveMatchRealtimeStatus.degraded:
      return MatchCenterSurfaceState.degraded;
    case LiveMatchRealtimeStatus.closed:
      return MatchCenterSurfaceState.blocked;
    case LiveMatchRealtimeStatus.idle:
    case LiveMatchRealtimeStatus.connecting:
    case LiveMatchRealtimeStatus.syncing:
    case LiveMatchRealtimeStatus.live:
    case LiveMatchRealtimeStatus.confirmed:
      return MatchCenterSurfaceState.syncing;
  }
}

String _fallbackRealtimeMessage(LiveMatchRealtimeStatus status) {
  switch (status) {
    case LiveMatchRealtimeStatus.blocked:
      return 'Realtime match feed is blocked until backend authority is restored.';
    case LiveMatchRealtimeStatus.error:
      return 'Realtime match feed errored before a backend score-clock snapshot arrived.';
    case LiveMatchRealtimeStatus.reconnecting:
      return 'Realtime match feed is reconnecting; score and clock are withheld.';
    case LiveMatchRealtimeStatus.degraded:
      return 'Realtime match feed is degraded; score and clock are withheld.';
    case LiveMatchRealtimeStatus.closed:
      return 'Realtime match feed closed before backend score-clock truth was confirmed.';
    case LiveMatchRealtimeStatus.idle:
    case LiveMatchRealtimeStatus.connecting:
    case LiveMatchRealtimeStatus.syncing:
    case LiveMatchRealtimeStatus.live:
    case LiveMatchRealtimeStatus.confirmed:
      return 'Awaiting a backend-authored score and clock frame before showing match state.';
  }
}

String _pendingRealtimeLabel(MatchCenterSurfaceState state) {
  switch (state) {
    case MatchCenterSurfaceState.blocked:
      return 'BLOCKED';
    case MatchCenterSurfaceState.degraded:
      return 'DEGRADED';
    case MatchCenterSurfaceState.empty:
      return 'EMPTY';
    case MatchCenterSurfaceState.syncing:
      return 'SYNCING';
    case MatchCenterSurfaceState.confirmed:
      return 'CONFIRMED';
  }
}

IconData _realtimeStateIcon(MatchCenterSurfaceState state) {
  switch (state) {
    case MatchCenterSurfaceState.blocked:
      return Icons.lock_outline;
    case MatchCenterSurfaceState.degraded:
      return Icons.signal_wifi_statusbar_connected_no_internet_4;
    case MatchCenterSurfaceState.empty:
      return Icons.hourglass_empty_outlined;
    case MatchCenterSurfaceState.syncing:
      return Icons.sync_outlined;
    case MatchCenterSurfaceState.confirmed:
      return Icons.verified_outlined;
  }
}

IconData _overlayIcon(LiveMatchOverlayMode mode) {
  switch (mode) {
    case LiveMatchOverlayMode.shape:
      return Icons.account_tree_outlined;
    case LiveMatchOverlayMode.pressure:
      return Icons.speed_outlined;
    case LiveMatchOverlayMode.shots:
      return Icons.sports_soccer_outlined;
    case LiveMatchOverlayMode.xg:
      return Icons.ssid_chart_outlined;
    case LiveMatchOverlayMode.territory:
      return Icons.map_outlined;
    case LiveMatchOverlayMode.market:
      return Icons.stacked_line_chart_outlined;
  }
}

IconData _eventIcon(LiveMatchEventType type) {
  switch (type) {
    case LiveMatchEventType.goal:
      return Icons.sports_soccer_outlined;
    case LiveMatchEventType.card:
      return Icons.style_outlined;
    case LiveMatchEventType.substitution:
      return Icons.swap_horiz_outlined;
    case LiveMatchEventType.incident:
      return Icons.bolt_outlined;
  }
}

Color _eventColor(LiveMatchEventType type) {
  switch (type) {
    case LiveMatchEventType.goal:
      return GteShellTheme.accentArena;
    case LiveMatchEventType.card:
      return GteShellTheme.warning;
    case LiveMatchEventType.substitution:
      return GteShellTheme.accentWarm;
    case LiveMatchEventType.incident:
      return GteShellTheme.accentClub;
  }
}
