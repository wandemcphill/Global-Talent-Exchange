import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/match_playback_controller.dart';
import 'package:gte_frontend/data/live_match_fixtures.dart';
import 'package:gte_frontend/features/match/presentation/broadcast_package_models.dart';
import 'package:gte_frontend/features/match/presentation/broadcast_package_repository.dart';
import 'package:gte_frontend/features/match/widgets/gtex_matchday_ad_slot.dart';
import 'package:gte_frontend/data/match_gift_api.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_event.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/models/match_monetization.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/models/match_viewer_presentation.dart';
import 'package:gte_frontend/services/match_3d_bridge.dart';
import 'package:gte_frontend/services/match_3d_live_bootstrap_service.dart';
import 'package:gte_frontend/services/match_3d_monetization_service.dart';
import 'package:gte_frontend/services/match_commentary_engine.dart';
import 'package:gte_frontend/services/match_viewer_mapper.dart';
import 'package:gte_frontend/features/match/widgets/gtex_flash_split_ad_overlay.dart';
import 'package:gte_frontend/features/navigation/presentation/gte_navigation_shell_screen.dart';
import 'package:gte_frontend/services/ambient_audio_controller.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/match/broadcast/gtex_gifting_sheet.dart';
import 'package:gte_frontend/widgets/match/broadcast/gtex_gift_delivery_dialog.dart';
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
    this.initialReplayMinute,
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
  final int? initialReplayMinute;
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
  bool _showPreMatchBrief = false;
  int? _replayStartedMinute;

  AmbientAudioState? _ambientAudio;

  @override
  void initState() {
    super.initState();
    _showPreMatchBrief =
        widget.presentationMode == MatchViewerPresentationMode.broadcast;
    _viewStateFuture = _load();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    // Safely check if AmbientAudioState is available in ancestry or provider context
    try {
      final AmbientAudioState? audio = _findAmbientAudioState(context);
      if (_ambientAudio != audio) {
        _ambientAudio = audio;
        audio?.matchdayHandoff.enterMatchContext(
          widget.matchKey,
          currentContext: audio.currentContext,
        );
      }
    } catch (_) {}
  }

  @override
  void didUpdateWidget(covariant GtexMatchViewerScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.presentationMode != widget.presentationMode) {
      _showPreMatchBrief =
          widget.presentationMode == MatchViewerPresentationMode.broadcast;
    }
    if (oldWidget.initialReplayMinute != widget.initialReplayMinute) {
      _replayStartedMinute = null;
    }
    if (oldWidget.matchKey != widget.matchKey ||
        oldWidget.viewStateLoader != widget.viewStateLoader ||
        oldWidget.fallbackSnapshot != widget.fallbackSnapshot ||
        oldWidget.preferFallback != widget.preferFallback ||
        oldWidget.presentationMode != widget.presentationMode ||
        oldWidget.initialReplayMinute != widget.initialReplayMinute) {
      _reload();
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    _ambientAudio?.matchdayHandoff.leaveMatchContext();
    super.dispose();
  }

  AmbientAudioState? _findAmbientAudioState(BuildContext context) {
    final GteNavigationShellScreen? shell =
        context.findAncestorWidgetOfExactType<GteNavigationShellScreen>();
    if (shell?.ambientAudioController != null) {
      return shell!.ambientAudioController;
    }
    return null;
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

  /// Mounts the GTEX flash/split ad overlay from live monetization placements.
  /// Premium / ad-free viewers skip the overlay entirely.
  Widget _wrapWithMatchAds({
    required MatchViewState viewState,
    required double positionSeconds,
    required Widget child,
  }) {
    final MatchViewerMonetization monetization = viewState.monetization;
    if (!monetization.adsEnabled || monetization.premiumAdFree) {
      return child;
    }
    final MatchAdPlacement? flash =
        monetization.firstActiveOfType(
          MatchAdPlacementType.flash,
          positionSeconds,
        ) ??
        monetization.firstOfType(MatchAdPlacementType.flash) ??
        monetization.firstOfType(MatchAdPlacementType.preRoll);
    final MatchAdPlacement? split =
        monetization.firstActiveOfType(
          MatchAdPlacementType.split,
          positionSeconds,
        ) ??
        monetization.firstOfType(MatchAdPlacementType.split) ??
        monetization.firstOfType(MatchAdPlacementType.liveBanner);
    final String? flashBrand = flash?.brand.trim();
    final String? splitBrand = split?.brand.trim();
    if ((flashBrand == null || flashBrand.isEmpty) &&
        (splitBrand == null || splitBrand.isEmpty)) {
      return child;
    }
    return GtexFlashSplitAdOverlay(
      flashBrand: flashBrand,
      splitBrand: splitBrand,
      enableFlash: flashBrand != null && flashBrand.isNotEmpty,
      enableSplit: splitBrand != null && splitBrand.isNotEmpty,
      flashSeconds: flash == null
          ? 5
          : ((flash.activeUntilSecond ?? 5) - (flash.activeFromSecond ?? 0))
              .clamp(1, 5),
      splitSeconds: split == null
          ? 10
          : ((split.activeUntilSecond ?? 10) - (split.activeFromSecond ?? 0))
              .clamp(1, 10),
      child: child,
    );
  }

  Future<void> _openGiftSheet(MatchGiftTarget target) {
    final MatchGiftClient? client = widget.giftClient;
    return GtexGiftingSheet.show(
      context,
      unitLabel: _giftUnitLabelForScope(target.sourceScope),
      recipientLabel: target.recipientLabel,
      catalogLoader: client is MatchGiftCatalogProvider
          ? () => (client as MatchGiftCatalogProvider).fetchCatalog()
          : null,
      onSelected: (MatchGiftCatalogItem gift) => _sendGift(target, gift),
    );
  }

  Future<void> _sendGift(
    MatchGiftTarget target,
    MatchGiftCatalogItem gift,
  ) async {
    final MatchGiftClient? client = widget.giftClient;
    if (client == null) {
      return;
    }
    try {
      final MatchGiftReceipt receipt = await client.sendGift(
        target: target,
        gift: gift,
      );
      if (!mounted) {
        return;
      }
      await GtexGiftDeliveryDialog.show(
        context,
        gift: gift,
        receipt: receipt,
      );
    } catch (_) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Gift could not be sent.')));
    }
  }

  MatchPlaybackController _ensureController(MatchViewState viewState) {
    final MatchPlaybackController? existing = _controller;
    if (existing != null && existing.viewState.matchId == viewState.matchId) {
      return existing;
    }
    existing?.dispose();
    final bool hasStarted =
        viewState.frames.any(
          (MatchTimelineFrame frame) =>
              frame.clockMinute > 0 ||
              frame.homeScore > 0 ||
              frame.awayScore > 0 ||
              frame.phase == MatchViewerPhase.halftime ||
              frame.phase == MatchViewerPhase.fulltime,
        ) ||
        viewState.events.any(
          (MatchEvent event) =>
              event.type == MatchViewerEventType.kickoff ||
              event.type == MatchViewerEventType.goal ||
              event.minute > 0,
        );
    final MatchPlaybackController created = MatchPlaybackController(
      vsync: this,
      viewState: viewState,
      autoplay: widget.presentationMode != MatchViewerPresentationMode.broadcast ||
          widget.initialReplayMinute != null ||
          hasStarted,
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
            final MatchGiftTarget? giftTarget = MatchGiftTarget.fromMetadata(
              viewState.monetization.metadata,
            );
            final bool matchHasStarted =
                viewState.frames.any(
                  (MatchTimelineFrame frame) =>
                      frame.clockMinute > 0 ||
                      frame.homeScore > 0 ||
                      frame.awayScore > 0 ||
                      frame.phase == MatchViewerPhase.halftime ||
                      frame.phase == MatchViewerPhase.fulltime,
                ) ||
                viewState.events.any(
                  (MatchEvent event) =>
                      event.type == MatchViewerEventType.kickoff ||
                      event.type == MatchViewerEventType.goal ||
                      event.minute > 0,
                );
            if (_showPreMatchBrief && !matchHasStarted) {
              final MatchPlaybackController? preMatchController =
                  viewState.frames.isEmpty ? null : _ensureController(viewState);
              final MatchPresentationPackage package =
                  BroadcastPackageRepository().resolve(viewState);
              return _MatchPreGameBrief(
                package: package,
                competitionName: widget.competition.name,
                canStart: preMatchController != null,
                onStart: () {
                  if (!mounted) return;
                  if (preMatchController == null) {
                    _reload();
                    return;
                  }
                  setState(() => _showPreMatchBrief = false);
                  preMatchController.play();
                },
                onRefresh: _reload,
              );
            }
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
            final int? replayMinute = widget.initialReplayMinute;
            if (replayMinute != null && _replayStartedMinute != replayMinute) {
              final List<MatchEvent> goals = viewState.events
                  .where((MatchEvent event) => event.type == MatchViewerEventType.goal)
                  .toList(growable: true);
              final List<MatchEvent> targets = goals.isNotEmpty
                  ? goals
                  : viewState.events.toList(growable: true);
              if (targets.isNotEmpty) {
                targets.sort((MatchEvent a, MatchEvent b) =>
                    (a.minute - replayMinute).abs().compareTo(
                      (b.minute - replayMinute).abs(),
                    ));
                final MatchEvent targetEvent = targets.first;
                _replayStartedMinute = replayMinute;
                WidgetsBinding.instance.addPostFrameCallback((_) {
                  if (mounted && identical(_controller, controller)) {
                    controller.replayEvent(targetEvent);
                  }
                });
              }
            }
            return ListenableBuilder(
              listenable: controller,
              builder: (BuildContext context, Widget? child) {
                final MatchTimelineFrame frame = controller.displayFrame;
                final MatchEvent? activeEvent = controller.activeEvent;
                final MatchEvent? activeGoalEvent =
                    activeEvent?.type == MatchViewerEventType.goal
                        ? activeEvent
                        : null;
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
                          child: _wrapWithMatchAds(
                            viewState: viewState,
                            positionSeconds: controller.positionSeconds,
                            child: _MatchLiveLayout(
                              viewState: viewState,
                              frame: frame,
                              previousFrame: controller.leftFrame,
                              activeEvent: activeEvent,
                              positionSeconds: controller.positionSeconds,
                              controller: controller,
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
                        if (activeGoalEvent != null) ...<Widget>[
                          const SizedBox(height: 4),
                          Align(
                            alignment: Alignment.center,
                            child: FilledButton.tonalIcon(
                              key: const Key('match-2d-replay-active-goal'),
                              onPressed: () => controller.replayEvent(activeGoalEvent),
                              icon: const Icon(Icons.replay_circle_filled_rounded),
                              label: Text('REPLAY GOAL · ${activeGoalEvent.minute}\''),
                            ),
                          ),
                        ],
                        if (widget.giftClient != null &&
                            giftTarget != null) ...<Widget>[
                          const SizedBox(height: 8),
                          _GiftActionButton(
                            recipientLabel: giftTarget.recipientLabel,
                            onPressed: () => _openGiftSheet(giftTarget),
                          ),
                        ],
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

class _GiftActionButton extends StatelessWidget {
  const _GiftActionButton({
    required this.recipientLabel,
    required this.onPressed,
  });

  final String recipientLabel;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.center,
      child: FilledButton.icon(
        key: const Key('match-2d-gift-button'),
        onPressed: onPressed,
        icon: const Icon(Icons.card_giftcard_outlined),
        label: Text(
          'Gift $recipientLabel',
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
        style: FilledButton.styleFrom(
          backgroundColor: const Color(0xFF7DD3FC),
          foregroundColor: const Color(0xFF07111D),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          minimumSize: const Size(0, 40),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        ),
      ),
    );
  }
}

class _MatchLiveLayout extends StatelessWidget {
  const _MatchLiveLayout({
    required this.viewState,
    required this.frame,
    required this.previousFrame,
    required this.activeEvent,
    required this.positionSeconds,
    required this.controller,
  });

  final MatchViewState viewState;
  final MatchTimelineFrame frame;
  final MatchTimelineFrame previousFrame;
  final MatchEvent? activeEvent;
  final double positionSeconds;
  final MatchPlaybackController controller;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final bool wide = constraints.maxWidth >= 980;
        final Widget pitch = _PitchStage(
          viewState: viewState,
          frame: frame,
          previousFrame: previousFrame,
          activeEvent: activeEvent,
        );
        final Widget insightPanel = _MatchInsightPanel(
          viewState: viewState,
          frame: frame,
          activeEvent: activeEvent,
          positionSeconds: positionSeconds,
          compact: !wide,
          controller: controller,
        );

        if (wide) {
          return Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              Expanded(flex: 7, child: pitch),
              const SizedBox(width: 10),
              SizedBox(width: 330, child: insightPanel),
            ],
          );
        }

        final double panelHeight =
            math
                .min(190, math.max(72, constraints.maxHeight * 0.34))
                .toDouble();
        return Column(
          children: <Widget>[
            Expanded(child: pitch),
            const SizedBox(height: 8),
            SizedBox(height: panelHeight, child: insightPanel),
          ],
        );
      },
    );
  }
}

