import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/match_playback_controller.dart';
import 'package:gte_frontend/data/live_match_fixtures.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_event.dart';
import 'package:gte_frontend/models/match_monetization.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/models/match_viewer_presentation.dart';
import 'package:gte_frontend/services/match_3d_bridge.dart';
import 'package:gte_frontend/services/match_3d_monetization_service.dart';
import 'package:gte_frontend/services/match_viewer_mapper.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/match/event_ticker_widget.dart';
import 'package:gte_frontend/widgets/match/pitch_2d_widget.dart';
import 'package:gte_frontend/widgets/match/scoreboard_widget.dart';
import 'package:gte_frontend/widgets/match_3d/gtex_3d_scene.dart';

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
  late Match3dMonetizationService _monetization;
  bool _ownsMonetization = false;
  String? _statusMessage;
  Match3dOverlayBurst? _overlayBurst;

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
    _attachMonetizationService(initial: true);
  }

  @override
  void didUpdateWidget(covariant GtexMatchViewerScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.competition.id != widget.competition.id ||
        oldWidget.matchKey != widget.matchKey ||
        oldWidget.fallbackSnapshot != widget.fallbackSnapshot ||
        oldWidget.preferFallback != widget.preferFallback ||
        oldWidget.viewStateLoader != widget.viewStateLoader) {
      _reload();
    }
    if (oldWidget.monetizationService != widget.monetizationService) {
      _detachMonetizationService();
      _attachMonetizationService(initial: false);
      return;
    }
    if (_ownsMonetization &&
        (oldWidget.renderMode != widget.renderMode ||
            oldWidget.entitlement != widget.entitlement)) {
      _monetization.updateEntitlement(widget.entitlement);
      _monetization.selectRenderMode(widget.renderMode);
    }
  }

  @override
  void dispose() {
    _detachMonetizationService();
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

  void _attachMonetizationService({required bool initial}) {
    final Match3dMonetizationService service =
        widget.monetizationService ??
        Match3dMonetizationService(
          entitlement: widget.entitlement,
          initialRenderMode: widget.renderMode,
        );
    _monetization = service;
    _ownsMonetization = widget.monetizationService == null;
    _monetization.addListener(_handleMonetizationChanged);
    if (!initial && mounted) {
      setState(() {});
    }
  }

  void _detachMonetizationService() {
    _monetization.removeListener(_handleMonetizationChanged);
    if (_ownsMonetization) {
      _monetization.dispose();
    }
  }

  void _handleMonetizationChanged() {
    if (!mounted) {
      return;
    }
    setState(() {});
  }

  Match3dMatchContext _matchContext(MatchViewState viewState) {
    return Match3dMatchContext(
      matchId: viewState.matchId,
      competitionId: widget.competition.id,
      isFinal: widget.competition.status == CompetitionStatus.completed,
      isMajorMatch:
          widget.presentationMode == MatchViewerPresentationMode.broadcast,
      isSpectator: widget.isSpectator,
      presentationMode: widget.presentationMode,
    );
  }

  Future<void> _toggleThreeDMode(MatchViewState viewState) async {
    final Match3dMatchContext matchContext = _matchContext(viewState);
    final RenderMode effectiveRenderMode = _monetization.effectiveRenderModeFor(
      matchContext,
    );
    if (effectiveRenderMode == RenderMode.threeD) {
      _monetization.selectRenderMode(RenderMode.twoD);
      return;
    }
    _monetization.selectRenderMode(RenderMode.threeD);
    if (_monetization.needsThreeDUnlock(matchContext)) {
      await _showThreeDUnlockPrompt(matchContext);
      return;
    }
    setState(() {
      _statusMessage = '3D lane active.';
    });
  }

  Future<void> _showThreeDUnlockPrompt(Match3dMatchContext matchContext) async {
    final Match3dActionResult? result = await showDialog<Match3dActionResult>(
      context: context,
      builder: (BuildContext dialogContext) {
        return AlertDialog(
          title: const Text('Watch in Cinematic Mode \u{1F3AC}'),
          content: Text(
            'Unlock the 3D lane for ${widget.competition.name} and stay in the cinematic camera feed.',
          ),
          actions: <Widget>[
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: const Text('Continue in 2D'),
            ),
            FilledButton(
              onPressed: () async {
                final Match3dActionResult result = await _monetization
                    .unlockThreeDForMatch(matchContext);
                if (!mounted) {
                  return;
                }
                if (result.success) {
                  _monetization.selectRenderMode(RenderMode.threeD);
                }
                if (dialogContext.mounted) {
                  Navigator.of(dialogContext).pop(result);
                }
              },
              child: const Text('Unlock & Watch'),
            ),
          ],
        );
      },
    );
    if (!mounted || result == null) {
      return;
    }
    _consumeActionResult(result);
  }

  Future<void> _showGiftOptions(Match3dMatchContext matchContext) async {
    final double? amount = await showDialog<double>(
      context: context,
      builder: (BuildContext dialogContext) {
        return SimpleDialog(
          title: const Text('Send Coin Gift'),
          children: Match3dMonetizationService.giftAmounts
              .map(
                (double amount) => SimpleDialogOption(
                  onPressed: () => Navigator.of(dialogContext).pop(amount),
                  child: Text('${amount.toStringAsFixed(1)} coin'),
                ),
              )
              .toList(growable: false),
        );
      },
    );
    if (!mounted || amount == null) {
      return;
    }
    final Match3dActionResult result = await _monetization.sendCoinGift(
      amount,
      matchContext,
    );
    if (!mounted) {
      return;
    }
    _consumeActionResult(result);
  }

  Future<void> _claimRewardedAd(MatchAdPlacement placement) async {
    final Match3dActionResult result = await _monetization.claimRewardedAd(
      adId: placement.id,
      rewardCoins: placement.rewardCoins ?? 0,
      brand: placement.brand,
    );
    if (!mounted) {
      return;
    }
    _consumeActionResult(result);
  }

  void _consumeActionResult(Match3dActionResult result) {
    setState(() {
      _statusMessage = result.message;
      _overlayBurst = result.overlayBurst;
    });
  }

  String _rewardedAdLabel(MatchAdPlacement placement) {
    final int rewardCoins = placement.rewardCoins ?? 0;
    if (rewardCoins > 0) {
      return 'Watch Ad \u00B7 +$rewardCoins coins';
    }
    return placement.ctaLabel ?? 'Watch Ad';
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: Text(widget.titleOverride ?? 'Match Viewer'),
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
                      'Preparing the pitch, 3D lane, ad placements, and replay controls.',
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
            final Match3dMatchContext matchContext = _matchContext(viewState);
            return LayoutBuilder(
              builder: (BuildContext context, BoxConstraints constraints) {
                final bool wide = constraints.maxWidth >= 1040;
                final MatchViewerMonetization monetization =
                    viewState.monetization;
                final bool showAds =
                    monetization.adsEnabled &&
                    (!monetization.premiumAdFree ||
                        !_monetization.effectiveEntitlement.isPremiumUser);
                final Widget viewerPanel = ListenableBuilder(
                  listenable: controller,
                  builder: (BuildContext context, Widget? child) {
                    final MatchEvent? activeEvent = controller.activeEvent;
                    final RenderMode effectiveRenderMode = _monetization
                        .effectiveRenderModeFor(matchContext);
                    final bool showThreeDScene =
                        effectiveRenderMode == RenderMode.threeD;
                    final MatchAdPlacement? preRoll =
                        showAds
                            ? monetization.firstActiveOfType(
                              MatchAdPlacementType.preRoll,
                              controller.positionSeconds,
                            )
                            : null;
                    final MatchAdPlacement? sponsored =
                        showAds
                            ? monetization.firstOfType(
                              MatchAdPlacementType.sponsoredHighlight,
                            )
                            : null;
                    final MatchAdPlacement? liveBanner =
                        showAds
                            ? monetization.firstActiveOfType(
                              MatchAdPlacementType.liveBanner,
                              controller.positionSeconds,
                            )
                            : null;
                    return Column(
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
                                        showThreeDScene
                                            ? Gtex3dScene(
                                              viewState: viewState,
                                              frame: controller.displayFrame,
                                              activeEvent: activeEvent,
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
                              if (preRoll != null)
                                Positioned(
                                  top: 110,
                                  left: 36,
                                  child: _PlacementBanner(
                                    key: const Key('match-ad-preroll'),
                                    brand: preRoll.brand,
                                    message: preRoll.message,
                                    accent: const Color(0xFFF79009),
                                    icon: Icons.campaign_outlined,
                                  ),
                                ),
                              if (sponsored != null)
                                Positioned(
                                  left: 36,
                                  bottom: 88,
                                  child: _PlacementBanner(
                                    key: const Key('match-sponsored-highlight'),
                                    brand: sponsored.brand,
                                    message: sponsored.message,
                                    accent: const Color(0xFF17B26A),
                                    icon: Icons.emoji_events_outlined,
                                  ),
                                ),
                              if (liveBanner != null)
                                Positioned(
                                  right: 36,
                                  bottom: 88,
                                  child: _PlacementBanner(
                                    key: const Key('match-ad-live-banner'),
                                    brand: liveBanner.brand,
                                    message: liveBanner.message,
                                    accent: const Color(0xFF53B1FD),
                                    icon: Icons.ads_click_outlined,
                                  ),
                                ),
                            ],
                          ),
                        ),
                        _FeedbackStrip(
                          message: _statusMessage,
                          overlayBurst: _overlayBurst,
                        ),
                        _ControlBar(
                          controller: controller,
                          showRestart: !widget.isSpectator,
                          showPremiumBadge:
                              _monetization.effectiveEntitlement.isPremiumUser,
                          showGiftAction: showThreeDScene,
                          renderMode: effectiveRenderMode,
                          onThreeDToggle: () => _toggleThreeDMode(viewState),
                          onGiftTap:
                              showThreeDScene
                                  ? () => _showGiftOptions(matchContext)
                                  : null,
                        ),
                      ],
                    );
                  },
                );
                final MatchAdPlacement? rewardedPlacement =
                    showAds
                        ? monetization.firstOfType(
                          MatchAdPlacementType.rewardedAd,
                        )
                        : null;
                final Widget rail = Column(
                  children: <Widget>[
                    Expanded(
                      child: _EventRail(
                        controller: controller,
                        viewState: viewState,
                      ),
                    ),
                    if (rewardedPlacement != null) ...<Widget>[
                      const SizedBox(height: 12),
                      _RewardedAdCard(
                        placement: rewardedPlacement,
                        actionLabel: _rewardedAdLabel(rewardedPlacement),
                        claimed: _monetization.hasClaimedRewardedAd(
                          rewardedPlacement.id,
                        ),
                        onClaim: () => _claimRewardedAd(rewardedPlacement),
                      ),
                    ],
                  ],
                );

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
                      height: rewardedPlacement == null ? 220 : 320,
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
  const _ControlBar({
    required this.controller,
    required this.showRestart,
    required this.showPremiumBadge,
    required this.showGiftAction,
    required this.renderMode,
    required this.onThreeDToggle,
    this.onGiftTap,
  });

  final MatchPlaybackController controller;
  final bool showRestart;
  final bool showPremiumBadge;
  final bool showGiftAction;
  final RenderMode renderMode;
  final VoidCallback onThreeDToggle;
  final VoidCallback? onGiftTap;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(18, 12, 18, 18),
      child: Column(
        children: <Widget>[
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: <Widget>[
                FilledButton.icon(
                  onPressed: controller.togglePlayPause,
                  icon: Icon(
                    controller.isPlaying ? Icons.pause : Icons.play_arrow,
                  ),
                  label: Text(controller.isPlaying ? 'Pause' : 'Play'),
                ),
                if (showRestart) ...<Widget>[
                  const SizedBox(width: 10),
                  FilledButton.tonalIcon(
                    onPressed: controller.restart,
                    icon: const Icon(Icons.replay),
                    label: const Text('Restart'),
                  ),
                ],
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
                const SizedBox(width: 10),
                FilledButton.tonalIcon(
                  onPressed: onThreeDToggle,
                  icon: Icon(
                    renderMode == RenderMode.threeD
                        ? Icons.view_in_ar_outlined
                        : Icons.movie_outlined,
                  ),
                  label: const Text('3D lane'),
                ),
                if (showGiftAction) ...<Widget>[
                  const SizedBox(width: 10),
                  FilledButton.tonalIcon(
                    onPressed: onGiftTap,
                    icon: const Icon(Icons.card_giftcard_outlined),
                    label: const Text('Gift'),
                  ),
                ],
                if (showPremiumBadge) ...<Widget>[
                  const SizedBox(width: 10),
                  Chip(
                    avatar: const Icon(Icons.workspace_premium, size: 18),
                    label: const Text('Pro Manager'),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 12),
          LinearProgressIndicator(
            value: controller.progress.clamp(0, 1),
            minHeight: 7,
            borderRadius: BorderRadius.circular(999),
            backgroundColor: Colors.white.withValues(alpha: 0.08),
            valueColor: const AlwaysStoppedAnimation<Color>(
              GteShellTheme.accentArena,
            ),
          ),
        ],
      ),
    );
  }
}

