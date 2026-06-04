import 'dart:async';

import 'package:flutter/material.dart';
import 'package:gte_frontend/core/app_feedback.dart';
import 'package:gte_frontend/features/match_center/data/match_gift_api.dart';

import 'package:gte_frontend/features/compete/domain/competition_models.dart';
import 'package:gte_frontend/features/match_center/models/match/gtex_broadcast_hud_state.dart';
import 'package:gte_frontend/features/match_center/models/match/gtex_match_render_mode.dart';
import 'package:gte_frontend/features/match_center/models/match/gtex_match_view_type.dart';
import 'package:gte_frontend/features/match_center/models/match_event.dart';
import 'package:gte_frontend/features/match_center/models/match_timeline_frame.dart';
import 'package:gte_frontend/features/match_center/models/match_view_state.dart';
import '../../../widgets/gte_shell_theme.dart';
import '../../../widgets/gte_state_panel.dart';
import '../../../widgets/gte_surface_panel.dart';
import '../widgets/broadcast/gtex_gifting_sheet.dart';
import '../widgets/broadcast/gtex_match_canvas_layer.dart';
import 'broadcast_package_models.dart';
import 'broadcast_package_repository.dart';
import 'broadcast_scene_director.dart';
import 'widgets/commentary_ribbon_widget.dart';
import 'widgets/formation_board_widget.dart';
import 'widgets/match_header_widget.dart';
import 'widgets/roster_card_widget.dart';
import 'widgets/scorebug_widget.dart';
import 'widgets/standings_context_widget.dart';
import 'widgets/storyline_panel_widget.dart';

typedef BroadcastPackageViewStateLoader = Future<MatchViewState> Function();

class BroadcastPackageScreen extends StatefulWidget {
  const BroadcastPackageScreen({
    super.key,
    required this.matchKey,
    required this.competition,
    required this.viewStateLoader,
    this.initialViewState,
    this.giftClient,
  });

  final String matchKey;
  final CompetitionSummary competition;
  final BroadcastPackageViewStateLoader viewStateLoader;
  final MatchViewState? initialViewState;
  final MatchGiftClient? giftClient;

  @override
  State<BroadcastPackageScreen> createState() => _BroadcastPackageScreenState();
}

class _BroadcastPackageScreenState extends State<BroadcastPackageScreen> {
  final BroadcastPackageRepository _packageRepository =
      const BroadcastPackageRepository();

  late Future<MatchViewState> _viewStateFuture;
  String? _giftStatusMessage;

  @override
  void initState() {
    super.initState();
    _viewStateFuture = _resolveViewState();
  }