class _PitchStage extends StatelessWidget {
  const _PitchStage({
    required this.viewState,
    required this.frame,
    required this.previousFrame,
    required this.activeEvent,
  });

  final MatchViewState viewState;
  final MatchTimelineFrame frame;
  final MatchTimelineFrame previousFrame;
  final MatchEvent? activeEvent;

  @override
  Widget build(BuildContext context) {
    return Container(
      key: const Key('match-2d-pitch-stage'),
      decoration: BoxDecoration(
        color: const Color(0x66111827),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      clipBehavior: Clip.antiAlias,
      child: Center(
        child: Padding(
          padding: const EdgeInsets.all(6),
          child: MatchPitch2D(
            viewState: viewState,
            frame: frame,
            previousFrame: previousFrame,
            activeEvent: activeEvent,
          ),
        ),
      ),
    );
  }
}

class _MatchInsightPanel extends StatelessWidget {
  const _MatchInsightPanel({
    required this.viewState,
    required this.frame,
    required this.activeEvent,
    required this.positionSeconds,
    required this.compact,
    required this.controller,
  });

  final MatchViewState viewState;
  final MatchTimelineFrame frame;
  final MatchEvent? activeEvent;
  final double positionSeconds;
  final bool compact;
  final MatchPlaybackController controller;