class _PlacementBanner extends StatelessWidget {
  const _PlacementBanner({
    super.key,
    required this.brand,
    required this.message,
    required this.accent,
    required this.icon,
  });

  final String brand;
  final String message;
  final Color accent;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(maxWidth: 280),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: const Color(0xFF0B1117).withValues(alpha: 0.92),
        border: Border.all(color: accent.withValues(alpha: 0.55)),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.24),
            blurRadius: 18,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(icon, color: accent, size: 18),
          const SizedBox(width: 10),
          Flexible(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                Text(
                  brand,
                  style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    color: accent,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  message,
                  style: Theme.of(
                    context,
                  ).textTheme.bodySmall?.copyWith(color: Colors.white),
                ),
              ],
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
    required this.actionLabel,
    required this.claimed,
    required this.onClaim,
  });

  final MatchAdPlacement placement;
  final String actionLabel;
  final bool claimed;
  final VoidCallback onClaim;

  @override
  Widget build(BuildContext context) {
    return Container(
      key: const Key('match-rewarded-ad-card'),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        color: Colors.white.withValues(alpha: 0.05),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            placement.brand,
            style: Theme.of(
              context,
            ).textTheme.titleSmall?.copyWith(color: GteShellTheme.accentArena),
          ),
          const SizedBox(height: 4),
          Text(
            placement.message,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 12),
          FilledButton(
            onPressed: claimed ? null : onClaim,
            child: Text(actionLabel),
          ),
          if (claimed) ...<Widget>[
            const SizedBox(height: 8),
            Text(
              'Reward claimed',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: GteShellTheme.positive,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _FeedbackStrip extends StatelessWidget {
  const _FeedbackStrip({required this.message, required this.overlayBurst});

  final String? message;
  final Match3dOverlayBurst? overlayBurst;

  @override
  Widget build(BuildContext context) {
    if ((message == null || message!.trim().isEmpty) && overlayBurst == null) {
      return const SizedBox.shrink();
    }
    return Padding(
      padding: const EdgeInsets.fromLTRB(18, 0, 18, 0),
      child: Wrap(
        spacing: 10,
        runSpacing: 10,
        children: <Widget>[
          if (message != null && message!.trim().isNotEmpty)
            _FeedbackPill(label: message!, accent: GteShellTheme.accentArena),
          if (overlayBurst != null)
            _FeedbackPill(
              label: overlayBurst!.label,
              accent: overlayBurst!.accentColor,
            ),
        ],
      ),
    );
  }
}

class _FeedbackPill extends StatelessWidget {
  const _FeedbackPill({required this.label, required this.accent});

  final String label;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: accent.withValues(alpha: 0.12),
        border: Border.all(color: accent.withValues(alpha: 0.36)),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.bodySmall?.copyWith(
          color: Colors.white,
          fontWeight: FontWeight.w700,
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
