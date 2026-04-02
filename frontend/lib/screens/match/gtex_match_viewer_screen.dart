import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/match_playback_controller.dart';
import 'package:gte_frontend/data/live_match_fixtures.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_event.dart';
import 'package:gte_frontend/models/match_monetization.dart';
import 'package:gte_frontend/models/match_viewer_presentation.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/models/real_match_engine_presentation.dart';
import 'package:gte_frontend/services/match_3d_bridge.dart';
import 'package:gte_frontend/services/match_3d_monetization_service.dart';
import 'package:gte_frontend/services/match_viewer_mapper.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
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
    this.renderMode = RenderMode.twoD,
    this.viewStateLoader,
    this.continuationLoader,
    this.entitlement = const Match3dUserEntitlement(),
    this.isSpectator = false,
    this.monetizationService,
    this.titleOverride,
    this.engineBridge,
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
  final String? titleOverride;
  final Match3DBridge? engineBridge;

  @override
  State<GtexMatchViewerScreen> createState() => _GtexMatchViewerScreenState();
}

class _GtexMatchViewerScreenState extends State<GtexMatchViewerScreen>
    with SingleTickerProviderStateMixin {
  late Future<MatchViewState> _viewStateFuture;
  MatchPlaybackController? _controller;
  Match3dMonetizationService? _monetizationService;
  bool _ownsMonetizationService = false;
  String? _statusMessage;
  final List<Match3dOverlayBurst> _overlayBursts = <Match3dOverlayBurst>[];

  RenderMode get _requestedRenderMode {
    switch (widget.renderMode) {
      case RenderMode.threeD:
        return RenderMode.threeD;
      case RenderMode.auto:
      case RenderMode.twoD:
        return RenderMode.twoD;
    }
  }

  @override
  void initState() {
    super.initState();
    _viewStateFuture = _load();
    _configureMonetizationService();
  }

  @override
  void didUpdateWidget(covariant GtexMatchViewerScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.monetizationService != widget.monetizationService ||
        oldWidget.entitlement != widget.entitlement ||
        oldWidget.renderMode != widget.renderMode) {
      _configureMonetizationService();
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    final Match3dMonetizationService? monetizationService =
        _monetizationService;
    monetizationService?.removeListener(_handleMonetizationChanged);
    if (_ownsMonetizationService) {
      monetizationService?.dispose();
    }
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
      _statusMessage = null;
      _overlayBursts.clear();
    });
  }

  void _configureMonetizationService() {
    final Match3dMonetizationService nextService =
        widget.monetizationService ??
        Match3dMonetizationService(
          entitlement: widget.entitlement,
          initialRenderMode: _requestedRenderMode,
        );
    final Match3dMonetizationService? currentService = _monetizationService;
    if (identical(currentService, nextService)) {
      nextService.updateEntitlement(widget.entitlement);
      if (nextService.selectedRenderMode != _requestedRenderMode) {
        nextService.selectRenderMode(_requestedRenderMode);
      }
      return;
    }
    currentService?.removeListener(_handleMonetizationChanged);
    if (_ownsMonetizationService) {
      currentService?.dispose();
    }
    _monetizationService = nextService;
    _ownsMonetizationService = widget.monetizationService == null;
    nextService.updateEntitlement(widget.entitlement);
    if (nextService.selectedRenderMode != _requestedRenderMode) {
      nextService.selectRenderMode(_requestedRenderMode);
    }
    nextService.addListener(_handleMonetizationChanged);
  }

  void _handleMonetizationChanged() {
    if (!mounted) {
      return;
    }
    setState(() {});
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

  Match3dMonetizationService _ensureMonetizationService() {
    final Match3dMonetizationService? monetizationService =
        _monetizationService;
    if (monetizationService != null) {
      return monetizationService;
    }
    _configureMonetizationService();
    return _monetizationService!;
  }

  Match3dMatchContext _buildMatchContext(MatchViewState viewState) {
    return Match3dMatchContext(
      matchId: viewState.matchId,
      competitionId: widget.competition.id,
      isFinal: widget.competition.status == CompetitionStatus.completed,
      isMajorMatch: true,
      isSpectator: widget.isSpectator,
      presentationMode: widget.presentationMode,
    );
  }

  MatchEngineCameraPreset _cameraPresetFor(Match3dCameraPreset preset) {
    switch (preset) {
      case Match3dCameraPreset.broadcast:
        return MatchEngineCameraPreset.tactical_high;
      case Match3dCameraPreset.sideline:
        return MatchEngineCameraPreset.attacking_third_left;
      case Match3dCameraPreset.goalbox:
        return MatchEngineCameraPreset.goal_replay;
    }
  }

  void _setStatusMessage(String? message) {
    if (!mounted) {
      return;
    }
    setState(() {
      _statusMessage = message;
    });
  }

  void _pushOverlayBurst(Match3dOverlayBurst? burst) {
    if (!mounted || burst == null) {
      return;
    }
    setState(() {
      _overlayBursts.insert(0, burst);
      if (_overlayBursts.length > 6) {
        _overlayBursts.removeRange(6, _overlayBursts.length);
      }
    });
  }

  Future<void> _selectRenderMode(
    MatchViewState viewState,
    RenderMode mode,
  ) async {
    final Match3dMonetizationService monetizationService =
        _ensureMonetizationService();
    final Match3dMatchContext matchContext = _buildMatchContext(viewState);
    if (mode != RenderMode.threeD) {
      monetizationService.selectRenderMode(mode);
      return;
    }
    if (canAccess3D(matchContext, monetizationService.effectiveEntitlement)) {
      monetizationService.selectRenderMode(RenderMode.threeD);
      return;
    }
    final Match3dUpgradeAction? action = await Match3dUpgradePrompt.show(
      context,
      matchUnlockPrice: Match3dMonetizationService.threeDUnlockPrice,
      tournamentBoostPrice: monetizationService.tournamentBoostPrice,
    );
    if (!mounted) {
      return;
    }
    switch (action) {
      case Match3dUpgradeAction.unlock3d:
        final Match3dActionResult result = await monetizationService
            .unlockThreeDForMatch(matchContext);
        if (!mounted) {
          return;
        }
        _setStatusMessage(result.message);
        _pushOverlayBurst(result.overlayBurst);
        if (result.success) {
          monetizationService.selectRenderMode(RenderMode.threeD);
        } else {
          monetizationService.selectRenderMode(RenderMode.twoD);
        }
      case Match3dUpgradeAction.upgradeTournament:
        final Match3dActionResult result = await monetizationService
            .upgradeTournamentExperience(matchContext);
        if (!mounted) {
          return;
        }
        _setStatusMessage(result.message);
        _pushOverlayBurst(result.overlayBurst);
        if (result.success) {
          monetizationService.selectRenderMode(RenderMode.threeD);
        } else {
          monetizationService.selectRenderMode(RenderMode.twoD);
        }
      case Match3dUpgradeAction.continueIn2d:
      case null:
        monetizationService.selectRenderMode(RenderMode.twoD);
    }
  }

  Future<void> _unlockInteraction(
    Match3dPaidInteraction interaction,
    MatchViewState viewState,
  ) async {
    final Match3dActionResult result = await _ensureMonetizationService()
        .unlockInteraction(interaction, _buildMatchContext(viewState));
    _setStatusMessage(result.message);
    _pushOverlayBurst(result.overlayBurst);
  }

  Future<void> _upgradeTournamentExperience(MatchViewState viewState) async {
    final Match3dActionResult result = await _ensureMonetizationService()
        .upgradeTournamentExperience(_buildMatchContext(viewState));
    _setStatusMessage(result.message);
    _pushOverlayBurst(result.overlayBurst);
  }

  Future<void> _sendGift(double amount, MatchViewState viewState) async {
    final Match3dActionResult result = await _ensureMonetizationService()
        .sendCoinGift(amount, _buildMatchContext(viewState));
    _setStatusMessage(result.message);
    _pushOverlayBurst(result.overlayBurst);
  }

  Future<void> _sendReaction(
    Match3dReaction reaction,
    MatchViewState viewState,
  ) async {
    final Match3dActionResult result = _ensureMonetizationService()
        .sendReaction(reaction, _buildMatchContext(viewState));
    _setStatusMessage(result.message);
    _pushOverlayBurst(result.overlayBurst);
  }

  Future<void> _claimRewardedAd(MatchAdPlacement placement) async {
    final Match3dActionResult result = await _ensureMonetizationService()
        .claimRewardedAd(
          adId: placement.id,
          rewardCoins: placement.rewardCoins ?? 0,
          brand: placement.brand,
        );
    _setStatusMessage(result.message);
    _pushOverlayBurst(result.overlayBurst);
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: Text(widget.titleOverride ?? '2D Match Viewer'),
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
          builder: (
            BuildContext context,
            AsyncSnapshot<MatchViewState> snapshot,
          ) {
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
            final MatchPlaybackController controller = _ensureController(
              viewState,
            );
            final Match3dMonetizationService monetizationService =
                _ensureMonetizationService();
            return ListenableBuilder(
              listenable: Listenable.merge(<Listenable>[
                controller,
                monetizationService,
              ]),
              builder: (BuildContext context, Widget? child) {
                final Match3dMatchContext matchContext = _buildMatchContext(
                  viewState,
                );
                final MatchEvent? activeEvent = controller.activeEvent;
                final RenderMode effectiveRenderMode = monetizationService
                    .effectiveRenderModeFor(matchContext);
                final bool showThreeD =
                    effectiveRenderMode == RenderMode.threeD;
                final bool adsEnabled = viewState.monetization.adsEnabled;
                final MatchAdPlacement? preRollPlacement =
                    adsEnabled
                        ? viewState.monetization.firstActiveOfType(
                          MatchAdPlacementType.preRoll,
                          controller.positionSeconds,
                        )
                        : null;
                final MatchAdPlacement? sponsoredPlacement =
                    adsEnabled
                        ? viewState.monetization.sponsoredPlacementForEvent(
                              activeEvent?.id,
                            ) ??
                            viewState.monetization.firstOfType(
                              MatchAdPlacementType.sponsoredHighlight,
                            )
                        : null;
                final MatchAdPlacement? liveBannerPlacement =
                    adsEnabled
                        ? viewState.monetization.firstActiveOfType(
                          MatchAdPlacementType.liveBanner,
                          controller.positionSeconds,
                        )
                        : null;
                final MatchAdPlacement? rewardedPlacement =
                    adsEnabled
                        ? viewState.monetization.firstOfType(
                          MatchAdPlacementType.rewardedAd,
                        )
                        : null;
                final bool rewardClaimed =
                    rewardedPlacement != null &&
                    monetizationService.hasClaimedRewardedAd(
                      rewardedPlacement.id,
                    );
                final bool showSupportControls =
                    monetizationService.effectiveEntitlement.isPremiumUser ||
                    monetizationService.availableCoinBalance > 0;
                return LayoutBuilder(
                  builder: (BuildContext context, BoxConstraints constraints) {
                    final bool wide = constraints.maxWidth >= 1040;
                    final Widget viewerPanel = Column(
                      children: <Widget>[
                        Expanded(
                          child: Stack(
                            children: <Widget>[
                              Positioned.fill(
                                child: Padding(
                                  padding: const EdgeInsets.fromLTRB(
                                    18,
                                    18,
                                    18,
                                    18,
                                  ),
                                  child: RepaintBoundary(
                                    child:
                                        showThreeD
                                            ? Gtex3dScene(
                                              viewState: viewState,
                                              frame: controller.displayFrame,
                                              activeEvent: activeEvent,
                                              cameraPreset: _cameraPresetFor(
                                                monetizationService
                                                    .cameraPreset,
                                              ),
                                              bridge: widget.engineBridge,
                                            )
                                            : Pitch2dWidget(
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
                                      constraints: const BoxConstraints(
                                        maxWidth: 360,
                                      ),
                                      child: EventTickerWidget(
                                        event: activeEvent,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              if (sponsoredPlacement != null)
                                Positioned(
                                  left: 28,
                                  top: 116,
                                  child: _AdPlacementChip(
                                    key: const Key('match-sponsored-highlight'),
                                    brand: sponsoredPlacement.brand,
                                    message: sponsoredPlacement.message,
                                    accentColor: GteShellTheme.accentArena,
                                  ),
                                ),
                              if (preRollPlacement != null)
                                Positioned(
                                  left: 28,
                                  bottom: 96,
                                  child: _AdPlacementChip(
                                    key: const Key('match-ad-preroll'),
                                    brand: preRollPlacement.brand,
                                    message: preRollPlacement.message,
                                    accentColor: GteShellTheme.accentCapital,
                                  ),
                                ),
                              if (liveBannerPlacement != null)
                                Positioned(
                                  left: 28,
                                  right: 28,
                                  bottom: 92,
                                  child: _LiveBannerCard(
                                    key: const Key('match-ad-live-banner'),
                                    brand: liveBannerPlacement.brand,
                                    message: liveBannerPlacement.message,
                                  ),
                                ),
                              if (showSupportControls)
                                Positioned.fill(
                                  child: GiftingOverlay(
                                    activeBursts: _overlayBursts,
                                    overflowCount:
                                        _overlayBursts.length > 3
                                            ? _overlayBursts.length - 3
                                            : 0,
                                    availableCoins:
                                        monetizationService
                                            .availableCoinBalance,
                                    onSendGift:
                                        (double amount) =>
                                            _sendGift(amount, viewState),
                                    onSendReaction:
                                        (Match3dReaction reaction) =>
                                            _sendReaction(reaction, viewState),
                                  ),
                                ),
                            ],
                          ),
                        ),
                        if (!widget.isSpectator)
                          _ControlBar(
                            controller: controller,
                            compactReplayControls: widget.isSpectator,
                          ),
                      ],
                    );
                    final Widget rail = Column(
                      children: <Widget>[
                        PremiumControls(
                          entitlement: monetizationService.effectiveEntitlement,
                          selectedRenderMode:
                              monetizationService.selectedRenderMode,
                          effectiveRenderMode: effectiveRenderMode,
                          threeDAvailable: canAccess3D(
                            matchContext,
                            monetizationService.effectiveEntitlement,
                          ),
                          availableCoins:
                              monetizationService.availableCoinBalance,
                          cameraPreset: monetizationService.cameraPreset,
                          canUsePremiumCamera: monetizationService
                              .canUsePremiumCamera(matchContext),
                          canUseFastReplay: monetizationService
                              .canUseFastReplay(matchContext),
                          onRenderModeSelected:
                              (RenderMode mode) =>
                                  _selectRenderMode(viewState, mode),
                          onCameraPresetSelected:
                              (Match3dCameraPreset preset) =>
                                  monetizationService.setCameraPreset(
                                    preset,
                                    matchContext,
                                  ),
                          onUnlockSlowMotion:
                              () => _unlockInteraction(
                                Match3dPaidInteraction.slowMotionReplay,
                                viewState,
                              ),
                          onUnlockAlternateCamera:
                              () => _unlockInteraction(
                                Match3dPaidInteraction.alternateCameraAngle,
                                viewState,
                              ),
                          onUnlockHighlightAttack:
                              () => _unlockInteraction(
                                Match3dPaidInteraction.highlightNextAttack,
                                viewState,
                              ),
                          onUpgradeTournament:
                              monetizationService.tournamentBoostPrice == null
                                  ? null
                                  : () =>
                                      _upgradeTournamentExperience(viewState),
                        ),
                        if (_statusMessage != null) ...<Widget>[
                          const SizedBox(height: 12),
                          _StatusCard(message: _statusMessage!),
                        ],
                        if (rewardedPlacement != null) ...<Widget>[
                          const SizedBox(height: 12),
                          _RewardedAdCard(
                            placement: rewardedPlacement,
                            claimed: rewardClaimed,
                            onClaim:
                                rewardClaimed
                                    ? null
                                    : () => _claimRewardedAd(rewardedPlacement),
                          ),
                        ],
                        const SizedBox(height: 12),
                        Expanded(
                          child: _EventRail(
                            controller: controller,
                            viewState: viewState,
                          ),
                        ),
                      ],
                    );
                    if (wide) {
                      return Row(
                        children: <Widget>[
                          Expanded(flex: 3, child: viewerPanel),
                          SizedBox(
                            width: 360,
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
                          height: 420,
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
            );
          },
        ),
      ),
    );
  }
}

class _ControlBar extends StatelessWidget {
  const _ControlBar({
    required this.controller,
    this.compactReplayControls = false,
  });

  final MatchPlaybackController controller;
  final bool compactReplayControls;

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
          if (!compactReplayControls) ...<Widget>[
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
          ],
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

class _AdPlacementChip extends StatelessWidget {
  const _AdPlacementChip({
    super.key,
    required this.brand,
    required this.message,
    required this.accentColor,
  });

  final String brand;
  final String message;
  final Color accentColor;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(maxWidth: 320),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: const Color(0xD9111D2B),
        border: Border.all(color: accentColor.withValues(alpha: 0.38)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            brand,
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: accentColor,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            message,
            style: Theme.of(
              context,
            ).textTheme.bodySmall?.copyWith(color: Colors.white),
          ),
        ],
      ),
    );
  }
}

class _LiveBannerCard extends StatelessWidget {
  const _LiveBannerCard({
    super.key,
    required this.brand,
    required this.message,
  });

  final String brand;
  final String message;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        gradient: const LinearGradient(
          colors: <Color>[Color(0xFF101D2D), Color(0xFF18314A)],
        ),
        border: Border.all(color: Colors.white.withValues(alpha: 0.14)),
      ),
      child: Row(
        children: <Widget>[
          const Icon(Icons.campaign_outlined, color: GteShellTheme.accentArena),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              '$brand | $message',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: Colors.white,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _RewardedAdCard extends StatelessWidget {
  const _RewardedAdCard({
    required this.placement,
    required this.claimed,
    required this.onClaim,
  });

  final MatchAdPlacement placement;
  final bool claimed;
  final VoidCallback? onClaim;

  @override
  Widget build(BuildContext context) {
    final int rewardCoins = placement.rewardCoins ?? 0;
    return Container(
      key: const Key('match-rewarded-ad-card'),
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(22),
        color: const Color(0xD7101B2A),
        border: Border.all(
          color: GteShellTheme.accentCapital.withValues(alpha: 0.34),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            placement.brand,
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
              color: GteShellTheme.accentCapital,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            placement.message,
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(color: Colors.white70),
          ),
          const SizedBox(height: 12),
          FilledButton.tonalIcon(
            onPressed: onClaim,
            icon: Icon(
              claimed ? Icons.verified_outlined : Icons.play_circle_outline,
            ),
            label: Text(
              claimed ? 'Reward claimed' : 'Watch Ad · +$rewardCoins coins',
            ),
          ),
        ],
      ),
    );
  }
}

class _StatusCard extends StatelessWidget {
  const _StatusCard({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: Colors.white.withValues(alpha: 0.06),
        border: Border.all(color: Colors.white.withValues(alpha: 0.10)),
      ),
      child: Text(
        message,
        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
          color: Colors.white,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}

class _EventRail extends StatelessWidget {
  const _EventRail({required this.controller, required this.viewState});

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
                  style: Theme.of(
                    context,
                  ).textTheme.bodySmall?.copyWith(color: Colors.white70),
                ),
                if (event.isDataUnavailable) ...<Widget>[
                  const SizedBox(height: 4),
                  Text(
                    'Data unavailable placeholder',
                    style: Theme.of(
                      context,
                    ).textTheme.labelSmall?.copyWith(color: Colors.white60),
                  ),
                ],
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
