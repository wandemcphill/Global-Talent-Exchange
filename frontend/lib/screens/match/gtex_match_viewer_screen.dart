import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:gte_frontend/data/live_match_fixtures.dart';
import 'package:gte_frontend/features/match/presentation/broadcast_package_models.dart';
import 'package:gte_frontend/features/match/presentation/broadcast_package_repository.dart';
import 'package:gte_frontend/features/match/presentation/real_match_scene_director.dart';
import 'package:gte_frontend/features/match/presentation/widgets/commentary_ribbon_widget.dart';
import 'package:gte_frontend/features/match/presentation/widgets/match_moment_banner_widget.dart';
import 'package:gte_frontend/features/match/presentation/widgets/match_recap_board_widget.dart';
import 'package:gte_frontend/features/match/presentation/widgets/player_ratings_strip_widget.dart';
import 'package:gte_frontend/features/match/presentation/widgets/real_match_scorebug_widget.dart';
import 'package:gte_frontend/features/match/presentation/widgets/real_match_tactical_hud_widget.dart';
import 'package:gte_frontend/features/match/presentation/widgets/standings_context_widget.dart';
import 'package:gte_frontend/features/match/presentation/widgets/storyline_panel_widget.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_event.dart';
import 'package:gte_frontend/models/match_monetization.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/models/match_viewer_presentation.dart';
import 'package:gte_frontend/models/real_match_engine_presentation.dart';
import 'package:gte_frontend/services/match_3d_monetization_service.dart';
import 'package:gte_frontend/services/match_broadcast_presentation.dart';
import 'package:gte_frontend/services/match_viewer_mapper.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/match/pitch_2d_widget.dart';
import 'package:gte_frontend/widgets/match_3d/gtex_3d_scene.dart';
import 'package:gte_frontend/widgets/match_3d/monetization/gifting_overlay.dart';
import 'package:gte_frontend/widgets/match_3d/monetization/match_3d_upgrade_prompt.dart';
import 'package:gte_frontend/widgets/match_3d/monetization/premium_controls.dart';