  @override
  Widget build(BuildContext context) {
    final Widget body =
        compact
            ? SingleChildScrollView(
              padding: const EdgeInsets.all(8),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  _TacticalSummary(viewState: viewState, frame: frame),
                  const SizedBox(height: 8),
                  _MatchTeamSheetExpansion(
                    viewState: viewState,
                    compact: true,
                  ),
                  const SizedBox(height: 8),
                  _PlayerPanels(
                    viewState: viewState,
                    frame: frame,
                    activeEvent: activeEvent,
                    compact: true,
                  ),
                  const SizedBox(height: 8),
                  _EventFeed(
                    events: _feedEventsForPosition(
                      events: viewState.events,
                      positionSeconds: positionSeconds,
                    ),
                    activeEvent: activeEvent,
                    compact: true,
                    controller: controller,
                  ),
                ],
              ),
            )
            : Padding(
              padding: const EdgeInsets.all(8),
              child: Column(
                children: <Widget>[
                  _TacticalSummary(viewState: viewState, frame: frame),
                  const SizedBox(height: 8),
                  _PlayerPanels(
                    viewState: viewState,
                    frame: frame,
                    activeEvent: activeEvent,
                    compact: false,
                  ),
                  const SizedBox(height: 8),
                  _MatchTeamSheetExpansion(
                    viewState: viewState,
                    compact: false,
                  ),
                  const SizedBox(height: 8),
                  Expanded(
                    child: _EventFeed(
                      events: _feedEventsForPosition(
                        events: viewState.events,
                        positionSeconds: positionSeconds,
                      ),
                      activeEvent: activeEvent,
                      compact: false,
                      controller: controller,
                    ),
                  ),
                ],
              ),
            );