  @override
  void didUpdateWidget(covariant BroadcastPackageScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.matchKey == widget.matchKey &&
        identical(oldWidget.initialViewState, widget.initialViewState)) {
      return;
    }
    _viewStateFuture = _resolveViewState();
  }

  @override
  void dispose() {
    super.dispose();
  }

  void _reload() {
    setState(() {
      _viewStateFuture = widget.viewStateLoader();
    });
  }

  Future<MatchViewState> _resolveViewState() {
    final MatchViewState? initialViewState = widget.initialViewState;
    if (initialViewState != null) {
      return Future<MatchViewState>.value(initialViewState);
    }
    return widget.viewStateLoader();
  }

  MatchGiftTarget? _giftTargetFor(MatchViewState viewState) {
    if (widget.giftClient == null) {
      return null;
    }
    return MatchGiftTarget.fromMetadata(viewState.engagement.metadata);
  }

  Future<void> _openGiftSheet(MatchViewState viewState) async {
    if (_giftTargetFor(viewState) == null) {
      return;
    }
    await GtexGiftingSheet.show(
      context,
      onSelected: (MatchGiftCatalogItem gift) => _sendGift(viewState, gift),
    );
  }

  Future<void> _sendGift(
    MatchViewState viewState,
    MatchGiftCatalogItem gift,
  ) async {
    final MatchGiftClient? giftClient = widget.giftClient;
    final MatchGiftTarget? target = _giftTargetFor(viewState);
    if (giftClient == null || target == null) {
      return;
    }
    setState(() {
      _giftStatusMessage =
          'Sending ${gift.label} to ${target.recipientLabel}...';
    });
    try {
      final MatchGiftReceipt receipt = await giftClient.sendGift(
        target: target,
        gift: gift,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _giftStatusMessage = receipt.confirmationMessage;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _giftStatusMessage = AppFeedback.messageFor(
          error,
          fallback: 'The live gift could not be sent.',
        );
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return Scaffold(
      backgroundColor: tokens.background,
      appBar: AppBar(
        title: const Text('Broadcast Package'),
        actions: <Widget>[
          IconButton(
            tooltip: 'Refresh route',
            onPressed: _reload,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: DecoratedBox(
        decoration: gteBackdropDecoration(),
        child: FutureBuilder<MatchViewState>(
          future: _viewStateFuture,
          builder: (
            BuildContext context,
            AsyncSnapshot<MatchViewState> snapshot,
          ) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Center(
                child: Padding(
                  padding: EdgeInsets.all(24),
                  child: GteStatePanel(
                    eyebrow: 'BROADCAST PACKAGE',
                    title: 'Loading match-day package',
                    message:
                        'Preparing title boards, lineup cards, context modules, and the live broadcast lane.',
                    icon: Icons.live_tv_rounded,
                    isLoading: true,
                  ),
                ),
              );
            }
            if (!snapshot.hasData) {
              return Center(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: GteStatePanel(
                    eyebrow: 'BROADCAST PACKAGE',
                    title: 'Package unavailable',
                    message:
                        'The broadcast package could not load the live match-viewer session for this match key.',
                    icon: Icons.warning_amber_rounded,
                    actionLabel: 'Retry',
                    onAction: _reload,
                  ),
                ),
              );
            }

            final MatchViewState viewState = snapshot.data!;
            if (!_hasBackendAuthoredTimeline(viewState)) {
              return Center(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: GteStatePanel(
                    eyebrow: 'BROADCAST PACKAGE',
                    title: 'Backend package pending',
                    message:
                        'This package received non-backend match data (${viewState.source}), so the on-air lane is blocked until a backend or realtime-authored timeline is available.',
                    icon: Icons.lock_clock_rounded,
                    actionLabel: 'Retry',
                    onAction: _reload,
                  ),
                ),
              );
            }
            if (viewState.frames.isEmpty) {
              return Center(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: GteStatePanel(
                    eyebrow: 'BROADCAST PACKAGE',
                    title: 'Timeline unavailable',
                    message:
                        'This live session did not include any match frames, so the package cannot stage the on-air lane.',
                    icon: Icons.warning_amber_rounded,
                    actionLabel: 'Retry',
                    onAction: _reload,
                  ),
                ),
              );
            }
            if (!_hasOnlyBackendAuthoredFrames(viewState)) {
              return Center(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: GteStatePanel(
                    eyebrow: 'BROADCAST PACKAGE',
                    title: 'Generated timeline blocked',
                    message:
                        'This package received untrusted or injected frame data, so the on-air lane is blocked until the backend sends static realtime frames.',
                    icon: Icons.lock_clock_rounded,
                    actionLabel: 'Retry',
                    onAction: _reload,
                  ),
                ),
              );
            }

            final BroadcastPackageData data = _packageRepository
                .resolveBroadcastData(
                  matchKey: widget.matchKey,
                  viewState: viewState,
                );
            final MatchGiftTarget? giftTarget = _giftTargetFor(viewState);
            final double packageSeconds = _backendDisplaySeconds(viewState);
            final MatchTimelineFrame frame = _backendDisplayFrame(viewState);
            final MatchEvent? activeEvent =
                viewState.scoreRevealLocked
                    ? null
                    : _backendAuthoredActiveEvent(viewState, frame);
            final BroadcastSceneSnapshot scene = MatchSceneDirector.resolve(
              frame: frame,
              activeEvent: activeEvent,
              packageSeconds: packageSeconds,
            );
            final String phaseLabel = _statusLabel(frame, activeEvent);
            final Widget liveWindow = _BroadcastLiveWindow(
              frame: frame,
              activeEvent: activeEvent,
              viewState: viewState,
              package: data.package,
              scene: scene,
            );

            return LayoutBuilder(
              builder: (BuildContext context, BoxConstraints constraints) {
                final bool wide = constraints.maxWidth >= 1180;
                final bool showRoster =
                    data.package.home.starters.isNotEmpty ||
                    data.package.away.starters.isNotEmpty;
                final bool showContext = data.package.context.hasAnyContent;
                final bool showStoryline = data.hasStorylinePanel;
                final Widget mainColumn = Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    if (giftTarget != null) ...<Widget>[
                      _BroadcastGiftPanel(
                        recipientLabel: giftTarget.recipientLabel,
                        statusMessage: _giftStatusMessage,
                        onSendGift: () => _openGiftSheet(viewState),
                      ),
                      const SizedBox(height: 18),
                    ],
                    _buildMainColumn(
                      context: context,
                      wide: wide,
                      data: data,
                      liveWindow: liveWindow,
                      scene: scene,
                      phaseLabel: phaseLabel,
                      packageSeconds: packageSeconds,
                      viewState: viewState,
                      showRoster: showRoster,
                      showContext: showContext,
                      showStoryline: showStoryline,
                    ),
                  ],
                );
                if (!wide) {
                  return SafeArea(
                    child: SingleChildScrollView(
                      padding: const EdgeInsets.fromLTRB(18, 18, 18, 24),
                      child: mainColumn,
                    ),
                  );
                }
                return SafeArea(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.fromLTRB(18, 18, 18, 24),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Expanded(flex: 5, child: mainColumn),
                        const SizedBox(width: 18),
                        SizedBox(
                          width: 360,
                          child: _buildSideRail(
                            data: data,
                            scene: scene,
                            showContext: showContext,
                            showStoryline: showStoryline,
                          ),
                        ),
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

  Widget _buildMainColumn({
    required BuildContext context,
    required bool wide,
    required BroadcastPackageData data,
    required Widget liveWindow,
    required BroadcastSceneSnapshot scene,
    required String phaseLabel,
    required double packageSeconds,
    required MatchViewState viewState,
    required bool showRoster,
    required bool showContext,
    required bool showStoryline,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        MatchHeaderWidget(
          package: data.package,
          competitionName: widget.competition.name,
          phaseLabel: phaseLabel.toUpperCase(),
          isSegmented: viewState.hasMoreSegments,
        ),
        const SizedBox(height: 18),
        _SceneControlBar(
          scene: scene,
          packageSeconds: packageSeconds,
          onRefresh: _reload,
        ),
        const SizedBox(height: 14),
        _SceneSequenceStrip(scene: scene.scene),
        const SizedBox(height: 18),
        _SceneHeroCard(scene: scene, data: data, liveWindow: liveWindow),
        const SizedBox(height: 18),
        liveWindow,
        if (showRoster) ...<Widget>[
          const SizedBox(height: 18),
          RosterCardWidget(package: data.package),
        ],
        if (data.package.home.starters.isNotEmpty ||
            data.package.away.starters.isNotEmpty) ...<Widget>[
          const SizedBox(height: 18),
          if (wide)
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Expanded(
                  child: FormationBoardWidget(
                    team: data.package.home,
                    title: '${data.package.home.teamName} Formation',
                  ),
                ),
                const SizedBox(width: 18),
                Expanded(
                  child: FormationBoardWidget(
                    team: data.package.away,
                    title: '${data.package.away.teamName} Formation',
                  ),
                ),
              ],
            )
          else ...<Widget>[
            FormationBoardWidget(
              team: data.package.home,
              title: '${data.package.home.teamName} Formation',
            ),
            const SizedBox(height: 18),
            FormationBoardWidget(
              team: data.package.away,
              title: '${data.package.away.teamName} Formation',
            ),
          ],
        ],
        if (!wide && showContext) ...<Widget>[
          const SizedBox(height: 18),
          StandingsContextWidget(
            contextBoard: data.package.context,
            homeTeam: data.package.home,
            awayTeam: data.package.away,
          ),
        ],
        if (!wide && showStoryline) ...<Widget>[
          const SizedBox(height: 18),
          StorylinePanelWidget(panel: data.storylinePanel),
        ],
        if (!wide && _hasStudioWrap(data.package)) ...<Widget>[
          const SizedBox(height: 18),
          _StudioWrapCard(package: data.package, scene: scene),
        ],
      ],
    );
  }

  Widget _buildSideRail({
    required BroadcastPackageData data,
    required BroadcastSceneSnapshot scene,
    required bool showContext,
    required bool showStoryline,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        if (showContext)
          StandingsContextWidget(
            contextBoard: data.package.context,
            homeTeam: data.package.home,
            awayTeam: data.package.away,
          ),
        if (showContext && showStoryline) const SizedBox(height: 18),
        if (showStoryline) StorylinePanelWidget(panel: data.storylinePanel),
        if ((showContext || showStoryline) && _hasStudioWrap(data.package))
          const SizedBox(height: 18),
        if (_hasStudioWrap(data.package))
          _StudioWrapCard(package: data.package, scene: scene),
      ],
    );
  }
}