import '../../controllers/match_3d_timeline_controller.dart';
import '../../services/match_3d_bridge.dart';

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
  final BroadcastPackageRepository _packageRepository =
      const BroadcastPackageRepository();

  Match3dMonetizationService? _ownedMonetizationService;
  Match3dMonetizationService? _monetizationService;
  Match3dTimelineController? _controller;
  MatchViewState? _viewState;
  Object? _loadError;
  bool _loading = true;
  bool _loadingContinuation = false;
  bool _resumeAfterLifecycle = false;
  String? _continuationNotice;
  String? _statusMessage;
  int _sourceSession = 0;
  final List<Match3dOverlayBurst> _activeBursts = <Match3dOverlayBurst>[];
  final Map<String, Timer> _burstTimers = <String, Timer>{};
  Timer? _retryTimer;
  Timer? _statusMessageTimer;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _bindMonetizationService(widget.monetizationService);
    _startInitialLoad();
  }

  @override
  void didUpdateWidget(covariant GtexMatchViewerScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.monetizationService != widget.monetizationService ||
        oldWidget.entitlement != widget.entitlement ||
        oldWidget.renderMode != widget.renderMode ||
        oldWidget.onPurchaseIntent != widget.onPurchaseIntent ||
        oldWidget.tournamentBoostPrice != widget.tournamentBoostPrice) {
      _bindMonetizationService(widget.monetizationService);
      _syncControllerSpeedOptions();
    }
    final bool sourceChanged =
        oldWidget.matchKey != widget.matchKey ||
        oldWidget.viewStateLoader != widget.viewStateLoader ||
        oldWidget.continuationLoader != widget.continuationLoader ||
        oldWidget.fallbackSnapshot != widget.fallbackSnapshot ||
        oldWidget.preferFallback != widget.preferFallback ||
        oldWidget.presentationMode != widget.presentationMode ||
        oldWidget.isMajorMatch != widget.isMajorMatch ||
        oldWidget.isSpectator != widget.isSpectator;
    if (sourceChanged) {
      _sourceSession += 1;
      _controller?.removeListener(_handleControllerTick);
      _controller?.dispose();
      _controller = null;
      _viewState = null;
      _loadError = null;
      _cancelTransientTimers();
      setState(() {
        _loading = true;
        _continuationNotice = null;
        _statusMessage = null;
        _activeBursts.clear();
      });
      _startInitialLoad();
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _controller?.removeListener(_handleControllerTick);
    _controller?.dispose();
    _cancelTransientTimers();
    _monetizationService?.removeListener(_handleMonetizationChanged);
    _ownedMonetizationService?.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    final Match3dTimelineController? controller = _controller;
    if (controller == null) {
      return;
    }
    if (state == AppLifecycleState.paused ||
        state == AppLifecycleState.inactive) {
      _resumeAfterLifecycle = controller.isPlaying;
      controller.pause();
      return;
    }
    if (state == AppLifecycleState.resumed && _resumeAfterLifecycle) {
      controller.play();
      _resumeAfterLifecycle = false;
    }
  }

  void _bindMonetizationService(Match3dMonetizationService? service) {
    _monetizationService?.removeListener(_handleMonetizationChanged);
    _ownedMonetizationService?.dispose();
    _ownedMonetizationService = null;
    _monetizationService =
        service ??
        Match3dMonetizationService(
          entitlement: widget.entitlement,
          initialRenderMode: widget.renderMode,
          onPurchaseIntent: widget.onPurchaseIntent,
          tournamentBoostPrice: widget.tournamentBoostPrice,
        );
    if (service == null) {
      _ownedMonetizationService = _monetizationService;
    } else {
      _monetizationService!.updateEntitlement(widget.entitlement);
      _monetizationService!.selectRenderMode(widget.renderMode);
    }
    _monetizationService!.addListener(_handleMonetizationChanged);
  }

  Match3dMonetizationService get _monetization => _monetizationService!;

  void _startInitialLoad() {
    final int sessionId = ++_sourceSession;
    unawaited(_loadInitialViewState(sessionId));
  }

  Future<void> _loadInitialViewState(int sessionId) async {
    try {
      final MatchViewState state = await _resolveInitialViewState();
      if (!mounted || sessionId != _sourceSession) {
        return;
      }
      _installController(state, preservePlaybackState: false);
    } catch (error) {
      if (!mounted || sessionId != _sourceSession) {
        return;
      }
      setState(() {
        _loading = false;
        _loadError = error;
      });
    }
  }

  Future<MatchViewState> _resolveInitialViewState() {
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

  void _installController(
    MatchViewState state, {
    required bool preservePlaybackState,
  }) {
    final Match3dTimelineController? previous = _controller;
    final double previousPosition =
        preservePlaybackState ? previous?.positionSeconds ?? 0 : 0;
    final bool wasPlaying =
        preservePlaybackState ? previous?.isPlaying ?? true : true;
    final MatchPlaybackSpeedMode previousSpeedMode =
        previous?.speedMode ?? MatchPlaybackSpeedMode.normal;

    previous?.removeListener(_handleControllerTick);
    final Match3dTimelineController controller = Match3dTimelineController(
      vsync: this,
      viewState: state,
      autoplay: false,
      initialSpeedMode: previousSpeedMode,
    );
    controller.updateSpeedOptions(_monetization.speedOptionsFor(_matchContext));
    controller.addListener(_handleControllerTick);
    if (previousPosition > 0) {
      controller.seekTo(
        math.min(previousPosition, state.durationSeconds.toDouble()),
      );
    }
    if (wasPlaying) {
      controller.play();
    }
    previous?.dispose();
    setState(() {
      _loading = false;
      _loadError = null;
      _viewState = state;
      _controller = controller;
      _continuationNotice = null;
      _loadingContinuation = false;
    });
  }

  Match3dMatchContext get _matchContext {
    final String competitionName = widget.competition.name.trim().toLowerCase();
    return Match3dMatchContext(
      matchId: widget.matchKey,
      competitionId: widget.competition.id,
      isFinal: competitionName.contains('final'),
      isMajorMatch:
          widget.isMajorMatch ||
          widget.presentationMode == MatchViewerPresentationMode.broadcast,
      isSpectator: widget.isSpectator,
      presentationMode: widget.presentationMode,
      performanceSafe: true,
    );
  }

  void _handleMonetizationChanged() {
    _syncControllerSpeedOptions();
    if (mounted) {
      setState(() {});
    }
  }

  void _syncControllerSpeedOptions() {
    _controller?.updateSpeedOptions(
      _monetization.speedOptionsFor(_matchContext),
    );
  }

  void _handleControllerTick() {
    _maybeRequestContinuation();
  }

  void _maybeRequestContinuation() {
    final Match3dTimelineController? controller = _controller;
    final MatchViewState? state = _viewState;
    final MatchViewContinuationLoader? continuationLoader =
        widget.continuationLoader;
    if (controller == null ||
        state == null ||
        continuationLoader == null ||
        _loadingContinuation ||
        !state.hasMoreSegments ||
        state.nextSegmentToken == null ||
        state.nextSegmentToken!.trim().isEmpty) {
      return;
    }
    final double triggerAt =
        math.max(0, state.segmentEndSeconds.toDouble() - 0.25).toDouble();
    if (controller.positionSeconds < triggerAt) {
      return;
    }
    unawaited(
      _loadContinuation(
        sessionId: _sourceSession,
        continuationLoader: continuationLoader,
        continuationToken: state.nextSegmentToken!,
      ),
    );
  }

  Future<void> _loadContinuation({
    required int sessionId,
    required MatchViewContinuationLoader continuationLoader,
    required String continuationToken,
    bool isRetry = false,
  }) async {
    if (_loadingContinuation) {
      return;
    }
    setState(() {
      _loadingContinuation = true;
      if (!isRetry) {
        _continuationNotice = null;
      }
    });
    try {
      final MatchViewState nextSegment = await continuationLoader(
        matchKey: widget.matchKey,
        continuationToken: continuationToken,
      );
      if (!mounted || sessionId != _sourceSession || _viewState == null) {
        return;
      }
      _retryTimer?.cancel();
      final MatchViewState merged = _mergeSegments(_viewState!, nextSegment);
      _installController(merged, preservePlaybackState: true);
    } catch (_) {
      if (!mounted || sessionId != _sourceSession) {
        return;
      }
      setState(() {
        _loadingContinuation = false;
        _continuationNotice = 'Segment delayed. Retrying playback...';
      });
      _retryTimer?.cancel();
      _retryTimer = Timer(const Duration(seconds: 1), () {
        if (!mounted) {
          return;
        }
        unawaited(
          _loadContinuation(
            sessionId: sessionId,
            continuationLoader: continuationLoader,
            continuationToken: continuationToken,
            isRetry: true,
          ),
        );
      });
    }
  }

  MatchViewState _mergeSegments(MatchViewState current, MatchViewState next) {
    final Map<String, MatchEvent> eventsById = <String, MatchEvent>{
      for (final MatchEvent event in current.events) event.id: event,
    };
    for (final MatchEvent event in next.events) {
      eventsById[event.id] = event;
    }
    final List<MatchEvent> events = eventsById.values.toList(growable: false)
      ..sort(
        (MatchEvent left, MatchEvent right) =>
            left.timeSeconds.compareTo(right.timeSeconds),
      );

    final Map<String, MatchTimelineFrame> framesById = <
      String,
      MatchTimelineFrame
    >{for (final MatchTimelineFrame frame in current.frames) frame.id: frame};
    for (final MatchTimelineFrame frame in next.frames) {
      framesById[frame.id] = frame;
    }
    final List<MatchTimelineFrame> frames = framesById.values.toList(
      growable: false,
    )..sort(
      (MatchTimelineFrame left, MatchTimelineFrame right) =>
          left.timeSeconds.compareTo(right.timeSeconds),
    );

    return current.copyWith(
      source: next.source,
      durationSeconds: math.max(current.durationSeconds, next.durationSeconds),
      events: events,
      frames: frames,
      segmentStartSeconds: current.segmentStartSeconds,
      segmentEndSeconds: next.segmentEndSeconds,
      hasMoreSegments: next.hasMoreSegments,
      nextSegmentToken: next.nextSegmentToken,
      monetization:
          next.monetization.hasPlacements
              ? next.monetization
              : current.monetization,
      presentationPackage:
          next.presentationPackage ?? current.presentationPackage,
    );
  }

  Future<void> _handleRenderModeSelection(RenderMode mode) async {
    _monetization.selectRenderMode(mode);
    if (mode != RenderMode.threeD ||
        !_monetization.needsThreeDUnlock(_matchContext)) {
      return;
    }
    final Match3dUpgradeAction? action = await Match3dUpgradePrompt.show(
      context,
      matchUnlockPrice: Match3dMonetizationService.threeDUnlockPrice,
      tournamentBoostPrice: widget.tournamentBoostPrice,
    );
    if (!mounted || action == null) {
      return;
    }
    switch (action) {
      case Match3dUpgradeAction.continueIn2d:
        _monetization.selectRenderMode(RenderMode.twoD);
      case Match3dUpgradeAction.unlock3d:
        final Match3dActionResult result = await _monetization
            .unlockThreeDForMatch(_matchContext);
        _applyActionResult(result);
      case Match3dUpgradeAction.upgradeTournament:
        final Match3dActionResult result = await _monetization
            .upgradeTournamentExperience(_matchContext);
        _applyActionResult(result);
    }
  }

  Future<void> _unlockInteraction(Match3dPaidInteraction interaction) async {
    final Match3dActionResult result = await _monetization.unlockInteraction(
      interaction,
      _matchContext,
    );
    _applyActionResult(result);
  }

  Future<void> _sendGift(double amount) async {
    final Match3dActionResult result = await _monetization.sendCoinGift(
      amount,
      _matchContext,
    );
    _applyActionResult(result);
  }

  Future<void> _sendReaction(Match3dReaction reaction) async {
    final Match3dActionResult result = _monetization.sendReaction(
      reaction,
      _matchContext,
    );
    _applyActionResult(result);
  }

  Future<void> _claimRewardedAd(MatchAdPlacement placement) async {
    final int rewardCoins = placement.rewardCoins ?? 0;
    final Match3dActionResult result = await _monetization.claimRewardedAd(
      adId: placement.id,
      rewardCoins: rewardCoins,
      brand: placement.brand,
    );
    _applyActionResult(result);
  }

  void _applyActionResult(Match3dActionResult result) {
    if (result.overlayBurst != null) {
      _activeBursts.insert(0, result.overlayBurst!);
      _scheduleBurstRemoval(result.overlayBurst!.id);
    }
    if (result.message != null && result.message!.trim().isNotEmpty) {
      _statusMessageTimer?.cancel();
      setState(() {
        _statusMessage = result.message;
      });
      _statusMessageTimer = Timer(const Duration(seconds: 4), () {
        if (!mounted) {
          return;
        }
        setState(() {
          _statusMessage = null;
        });
      });
    } else if (mounted) {
      setState(() {});
    }
  }

  void _scheduleBurstRemoval(String burstId) {
    _burstTimers.remove(burstId)?.cancel();
    _burstTimers[burstId] = Timer(const Duration(seconds: 4), () {
      if (!mounted) {
        return;
      }
      setState(() {
        _activeBursts.removeWhere(
          (Match3dOverlayBurst burst) => burst.id == burstId,
        );
      });
    });
  }

  void _cancelTransientTimers() {
    _retryTimer?.cancel();
    _statusMessageTimer?.cancel();
    for (final Timer timer in _burstTimers.values) {
      timer.cancel();
    }
    _burstTimers.clear();
  }

  Future<void> _reload() async {
    _sourceSession += 1;
    _cancelTransientTimers();
    _controller?.removeListener(_handleControllerTick);
    _controller?.dispose();
    _controller = null;
    setState(() {
      _loading = true;
      _loadError = null;
      _continuationNotice = null;
      _statusMessage = null;
      _activeBursts.clear();
    });
    _startInitialLoad();
  }

  String _routeTitle() {
    final String? override = widget.titleOverride?.trim();
    if (override != null && override.isNotEmpty) {
      return override;
    }
    if (widget.renderMode == RenderMode.threeD) {
      return '3D Match Viewer';
    }
    return '2D Match Viewer';
  }

  @override
  Widget build(BuildContext context) {
    final bool compactToolbar = MediaQuery.sizeOf(context).width < 420;
    return Scaffold(
      backgroundColor: const Color(0xFF050B12),
      appBar: AppBar(
        title: Text(compactToolbar ? 'Viewer' : _routeTitle()),
        backgroundColor: const Color(0xFF08121C),
        foregroundColor: Colors.white,
        actions:
            compactToolbar
                ? const <Widget>[]
                : <Widget>[
                  IconButton(
                    tooltip: 'Refresh viewer',
                    onPressed: _reload,
                    icon: const Icon(Icons.refresh_rounded),
                  ),
                ],
      ),
      body: DecoratedBox(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: <Color>[
              Color(0xFF08131D),
              Color(0xFF071019),
              Color(0xFF050A10),
            ],
          ),
        ),
        child:
            _loading
                ? const Center(
                  child: Padding(
                    padding: EdgeInsets.all(24),
                    child: GteStatePanel(
                      eyebrow: 'MATCH VIEWER',
                      title: 'Loading match presentation',
                      message:
                          'Preparing the verified timeline, broadcast overlays, and Flutter-rendered match lane.',
                      icon: Icons.live_tv_rounded,
                      isLoading: true,
                    ),
                  ),
                )
                : _loadError != null ||
                    _viewState == null ||
                    _controller == null
                ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: GteStatePanel(
                      eyebrow: 'MATCH VIEWER',
                      title: 'Match presentation unavailable',
                      message:
                          'The viewer could not load a verified match timeline for this route.',
                      icon: Icons.warning_amber_rounded,
                      actionLabel: 'Retry',
                      onAction: _reload,
                    ),
                  ),
                )
                : ListenableBuilder(
                  listenable: _controller!,
                  builder: (BuildContext context, Widget? child) {
                    return _LoadedViewerBody(
                      competition: widget.competition,
                      matchContext: _matchContext,
                      presentationMode: widget.presentationMode,
                      isSpectator: widget.isSpectator,
                      monetization: _monetization,
                      packageRepository: _packageRepository,
                      viewState: _viewState!,
                      controller: _controller!,
                      engineBridge: widget.engineBridge,
                      continuationNotice: _continuationNotice,
                      statusMessage: _statusMessage,
                      activeBursts: _activeBursts,
                      onRestart: () => _controller!.restart(),
                      onTogglePlayback: () => _controller!.togglePlayPause(),
                      onJumpToNextEvent: () => _controller!.jumpToNextEvent(),
                      onRenderModeSelected: _handleRenderModeSelection,
                      onCameraPresetSelected: (Match3dCameraPreset preset) {
                        _monetization.setCameraPreset(preset, _matchContext);
                      },
                      onUnlockSlowMotion:
                          () => _unlockInteraction(
                            Match3dPaidInteraction.slowMotionReplay,
                          ),
                      onUnlockAlternateCamera:
                          () => _unlockInteraction(
                            Match3dPaidInteraction.alternateCameraAngle,
                          ),
                      onUnlockHighlightAttack:
                          () => _unlockInteraction(
                            Match3dPaidInteraction.highlightNextAttack,
                          ),
                      onUpgradeTournament:
                          widget.tournamentBoostPrice == null
                              ? null
                              : () async {
                                final Match3dActionResult result =
                                    await _monetization
                                        .upgradeTournamentExperience(
                                          _matchContext,
                                        );
                                _applyActionResult(result);
                              },
                      onSendGift: _sendGift,
                      onSendReaction: _sendReaction,
                      onClaimRewardedAd: _claimRewardedAd,
                    );
                  },
                ),
      ),
    );
  }
}