    return Container(
      key: const Key('match-2d-live-panel'),
      decoration: BoxDecoration(
        color: const Color(0xD90B1220),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.white.withValues(alpha: 0.10)),
      ),
      clipBehavior: Clip.antiAlias,
      child: body,
    );
  }
}

class _MatchTeamSheetExpansion extends StatelessWidget {
  const _MatchTeamSheetExpansion({
    required this.viewState,
    required this.compact,
  });

  final MatchViewState viewState;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final MatchPresentationPackage package =
        BroadcastPackageRepository().resolve(viewState);
    return Container(
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.035),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(8),
        clipBehavior: Clip.antiAlias,
        child: ExpansionTile(
        key: const Key('match-2d-official-team-sheets'),
        tilePadding: const EdgeInsets.symmetric(horizontal: 10),
        childrenPadding: const EdgeInsets.fromLTRB(8, 0, 8, 10),
        iconColor: const Color(0xFFF0C66B),
        collapsedIconColor: Colors.white70,
        title: const Text(
          'Official lineups & bench',
          style: TextStyle(
            color: Colors.white,
            fontSize: 12,
            fontWeight: FontWeight.w900,
          ),
        ),
        subtitle: Text(
          '${package.home.formation} · ${package.home.coachName ?? 'Home manager'}  /  '
          '${package.away.formation} · ${package.away.coachName ?? 'Away manager'}',
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(color: Color(0xFFB7C3D0), fontSize: 10),
        ),
        children: <Widget>[
          SizedBox(
            height: compact ? 245 : 225,
            child: SingleChildScrollView(
              child: Column(
                children: <Widget>[
                  _PreMatchTeamSheet(team: package.home),
                  const SizedBox(height: 8),
                  _PreMatchTeamSheet(team: package.away),
                ],
              ),
            ),
          ),
        ],
        ),
      ),
    );
  }
}

class _TacticalSummary extends StatelessWidget {
  const _TacticalSummary({required this.viewState, required this.frame});

  final MatchViewState viewState;
  final MatchTimelineFrame frame;

  @override
  Widget build(BuildContext context) {
    final String possession =
        frame.possessionSide == MatchViewerSide.home
            ? viewState.homeTeam.shortName
            : viewState.awayTeam.shortName;
    final String shape =
        '${viewState.homeTeam.formation} / ${viewState.awayTeam.formation}';
    final String pressure = '${(_pressureIndex(frame) * 100).round()}%';

    return _PanelBlock(
      key: const Key('match-2d-tactical-summary'),
      title: 'Tactical Overlay',
      child: Wrap(
        spacing: 6,
        runSpacing: 6,
        children: <Widget>[
          _InfoChip(label: 'Shape', value: shape),
          _InfoChip(label: 'Heat', value: _heatZoneLabel(frame)),
          _InfoChip(label: 'Press', value: pressure),
          _InfoChip(label: 'Ball', value: possession),
        ],
      ),
    );
  }
}

class _PlayerPanels extends StatelessWidget {
  const _PlayerPanels({
    required this.viewState,
    required this.frame,
    required this.activeEvent,
    required this.compact,
  });

  final MatchViewState viewState;
  final MatchTimelineFrame frame;
  final MatchEvent? activeEvent;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final Widget home = _TeamPlayerPanel(
      team: viewState.homeTeam,
      players: _focusPlayers(
        frame: frame,
        side: MatchViewerSide.home,
        limit: compact ? 2 : 3,
      ),
      activeEvent: activeEvent,
    );
    final Widget away = _TeamPlayerPanel(
      team: viewState.awayTeam,
      players: _focusPlayers(
        frame: frame,
        side: MatchViewerSide.away,
        limit: compact ? 2 : 3,
      ),
      activeEvent: activeEvent,
    );

    return _PanelBlock(
      key: const Key('match-2d-player-panels'),
      title: 'Player Panels',
      child:
          compact
              ? Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Expanded(child: home),
                  const SizedBox(width: 8),
                  Expanded(child: away),
                ],
              )
              : Column(
                children: <Widget>[home, const SizedBox(height: 8), away],
              ),
    );
  }
}

class _TeamPlayerPanel extends StatelessWidget {
  const _TeamPlayerPanel({
    required this.team,
    required this.players,
    required this.activeEvent,
  });

  final MatchViewerTeam team;
  final List<MatchViewerPlayerFrame> players;
  final MatchEvent? activeEvent;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              _TeamDot(color: _parseHexColor(team.primaryColorHex)),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  '${team.shortName} ${team.formation}',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.w900,
                    letterSpacing: 0,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 7),
          for (final MatchViewerPlayerFrame player in players)
            _PlayerFocusRow(
              player: player,
              teamColor: _parseHexColor(team.primaryColorHex),
              label: _playerDisplayLabel(player, activeEvent),
            ),
        ],
      ),
    );
  }
}