bool _hasBackendAuthoredTimeline(MatchViewState viewState) {
  final String source = viewState.source.trim().toLowerCase();
  if (source.isEmpty ||
      source == 'fixture' ||
      source == 'unknown' ||
      source.contains('fixture') ||
      source.contains('local') ||
      source.contains('simulation')) {
    return false;
  }
  if (source.contains('backend') ||
      source.contains('realtime') ||
      source.contains('websocket') ||
      source.contains('transport') ||
      source.contains('match_engine') ||
      source.contains('ops')) {
    return true;
  }
  return viewState.timelineProof.signed &&
      viewState.timelineProof.status == MatchVerificationStatus.verified;
}

bool _hasOnlyBackendAuthoredFrames(MatchViewState viewState) {
  for (final MatchTimelineFrame frame in viewState.frames) {
    if (frame.isSynthetic || frame.injectedEvents.isNotEmpty) {
      return false;
    }
  }
  return true;
}

double _backendDisplaySeconds(MatchViewState viewState) {
  if (viewState.frames.isEmpty) {
    return 0;
  }
  final double firstFrameSeconds = viewState.firstFrame.timeSeconds;
  final double lastFrameSeconds = viewState.lastFrame.timeSeconds;
  if (viewState.segmentEndSeconds > 0) {
    return viewState.segmentEndSeconds
        .clamp(firstFrameSeconds, lastFrameSeconds)
        .toDouble();
  }
  return firstFrameSeconds;
}