class _LoadedViewerBody extends StatelessWidget {
  const _LoadedViewerBody({
    required this.competition,
    required this.matchContext,
    required this.presentationMode,
    required this.isSpectator,
    required this.monetization,
    required this.packageRepository,
    required this.viewState,
    required this.controller,
    required this.engineBridge,
    required this.continuationNotice,
    required this.statusMessage,
    required this.activeBursts,
    required this.onRestart,
    required this.onTogglePlayback,
    required this.onJumpToNextEvent,
    required this.onRenderModeSelected,
    required this.onCameraPresetSelected,
    required this.onUnlockSlowMotion,
    required this.onUnlockAlternateCamera,
    required this.onUnlockHighlightAttack,
    required this.onUpgradeTournament,
    required this.onSendGift,
    required this.onSendReaction,
    required this.onClaimRewardedAd,
  });

  final CompetitionSummary competition;
  final Match3dMatchContext matchContext;
  final MatchViewerPresentationMode presentationMode;
  final bool isSpectator;
  final Match3dMonetizationService monetization;
  final BroadcastPackageRepository packageRepository;
  final MatchViewState viewState;
  final Match3dTimelineController controller;
  final Match3DBridge? engineBridge;
  final String? continuationNotice;
  final String? statusMessage;
  final List<Match3dOverlayBurst> activeBursts;
  final VoidCallback onRestart;
  final VoidCallback onTogglePlayback;
  final VoidCallback onJumpToNextEvent;
  final Future<void> Function(RenderMode mode) onRenderModeSelected;
  final ValueChanged<Match3dCameraPreset> onCameraPresetSelected;
  final VoidCallback onUnlockSlowMotion;
  final VoidCallback onUnlockAlternateCamera;
  final VoidCallback onUnlockHighlightAttack;
  final Future<void> Function()? onUpgradeTournament;
  final Future<void> Function(double amount) onSendGift;
  final Future<void> Function(Match3dReaction reaction) onSendReaction;
  final Future<void> Function(MatchAdPlacement placement) onClaimRewardedAd;

