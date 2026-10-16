import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/match_3d_timeline_controller.dart';
import 'package:gte_frontend/data/match/match_simulation_models.dart';
import 'package:gte_frontend/models/match_event.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/services/fairness_indicator_service.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';
import 'package:gte_frontend/widgets/gtex_branding.dart';
import 'package:gte_frontend/widgets/match/pitch_2d_widget.dart';
import 'package:gte_frontend/widgets/match/scoreboard_widget.dart';

enum _SimulationSpeed {
  x1,
  x2,
  x4,
  instant,
}

class GtexMatchSimulationScreen extends StatefulWidget {
  const GtexMatchSimulationScreen({
    super.key,
    required this.result,
    this.title,
    this.competitionLabel,
  });

  final MatchSimulationResult result;
  final String? title;
  final String? competitionLabel;

  @override
  State<GtexMatchSimulationScreen> createState() =>
      _GtexMatchSimulationScreenState();
}

class _GtexMatchSimulationScreenState extends State<GtexMatchSimulationScreen>
    with SingleTickerProviderStateMixin {
  late Match3dTimelineController _controller;
  _SimulationSpeed _selectedSpeed = _SimulationSpeed.x1;

  @override
  void initState() {
    super.initState();
    _controller = _buildController(widget.result);
  }

  @override
  void didUpdateWidget(covariant GtexMatchSimulationScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.result != widget.result) {
      _controller
        ..removeListener(_handleControllerChanged)
        ..dispose();
      _controller = _buildController(widget.result);
    }
  }

  @override
  void dispose() {
    _controller
      ..removeListener(_handleControllerChanged)
      ..dispose();
    super.dispose();
  }

  Match3dTimelineController _buildController(MatchSimulationResult result) {
    final Match3dTimelineController controller = Match3dTimelineController(
      vsync: this,
      viewState: result.viewState,
      autoplay: true,
    );
    controller.updateSpeedOptions(const <double>[1, 2, 4]);
    controller.addListener(_handleControllerChanged);
    return controller;
  }

  void _handleControllerChanged() {
    if (!mounted) {
      return;
    }
    setState(() {});
  }

  void _setSpeed(_SimulationSpeed speed) {
    setState(() {
      _selectedSpeed = speed;
    });
    switch (speed) {
      case _SimulationSpeed.x1:
        if (_controller.positionSeconds >=
            widget.result.viewState.durationSeconds.toDouble()) {
          _controller.restart();
          _controller.play();
        }
        _controller.setSpeed(1);
        break;
      case _SimulationSpeed.x2:
        if (_controller.positionSeconds >=
            widget.result.viewState.durationSeconds.toDouble()) {
          _controller.restart();
          _controller.play();
        }
        _controller.setSpeed(2);
        break;
      case _SimulationSpeed.x4:
        if (_controller.positionSeconds >=
            widget.result.viewState.durationSeconds.toDouble()) {
          _controller.restart();
          _controller.play();
        }
        _controller.setSpeed(4);
        break;
      case _SimulationSpeed.instant:
        _controller.seekToSeconds(
          widget.result.viewState.durationSeconds.toDouble(),
        );
        _controller.pause();
        break;
    }
  }

  List<MatchSimulationPlayerPerformance> get _sortedPerformances =>
      widget.result.playerPerformances;

  List<_EventCardData> get _timelineEvents => widget.result.timelineEvents
      .where((event) => event.type.name != 'kickoff')
      .map(_EventCardData.fromEvent)
      .toList(growable: false);

  List<_EventCardData> get _visibleCommentary {
    final double now = _controller.positionSeconds + 0.001;
    final List<_EventCardData> visible = widget.result.timelineEvents
        .where((event) => event.timeSeconds <= now)
        .map(_EventCardData.fromEvent)
        .toList(growable: false);
    final List<_EventCardData> recent =
        visible.reversed.take(7).toList(growable: false);
    return recent.isEmpty
        ? <_EventCardData>[
            const _EventCardData(
              minuteLabel: '0\'',
              title: 'Kickoff',
              commentary: 'The simulation is loading its opening phase.',
            ),
          ]
        : recent;
  }

  FairnessBadgeState get _fairnessBadge =>
      FairnessIndicatorService.build(widget.result.viewState);

  List<String> get _liveActionLabels {
    final List<MatchViewerPlayerFrame> candidates = _controller
        .displayFrame.players
        .where(
          (MatchViewerPlayerFrame player) =>
              player.animationState != MatchPlayerAnimationState.idle &&
              player.animationState != MatchPlayerAnimationState.jog,
        )
        .toList(growable: false)
      ..sort((MatchViewerPlayerFrame left, MatchViewerPlayerFrame right) {
        final double leftScore =
            (left.highlighted ? 2 : 0) + left.speedRatio + left.blendFactor;
        final double rightScore =
            (right.highlighted ? 2 : 0) + right.speedRatio + right.blendFactor;
        return rightScore.compareTo(leftScore);
      });
    return candidates
        .take(3)
        .map(
          (MatchViewerPlayerFrame player) =>
              '${widget.result.viewState.teamForSide(player.side).shortName} ${player.label} ${player.animationState.label}',
        )
        .toList(growable: false);
  }

  Widget _buildPitchPanel() {
    return GteSurfacePanel(
      emphasized: true,
      accentColor: GteShellTheme.accentArena,
      padding: const EdgeInsets.all(12),
      child: Pitch2dWidget(
        viewState: widget.result.viewState,
        frame: _controller.displayFrame,
        showFormationOverlay: false,
      ),
    );
  }

  Widget _buildAnalysisSection({required bool stacked}) {
    if (stacked) {
      return Column(
        children: <Widget>[
          Expanded(
            child: _CommentaryPanel(
              entries: _visibleCommentary,
            ),
          ),
          const SizedBox(height: 12),
          Expanded(
            child: _SimulationTabs(
              result: widget.result,
              timelineEvents: _timelineEvents,
              performances: _sortedPerformances,
              fairnessBadge: _fairnessBadge,
            ),
          ),
        ],
      );
    }
    return Row(
      children: <Widget>[
        Expanded(
          child: _CommentaryPanel(
            entries: _visibleCommentary,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _SimulationTabs(
            result: widget.result,
            timelineEvents: _timelineEvents,
            performances: _sortedPerformances,
            fairnessBadge: _fairnessBadge,
          ),
        ),
      ],
    );
  }

  Widget _buildScrollableBody(int visibleMinute) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
      children: <Widget>[
        ScoreboardWidget(
          viewState: widget.result.viewState,
          frame: _controller.displayFrame,
          activeEvent: _controller.activeEvent,
        ),
        const SizedBox(height: 10),
        _SimulationSummaryRow(
          homeTeam: widget.result.request.homeTeam,
          awayTeam: widget.result.request.awayTeam,
          visibleMinute: visibleMinute,
          importanceLabel: widget.result.request.importance.label,
          fairnessLabel: _fairnessBadge.label,
          liveActions: _liveActionLabels,
        ),
        const SizedBox(height: 12),
        SizedBox(height: 250, child: _buildPitchPanel()),
        const SizedBox(height: 12),
        _SimulationControls(
          isPlaying: _controller.isPlaying,
          selectedSpeed: _selectedSpeed,
          onTogglePlay: _controller.togglePlayPause,
          onRestart: () {
            _controller.restart();
            _controller.play();
            _setSpeed(_selectedSpeed == _SimulationSpeed.instant
                ? _SimulationSpeed.x1
                : _selectedSpeed);
          },
          onSpeedSelected: _setSpeed,
        ),
        const SizedBox(height: 12),
        SizedBox(
          height: 260,
          child: _CommentaryPanel(
            entries: _visibleCommentary,
          ),
        ),
        const SizedBox(height: 12),
        SizedBox(
          height: 340,
          child: _SimulationTabs(
            result: widget.result,
            timelineEvents: _timelineEvents,
            performances: _sortedPerformances,
            fairnessBadge: _fairnessBadge,
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final String matchTitle = widget.title ??
        '${widget.result.request.homeTeam.name} vs ${widget.result.request.awayTeam.name}';
    final String competitionLabel =
        widget.competitionLabel ?? widget.result.request.importance.label;
    final int visibleMinute = _controller.clockMinute.floor();

    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: Text(matchTitle),
          actions: <Widget>[
            Padding(
              padding: const EdgeInsets.only(right: 16),
              child: Center(
                child: Text(
                  competitionLabel,
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ),
            ),
          ],
        ),
        body: SafeArea(
          top: false,
          child: LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              if (constraints.maxHeight < 760) {
                return _buildScrollableBody(visibleMinute);
              }
              return Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
                child: Column(
                  children: <Widget>[
                    ScoreboardWidget(
                      viewState: widget.result.viewState,
                      frame: _controller.displayFrame,
                      activeEvent: _controller.activeEvent,
                    ),
                    const SizedBox(height: 10),
                    _SimulationSummaryRow(
                      homeTeam: widget.result.request.homeTeam,
                      awayTeam: widget.result.request.awayTeam,
                      visibleMinute: visibleMinute,
                      importanceLabel: widget.result.request.importance.label,
                      fairnessLabel: _fairnessBadge.label,
                      liveActions: _liveActionLabels,
                    ),
                    const SizedBox(height: 12),
                    Expanded(
                      flex: 6,
                      child: _buildPitchPanel(),
                    ),
                    const SizedBox(height: 12),
                    _SimulationControls(
                      isPlaying: _controller.isPlaying,
                      selectedSpeed: _selectedSpeed,
                      onTogglePlay: _controller.togglePlayPause,
                      onRestart: () {
                        _controller.restart();
                        _controller.play();
                        _setSpeed(_selectedSpeed == _SimulationSpeed.instant
                            ? _SimulationSpeed.x1
                            : _selectedSpeed);
                      },
                      onSpeedSelected: _setSpeed,
                    ),
                    const SizedBox(height: 12),
                    Expanded(
                      flex: 5,
                      child: _buildAnalysisSection(
                        stacked: constraints.maxWidth < 900,
                      ),
                    ),
                  ],
                ),
              );
            },
          ),
        ),
      ),
    );
  }
}