MatchTimelineFrame _backendDisplayFrame(MatchViewState viewState) {
  final double displaySeconds = _backendDisplaySeconds(viewState);
  MatchTimelineFrame selected = viewState.firstFrame;
  for (final MatchTimelineFrame frame in viewState.frames) {
    if (frame.timeSeconds > displaySeconds + 0.0001) {
      break;
    }
    selected = frame;
  }
  return selected;
}

MatchEvent? _backendAuthoredActiveEvent(
  MatchViewState viewState,
  MatchTimelineFrame frame,
) {
  return viewState.eventById(frame.activeEventId);
}

class _SceneControlBar extends StatelessWidget {
  const _SceneControlBar({
    required this.scene,
    required this.packageSeconds,
    required this.onRefresh,
  });

  final BroadcastSceneSnapshot scene;
  final double packageSeconds;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return GteSurfacePanel(
      padding: const EdgeInsets.all(14),
      accentColor: GteShellTheme.definitionOf(context).primaryColor,
      child: LayoutBuilder(
        builder: (BuildContext context, BoxConstraints constraints) {
          final bool stacked = constraints.maxWidth < 760;
          final Widget summary = Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Backend scene dock',
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: GteShellTheme.definitionOf(context).primaryColor,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 0.9,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                '${scene.label} / ${packageSeconds.toStringAsFixed(1)}s',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  color: tokens.textPrimary,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          );
          final Widget actions = Wrap(
            spacing: 8,
            runSpacing: 8,
            children: <Widget>[
              FilledButton.tonalIcon(
                onPressed: onRefresh,
                icon: const Icon(Icons.refresh_rounded),
                label: const Text('Refresh backend'),
              ),
            ],
          );
          if (stacked) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[summary, const SizedBox(height: 14), actions],
            );
          }
          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Expanded(child: summary),
              const SizedBox(width: 16),
              actions,
            ],
          );
        },
      ),
    );
  }
}

class _SceneSequenceStrip extends StatelessWidget {
  const _SceneSequenceStrip({required this.scene});