  @override
  Widget build(BuildContext context) {
    final MatchTimelineFrame frame = controller.displayFrame;
    final MatchEvent? activeEvent = controller.activeEvent;
    final BroadcastPackageData packageData = packageRepository
        .resolveBroadcastData(
          matchKey: matchContext.matchId,
          viewState: viewState,
        );
    final MatchPresentationPackage package = packageData.package;
    final MatchEnginePresentationState realPresentation =
        RealMatchSceneDirector.resolve(
          viewState: viewState,
          frame: frame,
          package: package,
          activeEvent: activeEvent,
          playbackSeconds: controller.positionSeconds,
        );
    final MatchBroadcastPresentationState? broadcastPresentation =
        presentationMode == MatchViewerPresentationMode.broadcast
            ? MatchBroadcastPresentationBuilder.build(
              viewState: viewState,
              controller: controller,
            )
            : null;
    final RenderMode effectiveRenderMode = monetization.effectiveRenderModeFor(
      matchContext,
    );
    final bool compactSurface = MediaQuery.sizeOf(context).width < 420;
    final bool showBroadcastMode =
        presentationMode == MatchViewerPresentationMode.broadcast;
    final bool showAds =
        viewState.monetization.adsEnabled &&
        !(viewState.monetization.premiumAdFree &&
            monetization.effectiveEntitlement.isPremiumUser);
    final MatchAdPlacement? preRollPlacement =
        showAds
            ? viewState.monetization.firstActiveOfType(
              MatchAdPlacementType.preRoll,
              controller.positionSeconds,
            )
            : null;
    final MatchAdPlacement? liveBannerPlacement =
        showAds
            ? viewState.monetization.firstActiveOfType(
              MatchAdPlacementType.liveBanner,
              controller.positionSeconds,
            )
            : null;
    final MatchAdPlacement? rewardedPlacement =
        showAds
            ? viewState.monetization.firstOfType(
              MatchAdPlacementType.rewardedAd,
            )
            : null;
    final MatchAdPlacement? sponsoredPlacement =
        showAds
            ? viewState.monetization.firstOfType(
              MatchAdPlacementType.sponsoredHighlight,
            )
            : null;

    final String surfaceTitle =
        showBroadcastMode ? 'Live broadcast' : 'Replay lane';
    final String surfaceSubtitle =
        showBroadcastMode
            ? 'EA FC polish, eFootball readability, and Football Manager density within the shipped Flutter match lane.'
            : 'Stable event-to-scene playback with premium overlays, ratings, and camera-aware presentation.';

    final Widget sceneWidget =
        effectiveRenderMode == RenderMode.threeD
            ? Gtex3dScene(
              viewState: viewState,
              frame: frame,
              activeEvent: activeEvent,
              cameraPreset: _resolveCameraPreset(
                presentation: realPresentation,
                userPreset: monetization.cameraPreset,
              ),
              bridge: engineBridge,
              runtimePlayers: controller.playerEntities,
              runtimeBall: controller.ballEntity,
            )
            : Pitch2dWidget(
              viewState: viewState,
              frame: frame,
              showFormationOverlay: false,
              presentation: broadcastPresentation?.pitchPresentation,
            );

    final Widget scorebug =
        showBroadcastMode
            ? _BroadcastScorebug(
              package: package,
              state: broadcastPresentation!,
            )
            : RealMatchScorebugWidget(
              homeName: package.home.displayCode,
              awayName: package.away.displayCode,
              homeScore: frame.homeScore,
              awayScore: frame.awayScore,
              clockLabel: realPresentation.clockLabel,
              phaseLabel: realPresentation.phaseLabel,
              stateLabel: realPresentation.stateLabel,
              cameraLabel: realPresentation.cameraLabel,
              eventLabel: realPresentation.scorebugEventLabel,
            );

    final Widget commentaryRibbon = CommentaryRibbonWidget(
      headline:
          showBroadcastMode
              ? broadcastPresentation!.commentaryHeadline ?? package.matchLabel
              : realPresentation.lowerThirdHeadline,
      detail:
          showBroadcastMode
              ? broadcastPresentation!.commentarySubtitle ??
                  package.context.matchSignificance ??
                  'Broadcast lane active.'
              : realPresentation.lowerThirdDetail,
      trailing:
          showBroadcastMode
              ? activeEvent?.clockLabel
              : realPresentation.lowerThirdTrailing,
    );

    final List<Widget> sceneOverlays = <Widget>[
      Positioned(top: 14, left: 14, right: 14, child: scorebug),
      Positioned(left: 14, right: 14, bottom: 14, child: commentaryRibbon),
    ];
    if (realPresentation.showBanner && !showBroadcastMode && !compactSurface) {
      sceneOverlays.add(
        Positioned(
          top: 112,
          left: 18,
          child: MatchMomentBannerWidget(banner: realPresentation.banner!),
        ),
      );
    }
    if (showBroadcastMode && broadcastPresentation!.showStartingBanner) {
      sceneOverlays.add(
        Positioned(
          left: 20,
          right: 20,
          top: 108,
          child: Opacity(
            opacity: broadcastPresentation!.startingBannerOpacity,
            child: const _CenterTitleBanner(title: 'Match starting...'),
          ),
        ),
      );
    }
    if (showBroadcastMode && broadcastPresentation!.showLineupBoard) {
      sceneOverlays.add(
        Positioned(
          left: 18,
          right: 18,
          bottom: 94,
          child: Opacity(
            opacity: broadcastPresentation!.lineupBoardOpacity,
            child: Row(
              children: <Widget>[
                Expanded(
                  child: _FormationTeaserCard(
                    teamName: package.home.teamName,
                    formation: package.home.formation,
                    accent: _teamAccent(package.home),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _FormationTeaserCard(
                    teamName: package.away.teamName,
                    formation: package.away.formation,
                    accent: _teamAccent(package.away),
                    alignEnd: true,
                  ),
                ),
              ],
            ),
          ),
        ),
      );
    }
    if (preRollPlacement != null) {
      sceneOverlays.add(
        Positioned(
          top: 112,
          right: 18,
          child: _PlacementCard(
            key: const Key('match-ad-preroll'),
            placement: preRollPlacement,
            compact: true,
          ),
        ),
      );
    }
    if (effectiveRenderMode == RenderMode.threeD) {
      sceneOverlays.add(
        Positioned.fill(
          child: GiftingOverlay(
            activeBursts: activeBursts,
            availableCoins: monetization.availableCoinBalance,
            onSendGift: onSendGift,
            onSendReaction: onSendReaction,
          ),
        ),
      );
    }
    if (showBroadcastMode && broadcastPresentation!.isVarChecking) {
      sceneOverlays.add(
        Positioned(
          top: 168,
          right: 18,
          child: const _MiniPhaseChip(label: 'VAR', accent: Color(0xFFF79009)),
        ),
      );
    }

    final List<Widget> sceneSupport = <Widget>[
      if (realPresentation.showRatingsStrip)
        PlayerRatingsStripWidget(players: realPresentation.ratingLeaders),
      if (realPresentation.showSummaryBoard)
        MatchRecapBoardWidget(summaryBoard: realPresentation.summaryBoard!),
    ];

    final Widget premiumControls = PremiumControls(
      entitlement: monetization.effectiveEntitlement,
      selectedRenderMode: monetization.selectedRenderMode,
      effectiveRenderMode: effectiveRenderMode,
      availableCoins: monetization.availableCoinBalance,
      cameraPreset: monetization.cameraPreset,
      canUsePremiumCamera: monetization.canUsePremiumCamera(matchContext),
      canUseFastReplay: monetization.canUseFastReplay(matchContext),
      onRenderModeSelected: (RenderMode mode) {
        unawaited(onRenderModeSelected(mode));
      },
      onCameraPresetSelected: onCameraPresetSelected,
      onUnlockSlowMotion: onUnlockSlowMotion,
      onUnlockAlternateCamera: onUnlockAlternateCamera,
      onUnlockHighlightAttack: onUnlockHighlightAttack,
      onUpgradeTournament:
          onUpgradeTournament == null
              ? null
              : () {
                unawaited(onUpgradeTournament!());
              },
    );

    final List<Widget> sideRailChildren = <Widget>[
      premiumControls,
      if (rewardedPlacement != null) ...<Widget>[
        const SizedBox(height: 18),
        _RewardedAdCard(
          key: const Key('match-rewarded-ad-card'),
          placement: rewardedPlacement,
          claimed: monetization.hasClaimedRewardedAd(rewardedPlacement.id),
          onPressed: () => onClaimRewardedAd(rewardedPlacement),
        ),
      ],
      if (sponsoredPlacement != null) ...<Widget>[
        const SizedBox(height: 18),
        _PlacementCard(
          key: const Key('match-sponsored-highlight'),
          placement: sponsoredPlacement,
        ),
      ],
      if (showBroadcastMode ||
          effectiveRenderMode == RenderMode.threeD) ...<Widget>[
        const SizedBox(height: 18),
        RealMatchTacticalHudWidget(
          package: package,
          presentation: realPresentation,
        ),
      ],
      const SizedBox(height: 18),
      if (showBroadcastMode || package.context.hasAnyContent) ...<Widget>[
        StandingsContextWidget(
          contextBoard: package.context,
          homeTeam: package.home,
          awayTeam: package.away,
        ),
      ],
      if (packageData.hasStorylinePanel) ...<Widget>[
        const SizedBox(height: 18),
        StorylinePanelWidget(panel: packageData.storylinePanel),
      ],
    ];

    final Widget controlBar =
        isSpectator
            ? const SizedBox.shrink()
            : _ViewerControlBar(
              isPlaying: controller.isPlaying,
              speedLabel: controller.speedLabel,
              durationLabel: 'Duration: ${_resolvedDurationSeconds()}s',
              onRestart: onRestart,
              onTogglePlayback: onTogglePlayback,
              onJumpToNextEvent: onJumpToNextEvent,
              onCycleSpeed: controller.cycleSpeed,
            );

    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final bool wide = constraints.maxWidth >= 1220;
        final Widget scenePanel = _ScenePanel(
          surfaceTitle: surfaceTitle,
          surfaceSubtitle: surfaceSubtitle,
          competition: competition,
          package: package,
          phaseLabel:
              showBroadcastMode
                  ? (broadcastPresentation?.statusLabel ?? 'LIVE')
                  : realPresentation.phaseLabel,
          renderModeLabel:
              effectiveRenderMode == RenderMode.threeD ? 'Flutter 3D' : '2D',
          cameraLabel:
              showBroadcastMode ? 'BROADCAST' : realPresentation.cameraLabel,
          scene: sceneWidget,
          overlays: sceneOverlays,
          supportModules: sceneSupport,
        );

        final List<Widget> mainColumnChildren = <Widget>[
          if (continuationNotice != null)
            _InlineStatusBanner(
              text: continuationNotice!,
              accent: const Color(0xFFF79009),
            ),
          if (continuationNotice != null) const SizedBox(height: 14),
          if (statusMessage != null)
            _InlineStatusBanner(
              text: statusMessage!,
              accent: const Color(0xFF17B26A),
            ),
          if (statusMessage != null) const SizedBox(height: 14),
          scenePanel,
          if (!isSpectator) ...<Widget>[const SizedBox(height: 18), controlBar],
          if (!wide && constraints.maxWidth >= 420) ...<Widget>[
            const SizedBox(height: 18),
            ...sideRailChildren,
          ],
          if (liveBannerPlacement != null) ...<Widget>[
            const SizedBox(height: 18),
            _LiveBannerCard(
              key: const Key('match-ad-live-banner'),
              placement: liveBannerPlacement,
            ),
          ],
        ];

        if (!wide) {
          return SafeArea(
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(18, 18, 18, 24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: mainColumnChildren,
              ),
            ),
          );
        }

        return SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(18, 18, 18, 24),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Expanded(
                  flex: 5,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: mainColumnChildren,
                  ),
                ),
                const SizedBox(width: 18),
                SizedBox(
                  width: 360,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: sideRailChildren,
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  int _resolvedDurationSeconds() {
    final int eventDuration =
        viewState.events.isEmpty ? 0 : viewState.events.last.timeSeconds.ceil();
    final int frameDuration =
        viewState.frames.isEmpty ? 0 : viewState.frames.last.timeSeconds.ceil();
    return math.max(
      viewState.durationSeconds,
      math.max(eventDuration, frameDuration),
    );
  }

  MatchEngineCameraPreset _resolveCameraPreset({
    required MatchEnginePresentationState presentation,
    required Match3dCameraPreset userPreset,
  }) {
    switch (userPreset) {
      case Match3dCameraPreset.broadcast:
        return presentation.cameraPreset;
      case Match3dCameraPreset.sideline:
        if (presentation.cameraPreset == MatchEngineCameraPreset.goal_replay ||
            presentation.cameraPreset ==
                MatchEngineCameraPreset.set_piece_left ||
            presentation.cameraPreset ==
                MatchEngineCameraPreset.set_piece_right ||
            presentation.cameraPreset ==
                MatchEngineCameraPreset.attacking_third_left ||
            presentation.cameraPreset ==
                MatchEngineCameraPreset.attacking_third_right) {
          return presentation.cameraPreset;
        }
        return presentation.possessionSide == MatchViewerSide.home
            ? MatchEngineCameraPreset.attacking_third_right
            : MatchEngineCameraPreset.attacking_third_left;
      case Match3dCameraPreset.goalbox:
        switch (presentation.eventMapping) {
          case MatchSceneEventMapping.goal:
          case MatchSceneEventMapping.save:
          case MatchSceneEventMapping.shot:
          case MatchSceneEventMapping.penalty:
            return MatchEngineCameraPreset.goal_replay;
          case MatchSceneEventMapping.corner:
          case MatchSceneEventMapping.free_kick:
            return presentation.possessionSide == MatchViewerSide.home
                ? MatchEngineCameraPreset.set_piece_right
                : MatchEngineCameraPreset.set_piece_left;
          default:
            return presentation.cameraPreset;
        }
    }
  }

  Color _teamAccent(MatchPresentationTeam team) {
    return _colorFromHex(team.accentColorHex, const Color(0xFF53B1FD));
  }

  Color _colorFromHex(String? value, Color fallback) {
    if (value == null || value.trim().isEmpty) {
      return fallback;
    }
    var normalized = value.trim().replaceFirst('#', '');
    if (normalized.length == 6) {
      normalized = 'FF$normalized';
    }
    final int? parsed = int.tryParse(normalized, radix: 16);
    if (parsed == null) {
      return fallback;
    }
    return Color(parsed);
  }
}

class _ScenePanel extends StatelessWidget {
  const _ScenePanel({
    required this.surfaceTitle,
    required this.surfaceSubtitle,
    required this.competition,
    required this.package,
    required this.phaseLabel,
    required this.renderModeLabel,
    required this.cameraLabel,
    required this.scene,
    required this.overlays,
    required this.supportModules,
  });