class _PlayerFocusRow extends StatelessWidget {
  const _PlayerFocusRow({
    required this.player,
    required this.teamColor,
    required this.label,
  });

  final MatchViewerPlayerFrame player;
  final Color teamColor;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 5),
      child: Row(
        children: <Widget>[
          CircleAvatar(
            radius: 13,
            backgroundColor: teamColor,
            child: Text(
              _avatarLabel(player),
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: _textColorFor(teamColor),
                fontWeight: FontWeight.w900,
                letterSpacing: 0,
              ),
            ),
          ),
          const SizedBox(width: 7),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0,
                  ),
                ),
                Text(
                  '${player.animationState.label} - ${player.staminaPct.clamp(0, 100)}%',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: Colors.white.withValues(alpha: 0.62),
                    letterSpacing: 0,
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

class _EventFeed extends StatelessWidget {
  const _EventFeed({
    required this.events,
    required this.activeEvent,
    required this.compact,
    required this.controller,
  });

  final List<MatchEvent> events;
  final MatchEvent? activeEvent;
  final bool compact;
  final MatchPlaybackController controller;

  @override
  Widget build(BuildContext context) {
    final List<Widget> tiles = events
        .map(
          (MatchEvent event) => _EventFeedTile(
            event: event,
            active: activeEvent?.id == event.id,
            onReplayGoal: () => controller.replayEvent(event),
          ),
        )
        .toList(growable: false);

    return _PanelBlock(
      key: const Key('match-2d-event-feed'),
      title: 'Event Feed',
      expandChild: !compact,
      child:
          compact
              ? Column(children: tiles.take(4).toList(growable: false))
              : ListView(padding: EdgeInsets.zero, children: tiles),
    );
  }
}

class _EventFeedTile extends StatelessWidget {
  const _EventFeedTile({
    required this.event,
    required this.active,
    required this.onReplayGoal,
  });

  final MatchEvent event;
  final bool active;
  final VoidCallback onReplayGoal;

  @override
  Widget build(BuildContext context) {
    final Color accent =
        active ? const Color(0xFF7DD3FC) : Colors.white.withValues(alpha: 0.42);
    return Container(
      margin: const EdgeInsets.only(top: 6),
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color:
            active
                ? const Color(0x1F7DD3FC)
                : Colors.white.withValues(alpha: 0.04),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: accent.withValues(alpha: active ? 0.55 : 1)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(event.icon, color: accent, size: 17),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  "${event.minute}'  ${event.bannerText}",
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  MatchCommentaryEngine.lineForEvent(event),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: Colors.white.withValues(alpha: 0.66),
                    letterSpacing: 0,
                  ),
                ),
                if (event.type == MatchViewerEventType.goal)
                  Align(
                    alignment: Alignment.centerLeft,
                    child: TextButton.icon(
                      key: Key('match-2d-replay-goal-${event.id}'),
                      onPressed: onReplayGoal,
                      icon: const Icon(Icons.replay_rounded, size: 15),
                      label: Text('Replay goal · ${event.minute}\''),
                      style: TextButton.styleFrom(
                        foregroundColor: const Color(0xFFFDE68A),
                        padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
                        minimumSize: const Size(0, 30),
                        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                      ),
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

class _PanelBlock extends StatelessWidget {
  const _PanelBlock({
    super.key,
    required this.title,
    required this.child,
    this.expandChild = false,
  });

  final String title;
  final Widget child;
  final bool expandChild;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.16),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.white.withValues(alpha: 0.07)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: expandChild ? MainAxisSize.max : MainAxisSize.min,
        children: <Widget>[
          Text(
            title,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
              color: Colors.white.withValues(alpha: 0.86),
              fontWeight: FontWeight.w900,
              letterSpacing: 0,
            ),
          ),
          const SizedBox(height: 6),
          if (expandChild) Expanded(child: child) else child,
        ],
      ),
    );
  }
}

class _InfoChip extends StatelessWidget {
  const _InfoChip({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(minHeight: 26),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Text(
        '$label $value',
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
          color: Colors.white.withValues(alpha: 0.82),
          fontWeight: FontWeight.w800,
          letterSpacing: 0,
        ),
      ),
    );
  }
}