class _SimulationSummaryRow extends StatelessWidget {
  const _SimulationSummaryRow({
    required this.homeTeam,
    required this.awayTeam,
    required this.visibleMinute,
    required this.importanceLabel,
    required this.fairnessLabel,
    required this.liveActions,
  });

  final MatchSimulationTeam homeTeam;
  final MatchSimulationTeam awayTeam;
  final int visibleMinute;
  final String importanceLabel;
  final String fairnessLabel;
  final List<String> liveActions;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: <Widget>[
        _SummaryChip(label: 'Minute $visibleMinute'),
        _SummaryChip(label: homeTeam.tactics.summary),
        _SummaryChip(label: awayTeam.tactics.summary),
        _SummaryChip(label: fairnessLabel),
        _SummaryChip(label: importanceLabel),
        for (final String action in liveActions.take(2))
          _SummaryChip(label: action),
      ],
    );
  }
}

class _SimulationControls extends StatelessWidget {
  const _SimulationControls({
    required this.isPlaying,
    required this.selectedSpeed,
    required this.onTogglePlay,
    required this.onRestart,
    required this.onSpeedSelected,
  });

  final bool isPlaying;
  final _SimulationSpeed selectedSpeed;
  final VoidCallback onTogglePlay;
  final VoidCallback onRestart;
  final ValueChanged<_SimulationSpeed> onSpeedSelected;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      padding: const EdgeInsets.fromLTRB(14, 10, 14, 10),
      child: Row(
        children: <Widget>[
          FilledButton.icon(
            onPressed: onTogglePlay,
            icon: Icon(isPlaying ? Icons.pause : Icons.play_arrow),
            label: Text(isPlaying ? 'Pause' : 'Play'),
          ),
          const SizedBox(width: 10),
          OutlinedButton.icon(
            onPressed: onRestart,
            icon: const Icon(Icons.replay),
            label: const Text('Replay'),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: SegmentedButton<_SimulationSpeed>(
                showSelectedIcon: false,
                segments: const <ButtonSegment<_SimulationSpeed>>[
                  ButtonSegment<_SimulationSpeed>(
                    value: _SimulationSpeed.x1,
                    label: Text('x1'),
                  ),
                  ButtonSegment<_SimulationSpeed>(
                    value: _SimulationSpeed.x2,
                    label: Text('x2'),
                  ),
                  ButtonSegment<_SimulationSpeed>(
                    value: _SimulationSpeed.x4,
                    label: Text('x4'),
                  ),
                  ButtonSegment<_SimulationSpeed>(
                    value: _SimulationSpeed.instant,
                    label: Text('Instant'),
                  ),
                ],
                selected: <_SimulationSpeed>{selectedSpeed},
                onSelectionChanged: (Set<_SimulationSpeed> value) {
                  onSpeedSelected(value.first);
                },
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _CommentaryPanel extends StatelessWidget {
  const _CommentaryPanel({
    required this.entries,
  });

  final List<_EventCardData> entries;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      accentColor: GteShellTheme.accentArena,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Live commentary',
              style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          Expanded(
            child: ListView.separated(
              itemCount: entries.length,
              separatorBuilder: (_, __) => const SizedBox(height: 10),
              itemBuilder: (BuildContext context, int index) {
                final _EventCardData entry = entries[index];
                return Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(16),
                    color: Colors.white.withValues(alpha: 0.03),
                    border:
                        Border.all(color: Colors.white.withValues(alpha: 0.06)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        '${entry.minuteLabel}  ${entry.title}',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 6),
                      Text(
                        entry.commentary,
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _SimulationTabs extends StatelessWidget {
  const _SimulationTabs({
    required this.result,
    required this.timelineEvents,
    required this.performances,
    required this.fairnessBadge,
  });

  final MatchSimulationResult result;
  final List<_EventCardData> timelineEvents;
  final List<MatchSimulationPlayerPerformance> performances;
  final FairnessBadgeState fairnessBadge;

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 3,
      child: GteSurfacePanel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            const TabBar(
              isScrollable: true,
              tabAlignment: TabAlignment.start,
              tabs: <Tab>[
                Tab(text: 'Stats'),
                Tab(text: 'Timeline'),
                Tab(text: 'Ratings'),
              ],
            ),
            const SizedBox(height: 12),
            Expanded(
              child: TabBarView(
                children: <Widget>[
                  _StatsTab(
                    result: result,
                    fairnessBadge: fairnessBadge,
                  ),
                  _TimelineTab(events: timelineEvents),
                  _RatingsTab(performances: performances),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _StatsTab extends StatelessWidget {
  const _StatsTab({
    required this.result,
    required this.fairnessBadge,
  });

  final MatchSimulationResult result;
  final FairnessBadgeState fairnessBadge;

  @override
  Widget build(BuildContext context) {
    final MatchSimulationTeamStats home = result.homeStats;
    final MatchSimulationTeamStats away = result.awayStats;
    return ListView(
      children: <Widget>[
        _StatComparisonRow(
          label: 'Possession',
          leftValue: '${home.possessionPct}%',
          rightValue: '${away.possessionPct}%',
        ),
        _StatComparisonRow(
          label: 'Shots',
          leftValue: '${home.shots}',
          rightValue: '${away.shots}',
        ),
        _StatComparisonRow(
          label: 'Shots on target',
          leftValue: '${home.shotsOnTarget}',
          rightValue: '${away.shotsOnTarget}',
        ),
        _StatComparisonRow(
          label: 'xG',
          leftValue: home.expectedGoals.toStringAsFixed(2),
          rightValue: away.expectedGoals.toStringAsFixed(2),
        ),
        _StatComparisonRow(
          label: 'Big chances',
          leftValue: '${home.bigChances}',
          rightValue: '${away.bigChances}',
        ),
        _StatComparisonRow(
          label: 'Turnovers forced',
          leftValue: '${home.turnoversForced}',
          rightValue: '${away.turnoversForced}',
        ),
        _StatComparisonRow(
          label: 'Avg stamina',
          leftValue: '${home.averageStaminaPct}%',
          rightValue: '${away.averageStaminaPct}%',
        ),
        _StatComparisonRow(
          label: 'Recovery runs',
          leftValue: '${home.recoveries}',
          rightValue: '${away.recoveries}',
        ),
        _StatComparisonRow(
          label: 'Press wins',
          leftValue: '${home.successfulPresses}',
          rightValue: '${away.successfulPresses}',
        ),
        const SizedBox(height: 10),
        Text(
          'Tactical matchup',
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 8),
        Text(
          '${result.request.homeTeam.name}: ${result.request.homeTeam.tactics.detailSummary}',
          style: Theme.of(context).textTheme.bodyMedium,
        ),
        const SizedBox(height: 4),
        Text(
          '${result.request.awayTeam.name}: ${result.request.awayTeam.tactics.detailSummary}',
          style: Theme.of(context).textTheme.bodyMedium,
        ),
        const SizedBox(height: 14),
        Text(
          'Integrity envelope',
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 8),
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            color: Colors.white.withValues(alpha: 0.03),
            border: Border.all(color: Colors.white.withValues(alpha: 0.06)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                fairnessBadge.label,
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 6),
              Text(
                fairnessBadge.message,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _TimelineTab extends StatelessWidget {
  const _TimelineTab({required this.events});

  final List<_EventCardData> events;

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      itemCount: events.length,
      separatorBuilder: (_, __) => const SizedBox(height: 8),
      itemBuilder: (BuildContext context, int index) {
        final _EventCardData event = events[index];
        return Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            color: Colors.white.withValues(alpha: 0.03),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                '${event.minuteLabel}  ${event.title}',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 6),
              Text(event.commentary),
            ],
          ),
        );
      },
    );
  }
}

class _RatingsTab extends StatelessWidget {
  const _RatingsTab({required this.performances});

  final List<MatchSimulationPlayerPerformance> performances;

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      itemCount: performances.length,
      separatorBuilder: (_, __) => const SizedBox(height: 8),
      itemBuilder: (BuildContext context, int index) {
        final MatchSimulationPlayerPerformance performance =
            performances[index];
        final bool positive = performance.valueDeltaPct >= 0;
        final Color accent = performance.isMvp
            ? const Color(0xFFFDB022)
            : positive
                ? GteShellTheme.positive
                : GteShellTheme.warning;
        return Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            color: Colors.white.withValues(alpha: 0.03),
            border: Border.all(color: accent.withValues(alpha: 0.18)),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: <Widget>[
                        Text(
                          performance.player.name,
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        _Badge(
                          label: performance.formTag.label,
                          accent: accent,
                        ),
                        if (performance.isMvp)
                          _Badge(
                            label: 'MVP',
                            accent: const Color(0xFFFDB022),
                          ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(
                      '${performance.teamName}  |  Rating ${performance.rating.toStringAsFixed(1)}  |  ${performance.player.position}',
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'G ${performance.goals}  A ${performance.assists}  KP ${performance.keyPasses}  S ${performance.shots}  SoT ${performance.shotsOnTarget}',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: <Widget>[
                  Text(
                    '${positive ? '+' : ''}${(performance.valueDeltaPct * 100).toStringAsFixed(1)}%',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          color: accent,
                          fontWeight: FontWeight.w700,
                        ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '${performance.nextValueCredits.round()} cr',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }
}

class _StatComparisonRow extends StatelessWidget {
  const _StatComparisonRow({
    required this.label,
    required this.leftValue,
    required this.rightValue,
  });

  final String label;
  final String leftValue;
  final String rightValue;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        children: <Widget>[
          SizedBox(
            width: 72,
            child: Text(
              leftValue,
              style: Theme.of(context).textTheme.titleMedium,
            ),
          ),
          Expanded(
            child: Text(
              label,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ),
          SizedBox(
            width: 72,
            child: Text(
              rightValue,
              textAlign: TextAlign.right,
              style: Theme.of(context).textTheme.titleMedium,
            ),
          ),
        ],
      ),
    );
  }
}

class _SummaryChip extends StatelessWidget {
  const _SummaryChip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: Colors.white.withValues(alpha: 0.05),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Text(label, style: Theme.of(context).textTheme.bodySmall),
    );
  }
}

class _Badge extends StatelessWidget {
  const _Badge({
    required this.label,
    required this.accent,
  });

  final String label;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: accent.withValues(alpha: 0.12),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: accent,
              fontWeight: FontWeight.w700,
            ),
      ),
    );
  }
}

class _EventCardData {
  const _EventCardData({
    required this.minuteLabel,
    required this.title,
    required this.commentary,
  });

  final String minuteLabel;
  final String title;
  final String commentary;

  factory _EventCardData.fromEvent(MatchEvent event) {
    return _EventCardData(
      minuteLabel: "${event.minute}'",
      title: event.bannerText,
      commentary: event.commentary,
    );
  }
}