  final String surfaceTitle;
  final String surfaceSubtitle;
  final CompetitionSummary competition;
  final MatchPresentationPackage package;
  final String phaseLabel;
  final String renderModeLabel;
  final String cameraLabel;
  final Widget scene;
  final List<Widget> overlays;
  final List<Widget> supportModules;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(32),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[Color(0xFF0E1723), Color(0xFF08111A)],
        ),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.28),
            blurRadius: 30,
            offset: const Offset(0, 18),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: <Widget>[
              _MiniPhaseChip(
                label: competition.name,
                accent: const Color(0xFF53B1FD),
              ),
              _MiniPhaseChip(
                label: phaseLabel.toUpperCase(),
                accent: const Color(0xFFF79009),
              ),
              _MiniPhaseChip(
                label: renderModeLabel.toUpperCase(),
                accent: const Color(0xFF17B26A),
              ),
              _MiniPhaseChip(
                label: cameraLabel,
                accent: const Color(0xFF7DD3FC),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Text(
            surfaceTitle,
            style: Theme.of(context).textTheme.headlineMedium?.copyWith(
              color: Colors.white,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            surfaceSubtitle,
            style: Theme.of(context).textTheme.bodyLarge?.copyWith(
              color: const Color(0xFFB6C5D5),
              height: 1.35,
            ),
          ),
          const SizedBox(height: 14),
          Row(
            children: <Widget>[
              Expanded(
                child: Text(
                  package.home.teamName,
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
              Text(
                'VS',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  color: const Color(0xFF7DD3FC),
                  fontWeight: FontWeight.w800,
                ),
              ),
              Expanded(
                child: Text(
                  package.away.teamName,
                  textAlign: TextAlign.right,
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 18),
          ClipRRect(
            borderRadius: BorderRadius.circular(26),
            child: Container(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(26),
                border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
              ),
              child: AspectRatio(
                aspectRatio: 105 / 68,
                child: Stack(
                  fit: StackFit.expand,
                  children: <Widget>[scene, ...overlays],
                ),
              ),
            ),
          ),
          for (final Widget module in supportModules) ...<Widget>[
            const SizedBox(height: 18),
            module,
          ],
        ],
      ),
    );
  }
}

class _BroadcastScorebug extends StatelessWidget {
  const _BroadcastScorebug({required this.package, required this.state});

  final MatchPresentationPackage package;
  final MatchBroadcastPresentationState state;

  @override
  Widget build(BuildContext context) {
    final String homeScore =
        state.scoreMasked ? '--' : '${state.visibleHomeScore ?? 0}';
    final String awayScore =
        state.scoreMasked ? '--' : '${state.visibleAwayScore ?? 0}';
    return DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(22),
        gradient: const LinearGradient(
          colors: <Color>[Color(0xF40A1118), Color(0xF4122130)],
        ),
        border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
      ),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(14, 12, 14, 10),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Row(
              children: <Widget>[
                _MaskedTeamScore(
                  name: package.home.displayCode,
                  score: homeScore,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    children: <Widget>[
                      Text(
                        state.clockLabel,
                        style: Theme.of(
                          context,
                        ).textTheme.headlineSmall?.copyWith(
                          color: Colors.white,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        state.statusLabel,
                        style: Theme.of(context).textTheme.labelLarge?.copyWith(
                          color: const Color(0xFFFDB022),
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 12),
                _MaskedTeamScore(
                  name: package.away.displayCode,
                  score: awayScore,
                  alignEnd: true,
                ),
              ],
            ),
            if (state.showCommentary) ...<Widget>[
              const SizedBox(height: 8),
              Text(
                state.commentaryHeadline!,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: Colors.white70,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _MaskedTeamScore extends StatelessWidget {
  const _MaskedTeamScore({
    required this.name,
    required this.score,
    this.alignEnd = false,
  });

  final String name;
  final String score;
  final bool alignEnd;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 92,
      child: Column(
        crossAxisAlignment:
            alignEnd ? CrossAxisAlignment.end : CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            name,
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: Colors.white70,
              fontWeight: FontWeight.w700,
            ),
          ),
          Text(
            score,
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
              color: Colors.white,
              fontWeight: FontWeight.w900,
            ),
          ),
        ],
      ),
    );
  }
}

class _ViewerControlBar extends StatelessWidget {
  const _ViewerControlBar({
    required this.isPlaying,
    required this.speedLabel,
    required this.durationLabel,
    required this.onRestart,
    required this.onTogglePlayback,
    required this.onJumpToNextEvent,
    required this.onCycleSpeed,
  });

  final bool isPlaying;
  final String speedLabel;
  final String durationLabel;
  final VoidCallback onRestart;
  final VoidCallback onTogglePlayback;
  final VoidCallback onJumpToNextEvent;
  final VoidCallback onCycleSpeed;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final bool stacked = constraints.maxWidth < 540;
        return Container(
          width: double.infinity,
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(24),
            color: const Color(0xD9111C28),
            border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
          ),
          child:
              stacked
                  ? Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: <Widget>[
                      _ViewerActionButton(
                        icon: Icons.restart_alt_rounded,
                        label: 'Restart',
                        onPressed: onRestart,
                        filled: true,
                      ),
                      const SizedBox(height: 8),
                      _ViewerActionButton(
                        icon:
                            isPlaying
                                ? Icons.pause_rounded
                                : Icons.play_arrow_rounded,
                        label: isPlaying ? 'Pause' : 'Play',
                        onPressed: onTogglePlayback,
                        filled: true,
                      ),
                      const SizedBox(height: 8),
                      _ViewerActionButton(
                        icon: Icons.skip_next_rounded,
                        label: 'Next event',
                        onPressed: onJumpToNextEvent,
                        filled: true,
                      ),
                      const SizedBox(height: 8),
                      _ViewerActionButton(
                        icon: Icons.speed_rounded,
                        label: speedLabel,
                        onPressed: onCycleSpeed,
                        filled: false,
                      ),
                      const SizedBox(height: 12),
                      Text(
                        durationLabel,
                        style: Theme.of(context).textTheme.labelLarge?.copyWith(
                          color: Colors.white70,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  )
                  : Wrap(
                    spacing: 10,
                    runSpacing: 10,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: <Widget>[
                      FilledButton.tonalIcon(
                        onPressed: onRestart,
                        icon: const Icon(Icons.restart_alt_rounded),
                        label: const Text('Restart'),
                      ),
                      FilledButton.tonalIcon(
                        onPressed: onTogglePlayback,
                        icon: Icon(
                          isPlaying
                              ? Icons.pause_rounded
                              : Icons.play_arrow_rounded,
                        ),
                        label: Text(isPlaying ? 'Pause' : 'Play'),
                      ),
                      FilledButton.tonalIcon(
                        onPressed: onJumpToNextEvent,
                        icon: const Icon(Icons.skip_next_rounded),
                        label: const Text('Next event'),
                      ),
                      OutlinedButton.icon(
                        onPressed: onCycleSpeed,
                        icon: const Icon(Icons.speed_rounded),
                        label: Text(speedLabel),
                      ),
                      const SizedBox(width: 6),
                      Text(
                        durationLabel,
                        style: Theme.of(context).textTheme.labelLarge?.copyWith(
                          color: Colors.white70,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
        );
      },
    );
  }
}

class _ViewerActionButton extends StatelessWidget {
  const _ViewerActionButton({
    required this.icon,
    required this.label,
    required this.onPressed,
    required this.filled,
  });

  final IconData icon;
  final String label;
  final VoidCallback onPressed;
  final bool filled;

  @override
  Widget build(BuildContext context) {
    final Widget child = Row(
      mainAxisSize: MainAxisSize.max,
      children: <Widget>[
        Icon(icon),
        const SizedBox(width: 8),
        Expanded(
          child: Text(label, maxLines: 1, overflow: TextOverflow.ellipsis),
        ),
      ],
    );
    if (filled) {
      return FilledButton.tonal(onPressed: onPressed, child: child);
    }
    return OutlinedButton(onPressed: onPressed, child: child);
  }
}

class _InlineStatusBanner extends StatelessWidget {
  const _InlineStatusBanner({required this.text, required this.accent});

  final String text;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: accent.withValues(alpha: 0.14),
        border: Border.all(color: accent.withValues(alpha: 0.36)),
      ),
      child: Text(
        text,
        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
          color: Colors.white,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

class _MiniPhaseChip extends StatelessWidget {
  const _MiniPhaseChip({required this.label, required this.accent});

  final String label;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: accent.withValues(alpha: 0.16),
        border: Border.all(color: accent.withValues(alpha: 0.34)),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelMedium?.copyWith(
          color: Colors.white,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }
}

class _CenterTitleBanner extends StatelessWidget {
  const _CenterTitleBanner({required this.title});

  final String title;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(999),
          color: const Color(0xE00C1722),
          border: Border.all(color: Colors.white.withValues(alpha: 0.16)),
        ),
        child: Text(
          title,
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
            color: Colors.white,
            fontWeight: FontWeight.w900,
          ),
        ),
      ),
    );
  }
}

