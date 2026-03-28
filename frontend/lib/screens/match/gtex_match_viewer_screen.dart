import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';
import 'package:gte_frontend/controllers/match_3d_timeline_controller.dart';
import 'package:gte_frontend/data/live_match_fixtures.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_event.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/models/match_viewer_presentation.dart';
import 'package:gte_frontend/services/match_3d_bridge.dart';
import 'package:gte_frontend/services/match_3d_monetization_service.dart';
import 'package:gte_frontend/services/match_broadcast_presentation.dart';
import 'package:gte_frontend/services/match_viewer_mapper.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/match/broadcast_overlays.dart';
import 'package:gte_frontend/widgets/match/event_ticker_widget.dart';
import 'package:gte_frontend/widgets/match/pitch_2d_widget.dart';
import 'package:gte_frontend/widgets/match/scoreboard_widget.dart';
import 'package:gte_frontend/widgets/match_3d/gtex_3d_scene.dart';
import 'package:gte_frontend/widgets/match_3d/monetization/gifting_overlay.dart';
import 'package:gte_frontend/widgets/match_3d/monetization/match_3d_upgrade_prompt.dart';
import 'package:gte_frontend/widgets/match_3d/monetization/premium_controls.dart';

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
    this.viewStateLoader,
    this.continuationLoader,
    this.renderMode = RenderMode.twoD,
    this.isSpectator = false,
    this.isMajorMatch = false,
    this.entitlement,
    this.monetizationService,
    this.onPurchaseIntent,
    this.tournamentBoostPrice,
    this.titleOverride,
    this.engineBridge,
  });

  final CompetitionSummary competition;
  final String matchKey;
  final LiveMatchSnapshot? fallbackSnapshot;
  final bool preferFallback;
  final MatchViewerPresentationMode presentationMode;
  final MatchViewStateLoader? viewStateLoader;
  final MatchViewContinuationLoader? continuationLoader;
  final RenderMode renderMode;
  final bool isSpectator;
  final bool isMajorMatch;
  final Match3dUserEntitlement? entitlement;
  final Match3dMonetizationService? monetizationService;
  final Match3dPurchaseIntentHandler? onPurchaseIntent;
  final double? tournamentBoostPrice;
  final String? titleOverride;
  final Match3DBridge? engineBridge;

  @override
  State<GtexMatchViewerScreen> createState() => _GtexMatchViewerScreenState();
}

