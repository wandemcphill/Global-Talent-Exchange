import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/match_playback_controller.dart';
import 'package:gte_frontend/data/live_match_fixtures.dart';
import 'package:gte_frontend/data/match_gift_api.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_event.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/models/match_viewer_presentation.dart';
import 'package:gte_frontend/services/match_3d_bridge.dart';
import 'package:gte_frontend/services/match_3d_live_bootstrap_service.dart';
import 'package:gte_frontend/services/match_3d_monetization_service.dart';
import 'package:gte_frontend/services/match_viewer_mapper.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/match/pitch_2d_widget.dart';

typedef MatchViewStateLoader = Future<MatchViewState> Function();
typedef MatchViewContinuationLoader =
    Future<MatchViewState> Function({
      required String matchKey,
      required String continuationToken,
    });

class GtexMatchViewerScreen extends StatefulWidget {
  const GtexMatchViewerScreen({
    super.key,
    required this.competition,
    required this.matchKey,
    this.fallbackSnapshot,
    this.preferFallback = false,
    this.presentationMode = MatchViewerPresentationMode.replay,
    this.renderMode = RenderMode.twoD,
    this.viewStateLoader,
    this.continuationLoader,
    this.entitlement = const Match3dUserEntitlement(),
    this.isSpectator = false,
    this.monetizationService,
    this.giftClient,
    this.titleOverride,
    this.engineBridge,
    this.androidLiveBootstrapProvisioner,
  });

  final CompetitionSummary competition;
  final String matchKey;
  final LiveMatchSnapshot? fallbackSnapshot;
  final bool preferFallback;
  final MatchViewerPresentationMode presentationMode;
  final RenderMode renderMode;
  final MatchViewStateLoader? viewStateLoader;
  final MatchViewContinuationLoader? continuationLoader;
  final Match3dUserEntitlement entitlement;
  final bool isSpectator;
  final Match3dMonetizationService? monetizationService;
  final MatchGiftClient? giftClient;
  final String? titleOverride;
  final Match3DBridge? engineBridge;
  final Match3dAndroidLiveBootstrapProvisioner? androidLiveBootstrapProvisioner;

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
  void didUpdateWidget(covariant GtexMatchViewerScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.matchKey != widget.matchKey ||
        oldWidget.viewStateLoader != widget.viewStateLoader ||
        oldWidget.fallbackSnapshot != widget.fallbackSnapshot ||
        oldWidget.preferFallback != widget.preferFallback) {
      _reload();
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  Future<MatchViewState> _load() {
    final MatchViewStateLoader? loader = widget.viewStateLoader;
    if (loader != null) {
      return loader();
    }
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
        body: FutureBuilder<MatchViewState>(
          future: _viewStateFuture,
          builder: (
            BuildContext context,
            AsyncSnapshot<MatchViewState> snapshot,
          ) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const _MatchViewerLoading();
            }
            if (snapshot.hasError || !snapshot.hasData) {
              return _MatchViewerError(onReload: _reload);
            }
            final MatchViewState viewState = snapshot.data!;
            if (viewState.frames.isEmpty) {
              return _MatchViewerError(
                onReload: _reload,
                message:
                    'This match does not yet have a 2D timeline to display.',
              );
            }
            final MatchPlaybackController controller = _ensureController(
              viewState,
            );
            return ListenableBuilder(
              listenable: controller,
              builder: (BuildContext context, Widget? child) {
                final MatchTimelineFrame frame = controller.displayFrame;
                final MatchEvent? activeEvent = controller.activeEvent;
                return SafeArea(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(14, 10, 14, 12),
                    child: Column(
                      children: <Widget>[
                        _ScoreStrip(
                          timeLabel: _formatPlaybackClock(
                            controller.positionSeconds,
                          ),
                          homeName: viewState.homeTeam.shortName,
                          awayName: viewState.awayTeam.shortName,
                          homeScore: frame.homeScore,
                          awayScore: frame.awayScore,
                          onReload: _reload,
                        ),
                        const SizedBox(height: 10),
                        Expanded(
                          child: Center(
                            child: MatchPitch2D(
                              viewState: viewState,
                              frame: frame,
                              previousFrame: controller.leftFrame,
                              activeEvent: activeEvent,
                            ),
                          ),
                        ),
                        const SizedBox(height: 10),
                        _CommentaryCapsule(
                          text: _commentaryFor(
                            activeEvent: activeEvent,
                            frame: frame,
                          ),
                        ),
                        if (!widget.isSpectator) ...<Widget>[
                          const SizedBox(height: 8),
                          _CompactControlBar(controller: controller),
                        ],
                      ],
                    ),
                  ),
                );
              },
            );
          },
        ),
      ),
    );
  }
}

class _ScoreStrip extends StatelessWidget {
  const _ScoreStrip({
    required this.timeLabel,
    required this.homeName,
    required this.awayName,
    required this.homeScore,
    required this.awayScore,
    required this.onReload,
  });

  final String timeLabel;
  final String homeName;
  final String awayName;
  final int homeScore;
  final int awayScore;
  final VoidCallback onReload;