class _FormationTeaserCard extends StatelessWidget {
  const _FormationTeaserCard({
    required this.teamName,
    required this.formation,
    required this.accent,
    this.alignEnd = false,
  });

  final String teamName;
  final String formation;
  final Color accent;
  final bool alignEnd;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        color: const Color(0xDD0E1723),
        border: Border.all(color: accent.withValues(alpha: 0.46)),
      ),
      child: Column(
        crossAxisAlignment:
            alignEnd ? CrossAxisAlignment.end : CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            teamName,
            textAlign: alignEnd ? TextAlign.right : TextAlign.left,
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: Colors.white,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            'Formation $formation',
            textAlign: alignEnd ? TextAlign.right : TextAlign.left,
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
              color: accent,
              fontWeight: FontWeight.w900,
            ),
          ),
        ],
      ),
    );
  }
}

class _PlacementCard extends StatelessWidget {
  const _PlacementCard({
    super.key,
    required this.placement,
    this.compact = false,
  });

  final MatchAdPlacement placement;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: compact ? const BoxConstraints(maxWidth: 240) : null,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        gradient: const LinearGradient(
          colors: <Color>[Color(0xE9111C29), Color(0xE9182839)],
        ),
        border: Border.all(color: const Color(0x66F79009)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Text(
            placement.brand.toUpperCase(),
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: const Color(0xFFFDB022),
              fontWeight: FontWeight.w900,
              letterSpacing: 0.9,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            placement.message,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: Colors.white,
              fontWeight: FontWeight.w700,
            ),
          ),
          if (!compact && placement.targetingTags.isNotEmpty) ...<Widget>[
            const SizedBox(height: 8),
            Text(
              placement.targetingTags.take(3).join(' | '),
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: Colors.white70),
            ),
          ],
        ],
      ),
    );
  }
}