class _GtexMatchViewerScreenState extends State<GtexMatchViewerScreen>
    with TickerProviderStateMixin, WidgetsBindingObserver {
  static const Duration _overlayBurstWindow = Duration(seconds: 10);
  static const int _maxRenderedOverlayBurstsPerWindow = 3;

  late Future<MatchViewState> _viewStateFuture;
  Match3dTimelineController? _controller;
  late Match3dMonetizationService _monetization;
  late final bool _ownsMonetization;

  final List<Match3dOverlayBurst> _overlayBursts = <Match3dOverlayBurst>[];
  final List<DateTime> _overlayBurstTimestamps = <DateTime>[];
  final List<Duration> _recentFrameSpans = <Duration>[];
  final Set<Timer> _overlayTimers = <Timer>{};

  bool _performanceSafe = true;
  bool _performanceNoticeShown = false;
  bool _loadingContinuation = false;
  bool _continuationRetryScheduled = false;
  bool _continuationNeedsUserRetry = false;
  bool _spectatorReactionsMuted = false;
  bool _resumePlaybackOnAppResume = false;
  int _overlayBurstOverflowCount = 0;
  double? _pendingResumePositionSeconds;
  Timer? _continuationRetryTimer;
  String? _pendingContinuationToken;
  double? _pendingContinuationResumeSeconds;

  bool get _broadcastMode =>
      widget.presentationMode == MatchViewerPresentationMode.broadcast;

  bool get _canLoadContinuation =>
      widget.continuationLoader != null || widget.viewStateLoader == null;

  MatchViewContinuationLoader get _continuationLoader =>
      widget.continuationLoader ?? MatchViewerMapper.loadContinuation;

  @override
  void initState() {
    super.initState();
    _viewStateFuture = _load();
    WidgetsBinding.instance.addObserver(this);
    _ownsMonetization = widget.monetizationService == null;
    _monetization =
        widget.monetizationService ??
        Match3dMonetizationService(
          entitlement: widget.entitlement,
          initialRenderMode: widget.renderMode,
          onPurchaseIntent: widget.onPurchaseIntent,
          tournamentBoostPrice: widget.tournamentBoostPrice,
        );
    SchedulerBinding.instance.addTimingsCallback(_handleFrameTimings);
  }

  @override
  void didUpdateWidget(covariant GtexMatchViewerScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (_sourceConfigChanged(oldWidget)) {
      _reload();
    }
    if (_ownsMonetization) {
      if (oldWidget.entitlement != widget.entitlement) {
        _monetization.updateEntitlement(widget.entitlement);
      }
      if (oldWidget.renderMode != widget.renderMode) {
        _monetization.selectRenderMode(widget.renderMode);
      }
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    SchedulerBinding.instance.removeTimingsCallback(_handleFrameTimings);
    _cancelOverlayTimers();
    _cancelContinuationRetry();
    _controller?.removeListener(_handleControllerTick);
    _controller?.dispose();
    if (_ownsMonetization) {
      _monetization.dispose();
    }
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    final Match3dTimelineController? controller = _controller;
    if (controller == null) {
      return;
    }
    if (state == AppLifecycleState.resumed) {
      if (_resumePlaybackOnAppResume) {
        _resumePlaybackOnAppResume = false;
        controller.play();
      }
      return;
    }
    _resumePlaybackOnAppResume = controller.isPlaying;
    if (_resumePlaybackOnAppResume) {
      controller.pause();
    }
  }

  Future<MatchViewState> _load() {
    if (widget.viewStateLoader != null) {
      return widget.viewStateLoader!();
    }
    return MatchViewerMapper.load(
      competition: widget.competition,
      matchKey: widget.matchKey,
      fallbackSnapshot: widget.fallbackSnapshot,
      preferFallback: widget.preferFallback,
    );
  }

  void _reload() {
    _controller?.removeListener(_handleControllerTick);
    _controller?.dispose();
    _controller = null;
    _cancelOverlayTimers();
    _cancelContinuationRetry();
    _overlayBursts.clear();
    _overlayBurstTimestamps.clear();
    _recentFrameSpans.clear();
    _performanceSafe = true;
    _performanceNoticeShown = false;
    _loadingContinuation = false;
    _continuationRetryScheduled = false;
    _continuationNeedsUserRetry = false;
    _overlayBurstOverflowCount = 0;
    _pendingResumePositionSeconds = null;
    setState(() {
      _viewStateFuture = _load();
    });
  }

  bool _sourceConfigChanged(GtexMatchViewerScreen oldWidget) {
    return oldWidget.competition != widget.competition ||
        oldWidget.matchKey != widget.matchKey ||
        oldWidget.fallbackSnapshot != widget.fallbackSnapshot ||
        oldWidget.preferFallback != widget.preferFallback ||
        oldWidget.presentationMode != widget.presentationMode ||
        oldWidget.viewStateLoader != widget.viewStateLoader ||
        oldWidget.continuationLoader != widget.continuationLoader;
  }

  Match3dTimelineController _ensureController(MatchViewState viewState) {
    final Match3dTimelineController? existing = _controller;
    if (existing != null &&
        _canReuseController(existing.viewState, viewState)) {
      return existing;
    }
    existing?.removeListener(_handleControllerTick);
    existing?.dispose();
    final Match3dTimelineController created = Match3dTimelineController(
      vsync: this,
      viewState: viewState,
      autoplay: true,
    );
    final double? pendingResumePositionSeconds = _pendingResumePositionSeconds;
    if (pendingResumePositionSeconds != null) {
      created.seekToSeconds(pendingResumePositionSeconds);
      created.play();
      _pendingResumePositionSeconds = null;
    }
    created.addListener(_handleControllerTick);
    _controller = created;
    return created;
  }

  bool _canReuseController(MatchViewState current, MatchViewState next) {
    return current.matchId == next.matchId &&
        current.durationSeconds == next.durationSeconds &&
        current.segmentEndSeconds == next.segmentEndSeconds &&
        current.hasMoreSegments == next.hasMoreSegments &&
        current.nextSegmentToken == next.nextSegmentToken;
  }

  void _handleFrameTimings(List<FrameTiming> timings) {
    if (!mounted || _monetization.selectedRenderMode != RenderMode.threeD) {
      _recentFrameSpans.clear();
      return;
    }
    for (final FrameTiming timing in timings) {
      _recentFrameSpans.add(timing.totalSpan);
    }
    while (_recentFrameSpans.length > 8) {
      _recentFrameSpans.removeAt(0);
    }
    if (_recentFrameSpans.length < 6 || !_performanceSafe) {
      return;
    }
    final double averageMs =
        _recentFrameSpans.fold<double>(
          0,
          (double sum, Duration span) => sum + (span.inMicroseconds / 1000),
        ) /
        _recentFrameSpans.length;
    if (averageMs <= 34) {
      return;
    }
    _monetization.fallbackToTwoD(reason: Match3dFailureReason.performanceDrop);
    if (!mounted) {
      return;
    }
    setState(() {
      _performanceSafe = false;
    });
    if (_performanceNoticeShown) {
      return;
    }
    _performanceNoticeShown = true;
    ScaffoldMessenger.maybeOf(context)?.showSnackBar(
      const SnackBar(
        content: Text('Performance dipped, so playback fell back to 2D.'),
      ),
    );
  }

  Match3dMatchContext _buildMatchContext(MatchViewState viewState) {
    return Match3dMatchContext(
      matchId: viewState.matchId,
      competitionId: widget.competition.id,
      isFinal: viewState.lastFrame.phase == MatchViewerPhase.fulltime,
      isMajorMatch: widget.isMajorMatch,
      isSpectator: widget.isSpectator,
      presentationMode: widget.presentationMode,
      performanceSafe: _performanceSafe,
    );
  }

  void _scheduleBurst(Match3dOverlayBurst burst) {
    final DateTime now = DateTime.now();
    _pruneBurstWindow(now);
    if (_overlayBurstTimestamps.length >= _maxRenderedOverlayBurstsPerWindow) {
      setState(() {
        _overlayBurstOverflowCount += 1;
      });
      _scheduleOverlayTimer(_overlayBurstWindow, () {
        if (!mounted) {
          return;
        }
        setState(() {
          _pruneBurstWindow(DateTime.now());
        });
      });
      return;
    }
    _overlayBurstTimestamps.add(now);
    setState(() {
      _overlayBursts.insert(0, burst);
    });
    _scheduleOverlayTimer(const Duration(milliseconds: 1800), () {
      if (!mounted) {
        return;
      }
      setState(() {
        _overlayBursts.removeWhere(
          (Match3dOverlayBurst item) => item.id == burst.id,
        );
      });
    });
    _scheduleOverlayTimer(_overlayBurstWindow, () {
      if (!mounted) {
        return;
      }
      setState(() {
        _pruneBurstWindow(DateTime.now());
      });
    });
  }

  void _scheduleOverlayTimer(Duration delay, VoidCallback callback) {
    late final Timer timer;
    timer = Timer(delay, () {
      _overlayTimers.remove(timer);
      callback();
    });
    _overlayTimers.add(timer);
  }

  void _cancelOverlayTimers() {
    for (final Timer timer in _overlayTimers) {
      timer.cancel();
    }
    _overlayTimers.clear();
  }

  void _pruneBurstWindow(DateTime now) {
    _overlayBurstTimestamps.removeWhere(
      (DateTime timestamp) => now.difference(timestamp) >= _overlayBurstWindow,
    );
    if (_overlayBurstTimestamps.isEmpty) {
      _overlayBurstOverflowCount = 0;
    }
  }

  void _showActionResult(Match3dActionResult result) {
    final Match3dOverlayBurst? burst = result.overlayBurst;
    if (burst != null) {
      _scheduleBurst(burst);
    }
    final String? message = result.message;
    if (message == null || message.trim().isEmpty) {
      return;
    }
    ScaffoldMessenger.maybeOf(
      context,
    )?.showSnackBar(SnackBar(content: Text(message)));
  }

  void _handleControllerTick() {
    final Match3dTimelineController? controller = _controller;
    if (!mounted ||
        controller == null ||
        _loadingContinuation ||
        _continuationRetryScheduled ||
        !_canLoadContinuation) {
      return;
    }
    final MatchViewState viewState = controller.viewState;
    final String? continuationToken = viewState.nextSegmentToken;
    if (!viewState.hasMoreSegments ||
        continuationToken == null ||
        continuationToken.isEmpty ||
        controller.positionSeconds + 0.05 < viewState.durationSeconds) {
      return;
    }
    _requestContinuation(
      continuationToken: continuationToken,
      resumeFromSeconds: controller.positionSeconds,
    );
  }

  Future<void> _requestContinuation({
    required String continuationToken,
    required double resumeFromSeconds,
    bool allowAutoRetry = true,
  }) async {
    if (_loadingContinuation) {
      return;
    }
    _continuationRetryTimer?.cancel();
    _continuationRetryTimer = null;
    setState(() {
      _loadingContinuation = true;
      _continuationRetryScheduled = false;
      _continuationNeedsUserRetry = false;
      _pendingContinuationToken = continuationToken;
      _pendingContinuationResumeSeconds = resumeFromSeconds;
    });
    try {
      final MatchViewState continued = await _continuationLoader(
        matchKey: widget.matchKey,
        continuationToken: continuationToken,
      );
      if (!mounted) {
        return;
      }
      _controller?.removeListener(_handleControllerTick);
      _controller?.dispose();
      _controller = null;
      setState(() {
        _pendingResumePositionSeconds = resumeFromSeconds;
        _loadingContinuation = false;
        _pendingContinuationToken = null;
        _pendingContinuationResumeSeconds = null;
        _viewStateFuture = Future<MatchViewState>.value(continued);
      });
    } catch (_) {
      if (!mounted) {
        return;
      }
      if (allowAutoRetry) {
        setState(() {
          _loadingContinuation = false;
        });
        _scheduleContinuationRetry(
          continuationToken: continuationToken,
          resumeFromSeconds: resumeFromSeconds,
        );
        ScaffoldMessenger.maybeOf(context)?.showSnackBar(
          const SnackBar(
            content: Text('Next segment delayed. Retrying playback once.'),
          ),
        );
        return;
      }
      setState(() {
        _loadingContinuation = false;
        _continuationRetryScheduled = false;
        _continuationNeedsUserRetry = true;
      });
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(
        const SnackBar(
          content: Text('Unable to continue match playback right now.'),
        ),
      );
    }
  }

  void _scheduleContinuationRetry({
    required String continuationToken,
    required double resumeFromSeconds,
  }) {
    _continuationRetryTimer?.cancel();
    setState(() {
      _continuationRetryScheduled = true;
      _continuationNeedsUserRetry = false;
      _pendingContinuationToken = continuationToken;
      _pendingContinuationResumeSeconds = resumeFromSeconds;
    });
    _continuationRetryTimer = Timer(const Duration(seconds: 1), () {
      _continuationRetryTimer = null;
      if (!mounted) {
        return;
      }
      final String? pendingToken = _pendingContinuationToken;
      final double? pendingResumeSeconds = _pendingContinuationResumeSeconds;
      if (pendingToken == null || pendingResumeSeconds == null) {
        setState(() {
          _continuationRetryScheduled = false;
        });
        return;
      }
      unawaited(
        _requestContinuation(
          continuationToken: pendingToken,
          resumeFromSeconds: pendingResumeSeconds,
          allowAutoRetry: false,
        ),
      );
    });
  }

  void _cancelContinuationRetry() {
    _continuationRetryTimer?.cancel();
    _continuationRetryTimer = null;
    _continuationRetryScheduled = false;
    _continuationNeedsUserRetry = false;
    _pendingContinuationToken = null;
    _pendingContinuationResumeSeconds = null;
  }

  void _retryContinuationNow() {
    final String? continuationToken = _pendingContinuationToken;
    final double? resumeFromSeconds = _pendingContinuationResumeSeconds;
    if (continuationToken == null ||
        resumeFromSeconds == null ||
        _loadingContinuation) {
      return;
    }
    _continuationRetryTimer?.cancel();
    _continuationRetryTimer = null;
    unawaited(
      _requestContinuation(
        continuationToken: continuationToken,
        resumeFromSeconds: resumeFromSeconds,
        allowAutoRetry: false,
      ),
    );
  }

  Future<void> _openUpgradePrompt(
    Match3dMatchContext matchContext, {
    required RenderMode targetMode,
  }) async {
    final Match3dUpgradeAction? action = await Match3dUpgradePrompt.show(
      context,
      matchUnlockPrice: Match3dMonetizationService.threeDUnlockPrice,
      tournamentBoostPrice: _monetization.tournamentBoostPrice,
    );
    if (!mounted) {
      return;
    }
    switch (action) {
      case Match3dUpgradeAction.unlock3d:
        final Match3dActionResult result = await _monetization
            .unlockThreeDForMatch(matchContext);
        _showActionResult(result);
        if (result.success) {
          _monetization.selectRenderMode(targetMode);
        }
      case Match3dUpgradeAction.upgradeTournament:
        final Match3dActionResult result = await _monetization
            .upgradeTournamentExperience(matchContext);
        _showActionResult(result);
        if (result.success) {
          _monetization.selectRenderMode(RenderMode.auto);
        }
      case Match3dUpgradeAction.continueIn2d:
      case null:
        _monetization.selectRenderMode(RenderMode.twoD);
    }
  }

  Future<void> _handleRenderModeSelected(
    RenderMode mode,
    Match3dMatchContext matchContext,
  ) async {
    if (mode == RenderMode.twoD) {
      _monetization.selectRenderMode(RenderMode.twoD);
      return;
    }
    _monetization.selectRenderMode(mode);
    if (_monetization.needsThreeDUnlock(matchContext)) {
      await _openUpgradePrompt(matchContext, targetMode: mode);
    }
  }

  Future<void> _handleUnlockInteraction(
    Match3dPaidInteraction interaction,
    Match3dMatchContext matchContext,
  ) async {
    final Match3dActionResult result = await _monetization.unlockInteraction(
      interaction,
      matchContext,
    );
    _showActionResult(result);
    if (result.success &&
        interaction == Match3dPaidInteraction.alternateCameraAngle) {
      _monetization.setCameraPreset(Match3dCameraPreset.sideline, matchContext);
    }
  }

  Future<void> _handleSendGift(
    double amount,
    Match3dMatchContext matchContext,
  ) async {
    final Match3dActionResult result = await _monetization.sendCoinGift(
      amount,
      matchContext,
    );
    _showActionResult(result);
  }

  Future<void> _handleSendReaction(
    Match3dReaction reaction,
    Match3dMatchContext matchContext,
  ) async {
    final Match3dActionResult result = _monetization.sendReaction(
      reaction,
      matchContext,
    );
    _showActionResult(result);
  }

  void _syncControllerSpeeds(
    Match3dTimelineController controller,
    Match3dMatchContext matchContext,
  ) {
    final List<double> desired = _monetization.speedOptionsFor(matchContext);
    if (_listEquals(desired, controller.speedOptions)) {
      return;
    }
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) {
        return;
      }
      controller.updateSpeedOptions(desired);
    });
  }

  @override
  Widget build(BuildContext context) {
    final String title =
        widget.titleOverride ??
        (_broadcastMode ? 'Live broadcast' : '2D Match Viewer');
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: Text(title),
          actions: <Widget>[
            IconButton(
              tooltip: _broadcastMode ? 'Reload broadcast' : 'Reload replay',
              onPressed: _reload,
              icon: const Icon(Icons.refresh),
            ),
          ],
        ),
        body: FutureBuilder<MatchViewState>(
          future: _viewStateFuture,
          builder: (
            BuildContext context,
            AsyncSnapshot<MatchViewState> snapshot,
          ) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return Padding(
                padding: const EdgeInsets.all(20),
                child: GteStatePanel(
                  eyebrow: _broadcastMode ? 'LIVE BROADCAST' : 'MATCH VIEWER',
                  title:
                      _broadcastMode
                          ? 'Loading spectator feed'
                          : 'Loading replay viewer',
                  message:
                      _broadcastMode
                          ? 'Preparing the match feed, commentary overlays, and replay cues.'
                          : 'Preparing the playback timeline, scoreboard, and replay controls.',
                  icon:
                      _broadcastMode
                          ? Icons.live_tv_outlined
                          : Icons.sports_soccer,
                  accentColor: GteShellTheme.accentArena,
                  isLoading: true,
                ),
              );
            }
            if (!snapshot.hasData) {
              return Padding(
                padding: const EdgeInsets.all(20),
                child: GteStatePanel(
                  title:
                      _broadcastMode
                          ? 'Broadcast unavailable'
                          : 'Replay unavailable',
                  message:
                      _broadcastMode
                          ? 'Unable to load the spectator playback right now.'
                          : 'Unable to load the serialized replay timeline right now.',
                  icon: Icons.warning_amber_outlined,
                  actionLabel: 'Retry',
                  onAction: _reload,
                ),
              );
            }

            final MatchViewState viewState = snapshot.data!;
            if (viewState.frames.isEmpty) {
              return Padding(
                padding: const EdgeInsets.all(20),
                child: GteStatePanel(
                  title:
                      _broadcastMode
                          ? 'Broadcast feed incomplete'
                          : 'Replay data incomplete',
                  message:
                      _broadcastMode
                          ? 'The signed spectator timeline did not include any playback frames.'
                          : 'The replay timeline did not include any playback frames.',
                  icon: Icons.warning_amber_outlined,
                  actionLabel: 'Retry',
                  onAction: _reload,
                ),
              );
            }
            final Match3dTimelineController controller = _ensureController(
              viewState,
            );
            final Match3dMatchContext matchContext = _buildMatchContext(
              viewState,
            );

            return AnimatedBuilder(
              animation: Listenable.merge(<Listenable>[
                controller,
                _monetization,
              ]),
              builder: (BuildContext context, Widget? child) {
                _syncControllerSpeeds(controller, matchContext);
                final RenderMode activeRenderMode = _monetization
                    .effectiveRenderModeFor(matchContext);
                final MatchEvent? activeEvent = controller.activeEvent;
                final MatchBroadcastPresentationState presentation =
                    MatchBroadcastPresentationBuilder.build(
                      viewState: viewState,
                      controller: controller,
                    );
                final Widget viewer =
                    _broadcastMode
                        ? _BroadcastViewer(
                          controller: controller,
                          viewState: viewState,
                          matchContext: matchContext,
                          monetization: _monetization,
                          activeRenderMode: activeRenderMode,
                          activeEvent: activeEvent,
                          engineBridge: widget.engineBridge,
                          overlayBursts: _overlayBursts,
                          spectatorReactionsMuted: _spectatorReactionsMuted,
                          onToggleSpectatorMute: () {
                            setState(() {
                              _spectatorReactionsMuted =
                                  !_spectatorReactionsMuted;
                            });
                          },
                          onRenderModeSelected:
                              (RenderMode mode) =>
                                  _handleRenderModeSelected(mode, matchContext),
                          onCameraPresetSelected:
                              (Match3dCameraPreset preset) => _monetization
                                  .setCameraPreset(preset, matchContext),
                          onUnlockSlowMotion:
                              () => _handleUnlockInteraction(
                                Match3dPaidInteraction.slowMotionReplay,
                                matchContext,
                              ),
                          onUnlockAlternateCamera:
                              () => _handleUnlockInteraction(
                                Match3dPaidInteraction.alternateCameraAngle,
                                matchContext,
                              ),
                          onUnlockHighlightAttack:
                              () => _handleUnlockInteraction(
                                Match3dPaidInteraction.highlightNextAttack,
                                matchContext,
                              ),
                          onUpgradeTournament:
                              _monetization.tournamentBoostPrice == null
                                  ? null
                                  : () => _openUpgradePrompt(
                                    matchContext,
                                    targetMode: RenderMode.auto,
                                  ),
                          onSendGift:
                              (double amount) =>
                                  _handleSendGift(amount, matchContext),
                          onSendReaction:
                              (Match3dReaction reaction) =>
                                  _handleSendReaction(reaction, matchContext),
                          presentation: presentation,
                        )
                        : _ReplayViewer(
                          controller: controller,
                          viewState: viewState,
                          matchContext: matchContext,
                          monetization: _monetization,
                          activeRenderMode: activeRenderMode,
                          activeEvent: activeEvent,
                          engineBridge: widget.engineBridge,
                          overlayBursts: _overlayBursts,
                          overlayOverflowCount: _overlayBurstOverflowCount,
                          spectatorReactionsMuted: _spectatorReactionsMuted,
                          onToggleSpectatorMute: () {
                            setState(() {
                              _spectatorReactionsMuted =
                                  !_spectatorReactionsMuted;
                            });
                          },
                          onRenderModeSelected:
                              (RenderMode mode) =>
                                  _handleRenderModeSelected(mode, matchContext),
                          onCameraPresetSelected:
                              (Match3dCameraPreset preset) => _monetization
                                  .setCameraPreset(preset, matchContext),
                          onUnlockSlowMotion:
                              () => _handleUnlockInteraction(
                                Match3dPaidInteraction.slowMotionReplay,
                                matchContext,
                              ),
                          onUnlockAlternateCamera:
                              () => _handleUnlockInteraction(
                                Match3dPaidInteraction.alternateCameraAngle,
                                matchContext,
                              ),
                          onUnlockHighlightAttack:
                              () => _handleUnlockInteraction(
                                Match3dPaidInteraction.highlightNextAttack,
                                matchContext,
                              ),
                          onUpgradeTournament:
                              _monetization.tournamentBoostPrice == null
                                  ? null
                                  : () => _openUpgradePrompt(
                                    matchContext,
                                    targetMode: RenderMode.auto,
                                  ),
                          onSendGift:
                              (double amount) =>
                                  _handleSendGift(amount, matchContext),
                          onSendReaction:
                              (Match3dReaction reaction) =>
                                  _handleSendReaction(reaction, matchContext),
                        );
                final String? continuationStatus = _continuationStatusMessage();
                if (continuationStatus == null) {
                  return viewer;
                }
                return Stack(
                  fit: StackFit.expand,
                  children: <Widget>[
                    viewer,
                    Positioned(
                      left: 16,
                      right: 16,
                      bottom: 16,
                      child: SafeArea(
                        top: false,
                        child: _ContinuationStatusBanner(
                          message: continuationStatus,
                          loading:
                              _loadingContinuation ||
                              _continuationRetryScheduled,
                          actionLabel:
                              _continuationNeedsUserRetry ? 'Retry now' : null,
                          onAction:
                              _continuationNeedsUserRetry
                                  ? _retryContinuationNow
                                  : null,
                        ),
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

  String? _continuationStatusMessage() {
    if (_loadingContinuation) {
      return _broadcastMode
          ? 'Loading the next signed broadcast segment...'
          : 'Loading the next signed replay segment...';
    }
    if (_continuationRetryScheduled) {
      return 'Segment delayed. Retrying playback...';
    }
    if (_continuationNeedsUserRetry) {
      return 'Unable to load the next signed segment.';
    }
    return null;
  }
}

class _ReplayViewer extends StatelessWidget {
  const _ReplayViewer({
    required this.controller,
    required this.viewState,
    required this.matchContext,
    required this.monetization,
    required this.activeRenderMode,
    required this.activeEvent,
    required this.engineBridge,
    required this.overlayBursts,
    required this.overlayOverflowCount,
    required this.spectatorReactionsMuted,
    required this.onToggleSpectatorMute,
    required this.onRenderModeSelected,
    required this.onCameraPresetSelected,
    required this.onUnlockSlowMotion,
    required this.onUnlockAlternateCamera,
    required this.onUnlockHighlightAttack,
    required this.onUpgradeTournament,
    required this.onSendGift,
    required this.onSendReaction,
  });

  final Match3dTimelineController controller;
  final MatchViewState viewState;
  final Match3dMatchContext matchContext;
  final Match3dMonetizationService monetization;
  final RenderMode activeRenderMode;
  final MatchEvent? activeEvent;
  final Match3DBridge? engineBridge;
  final List<Match3dOverlayBurst> overlayBursts;
  final int overlayOverflowCount;
  final bool spectatorReactionsMuted;
  final VoidCallback onToggleSpectatorMute;
  final ValueChanged<RenderMode> onRenderModeSelected;
  final ValueChanged<Match3dCameraPreset> onCameraPresetSelected;
  final VoidCallback onUnlockSlowMotion;
  final VoidCallback onUnlockAlternateCamera;
  final VoidCallback onUnlockHighlightAttack;
  final VoidCallback? onUpgradeTournament;
  final Future<void> Function(double amount) onSendGift;
  final Future<void> Function(Match3dReaction reaction) onSendReaction;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final bool wide = constraints.maxWidth >= 1040;
        final bool compactHeader = constraints.maxWidth < 860;
        final bool showPremiumControls = wide;
        final Widget field = Padding(
          padding: const EdgeInsets.fromLTRB(18, 18, 18, 0),
          child: Stack(
            children: <Widget>[
              Positioned.fill(
                child: AnimatedSwitcher(
                  duration: const Duration(milliseconds: 260),
                  child: _RenderSurface(
                    key: ValueKey<RenderMode>(activeRenderMode),
                    controller: controller,
                    viewState: viewState,
                    renderMode: activeRenderMode,
                    cameraPreset: monetization.cameraPreset,
                    activeEvent: controller.activeEvent,
                    engineBridge: engineBridge,
                    broadcastMode: false,
                    presentation: null,
                  ),
                ),
              ),
              Positioned(
                top: 12,
                left: 12,
                right: 12,
                child:
                    compactHeader
                        ? Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: <Widget>[
                            ScoreboardWidget(
                              viewState: viewState,
                              frame: controller.displayFrame,
                              activeEvent: activeEvent,
                            ),
                            const SizedBox(height: 10),
                            Align(
                              alignment: Alignment.topRight,
                              child: ConstrainedBox(
                                constraints: const BoxConstraints(
                                  maxWidth: 320,
                                ),
                                child: EventTickerWidget(event: activeEvent),
                              ),
                            ),
                          ],
                        )
                        : Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Expanded(
                              child: Align(
                                alignment: Alignment.topLeft,
                                child: ScoreboardWidget(
                                  viewState: viewState,
                                  frame: controller.displayFrame,
                                  activeEvent: activeEvent,
                                ),
                              ),
                            ),
                            const SizedBox(width: 12),
                            Flexible(
                              child: Align(
                                alignment: Alignment.topRight,
                                child: ConstrainedBox(
                                  constraints: const BoxConstraints(
                                    maxWidth: 320,
                                  ),
                                  child: EventTickerWidget(event: activeEvent),
                                ),
                              ),
                            ),
                          ],
                        ),
              ),
              Positioned.fill(
                child: IgnorePointer(
                  child: _PlaybackCueOverlay(
                    frame: controller.displayFrame,
                    event: activeEvent,
                    autoPaused: controller.isAutoPaused,
                  ),
                ),
              ),
              Positioned.fill(
                child: GiftingOverlay(
                  activeBursts:
                      matchContext.isSpectator && spectatorReactionsMuted
                          ? const <Match3dOverlayBurst>[]
                          : overlayBursts,
                  overflowCount:
                      spectatorReactionsMuted ? 0 : overlayOverflowCount,
                  availableCoins: monetization.availableCoinBalance,
                  onSendGift: onSendGift,
                  onSendReaction: onSendReaction,
                ),
              ),
            ],
          ),
        );
        final Widget controls =
            showPremiumControls
                ? Padding(
                  padding: const EdgeInsets.fromLTRB(18, 14, 18, 0),
                  child: PremiumControls(
                    entitlement: monetization.effectiveEntitlement,
                    selectedRenderMode: monetization.selectedRenderMode,
                    effectiveRenderMode: activeRenderMode,
                    availableCoins: monetization.availableCoinBalance,
                    cameraPreset: monetization.cameraPreset,
                    canUsePremiumCamera: monetization.canUsePremiumCamera(
                      matchContext,
                    ),
                    canUseFastReplay: monetization.canUseFastReplay(
                      matchContext,
                    ),
                    onRenderModeSelected: onRenderModeSelected,
                    onCameraPresetSelected: onCameraPresetSelected,
                    onUnlockSlowMotion: onUnlockSlowMotion,
                    onUnlockAlternateCamera: onUnlockAlternateCamera,
                    onUnlockHighlightAttack: onUnlockHighlightAttack,
                    onUpgradeTournament: onUpgradeTournament,
                  ),
                )
                : const SizedBox.shrink();
        final Widget footer =
            matchContext.isSpectator
                ? _SpectatorStatusBar(
                  reactionsMuted: spectatorReactionsMuted,
                  viewerOnly: false,
                  onToggleMute: onToggleSpectatorMute,
                )
                : _ControlBar(controller: controller);
        final Widget viewerPanel = Column(
          children: <Widget>[Expanded(child: field), controls, footer],
        );

        final Widget rail = Padding(
          padding: const EdgeInsets.fromLTRB(0, 18, 18, 18),
          child: _EventRail(controller: controller, viewState: viewState),
        );

        if (wide) {
          return Row(
            children: <Widget>[
              Expanded(flex: 3, child: viewerPanel),
              SizedBox(width: 320, child: rail),
            ],
          );
        }

        final double fieldHeight = (constraints.maxHeight * 0.4).clamp(
          180.0,
          228.0,
        );
        return Column(
          children: <Widget>[
            SizedBox(height: fieldHeight, child: field),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.only(bottom: 18),
                child: Column(
                  children: <Widget>[
                    footer,
                    if (showPremiumControls) controls,
                    Padding(
                      padding: const EdgeInsets.fromLTRB(18, 0, 18, 0),
                      child: _EventRail(
                        controller: controller,
                        viewState: viewState,
                        shrinkWrap: true,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        );
      },
    );
  }
}

class _BroadcastViewer extends StatelessWidget {
  const _BroadcastViewer({
    required this.controller,
    required this.viewState,
    required this.matchContext,
    required this.monetization,
    required this.activeRenderMode,
    required this.activeEvent,
    required this.engineBridge,
    required this.overlayBursts,
    required this.spectatorReactionsMuted,
    required this.onToggleSpectatorMute,
    required this.onRenderModeSelected,
    required this.onCameraPresetSelected,
    required this.onUnlockSlowMotion,
    required this.onUnlockAlternateCamera,
    required this.onUnlockHighlightAttack,
    required this.onUpgradeTournament,
    required this.onSendGift,
    required this.onSendReaction,
    required this.presentation,
  });

  final Match3dTimelineController controller;
  final MatchViewState viewState;
  final Match3dMatchContext matchContext;
  final Match3dMonetizationService monetization;
  final RenderMode activeRenderMode;
  final MatchEvent? activeEvent;
  final Match3DBridge? engineBridge;
  final List<Match3dOverlayBurst> overlayBursts;
  final bool spectatorReactionsMuted;
  final VoidCallback onToggleSpectatorMute;
  final ValueChanged<RenderMode> onRenderModeSelected;
  final ValueChanged<Match3dCameraPreset> onCameraPresetSelected;
  final VoidCallback onUnlockSlowMotion;
  final VoidCallback onUnlockAlternateCamera;
  final VoidCallback onUnlockHighlightAttack;
  final VoidCallback? onUpgradeTournament;
  final Future<void> Function(double amount) onSendGift;
  final Future<void> Function(Match3dReaction reaction) onSendReaction;
  final MatchBroadcastPresentationState presentation;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final bool compactHeader = constraints.maxWidth < 980;
        final Widget surface = SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 18),
            child: Stack(
              children: <Widget>[
                Positioned.fill(
                  child: _RenderSurface(
                    key: const ValueKey<String>('broadcast-surface'),
                    controller: controller,
                    viewState: viewState,
                    renderMode: activeRenderMode,
                    cameraPreset:
                        activeRenderMode == RenderMode.threeD
                            ? monetization.cameraPreset
                            : Match3dCameraPreset.broadcast,
                    activeEvent: controller.activeEvent,
                    engineBridge: engineBridge,
                    broadcastMode: true,
                    presentation: presentation.pitchPresentation,
                  ),
                ),
                Positioned.fill(
                  child: BroadcastStadiumFade(
                    opacity: presentation.stadiumFadeOpacity,
                  ),
                ),
                Positioned.fill(
                  child: IgnorePointer(
                    child: DecoratedBox(
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          begin: Alignment.topCenter,
                          end: Alignment.bottomCenter,
                          colors: <Color>[
                            Colors.black.withValues(alpha: 0.34),
                            Colors.transparent,
                            Colors.black.withValues(alpha: 0.28),
                          ],
                          stops: const <double>[0, 0.42, 1],
                        ),
                      ),
                    ),
                  ),
                ),
                Positioned(
                  top: 12,
                  left: 12,
                  right: 12,
                  child: BroadcastScoreboardWidget(
                    viewState: viewState,
                    clockLabel: presentation.clockLabel,
                    homeScore: presentation.visibleHomeScore,
                    awayScore: presentation.visibleAwayScore,
                    scoreMasked: presentation.scoreMasked,
                    statusLabel: presentation.statusLabel,
                    cameraPreset: presentation.pitchPresentation.cameraPreset,
                  ),
                ),
                Positioned(
                  top: compactHeader ? 108 : 92,
                  left: 24,
                  right: 24,
                  child: Align(
                    alignment: Alignment.topCenter,
                    child: BroadcastStartingBanner(
                      opacity: presentation.startingBannerOpacity,
                    ),
                  ),
                ),
                Positioned(
                  top: compactHeader ? 176 : 166,
                  left: 24,
                  right: 24,
                  child: Align(
                    alignment: Alignment.topCenter,
                    child: BroadcastLineupBoard(
                      viewState: viewState,
                      opacity: presentation.lineupBoardOpacity,
                    ),
                  ),
                ),
                Positioned(
                  left: 12,
                  right: 12,
                  bottom: 12,
                  child: Align(
                    alignment: Alignment.bottomLeft,
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 520),
                      child: BroadcastCommentaryOverlay(
                        headline: presentation.commentaryHeadline,
                        subtitle: presentation.commentarySubtitle,
                        focusEvent: presentation.focusEvent,
                        isVarChecking: presentation.isVarChecking,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        );
        if (!matchContext.isSpectator) {
          return surface;
        }
        return Column(
          children: <Widget>[
            Expanded(child: surface),
            _SpectatorStatusBar(
              reactionsMuted: spectatorReactionsMuted,
              viewerOnly: true,
              onToggleMute: onToggleSpectatorMute,
            ),
          ],
        );
      },
    );
  }
}

class _RenderSurface extends StatelessWidget {
  const _RenderSurface({
    super.key,
    required this.controller,
    required this.viewState,
    required this.renderMode,
    required this.cameraPreset,
    required this.activeEvent,
    required this.engineBridge,
    required this.broadcastMode,
    required this.presentation,
  });

  final Match3dTimelineController controller;
  final MatchViewState viewState;
  final RenderMode renderMode;
  final Match3dCameraPreset cameraPreset;
  final MatchEvent? activeEvent;
  final Match3DBridge? engineBridge;
  final bool broadcastMode;
  final MatchPitchPresentation? presentation;

  @override
  Widget build(BuildContext context) {
    if (renderMode == RenderMode.threeD) {
      return Gtex3dScene(
        viewState: viewState,
        frame: controller.displayFrame,
        activeEvent: activeEvent,
        cameraPreset: cameraPreset,
        bridge: engineBridge,
      );
    }
    return RepaintBoundary(
      child: Pitch2dWidget(
        viewState: viewState,
        frame: controller.displayFrame,
        showFormationOverlay: !broadcastMode,
        presentation: presentation,
      ),
    );
  }
}

class _PlaybackCueOverlay extends StatelessWidget {
  const _PlaybackCueOverlay({
    required this.frame,
    required this.event,
    required this.autoPaused,
  });

  final MatchTimelineFrame frame;
  final MatchEvent? event;
  final bool autoPaused;

  @override
  Widget build(BuildContext context) {
    final bool hasOverlayText =
        frame.overlayText != null && frame.overlayText!.trim().isNotEmpty;
    final bool hasCue =
        hasOverlayText ||
        frame.flagAnimation ||
        frame.celebrationTeamId != null;
    if (!hasCue) {
      return const SizedBox.shrink();
    }
    final ThemeData theme = Theme.of(context);
    final Color accent = _overlayAccent(frame, event);
    return Stack(
      children: <Widget>[
        if (autoPaused)
          Positioned.fill(
            child: DecoratedBox(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: <Color>[
                    Colors.black.withValues(alpha: 0.22),
                    Colors.transparent,
                    Colors.black.withValues(alpha: 0.18),
                  ],
                ),
              ),
            ),
          ),
        if (frame.flagAnimation)
          Positioned(
            top: 40,
            right: 32,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(18),
                color: const Color(0xD90A1827),
                border: Border.all(color: accent.withValues(alpha: 0.72)),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  Icon(Icons.flag_outlined, color: accent, size: 20),
                  const SizedBox(width: 10),
                  Container(
                    width: 34,
                    height: 3,
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(999),
                      color: accent,
                    ),
                  ),
                ],
              ),
            ),
          ),
        if (hasOverlayText)
          Center(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 18),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(22),
                color: const Color(0xE6111C28),
                border: Border.all(color: accent.withValues(alpha: 0.78)),
                boxShadow: <BoxShadow>[
                  BoxShadow(
                    color: accent.withValues(alpha: 0.28),
                    blurRadius: 26,
                    spreadRadius: 2,
                  ),
                ],
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  Text(
                    frame.overlayText!,
                    style: theme.textTheme.headlineSmall?.copyWith(
                      color: Colors.white,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 1.4,
                    ),
                  ),
                  if (event != null) ...<Widget>[
                    const SizedBox(height: 8),
                    Text(
                      event!.bannerText,
                      textAlign: TextAlign.center,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: Colors.white70,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
      ],
    );
  }
}