  @override
  Widget build(BuildContext context) {
    final TextStyle? teamStyle = Theme.of(context).textTheme.labelLarge
        ?.copyWith(color: Colors.white, fontWeight: FontWeight.w800);
    return Container(
      key: const Key('match-2d-score-strip'),
      constraints: const BoxConstraints(minHeight: 44),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: const Color(0xEE111827),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
      ),
      child: Row(
        children: <Widget>[
          _TimePill(label: timeLabel),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              homeName.toUpperCase(),
              textAlign: TextAlign.right,
              overflow: TextOverflow.ellipsis,
              style: teamStyle,
            ),
          ),
          const SizedBox(width: 12),
          Text(
            '$homeScore - $awayScore',
            key: const Key('match-2d-scoreline'),
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              color: Colors.white,
              fontWeight: FontWeight.w900,
              letterSpacing: 0,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              awayName.toUpperCase(),
              overflow: TextOverflow.ellipsis,
              style: teamStyle,
            ),
          ),
          const SizedBox(width: 8),
          Tooltip(
            message: 'Reload match',
            child: IconButton(
              onPressed: onReload,
              icon: const Icon(Icons.refresh, size: 18),
              color: Colors.white,
              style: IconButton.styleFrom(
                backgroundColor: Colors.white.withValues(alpha: 0.08),
                fixedSize: const Size.square(32),
                minimumSize: const Size.square(32),
                padding: EdgeInsets.zero,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _TimePill extends StatelessWidget {
  const _TimePill({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      key: const Key('match-2d-clock'),
      width: 64,
      alignment: Alignment.center,
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 7),
      decoration: BoxDecoration(
        color: const Color(0xFF0B5CAD),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelLarge?.copyWith(
          color: Colors.white,
          fontWeight: FontWeight.w900,
          letterSpacing: 0,
        ),
      ),
    );
  }
}

class _CommentaryCapsule extends StatelessWidget {
  const _CommentaryCapsule({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.center,
      child: Container(
        key: const Key('match-2d-commentary-bar'),
        constraints: const BoxConstraints(maxWidth: 620, minHeight: 30),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          color: const Color(0xEA0B1220),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: const Color(0xFFEE7CCC), width: 1.2),
          boxShadow: <BoxShadow>[
            BoxShadow(
              color: const Color(0xFFEE7CCC).withValues(alpha: 0.24),
              blurRadius: 12,
              spreadRadius: 0.5,
            ),
          ],
        ),
        child: Text(
          text,
          textAlign: TextAlign.center,
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
          style: Theme.of(context).textTheme.labelMedium?.copyWith(
            color: Colors.white,
            fontWeight: FontWeight.w700,
            letterSpacing: 0,
          ),
        ),
      ),
    );
  }
}

class _CompactControlBar extends StatelessWidget {
  const _CompactControlBar({required this.controller});

  final MatchPlaybackController controller;

  @override
  Widget build(BuildContext context) {
    return Container(
      key: const Key('match-2d-controls'),
      constraints: const BoxConstraints(maxWidth: 620),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.24),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Row(
        children: <Widget>[
          _ControlIconButton(
            tooltip: controller.isPlaying ? 'Pause' : 'Play',
            icon: controller.isPlaying ? Icons.pause : Icons.play_arrow,
            onPressed: controller.togglePlayPause,
          ),
          _ControlIconButton(
            tooltip: 'Restart',
            icon: Icons.replay,
            onPressed: controller.restart,
          ),
          _ControlIconButton(
            tooltip: 'Speed ${controller.speed.toStringAsFixed(0)}x',
            icon: Icons.speed,
            onPressed: controller.cycleSpeed,
          ),
          _ControlIconButton(
            tooltip: 'Next event',
            icon: Icons.skip_next,
            onPressed: controller.jumpToNextEvent,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: LinearProgressIndicator(
              value: controller.progress.clamp(0, 1),
              minHeight: 5,
              borderRadius: BorderRadius.circular(999),
              backgroundColor: Colors.white.withValues(alpha: 0.10),
              valueColor: const AlwaysStoppedAnimation<Color>(
                Color(0xFF7DD3FC),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ControlIconButton extends StatelessWidget {
  const _ControlIconButton({
    required this.tooltip,
    required this.icon,
    required this.onPressed,
  });

  final String tooltip;
  final IconData icon;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: tooltip,
      child: IconButton(
        onPressed: onPressed,
        icon: Icon(icon, size: 18),
        color: Colors.white,
        style: IconButton.styleFrom(
          backgroundColor: Colors.white.withValues(alpha: 0.08),
          fixedSize: const Size.square(34),
          minimumSize: const Size.square(34),
          padding: EdgeInsets.zero,
        ),
      ),
    );
  }
}

class _MatchViewerLoading extends StatelessWidget {
  const _MatchViewerLoading();

  @override
  Widget build(BuildContext context) {
    return const SafeArea(
      child: Padding(
        padding: EdgeInsets.all(20),
        child: GteStatePanel(
          eyebrow: 'MATCHDAY',
          title: 'Loading 2D match',
          message: 'Preparing the pitch, squads, ball, and commentary.',
          icon: Icons.sports_soccer,
          accentColor: GteShellTheme.accentArena,
          isLoading: true,
        ),
      ),
    );
  }
}

class _MatchViewerError extends StatelessWidget {
  const _MatchViewerError({
    required this.onReload,
    this.message = 'Unable to load the 2D match timeline right now.',
  });

  final VoidCallback onReload;
  final String message;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: GteStatePanel(
          title: 'Match unavailable',
          message: message,
          icon: Icons.warning_amber_outlined,
          actionLabel: 'Retry',
          onAction: onReload,
        ),
      ),
    );
  }
}

String _formatPlaybackClock(double seconds) {
  final int totalSeconds = math.max(0, seconds.floor());
  final int minutes = totalSeconds ~/ 60;
  final int remainder = totalSeconds % 60;
  return '${minutes.toString().padLeft(2, '0')}:${remainder.toString().padLeft(2, '0')}';
}

String _commentaryFor({
  required MatchEvent? activeEvent,
  required MatchTimelineFrame frame,
}) {
  final String? commentary = activeEvent?.commentary.trim();
  if (commentary != null && commentary.isNotEmpty) {
    return commentary;
  }
  final String? banner = frame.eventBanner?.trim();
  if (banner != null && banner.isNotEmpty) {
    return banner;
  }
  return 'The match is settling into shape.';
}