class _RewardedAdCard extends StatelessWidget {
  const _RewardedAdCard({
    super.key,
    required this.placement,
    required this.claimed,
    required this.onPressed,
  });

  final MatchAdPlacement placement;
  final bool claimed;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    final int rewardCoins = placement.rewardCoins ?? 0;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(22),
        color: const Color(0xD9111C29),
        border: Border.all(color: Colors.white.withValues(alpha: 0.10)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            placement.brand,
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
              color: const Color(0xFFF79009),
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            placement.message,
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(color: Colors.white, height: 1.35),
          ),
          const SizedBox(height: 14),
          FilledButton.tonalIcon(
            onPressed: claimed ? null : onPressed,
            icon: const Icon(Icons.play_circle_outline_rounded),
            label: Text(
              claimed ? 'Reward claimed' : 'Watch Ad · +$rewardCoins coins',
            ),
          ),
        ],
      ),
    );
  }
}

class _LiveBannerCard extends StatelessWidget {
  const _LiveBannerCard({super.key, required this.placement});

  final MatchAdPlacement placement;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(22),
        gradient: const LinearGradient(
          colors: <Color>[Color(0xFF0B1723), Color(0xFF142233)],
        ),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Row(
        children: <Widget>[
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(999),
              color: const Color(0x1FF79009),
              border: Border.all(color: const Color(0x55F79009)),
            ),
            child: Text(
              placement.brand.toUpperCase(),
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                color: const Color(0xFFF79009),
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              placement.message,
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                color: Colors.white,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