class _ControlBar extends StatelessWidget {
  const _ControlBar({required this.controller});

  final Match3dTimelineController controller;

  @override
  Widget build(BuildContext context) {
    Widget buildProgressPanel() {
      return Column(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          LinearProgressIndicator(
            value: controller.progress.clamp(0, 1),
            minHeight: 7,
            borderRadius: BorderRadius.circular(999),
            backgroundColor: Colors.white.withValues(alpha: 0.08),
            valueColor: const AlwaysStoppedAnimation<Color>(
              GteShellTheme.accentArena,
            ),
          ),
          const SizedBox(height: 6),
          Align(
            alignment: Alignment.centerRight,
            child: Text(
              controller.isAutoPaused
                  ? 'Playback paused for event cue'
                  : 'Replay mode',
              style: Theme.of(
                context,
              ).textTheme.labelSmall?.copyWith(color: Colors.white70),
            ),
          ),
        ],
      );
    }

    List<Widget> buildButtons() {
      return <Widget>[
        FilledButton.icon(
          onPressed: controller.togglePlayPause,
          icon: Icon(controller.isPlaying ? Icons.pause : Icons.play_arrow),
          label: Text(controller.isPlaying ? 'Pause' : 'Play'),
        ),
        FilledButton.tonalIcon(
          onPressed: controller.restart,
          icon: const Icon(Icons.replay),
          label: const Text('Restart'),
        ),
        FilledButton.tonalIcon(
          onPressed: controller.cycleSpeed,
          icon: const Icon(Icons.speed),
          label: Text(controller.speedLabel),
        ),
        FilledButton.tonalIcon(
          onPressed: controller.jumpToNextEvent,
          icon: const Icon(Icons.skip_next),
          label: const Text('Next event'),
        ),
      ];
    }