class _TeamDot extends StatelessWidget {
  const _TeamDot({required this.color});

  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 10,
      height: 10,
      decoration: BoxDecoration(
        color: color,
        shape: BoxShape.circle,
        border: Border.all(color: Colors.white.withValues(alpha: 0.65)),
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
  if (activeEvent != null) {
    return MatchCommentaryEngine.lineForEvent(activeEvent, frame: frame);
  }
  final String? banner = frame.eventBanner?.trim();
  if (banner != null && banner.isNotEmpty) {
    return banner;
  }
  return MatchCommentaryEngine.fallbackForFrame(frame);
}

List<MatchEvent> _feedEventsForPosition({
  required List<MatchEvent> events,
  required double positionSeconds,
}) {
  final List<MatchEvent> visible = events
      .where((MatchEvent event) => event.timeSeconds <= positionSeconds + 12)
      .toList(growable: true);
  if (visible.isEmpty) {
    return events.take(4).toList(growable: false);
  }
  visible.sort(
    (MatchEvent left, MatchEvent right) =>
        right.timeSeconds.compareTo(left.timeSeconds),
  );
  return visible.take(6).toList(growable: false);
}

List<MatchViewerPlayerFrame> _focusPlayers({
  required MatchTimelineFrame frame,
  required MatchViewerSide side,
  required int limit,
}) {
  final List<MatchViewerPlayerFrame> players = frame.players
      .where((MatchViewerPlayerFrame player) => player.side == side)
      .where((MatchViewerPlayerFrame player) => player.active)
      .toList(growable: true);
  players.sort((MatchViewerPlayerFrame left, MatchViewerPlayerFrame right) {
    return _playerFocusScore(
      frame,
      right,
    ).compareTo(_playerFocusScore(frame, left));
  });
  return players.take(limit).toList(growable: false);
}

int _playerFocusScore(MatchTimelineFrame frame, MatchViewerPlayerFrame player) {
  int score = 0;
  if (frame.ball.ownerPlayerId == player.playerId) {
    score += 100;
  }
  if (player.highlighted) {
    score += 60;
  }
  if (player.state == MatchViewerPlayerState.attacking ||
      player.state == MatchViewerPlayerState.pressing ||
      player.state == MatchViewerPlayerState.moving) {
    score += 18;
  }
  if (player.line == MatchPlayerLine.attack) {
    score += 8;
  }
  if (player.line == MatchPlayerLine.midfield) {
    score += 4;
  }
  return score;
}

String _playerDisplayLabel(
  MatchViewerPlayerFrame player,
  MatchEvent? activeEvent,
) {
  if (activeEvent?.primaryPlayerId == player.playerId &&
      (activeEvent?.primaryPlayerName ?? '').trim().isNotEmpty) {
    return activeEvent!.primaryPlayerName!.trim();
  }
  if (activeEvent?.secondaryPlayerId == player.playerId &&
      (activeEvent?.secondaryPlayerName ?? '').trim().isNotEmpty) {
    return activeEvent!.secondaryPlayerName!.trim();
  }
  final String label = player.label.trim();
  if (label.isNotEmpty && int.tryParse(label) == null) {
    return label;
  }
  final int? shirtNumber = player.shirtNumber;
  return shirtNumber == null ? 'Player $label' : 'Player $shirtNumber';
}

String _avatarLabel(MatchViewerPlayerFrame player) {
  final int? shirtNumber = player.shirtNumber;
  if (shirtNumber != null) {
    return shirtNumber.toString();
  }
  final String label = player.label.trim();
  if (label.isEmpty) {
    return '?';
  }
  return label.length <= 2 ? label : label.substring(0, 2);
}

String _heatZoneLabel(MatchTimelineFrame frame) {
  final String? explicit = frame.dangerZone?.trim();
  if (explicit != null && explicit.isNotEmpty) {
    return explicit.replaceAll('_', ' ');
  }
  switch (frame.possessionPhase) {
    case MatchPossessionPhase.boxAttack:
      return 'box';
    case MatchPossessionPhase.finalThird:
      return 'final third';
    case MatchPossessionPhase.transition:
      return 'transition';
    case MatchPossessionPhase.setPiece:
    case MatchPossessionPhase.restart:
      return 'set piece';
    case MatchPossessionPhase.buildUp:
      return 'build up';
    case MatchPossessionPhase.attack:
      return 'attack';
    case MatchPossessionPhase.recovery:
      return 'recovery';
    case MatchPossessionPhase.stoppage:
    case MatchPossessionPhase.deadBall:
      return 'stoppage';
    case MatchPossessionPhase.control:
    case null:
      return 'middle';
  }
}

double _pressureIndex(MatchTimelineFrame frame) {
  final double? explicit = frame.pressureIndex;
  if (explicit != null) {
    return explicit.clamp(0.08, 1.0).toDouble();
  }
  return switch (frame.possessionPhase) {
    MatchPossessionPhase.boxAttack => 0.82,
    MatchPossessionPhase.finalThird => 0.68,
    MatchPossessionPhase.attack => 0.54,
    MatchPossessionPhase.transition => 0.58,
    MatchPossessionPhase.setPiece => 0.62,
    MatchPossessionPhase.restart => 0.44,
    MatchPossessionPhase.buildUp => 0.42,
    MatchPossessionPhase.recovery => 0.30,
    MatchPossessionPhase.stoppage || MatchPossessionPhase.deadBall => 0.22,
    MatchPossessionPhase.control || null => 0.34,
  };
}

Color _parseHexColor(String value) {
  final String normalized = value.replaceAll('#', '').trim();
  final String hex = normalized.length == 6 ? 'FF$normalized' : normalized;
  return Color(int.tryParse(hex, radix: 16) ?? 0xFF2563EB);
}

Color _textColorFor(Color fill) {
  return fill.computeLuminance() > 0.45
      ? const Color(0xFF111827)
      : Colors.white;
}

String _giftUnitLabelForScope(String sourceScope) {
  final String normalized = sourceScope.trim().toLowerCase();
  if (normalized == 'gtex' ||
      normalized == 'gtex_platform' ||
      normalized == 'gtex_competition') {
    return 'GTEX Coin';
  }
  return 'Fan Coin';
}




class _MatchPreGameBrief extends StatelessWidget {
  const _MatchPreGameBrief({
    required this.package,
    required this.competitionName,
    required this.canStart,
    required this.onStart,
    required this.onRefresh,
  });

