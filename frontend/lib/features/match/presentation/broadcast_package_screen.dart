import 'dart:async';

import 'package:flutter/material.dart';

import '../../../controllers/match_3d_timeline_controller.dart';
import '../../../models/competition_models.dart';
import '../../../models/match/gtex_broadcast_hud_state.dart';
import '../../../models/match/gtex_match_render_mode.dart';
import '../../../models/match/gtex_match_view_type.dart';
import '../../../models/match_event.dart';
import '../../../models/match_timeline_frame.dart';
import '../../../models/match_view_state.dart';
import '../../../widgets/gte_state_panel.dart';
import '../../../widgets/match/broadcast/gtex_match_canvas_layer.dart';
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
  });

  final String matchKey;
  final CompetitionSummary competition;
  final BroadcastPackageViewStateLoader viewStateLoader;

  @override
  State<BroadcastPackageScreen> createState() => _BroadcastPackageScreenState();
}

class _BroadcastPackageScreenState extends State<BroadcastPackageScreen>
    with SingleTickerProviderStateMixin {
  static const Duration _sceneTick = Duration(milliseconds: 900);

  final BroadcastPackageRepository _packageRepository =
      const BroadcastPackageRepository();

  late Future<MatchViewState> _viewStateFuture;
  Match3dTimelineController? _controller;
  Timer? _sceneTimer;
  double _packageSeconds = 0;

  @override
  void initState() {
    super.initState();
    _viewStateFuture = widget.viewStateLoader();
    _sceneTimer = Timer.periodic(_sceneTick, (_) {
      if (!mounted) {
        return;
      }
      setState(() {
        _packageSeconds += _sceneTick.inMilliseconds / 1000;
      });
    });
  }

  @override
  void dispose() {
    _sceneTimer?.cancel();
    _controller?.dispose();
    super.dispose();
  }

  void _reload() {
    _controller?.dispose();
    _controller = null;
    setState(() {
      _packageSeconds = 0;
      _viewStateFuture = widget.viewStateLoader();
    });
  }

  void _restartPackage() {
    _controller?.seekToSeconds(0);
    _controller?.play();
    setState(() {
      _packageSeconds = 0;
    });
  }

  void _skipToLive() {
    setState(() {
      _packageSeconds = MatchSceneDirector.preMatchSequenceSeconds;
    });
  }

  Match3dTimelineController _ensureController(MatchViewState viewState) {
    final Match3dTimelineController? existing = _controller;
    if (existing != null && existing.viewState.matchId == viewState.matchId) {
      return existing;
    }
    existing?.dispose();
    final Match3dTimelineController created = Match3dTimelineController(
      vsync: this,
      viewState: viewState,
      autoplay: true,
    );
    _controller = created;
    return created;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF060A10),
      appBar: AppBar(
        title: const Text('Broadcast Package'),
        actions: <Widget>[
          IconButton(
            tooltip: 'Restart package',
            onPressed: _restartPackage,
            icon: const Icon(Icons.restart_alt),
          ),
          IconButton(
            tooltip: 'Refresh route',
            onPressed: _reload,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: DecoratedBox(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: <Color>[Color(0xFF09111A), Color(0xFF04070C)],
          ),
        ),
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

            final BroadcastPackageData data = _packageRepository
                .resolveBroadcastData(
                  matchKey: widget.matchKey,
                  viewState: viewState,
                );
            final Match3dTimelineController controller = _ensureController(
              viewState,
            );

            return ListenableBuilder(
              listenable: controller,
              builder: (BuildContext context, Widget? child) {
                final MatchTimelineFrame frame = controller.displayFrame;
                final MatchEvent? activeEvent = controller.activeEvent;
                final BroadcastSceneSnapshot scene = MatchSceneDirector.resolve(
                  frame: frame,
                  activeEvent: activeEvent,
                  packageSeconds: _packageSeconds,
                );
                final String phaseLabel = _statusLabel(frame, activeEvent);
                final Widget liveWindow = _BroadcastLiveWindow(
                  controller: controller,
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
                    final Widget mainColumn = _buildMainColumn(
                      context: context,
                      wide: wide,
                      data: data,
                      liveWindow: liveWindow,
                      scene: scene,
                      phaseLabel: phaseLabel,
                      viewState: viewState,
                      showRoster: showRoster,
                      showContext: showContext,
                      showStoryline: showStoryline,
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
          onRestart: _restartPackage,
          onSkipToLive: _skipToLive,
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

class _SceneControlBar extends StatelessWidget {
  const _SceneControlBar({
    required this.scene,
    required this.onRestart,
    required this.onSkipToLive,
  });

  final BroadcastSceneSnapshot scene;
  final VoidCallback onRestart;
  final VoidCallback onSkipToLive;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: <Widget>[
        Expanded(
          child: Text(
            scene.label,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              color: Colors.white,
              fontWeight: FontWeight.w800,
            ),
          ),
        ),
        TextButton.icon(
          onPressed: onRestart,
          icon: const Icon(Icons.restart_alt),
          label: const Text('Restart'),
        ),
        const SizedBox(width: 8),
        FilledButton.tonalIcon(
          onPressed: onSkipToLive,
          icon: const Icon(Icons.play_circle_fill_rounded),
          label: const Text('Jump to live'),
        ),
      ],
    );
  }
}

class _SceneSequenceStrip extends StatelessWidget {
  const _SceneSequenceStrip({required this.scene});

  final BroadcastPackageScene scene;

  @override
  Widget build(BuildContext context) {
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
            return Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(999),
                color:
                    active
                        ? const Color(0xFF112536)
                        : Colors.white.withValues(alpha: 0.04),
                border: Border.all(
                  color:
                      active
                          ? const Color(0xFF7DD3FC).withValues(alpha: 0.55)
                          : Colors.white.withValues(alpha: 0.08),
                ),
              ),
              child: Text(
                group.key,
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: active ? const Color(0xFFBFE6FF) : Colors.white70,
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
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(28),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[Color(0xFF102030), Color(0xFF091017)],
        ),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Broadcast Open',
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: const Color(0xFF7DD3FC),
              fontWeight: FontWeight.w800,
              letterSpacing: 1.0,
            ),
          ),
          const SizedBox(height: 12),
          Text(
            package.matchLabel,
            style: Theme.of(context).textTheme.headlineMedium?.copyWith(
              color: Colors.white,
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
    return SizedBox(
      width: 150,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            label,
            style: Theme.of(
              context,
            ).textTheme.labelMedium?.copyWith(color: Colors.white60),
          ),
          const SizedBox(height: 4),
          Text(
            value,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              color: Colors.white,
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
    required this.controller,
    required this.viewState,
    required this.package,
    required this.scene,
  });

  final Match3dTimelineController controller;
  final MatchViewState viewState;
  final MatchPresentationPackage package;
  final BroadcastSceneSnapshot scene;

  @override
  Widget build(BuildContext context) {
    final MatchTimelineFrame frame = controller.displayFrame;
    final MatchEvent? activeEvent = controller.activeEvent;
    final String clockLabel = _clockLabel(frame, activeEvent);
    final String phaseLabel = _statusLabel(frame, activeEvent);
    final String headline = _commentaryHeadline(package, activeEvent, scene);
    final String detail = _commentaryDetail(package, activeEvent);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(30),
        gradient: const LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: <Color>[Color(0xFF0F1821), Color(0xFF080D13)],
        ),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
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
                      'Live Broadcast Lane',
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        color: Colors.white,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Pseudo-3D match window with scorebug, event ribbon, and commentary strip.',
                      style: Theme.of(
                        context,
                      ).textTheme.bodyMedium?.copyWith(color: Colors.white70),
                    ),
                  ],
                ),
              ),
              const _LaneTag(label: 'PSEUDO 3D'),
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
                      controller: controller,
                      frame: frame,
                      clockLabel: clockLabel,
                      phaseLabel: phaseLabel,
                      headline: headline,
                      detail: detail,
                    ),
                    viewType: GtexMatchViewType.pseudo3D,
                  ),
                  Positioned(
                    top: 12,
                    left: 12,
                    right: 12,
                    child: MatchScorebarWidget(
                      homeName: package.home.displayCode,
                      awayName: package.away.displayCode,
                      homeScore: frame.homeScore,
                      awayScore: frame.awayScore,
                      clockLabel: clockLabel,
                      statusLabel: phaseLabel,
                      cameraState: scene.cameraState,
                      eventLabel: activeEvent?.bannerText,
                    ),
                  ),
                  Positioned(
                    left: 12,
                    right: 12,
                    bottom: 12,
                    child: CommentaryRibbonWidget(
                      headline: headline,
                      detail: detail,
                      trailing: activeEvent?.clockLabel ?? clockLabel,
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
    required Match3dTimelineController controller,
    required MatchTimelineFrame frame,
    required String clockLabel,
    required String phaseLabel,
    required String headline,
    required String detail,
  }) {
    return GtexBroadcastHudState(
      clockLabel: clockLabel,
      statusLabel: phaseLabel,
      homeScore: frame.homeScore,
      awayScore: frame.awayScore,
      scoreMasked: false,
      controlsVisible: false,
      isPaused: !controller.isPlaying,
      speedLabel: controller.speedLabel,
      mode: GtexMatchRenderMode.standard,
      viewType: GtexMatchViewType.pseudo3D,
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
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelMedium?.copyWith(
          color: Colors.white,
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
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(28),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[Color(0xFF141E2A), Color(0xFF0A0F15)],
        ),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
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
              color: Colors.white,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            'Momentum, coach notes, and commentary pulls from the verified package layer.',
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(color: Colors.white70),
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
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          title,
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
            color: Colors.white,
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
                color: Colors.white70,
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

bool _hasStudioWrap(MatchPresentationPackage package) {
  return package.momentumNotes.isNotEmpty ||
      package.coachNotes.isNotEmpty ||
      package.commentaryHighlights.isNotEmpty;
}