    return Padding(
      padding: const EdgeInsets.fromLTRB(18, 12, 18, 18),
      child: LayoutBuilder(
        builder: (BuildContext context, BoxConstraints constraints) {
          final bool compact = constraints.maxWidth < 760;
          if (compact) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Wrap(spacing: 10, runSpacing: 10, children: buildButtons()),
                const SizedBox(height: 12),
                buildProgressPanel(),
              ],
            );
          }
          final List<Widget> buttons = buildButtons();
          return Row(
            children: <Widget>[
              buttons[0],
              const SizedBox(width: 10),
              buttons[1],
              const SizedBox(width: 10),
              buttons[2],
              const SizedBox(width: 10),
              buttons[3],
              const SizedBox(width: 14),
              Expanded(child: buildProgressPanel()),
            ],
          );
        },
      ),
    );
  }
}

class _SpectatorStatusBar extends StatelessWidget {
  const _SpectatorStatusBar({
    required this.reactionsMuted,
    required this.viewerOnly,
    required this.onToggleMute,
  });

  final bool reactionsMuted;
  final bool viewerOnly;
  final VoidCallback onToggleMute;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(18, 12, 18, 18),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(18),
          color: Colors.white.withValues(alpha: 0.05),
          border: Border.all(color: Colors.white.withValues(alpha: 0.09)),
        ),
        child: Row(
          children: <Widget>[
            Expanded(
              child: Text(
                viewerOnly
                    ? 'Broadcast mode stays presentation-only while reaction visibility can still be muted.'
                    : 'Spectator mode keeps playback viewer-only while gifting and camera enhancements remain available.',
              ),
            ),
            const SizedBox(width: 12),
            FilterChip(
              selected: reactionsMuted,
              onSelected: (_) => onToggleMute(),
              label: Text(
                reactionsMuted ? 'Reactions muted' : 'Mute reactions',
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ContinuationStatusBanner extends StatelessWidget {
  const _ContinuationStatusBanner({
    required this.message,
    required this.loading,
    this.actionLabel,
    this.onAction,
  });

  final String message;
  final bool loading;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(18),
          color: const Color(0xE6111E2B),
          border: Border.all(color: Colors.white.withValues(alpha: 0.14)),
          boxShadow: <BoxShadow>[
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.20),
              blurRadius: 18,
              offset: const Offset(0, 8),
            ),
          ],
        ),
        child: Row(
          children: <Widget>[
            if (loading) ...<Widget>[
              const SizedBox(
                width: 18,
                height: 18,
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
              const SizedBox(width: 12),
            ] else ...<Widget>[
              const Icon(Icons.warning_amber_rounded, color: Color(0xFFFDB022)),
              const SizedBox(width: 12),
            ],
            Expanded(
              child: Text(
                message,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            if (actionLabel != null && onAction != null) ...<Widget>[
              const SizedBox(width: 12),
              TextButton(onPressed: onAction, child: Text(actionLabel!)),
            ],
          ],
        ),
      ),
    );
  }
}

class _EventRail extends StatelessWidget {
  const _EventRail({
    required this.controller,
    required this.viewState,
    this.shrinkWrap = false,
  });

  final Match3dTimelineController controller;
  final MatchViewState viewState;
  final bool shrinkWrap;

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
            shrinkWrap: shrinkWrap,
            physics: shrinkWrap ? const NeverScrollableScrollPhysics() : null,
            padding: const EdgeInsets.all(16),
            children: <Widget>[
              Text(
                'Replay lane',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 8),
              Text(
                'Source: ${viewState.source} | Mode: ${viewState.matchMode.label} | Duration: ${viewState.durationSeconds}s | ${viewState.events.length} events',
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const SizedBox(height: 14),
              if (activeEvent != null)
                _EventTile(event: activeEvent, active: true),
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
  const _EventTile({required this.event, this.active = false});

  final MatchEvent event;
  final bool active;

  @override
  Widget build(BuildContext context) {
    final Color accent = _tileAccent(event.type);
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        color:
            active
                ? accent.withValues(alpha: 0.16)
                : Colors.white.withValues(alpha: 0.04),
        border: Border.all(
          color:
              active
                  ? accent.withValues(alpha: 0.68)
                  : Colors.white.withValues(alpha: 0.08),
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: accent.withValues(alpha: 0.16),
            ),
            child: Icon(event.icon, color: accent, size: 18),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                Text(
                  event.bannerText,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  '${event.clockLabel}  ${event.commentary}',
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(
                    context,
                  ).textTheme.bodySmall?.copyWith(color: Colors.white70),
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
    case MatchViewerEventType.foul:
    case MatchViewerEventType.penalty:
      return const Color(0xFFFDB022);
    case MatchViewerEventType.offside:
      return const Color(0xFFF97066);
    case MatchViewerEventType.redCard:
      return const Color(0xFFEF4444);
    case MatchViewerEventType.yellowCard:
      return const Color(0xFFFACC15);
    default:
      return const Color(0xFFD0D5DD);
  }
}

Color _overlayAccent(MatchTimelineFrame frame, MatchEvent? event) {
  final String? text = frame.overlayText?.trim().toLowerCase();
  if (text == 'offside') {
    return const Color(0xFFF97066);
  }
  if (text == 'checking...') {
    return const Color(0xFFFDB022);
  }
  if (text == 'confirmed' || text == 'goal') {
    return const Color(0xFF17B26A);
  }
  if (text == 'disallowed') {
    return const Color(0xFFEF4444);
  }
  return _tileAccent(event?.type ?? MatchViewerEventType.neutral);
}

bool _listEquals(List<double> left, List<double> right) {
  if (left.length != right.length) {
    return false;
  }
  for (int index = 0; index < left.length; index += 1) {
    if ((left[index] - right[index]).abs() > 0.0001) {
      return false;
    }
  }
  return true;
}
