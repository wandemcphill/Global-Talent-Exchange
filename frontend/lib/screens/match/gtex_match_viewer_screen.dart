import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/match_playback_controller.dart';
import 'package:gte_frontend/data/live_match_fixtures.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_event.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/services/match_viewer_mapper.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/match/event_ticker_widget.dart';
import 'package:gte_frontend/widgets/match/pitch_2d_widget.dart';
import 'package:gte_frontend/widgets/match/scoreboard_widget.dart';

class GtexMatchViewerScreen extends StatefulWidget {
  const GtexMatchViewerScreen({
    super.key,
    required this.competition,
    required this.matchKey,
    this.fallbackSnapshot,
    this.preferFallback = false,
  });

  final CompetitionSummary competition;
  final String matchKey;
  final LiveMatchSnapshot? fallbackSnapshot;
  final bool preferFallback;

  @override
  State<GtexMatchViewerScreen> createState() => _GtexMatchViewerScreenState();
}

class _GtexMatchViewerScreenState extends State<GtexMatchViewerScreen>
    with SingleTickerProviderStateMixin {
  late Future<MatchViewState> _viewStateFuture;
  MatchPlaybackController? _controller;

  @override
  void initState() {
    super.initState();
    _viewStateFuture = _load();
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  Future<MatchViewState> _load() {
    return MatchViewerMapper.load(
      competition: widget.competition,
      matchKey: widget.matchKey,
      fallbackSnapshot: widget.fallbackSnapshot,
      preferFallback: widget.preferFallback,
    );
  }

  void _reload() {
    _controller?.dispose();
    _controller = null;
    setState(() {
      _viewStateFuture = _load();
    });
  }

  MatchPlaybackController _ensureController(MatchViewState viewState) {
    final MatchPlaybackController? existing = _controller;
    if (existing != null && existing.viewState.matchId == viewState.matchId) {
      return existing;
    }
    existing?.dispose();
    final MatchPlaybackController created = MatchPlaybackController(
      vsync: this,
      viewState: viewState,
      autoplay: true,
    );
    _controller = created;
    return created;
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: const Text('2D Match Viewer'),
          actions: <Widget>[
            IconButton(
              tooltip: 'Reload replay',
              onPressed: _reload,
              icon: const Icon(Icons.refresh),
            ),
          ],
        ),
        body: FutureBuilder<MatchViewState>(
          future: _viewStateFuture,
          builder:
              (BuildContext context, AsyncSnapshot<MatchViewState> snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Padding(
                padding: EdgeInsets.all(20),
                child: GteStatePanel(
                  eyebrow: 'MATCH VIEWER',
                  title: 'Loading replay timeline',
                  message:
                      'Preparing the 2D pitch, timeline frames, and replay controls.',
                  icon: Icons.sports_soccer,
                  accentColor: GteShellTheme.accentArena,
                  isLoading: true,
                ),
              );
            }
            if (!snapshot.hasData) {
              return Padding(
                padding: const EdgeInsets.all(20),
                child: GteStatePanel(
                  title: 'Replay unavailable',
                  message:
                      'Unable to load the serialized replay timeline right now.',
                  icon: Icons.warning_amber_outlined,
                  actionLabel: 'Retry',
                  onAction: _reload,
                ),
              );
            }

            final MatchViewState viewState = snapshot.data!;
            final MatchPlaybackController controller =
                _ensureController(viewState);
            return LayoutBuilder(
              builder: (BuildContext context, BoxConstraints constraints) {
                final bool wide = constraints.maxWidth >= 1040;
                final Widget viewerPanel = ListenableBuilder(
                  listenable: controller,
                  builder: (BuildContext context, Widget? child) {
                    final MatchEvent? activeEvent = controller.activeEvent;
                    return Column(
                      children: <Widget>[
                        Expanded(
                          child: Stack(
                            children: <Widget>[
                              Positioned.fill(
                                child: Padding(
                                  padding:
                                      const EdgeInsets.fromLTRB(18, 18, 18, 18),
                                  child: RepaintBoundary(
                                    child: Pitch2dWidget(
                                      viewState: viewState,
                                      frame: controller.displayFrame,
                                    ),
                                  ),
                                ),
                              ),
                              Positioned(
                                top: 28,
                                left: 28,
                                right: 28,
                                child: Row(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: <Widget>[
                                    ScoreboardWidget(
                                      viewState: viewState,
                                      frame: controller.displayFrame,
                                      activeEvent: activeEvent,
                                    ),
                                    const Spacer(),
                                    ConstrainedBox(
                                      constraints:
                                          const BoxConstraints(maxWidth: 360),
                                      child:
                                          EventTickerWidget(event: activeEvent),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),
                        _ControlBar(controller: controller),
                      ],
                    );
                  },
                );

                final Widget rail =
                    _EventRail(controller: controller, viewState: viewState);
                if (wide) {
                  return Row(
                    children: <Widget>[
                      Expanded(flex: 3, child: viewerPanel),
                      SizedBox(
                        width: 320,
                        child: Padding(
                          padding: const EdgeInsets.fromLTRB(0, 18, 18, 18),
                          child: rail,
                        ),
                      ),
                    ],
                  );
                }
                return Column(
                  children: <Widget>[
                    Expanded(child: viewerPanel),
                    SizedBox(
                      height: 220,
                      child: Padding(
                        padding: const EdgeInsets.fromLTRB(18, 0, 18, 18),
                        child: rail,
                      ),
                    ),
                  ],
                );
              },
            );
          },
        ),
      ),
    );
  }
}

class _ControlBar extends StatelessWidget {
  const _ControlBar({required this.controller});

  final MatchPlaybackController controller;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(18, 12, 18, 18),
      child: Row(
        children: <Widget>[
          FilledButton.icon(
            onPressed: controller.togglePlayPause,
            icon: Icon(controller.isPlaying ? Icons.pause : Icons.play_arrow),
            label: Text(controller.isPlaying ? 'Pause' : 'Play'),
          ),
          const SizedBox(width: 10),
          FilledButton.tonalIcon(
            onPressed: controller.restart,
            icon: const Icon(Icons.replay),
            label: const Text('Restart'),
          ),
          const SizedBox(width: 10),
          FilledButton.tonalIcon(
            onPressed: controller.cycleSpeed,
            icon: const Icon(Icons.speed),
            label: Text('${controller.speed.toStringAsFixed(0)}x'),
          ),
          const SizedBox(width: 10),
          FilledButton.tonalIcon(
            onPressed: controller.jumpToNextEvent,
            icon: const Icon(Icons.skip_next),
            label: const Text('Next event'),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: LinearProgressIndicator(
              value: controller.progress.clamp(0, 1),
              minHeight: 7,
              borderRadius: BorderRadius.circular(999),
              backgroundColor: Colors.white.withValues(alpha: 0.08),
              valueColor: const AlwaysStoppedAnimation<Color>(
                GteShellTheme.accentArena,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _EventRail extends StatelessWidget {
  const _EventRail({
    required this.controller,
    required this.viewState,
  });

  final MatchPlaybackController controller;
  final MatchViewState viewState;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(24),
        color: Colors.white.withValues(alpha: 0.05),
        border: Border.all(color: Colors.white.withValues(alpha: 0.09)),
      ),
      child: ListenableBuilder(
        listenable: controller,
        builder: (BuildContext context, Widget? child) {
          final MatchEvent? activeEvent = controller.activeEvent;
          final List<MatchEvent> events = controller.upcomingEvents;
          return ListView(
            padding: const EdgeInsets.all(16),
            children: <Widget>[
              Text(
                'Replay lane',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 8),
              Text(
                'Source: ${viewState.source} | ${viewState.durationSeconds}s | ${viewState.events.length} events',
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const SizedBox(height: 14),
              if (activeEvent != null)
                _EventTile(
                  event: activeEvent,
                  active: true,
                ),
              ...events
                  .where((MatchEvent item) => item.id != activeEvent?.id)
                  .map(
                    (MatchEvent item) => Padding(
                      padding: const EdgeInsets.only(top: 8),
                      child: _EventTile(event: item),
                    ),
                  ),
            ],
          );
        },
      ),
    );
  }
}

class _EventTile extends StatelessWidget {
  const _EventTile({
    required this.event,
    this.active = false,
  });

  final MatchEvent event;
  final bool active;

  @override
  Widget build(BuildContext context) {
    final Color accent = _tileAccent(event.type);
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        color: active
            ? accent.withValues(alpha: 0.16)
            : Colors.white.withValues(alpha: 0.04),
        border: Border.all(
          color: active
              ? accent.withValues(alpha: 0.55)
              : Colors.white.withValues(alpha: 0.08),
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(event.icon, color: accent, size: 18),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  event.bannerText,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: Colors.white,
                        fontWeight: FontWeight.w600,
                      ),
                ),
                const SizedBox(height: 4),
                Text(
                  '${event.clockLabel} | ${event.teamName ?? 'Match'}',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Colors.white70,
                      ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

Color _tileAccent(MatchViewerEventType type) {
  switch (type) {
    case MatchViewerEventType.goal:
      return const Color(0xFF17B26A);
    case MatchViewerEventType.save:
      return const Color(0xFF53B1FD);
    case MatchViewerEventType.miss:
      return const Color(0xFFF79009);
    case MatchViewerEventType.offside:
      return const Color(0xFFF97066);
    case MatchViewerEventType.redCard:
      return const Color(0xFFF04438);
    default:
      return const Color(0xFFD0D5DD);
  }
}