  final MatchPresentationPackage package;
  final String competitionName;
  final bool canStart;
  final VoidCallback onStart;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1400),
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: <Widget>[
                  const Row(
                    children: <Widget>[
                      Icon(Icons.sports_soccer_rounded, color: Color(0xFFF0C66B), size: 25),
                      SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Text('GTEX MATCHDAY STUDIO', style: TextStyle(
                              color: Color(0xFFF0C66B), fontWeight: FontWeight.w900,
                              letterSpacing: 1.6, fontSize: 11,
                            )),
                            SizedBox(height: 3),
                            Text('Match preview & official team sheets', style: TextStyle(
                              color: Colors.white, fontWeight: FontWeight.w800, fontSize: 18,
                            )),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(competitionName, style: TextStyle(color: Colors.white60, fontSize: 12)),
                  const SizedBox(height: 14),
                  Container(
                    padding: const EdgeInsets.all(18),
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        begin: Alignment.topLeft, end: Alignment.bottomRight,
                        colors: <Color>[Color(0xFF172638), Color(0xFF09121D)],
                      ),
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(color: const Color(0x55F0C66B)),
                    ),
                    child: Column(
                      children: <Widget>[
                        Text(package.matchLabel.toUpperCase(), textAlign: TextAlign.center,
                          style: const TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.w900)),
                        const SizedBox(height: 12),
                        Row(
                          children: <Widget>[
                            Expanded(child: _PreMatchFormationBadge(team: package.home)),
                            const Padding(
                              padding: EdgeInsets.symmetric(horizontal: 12),
                              child: Text('VS', style: TextStyle(color: Color(0xFFF0C66B), fontWeight: FontWeight.w900, fontSize: 13)),
                            ),
                            Expanded(child: _PreMatchFormationBadge(team: package.away)),
                          ],
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 14),
                  LayoutBuilder(
                    builder: (BuildContext context, BoxConstraints constraints) {
                      if (constraints.maxWidth >= 860) {
                        return Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Expanded(child: _PreMatchTeamSheet(team: package.home)),
                            const SizedBox(width: 12),
                            Expanded(child: _PreMatchTeamSheet(team: package.away)),
                          ],
                        );
                      }
                      return Column(children: <Widget>[
                        _PreMatchTeamSheet(team: package.home),
                        const SizedBox(height: 12),
                        _PreMatchTeamSheet(team: package.away),
                      ]);
                    },
                  ),
                  const SizedBox(height: 14),
                  const GtexMatchdayAdSlot(placement: 'Pre-match broadcast & team-sheet programme'),
                  const SizedBox(height: 14),
                  SizedBox(
                    height: 52,
                    child: FilledButton.icon(
                      key: const Key('gtex-matchday-start-broadcast'),
                      onPressed: canStart ? onStart : onRefresh,
                      icon: Icon(canStart ? Icons.play_arrow_rounded : Icons.refresh_rounded, size: 24),
                      label: Text(
                        canStart ? 'WATCH 2D MATCH' : 'CHECK FOR MATCH TIMELINE',
                        style: const TextStyle(fontWeight: FontWeight.w900, letterSpacing: 1),
                      ),
                      style: FilledButton.styleFrom(backgroundColor: const Color(0xFFF0C66B), foregroundColor: const Color(0xFF101722)),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _PreMatchFormationBadge extends StatelessWidget {
  const _PreMatchFormationBadge({required this.team});
  final MatchPresentationTeam team;

  @override
  Widget build(BuildContext context) {
    final Color accent = _parseHexColor(team.primaryColorHex ?? '#1DBF73');
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.20),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: accent.withValues(alpha: 0.55)),
      ),
      child: Column(
        children: <Widget>[
          Text(team.shortName.isEmpty ? team.teamName : team.shortName, maxLines: 1,
            overflow: TextOverflow.ellipsis, textAlign: TextAlign.center,
            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 13)),
          const SizedBox(height: 3),
          Text(team.formation, style: TextStyle(color: accent, fontWeight: FontWeight.w900, fontSize: 22)),
          if (team.coachName?.trim().isNotEmpty == true) ...<Widget>[
            const SizedBox(height: 3),
            Text(team.coachName!, maxLines: 1, overflow: TextOverflow.ellipsis, textAlign: TextAlign.center,
              style: const TextStyle(color: Color(0xFFC1CEDB), fontSize: 11)),
          ],
        ],
      ),
    );
  }
}

class _PreMatchTeamSheet extends StatelessWidget {
  const _PreMatchTeamSheet({required this.team});
  final MatchPresentationTeam team;