  final BroadcastPackageScene scene;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final definition = GteShellTheme.definitionOf(context);
    const List<MapEntry<String, List<BroadcastPackageScene>>>
    groups = <MapEntry<String, List<BroadcastPackageScene>>>[
      MapEntry<String, List<BroadcastPackageScene>>(
        'Pre-match',
        <BroadcastPackageScene>[
          BroadcastPackageScene.titleBanner,
          BroadcastPackageScene.rosterCard,
        ],
      ),
      MapEntry<String, List<BroadcastPackageScene>>(
        'Lineups',
        <BroadcastPackageScene>[
          BroadcastPackageScene.homeFormation,
          BroadcastPackageScene.awayFormation,
        ],
      ),
      MapEntry<String, List<BroadcastPackageScene>>(
        'Context',
        <BroadcastPackageScene>[
          BroadcastPackageScene.contextBoard,
          BroadcastPackageScene.storylinePanel,
        ],
      ),
      MapEntry<String, List<BroadcastPackageScene>>(
        'Kickoff',
        <BroadcastPackageScene>[
          BroadcastPackageScene.kickoffTransition,
          BroadcastPackageScene.liveMatch,
        ],
      ),
      MapEntry<String, List<BroadcastPackageScene>>(
        'Halftime',
        <BroadcastPackageScene>[BroadcastPackageScene.halftimeBoard],
      ),
      MapEntry<String, List<BroadcastPackageScene>>(
        'Full-time',
        <BroadcastPackageScene>[BroadcastPackageScene.fulltimeBoard],
      ),
    ];
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: groups
          .map((MapEntry<String, List<BroadcastPackageScene>> group) {
            final bool active = group.value.contains(scene);
            return AnimatedContainer(
              duration: const Duration(milliseconds: 220),
              curve: Curves.easeOutCubic,
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(999),
                color:
                    active
                        ? definition.primaryColor.withValues(alpha: 0.16)
                        : tokens.surfaceHighlight.withValues(alpha: 0.06),
                border: Border.all(
                  color:
                      active
                          ? definition.primaryColor.withValues(alpha: 0.44)
                          : tokens.stroke.withValues(alpha: 0.82),
                ),
              ),
              child: Text(
                group.key,
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: active ? definition.primaryColor : tokens.textMuted,
                  fontWeight: FontWeight.w800,
                ),
              ),
            );
          })
          .toList(growable: false),
    );
  }
}

class _SceneHeroCard extends StatelessWidget {
  const _SceneHeroCard({
    required this.scene,
    required this.data,
    required this.liveWindow,
  });

  final BroadcastSceneSnapshot scene;
  final BroadcastPackageData data;
  final Widget liveWindow;

  @override
  Widget build(BuildContext context) {
    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 420),
      switchInCurve: Curves.easeOutCubic,
      switchOutCurve: Curves.easeInCubic,
      transitionBuilder: (Widget child, Animation<double> animation) {
        return FadeTransition(
          opacity: animation,
          child: SlideTransition(
            position: Tween<Offset>(
              begin: const Offset(0.05, 0),
              end: Offset.zero,
            ).animate(animation),
            child: child,
          ),
        );
      },
      child: KeyedSubtree(
        key: ValueKey<BroadcastPackageScene>(scene.scene),
        child: switch (scene.scene) {
          BroadcastPackageScene.titleBanner => _SceneSlate(
            package: data.package,
          ),
          BroadcastPackageScene.rosterCard => RosterCardWidget(
            package: data.package,
          ),
          BroadcastPackageScene.homeFormation => FormationBoardWidget(
            team: data.package.home,
            title: '${data.package.home.teamName} Formation',
          ),
          BroadcastPackageScene.awayFormation => FormationBoardWidget(
            team: data.package.away,
            title: '${data.package.away.teamName} Formation',
          ),
          BroadcastPackageScene.contextBoard =>
            data.package.context.hasAnyContent
                ? StandingsContextWidget(
                  contextBoard: data.package.context,
                  homeTeam: data.package.home,
                  awayTeam: data.package.away,
                )
                : _SceneSlate(package: data.package),
          BroadcastPackageScene.storylinePanel =>
            data.hasStorylinePanel
                ? StorylinePanelWidget(panel: data.storylinePanel)
                : _SceneSlate(package: data.package),
          BroadcastPackageScene.kickoffTransition => liveWindow,
          BroadcastPackageScene.liveMatch => liveWindow,
          BroadcastPackageScene.halftimeBoard => _StudioWrapCard(
            package: data.package,
            scene: scene,
          ),
          BroadcastPackageScene.fulltimeBoard => _StudioWrapCard(
            package: data.package,
            scene: scene,
          ),
        },
      ),
    );
  }
}