  @override
  Widget build(BuildContext context) {
    final Color accent = _parseHexColor(team.primaryColorHex ?? '#1DBF73');
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xD90B1420), borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white.withValues(alpha: 0.10)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Container(width: 4, height: 32, decoration: BoxDecoration(color: accent, borderRadius: BorderRadius.circular(4))),
              const SizedBox(width: 9),
              Expanded(child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(team.teamName, maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 16)),
                  Text('FORMATION ${team.formation}', style: TextStyle(color: accent, fontWeight: FontWeight.w900, fontSize: 10, letterSpacing: 0.8)),
                ],
              )),
              if (team.recentForm != null) _PreMatchTag(label: 'FORM ${team.recentForm}%'),
            ],
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 7, runSpacing: 7,
            children: <Widget>[
              _PreMatchTag(label: "Manager: ${team.coachName?.trim().isNotEmpty == true ? team.coachName!.trim() : 'Not supplied'}"),
              if (team.mentality?.trim().isNotEmpty == true)
                _PreMatchTag(label: 'Mentality: ${team.mentality!.replaceAll('_', ' ')}'),
              for (final String instruction in team.instructionSummary.take(2))
                _PreMatchTag(label: instruction),
            ],
          ),
          const SizedBox(height: 14),
          const Text('STARTING XI', style: TextStyle(color: Color(0xFFC1CEDB), fontSize: 10, fontWeight: FontWeight.w900, letterSpacing: 1)),
          const SizedBox(height: 6),
          if (team.starters.isEmpty)
            const Text('Starting-player details were not supplied for this team.', style: TextStyle(color: Color(0xFF8797A8), fontSize: 11))
          else
            for (final MatchPresentationPlayer player in team.starters)
              _PreMatchPlayerRow(player: player, accent: accent),
          const SizedBox(height: 10),
          const Divider(color: Color(0x243F5063)),
          const SizedBox(height: 7),
          Row(
            children: <Widget>[
              const Icon(Icons.sync_alt_rounded, color: Color(0xFFF0C66B), size: 16),
              const SizedBox(width: 7),
              const Expanded(child: Text('SUBSTITUTES', style: TextStyle(color: Color(0xFFC1CEDB), fontSize: 10, fontWeight: FontWeight.w900, letterSpacing: 1))),
              Text('${team.bench.length} listed', style: const TextStyle(color: Color(0xFF8797A8), fontSize: 10)),
            ],
          ),
          const SizedBox(height: 6),
          if (team.bench.isEmpty)
            const Text('Substitute list not supplied by the official match package.', style: TextStyle(color: Color(0xFF8797A8), fontSize: 11))
          else
            Wrap(
              spacing: 6, runSpacing: 6,
              children: team.bench.map((MatchPresentationPlayer player) {
                final String shirt = player.shirtNumber == null ? '' : '#${player.shirtNumber} ';
                return Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.04), borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: <Widget>[
                      Text(
                        '${shirt}${player.playerName}',
                        style: const TextStyle(
                          color: Color(0xFFD2DBE4),
                          fontSize: 10,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      if (player.role?.trim().isNotEmpty == true ||
                          player.rating != null) ...<Widget>[
                        const SizedBox(height: 3),
                        Text(
                          <String>[
                            if (player.role?.trim().isNotEmpty == true)
                              player.role!.replaceAll('_', ' ').toUpperCase(),
                            if (player.rating != null)
                              'OVR ${player.rating!.toStringAsFixed(1)}',
                          ].join(' · '),
                          style: const TextStyle(
                            color: Color(0xFFF0C66B),
                            fontSize: 8,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      ],
                    ],
                  ),
                );
              }).toList(growable: false),
            ),
        ],
      ),
    );
  }
}

class _PreMatchPlayerRow extends StatelessWidget {
  const _PreMatchPlayerRow({required this.player, required this.accent});
  final MatchPresentationPlayer player;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    final Widget portrait = Container(
      width: 30, height: 30, clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(color: accent.withValues(alpha: 0.12), shape: BoxShape.circle, border: Border.all(color: accent.withValues(alpha: 0.45))),
      child: player.hasPortrait
          ? Image.network(player.portraitUrl!, fit: BoxFit.cover,
              errorBuilder: (BuildContext context, Object error, StackTrace? stackTrace) => const Icon(Icons.person, color: Colors.white70, size: 16))
          : const Icon(Icons.person, color: Colors.white70, size: 16),
    );
    return Container(
      margin: const EdgeInsets.only(bottom: 5),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
      decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.035), borderRadius: BorderRadius.circular(7)),
      child: Row(
        children: <Widget>[
          portrait,
          const SizedBox(width: 8),
          SizedBox(
            width: 28,
            child: Text(player.shirtNumber == null ? '—' : '${player.shirtNumber}',
              style: TextStyle(color: accent, fontWeight: FontWeight.w900, fontSize: 11)),
          ),
          Expanded(child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(player.playerName, maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 11)),
              Text(player.role?.trim().isNotEmpty == true ? player.role!.replaceAll('_', ' ').toUpperCase() : 'PLAYER',
                style: const TextStyle(color: Color(0xFF8797A8), fontSize: 9)),
            ],
          )),
          if (player.rating != null)
            Text(player.rating!.toStringAsFixed(1), style: const TextStyle(color: Color(0xFFF0C66B), fontWeight: FontWeight.w900, fontSize: 11)),
        ],
      ),
    );
  }
}

class _PreMatchTag extends StatelessWidget {
  const _PreMatchTag({required this.label});
  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.045), borderRadius: BorderRadius.circular(5),
        border: Border.all(color: Colors.white.withValues(alpha: 0.10)),
      ),
      child: Text(label, style: const TextStyle(color: Color(0xFFC1CEDB), fontSize: 10, fontWeight: FontWeight.w700)),
    );
  }
}