class _SceneSlate extends StatelessWidget {
  const _SceneSlate({required this.package});

  final MatchPresentationPackage package;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final definition = GteShellTheme.definitionOf(context);
    return GteSurfacePanel(
      emphasized: true,
      accentColor: definition.primaryColor,
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Broadcast Open',
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: definition.primaryColor,
              fontWeight: FontWeight.w800,
              letterSpacing: 1.0,
            ),
          ),
          const SizedBox(height: 12),
          Text(
            package.matchLabel,
            style: Theme.of(context).textTheme.headlineMedium?.copyWith(
              color: tokens.textPrimary,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 18,
            runSpacing: 12,
            children: <Widget>[
              _SlateMetric(
                label: package.home.teamName,
                value: package.home.formation,
              ),
              _SlateMetric(
                label: package.away.teamName,
                value: package.away.formation,
              ),
              _SlateMetric(
                label: 'Storylines',
                value: '${package.context.storylines.length}',
              ),
              _SlateMetric(
                label: 'Desk notes',
                value:
                    '${package.coachNotes.length + package.momentumNotes.length}',
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _SlateMetric extends StatelessWidget {
  const _SlateMetric({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return SizedBox(
      width: 150,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            label,
            style: Theme.of(
              context,
            ).textTheme.labelMedium?.copyWith(color: tokens.textMuted),
          ),
          const SizedBox(height: 4),
          Text(
            value,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              color: tokens.textPrimary,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }
}

class _BroadcastLiveWindow extends StatelessWidget {
  const _BroadcastLiveWindow({
    required this.frame,
    required this.activeEvent,
    required this.viewState,
    required this.package,
    required this.scene,
  });

  final MatchTimelineFrame frame;
  final MatchEvent? activeEvent;
  final MatchViewState viewState;
  final MatchPresentationPackage package;
  final BroadcastSceneSnapshot scene;

  @override
  Widget build(BuildContext context) {
    final bool timelineMasked = viewState.scoreRevealLocked;
    final MatchEvent? resolvedActiveEvent = timelineMasked ? null : activeEvent;
    final String clockLabel =
        viewState.scoreRevealLocked
            ? '--:--'
            : _clockLabel(frame, resolvedActiveEvent);
    final String phaseLabel = _statusLabel(frame, resolvedActiveEvent);
    final String headline =
        timelineMasked
            ? package.matchLabel
            : _commentaryHeadline(package, resolvedActiveEvent, scene);
    final String detail =
        timelineMasked
            ? 'Live event detail pending backend confirmation.'
            : _commentaryDetail(package, resolvedActiveEvent);
    final tokens = GteShellTheme.tokensOf(context);
    final definition = GteShellTheme.definitionOf(context);
    return GteSurfacePanel(
      emphasized: true,
      accentColor: definition.primaryColor,
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      'Live 2D Broadcast Lane',
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        color: tokens.textPrimary,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Broadcast match window with scorebug, event ribbon, and commentary strip.',
                      style: Theme.of(
                        context,
                      ).textTheme.bodyMedium?.copyWith(color: tokens.textMuted),
                    ),
                  ],
                ),
              ),
              const _LaneTag(label: '2D BROADCAST'),
              const SizedBox(width: 8),
              _LaneTag(label: _cameraLabel(scene.cameraState)),
            ],
          ),
          const SizedBox(height: 14),
          ClipRRect(
            borderRadius: BorderRadius.circular(24),
            child: AspectRatio(
              aspectRatio: 105 / 68,
              child: Stack(
                fit: StackFit.expand,
                children: <Widget>[
                  GtexMatchCanvasLayer(
                    viewState: viewState,
                    frame: frame,
                    hudState: _buildHudState(
                      frame: frame,
                      clockLabel: clockLabel,
                      phaseLabel: phaseLabel,
                      headline: headline,
                      detail: detail,
                    ),
                    viewType: GtexMatchViewType.twoD,
                  ),
                  Positioned(
                    top: 12,
                    left: 12,
                    right: 12,
                    child: MatchScorebarWidget(
                      homeName: package.home.displayCode,
                      awayName: package.away.displayCode,
                      homeScore:
                          viewState.scoreRevealLocked ? null : frame.homeScore,
                      awayScore:
                          viewState.scoreRevealLocked ? null : frame.awayScore,
                      clockLabel: clockLabel,
                      statusLabel: phaseLabel,
                      cameraState: scene.cameraState,
                      eventLabel:
                          timelineMasked
                              ? null
                              : resolvedActiveEvent?.bannerText,
                    ),
                  ),
                  Positioned(
                    left: 12,
                    right: 12,
                    bottom: 12,
                    child: CommentaryRibbonWidget(
                      headline: headline,
                      detail: detail,
                      trailing:
                          viewState.scoreRevealLocked
                              ? clockLabel
                              : resolvedActiveEvent?.clockLabel ?? clockLabel,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  GtexBroadcastHudState _buildHudState({
    required MatchTimelineFrame frame,
    required String clockLabel,
    required String phaseLabel,
    required String headline,
    required String detail,
  }) {
    return GtexBroadcastHudState(
      clockLabel: clockLabel,
      statusLabel: phaseLabel,
      homeScore: viewState.scoreRevealLocked ? null : frame.homeScore,
      awayScore: viewState.scoreRevealLocked ? null : frame.awayScore,
      scoreMasked: viewState.scoreRevealLocked,
      controlsVisible: false,
      isPaused: false,
      speedLabel: 'Backend',
      mode: GtexMatchRenderMode.standard,
      viewType: GtexMatchViewType.twoD,
      commentary: headline,
      commentaryDetail: detail,
    );
  }
}

class _LaneTag extends StatelessWidget {
  const _LaneTag({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final accent = GteShellTheme.definitionOf(context).primaryColor;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: accent.withValues(alpha: 0.28)),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelMedium?.copyWith(
          color: tokens.textPrimary,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

class _StudioWrapCard extends StatelessWidget {
  const _StudioWrapCard({required this.package, required this.scene});

  final MatchPresentationPackage package;
  final BroadcastSceneSnapshot scene;

  @override
  Widget build(BuildContext context) {
    final List<String> momentum = package.momentumNotes
        .take(4)
        .toList(growable: false);
    final List<String> coach = package.coachNotes
        .take(4)
        .toList(growable: false);
    final List<String> commentary = package.commentaryHighlights
        .take(4)
        .toList(growable: false);
    final tokens = GteShellTheme.tokensOf(context);
    return GteSurfacePanel(
      accentColor: GteShellTheme.tokensOf(context).accentWarm,
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            scene.scene == BroadcastPackageScene.halftimeBoard
                ? 'Halftime Package'
                : scene.scene == BroadcastPackageScene.fulltimeBoard
                ? 'Full-time Package'
                : 'Studio Wrap',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
              color: tokens.textPrimary,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            'Momentum, coach notes, and commentary pulls from the verified package layer.',
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(color: tokens.textMuted),
          ),
          if (momentum.isNotEmpty) ...<Widget>[
            const SizedBox(height: 16),
            _WrapSection(title: 'Momentum', items: momentum),
          ],
          if (coach.isNotEmpty) ...<Widget>[
            const SizedBox(height: 14),
            _WrapSection(title: 'Staff Notes', items: coach),
          ],
          if (commentary.isNotEmpty) ...<Widget>[
            const SizedBox(height: 14),
            _WrapSection(title: 'Commentary Strip', items: commentary),
          ],
        ],
      ),
    );
  }
}

class _WrapSection extends StatelessWidget {
  const _WrapSection({required this.title, required this.items});

  final String title;
  final List<String> items;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          title,
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
            color: tokens.textPrimary,
            fontWeight: FontWeight.w800,
          ),
        ),
        const SizedBox(height: 8),
        for (final String item in items)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Text(
              '- $item',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: tokens.textMuted,
                height: 1.35,
              ),
            ),
          ),
      ],
    );
  }
}

String _clockLabel(MatchTimelineFrame frame, MatchEvent? activeEvent) {
  return activeEvent?.clockLabel ??
      "${frame.clockMinute.clamp(0, 120).round()}'";
}

String _statusLabel(MatchTimelineFrame frame, MatchEvent? activeEvent) {
  if (activeEvent != null) {
    switch (activeEvent.type) {
      case MatchViewerEventType.kickoff:
        return 'Kickoff';
      case MatchViewerEventType.halftime:
        return 'Halftime';
      case MatchViewerEventType.fulltime:
        return 'Full-time';
      case MatchViewerEventType.substitution:
        return 'Substitution';
      case MatchViewerEventType.setPiece:
      case MatchViewerEventType.penalty:
        return 'Set Piece';
      default:
        break;
    }
  }
  switch (frame.phase) {
    case MatchViewerPhase.kickoff:
      return 'Walkout';
    case MatchViewerPhase.halftime:
      return 'Halftime';
    case MatchViewerPhase.fulltime:
      return 'Full-time';
    case MatchViewerPhase.setPiece:
      return 'Set Piece';
    case MatchViewerPhase.openPlay:
      return 'Open Play';
  }
}

String _commentaryHeadline(
  MatchPresentationPackage package,
  MatchEvent? activeEvent,
  BroadcastSceneSnapshot scene,
) {
  if (activeEvent != null && activeEvent.bannerText.trim().isNotEmpty) {
    return activeEvent.bannerText;
  }
  if (scene.scene == BroadcastPackageScene.kickoffTransition) {
    return 'Kickoff incoming';
  }
  if (scene.scene == BroadcastPackageScene.liveMatch) {
    return package.matchLabel;
  }
  return scene.label;
}

String _commentaryDetail(
  MatchPresentationPackage package,
  MatchEvent? activeEvent,
) {
  if (activeEvent != null && activeEvent.commentary.trim().isNotEmpty) {
    return activeEvent.commentary;
  }
  if (package.commentaryHighlights.isNotEmpty) {
    return package.commentaryHighlights.first;
  }
  if (package.context.matchSignificance != null) {
    return package.context.matchSignificance!;
  }
  if (package.context.storylines.isNotEmpty) {
    return package.context.storylines.first;
  }
  return 'Broadcast lane active.';
}

String _cameraLabel(MatchSimCameraState state) {
  switch (state) {
    case MatchSimCameraState.stadiumWide:
      return 'STADIUM WIDE';
    case MatchSimCameraState.tunnelOrWalkout:
      return 'WALKOUT';
    case MatchSimCameraState.kickoffCenter:
      return 'KICKOFF';
    case MatchSimCameraState.tacticalTop:
      return 'TACTICAL TOP';
    case MatchSimCameraState.attackingThird:
      return 'ATTACKING THIRD';
    case MatchSimCameraState.setPieceLeft:
      return 'SET PIECE LEFT';
    case MatchSimCameraState.setPieceRight:
      return 'SET PIECE RIGHT';
    case MatchSimCameraState.goalReplayAngle:
      return 'GOAL REPLAY';
    case MatchSimCameraState.halftimeBoard:
      return 'HALFTIME BOARD';
    case MatchSimCameraState.fulltimeBoard:
      return 'FULL-TIME BOARD';
  }
}

class _BroadcastGiftPanel extends StatelessWidget {
  const _BroadcastGiftPanel({
    required this.recipientLabel,
    required this.statusMessage,
    required this.onSendGift,
  });

  final String recipientLabel;
  final String? statusMessage;
  final VoidCallback onSendGift;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      accentColor: GteShellTheme.accentArena,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Live support gifting',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          Text(
            'Send a verified live gift to $recipientLabel while the broadcast package is on air.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          if (statusMessage != null) ...<Widget>[
            const SizedBox(height: 12),
            Text(statusMessage!, style: Theme.of(context).textTheme.bodySmall),
          ],
          const SizedBox(height: 12),
          FilledButton.icon(
            onPressed: onSendGift,
            icon: const Icon(Icons.card_giftcard_rounded),
            label: const Text('Send gift'),
          ),
        ],
      ),
    );
  }
}

bool _hasStudioWrap(MatchPresentationPackage package) {
  return package.momentumNotes.isNotEmpty ||
      package.coachNotes.isNotEmpty ||
      package.commentaryHighlights.isNotEmpty;
}
