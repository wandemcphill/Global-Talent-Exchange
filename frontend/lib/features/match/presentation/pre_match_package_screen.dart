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
import 'match_scene_director.dart';
import 'widgets/commentary_ribbon_widget.dart';
import 'widgets/formation_board_widget.dart';
import 'widgets/match_scorebar_widget.dart';
import 'widgets/reaction_panel_widget.dart';
import 'widgets/roster_card_widget.dart';
import 'widgets/standings_context_widget.dart';

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
  static const double _preMatchSequenceSeconds = 16.0;

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
      _packageSeconds = _preMatchSequenceSeconds;
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
            colors: <Color>[Color(0xFF0A1420), Color(0xFF06090F)],
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
                        'Preparing the official roster sheet, formation boards, context overlays, and the on-air match lens.',
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

            final MatchPresentationPackage package = _packageRepository.resolve(
              viewState,
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
                return LayoutBuilder(
                  builder: (BuildContext context, BoxConstraints constraints) {
                    final bool wide = constraints.maxWidth >= 1180;
                    final Widget mainColumn = Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        _MatchTitleBanner(
                          package: package,
                          competitionName: widget.competition.name,
                          source: viewState.source,
                          hasMoreSegments: viewState.hasMoreSegments,
                        ),
                        const SizedBox(height: 18),
                        _SceneControlBar(
                          scene: scene,
                          onRestart: _restartPackage,
                          onSkipToLive: _skipToLive,
                        ),
                        const SizedBox(height: 14),
                        _SceneHeroCard(
                          scene: scene,
                          package: package,
                          liveLens: _BroadcastLiveLensCard(
                            controller: controller,
                            viewState: viewState,
                            package: package,
                            scene: scene,
                          ),
                        ),
                        const SizedBox(height: 18),
                        _BroadcastLiveLensCard(
                          controller: controller,
                          viewState: viewState,
                          package: package,
                          scene: scene,
                          title: 'On-Air Match Lens',
                          subtitle:
                              'Pseudo-3D broadcast lane with live score, event ribbon, and camera-state choreography.',
                        ),
                        const SizedBox(height: 18),
                        RosterCardWidget(package: package),
                        const SizedBox(height: 18),
                        if (wide)
                          Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Expanded(
                                child: FormationBoardWidget(
                                  team: package.home,
                                  title: '${package.home.teamName} Formation',
                                  accentColor: const Color(0xFF7DD3FC),
                                ),
                              ),
                              const SizedBox(width: 18),
                              Expanded(
                                child: FormationBoardWidget(
                                  team: package.away,
                                  title: '${package.away.teamName} Formation',
                                  accentColor: const Color(0xFFF59E0B),
                                ),
                              ),
                            ],
                          )
                        else ...<Widget>[
                          FormationBoardWidget(
                            team: package.home,
                            title: '${package.home.teamName} Formation',
                            accentColor: const Color(0xFF7DD3FC),
                          ),
                          const SizedBox(height: 18),
                          FormationBoardWidget(
                            team: package.away,
                            title: '${package.away.teamName} Formation',
                            accentColor: const Color(0xFFF59E0B),
                          ),
                        ],
                      ],
                    );

                    final Widget sideRail = Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        StandingsContextWidget(contextBoard: package.context),
                        const SizedBox(height: 18),
                        ReactionPanelWidget(
                          reactions: package.reactions,
                          storylines: package.context.storylines,
                        ),
                        const SizedBox(height: 18),
                        _PackageRecapBoard(package: package, scene: scene),
                      ],
                    );

                    return SafeArea(
                      child: SingleChildScrollView(
                        padding: const EdgeInsets.fromLTRB(18, 18, 18, 24),
                        child:
                            wide
                                ? Row(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: <Widget>[
                                    Expanded(flex: 5, child: mainColumn),
                                    const SizedBox(width: 18),
                                    SizedBox(width: 360, child: sideRail),
                                  ],
                                )
                                : Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: <Widget>[
                                    mainColumn,
                                    const SizedBox(height: 18),
                                    sideRail,
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
}

class _MatchTitleBanner extends StatelessWidget {
  const _MatchTitleBanner({
    required this.package,
    required this.competitionName,
    required this.source,
    required this.hasMoreSegments,
  });

  final MatchPresentationPackage package;
  final String competitionName;
  final String source;
  final bool hasMoreSegments;

  @override
  Widget build(BuildContext context) {
    final MatchContextBoard contextBoard = package.context;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(32),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[Color(0xFF11324A), Color(0xFF0A1520)],
        ),
        border: Border.all(color: Colors.white.withValues(alpha: 0.10)),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.24),
            blurRadius: 24,
            offset: const Offset(0, 14),
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
              _MetaPill(label: competitionName),
              if (contextBoard.competitionStage != null)
                _MetaPill(label: contextBoard.competitionStage!),
              if (contextBoard.dateLabel != null)
                _MetaPill(label: contextBoard.dateLabel!),
              if (contextBoard.kickoffLabel != null)
                _MetaPill(label: 'KO ${contextBoard.kickoffLabel!}'),
              if (contextBoard.venueName != null)
                _MetaPill(label: contextBoard.venueName!),
              _MetaPill(label: source.replaceAll('_', ' ').toUpperCase()),
              if (hasMoreSegments)
                const _MetaPill(label: 'SEGMENTED LIVE SESSION'),
            ],
          ),
          const SizedBox(height: 18),
          Text(
            'Football Manager style match-day package',
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: const Color(0xFFB7D6F5),
              letterSpacing: 1.0,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 10),
          Text(
            package.matchLabel,
            style: Theme.of(context).textTheme.headlineMedium?.copyWith(
              color: Colors.white,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 18),
          Row(
            children: <Widget>[
              Expanded(
                child: _TeamBannerBlock(
                  teamName: package.home.teamName,
                  formation: package.home.formation,
                  coachName: package.home.coachName,
                  alignEnd: false,
                ),
              ),
              Container(
                width: 72,
                height: 72,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: Colors.white.withValues(alpha: 0.08),
                  border: Border.all(
                    color: Colors.white.withValues(alpha: 0.12),
                  ),
                ),
                child: Text(
                  'VS',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
              Expanded(
                child: _TeamBannerBlock(
                  teamName: package.away.teamName,
                  formation: package.away.formation,
                  coachName: package.away.coachName,
                  alignEnd: true,
                ),
              ),
            ],
          ),
          if (contextBoard.matchSignificance != null) ...<Widget>[
            const SizedBox(height: 18),
            Text(
              contextBoard.matchSignificance!,
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                color: Colors.white70,
                height: 1.4,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _TeamBannerBlock extends StatelessWidget {
  const _TeamBannerBlock({
    required this.teamName,
    required this.formation,
    required this.coachName,
    required this.alignEnd,
  });

  final String teamName;
  final String formation;
  final String? coachName;
  final bool alignEnd;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment:
          alignEnd ? CrossAxisAlignment.end : CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          teamName,
          textAlign: alignEnd ? TextAlign.right : TextAlign.left,
          style: Theme.of(context).textTheme.titleLarge?.copyWith(
            color: Colors.white,
            fontWeight: FontWeight.w800,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          coachName == null ? formation : '$formation | $coachName',
          textAlign: alignEnd ? TextAlign.right : TextAlign.left,
          style: Theme.of(
            context,
          ).textTheme.bodyMedium?.copyWith(color: const Color(0xFFB8C8D8)),
        ),
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
            '${scene.label} | ${_cameraLabel(scene.cameraState)}',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              color: Colors.white,
              fontWeight: FontWeight.w800,
            ),
          ),
        ),
        TextButton.icon(
          onPressed: onRestart,
          icon: const Icon(Icons.restart_alt),
          label: const Text('Restart package'),
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

class _SceneHeroCard extends StatelessWidget {
  const _SceneHeroCard({
    required this.scene,
    required this.package,
    required this.liveLens,
  });

  final BroadcastSceneSnapshot scene;
  final MatchPresentationPackage package;
  final Widget liveLens;

  @override
  Widget build(BuildContext context) {
    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 480),
      switchInCurve: Curves.easeOutCubic,
      switchOutCurve: Curves.easeInCubic,
      transitionBuilder: (Widget child, Animation<double> animation) {
        return FadeTransition(
          opacity: animation,
          child: SlideTransition(
            position: Tween<Offset>(
              begin: const Offset(0.06, 0),
              end: Offset.zero,
            ).animate(animation),
            child: child,
          ),
        );
      },
      child: KeyedSubtree(
        key: ValueKey<BroadcastPackageScene>(scene.scene),
        child: switch (scene.scene) {
          BroadcastPackageScene.titleBanner => _HeroTitleCard(package: package),
          BroadcastPackageScene.rosterCard => RosterCardWidget(
            package: package,
          ),
          BroadcastPackageScene.homeFormation => FormationBoardWidget(
            team: package.home,
            title: '${package.home.teamName} Formation',
            accentColor: const Color(0xFF7DD3FC),
          ),
          BroadcastPackageScene.awayFormation => FormationBoardWidget(
            team: package.away,
            title: '${package.away.teamName} Formation',
            accentColor: const Color(0xFFF59E0B),
          ),
          BroadcastPackageScene.contextBoard => StandingsContextWidget(
            contextBoard: package.context,
          ),
          BroadcastPackageScene.reactions => ReactionPanelWidget(
            reactions: package.reactions,
            storylines: package.context.storylines,
          ),
          BroadcastPackageScene.kickoffLive => liveLens,
          BroadcastPackageScene.halftimeBoard => _PackageRecapBoard(
            package: package,
            scene: scene,
          ),
          BroadcastPackageScene.fulltimeBoard => _PackageRecapBoard(
            package: package,
            scene: scene,
          ),
        },
      ),
    );
  }
}

class _HeroTitleCard extends StatelessWidget {
  const _HeroTitleCard({required this.package});

  final MatchPresentationPackage package;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(30),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[Color(0xFF0F2230), Color(0xFF091117)],
        ),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Matchday title board',
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: const Color(0xFF7DD3FC),
              letterSpacing: 1.0,
              fontWeight: FontWeight.w800,
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
          const SizedBox(height: 18),
          Wrap(
            spacing: 18,
            runSpacing: 18,
            children: <Widget>[
              _TitleMetric(
                label: package.home.teamName,
                value: package.home.formation,
              ),
              _TitleMetric(
                label: package.away.teamName,
                value: package.away.formation,
              ),
              _TitleMetric(
                label: 'Storylines',
                value: '${package.context.storylines.length}',
              ),
              _TitleMetric(
                label: 'Reaction cards',
                value: '${package.reactions.length}',
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _TitleMetric extends StatelessWidget {
  const _TitleMetric({required this.label, required this.value});

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
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
              color: Colors.white60,
              letterSpacing: 0.7,
            ),
          ),
          const SizedBox(height: 6),
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

class _BroadcastLiveLensCard extends StatelessWidget {
  const _BroadcastLiveLensCard({
    required this.controller,
    required this.viewState,
    required this.package,
    required this.scene,
    this.title = 'Live Window',
    this.subtitle = 'Match lens',
  });

  final Match3dTimelineController controller;
  final MatchViewState viewState;
  final MatchPresentationPackage package;
  final BroadcastSceneSnapshot scene;
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    final MatchTimelineFrame frame = controller.displayFrame;
    final MatchEvent? activeEvent = controller.activeEvent;
    final String clockLabel = _clockLabel(frame, activeEvent);
    final String statusLabel = _statusLabel(frame, activeEvent);
    final String headline = _commentaryHeadline(activeEvent, scene);
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
                      title,
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        color: Colors.white,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      subtitle,
                      style: Theme.of(
                        context,
                      ).textTheme.bodyMedium?.copyWith(color: Colors.white70),
                    ),
                  ],
                ),
              ),
              const _MetaPill(label: 'PSEUDO 3D'),
              const SizedBox(width: 8),
              _MetaPill(label: _cameraLabel(scene.cameraState)),
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
                      clockLabel: clockLabel,
                      statusLabel: statusLabel,
                      frame: frame,
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
                      homeName: viewState.homeTeam.shortName,
                      awayName: viewState.awayTeam.shortName,
                      homeScore: frame.homeScore,
                      awayScore: frame.awayScore,
                      clockLabel: clockLabel,
                      statusLabel: statusLabel,
                      cameraState: scene.cameraState,
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
    required String clockLabel,
    required String statusLabel,
    required MatchTimelineFrame frame,
    required String headline,
    required String detail,
  }) {
    return GtexBroadcastHudState(
      clockLabel: clockLabel,
      statusLabel: statusLabel,
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

class _PackageRecapBoard extends StatelessWidget {
  const _PackageRecapBoard({required this.package, required this.scene});

  final MatchPresentationPackage package;
  final BroadcastSceneSnapshot scene;

  @override
  Widget build(BuildContext context) {
    final List<String> momentum =
        package.momentumNotes.isEmpty
            ? package.context.storylines.take(3).toList(growable: false)
            : package.momentumNotes.take(4).toList(growable: false);
    final List<String> coach =
        package.coachNotes.isEmpty
            ? <String>[
              if (package.home.coachName != null)
                '${package.home.teamName}: ${package.home.coachName}',
              if (package.away.coachName != null)
                '${package.away.teamName}: ${package.away.coachName}',
            ]
            : package.coachNotes.take(4).toList(growable: false);
    final List<String> commentary =
        package.commentaryHighlights.isEmpty
            ? package.reactions
                .map((MatchReactionCard item) => item.headline)
                .take(4)
                .toList(growable: false)
            : package.commentaryHighlights.take(4).toList(growable: false);

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
                ? 'Fulltime Package'
                : 'Broadcast Recap',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
              color: Colors.white,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            'Standings recap, momentum notes, coach reaction, and desk lines pulled from the live match-viewer contract.',
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(color: Colors.white70),
          ),
          const SizedBox(height: 16),
          _RecapSection(title: 'Momentum', items: momentum),
          const SizedBox(height: 14),
          _RecapSection(title: 'Coach and staff', items: coach),
          const SizedBox(height: 14),
          _RecapSection(title: 'Desk lines', items: commentary),
        ],
      ),
    );
  }
}

class _RecapSection extends StatelessWidget {
  const _RecapSection({required this.title, required this.items});

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
        if (items.isEmpty)
          Text(
            'No verified items are attached to this payload yet.',
            style: Theme.of(
              context,
            ).textTheme.bodySmall?.copyWith(color: Colors.white60),
          )
        else
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

class _MetaPill extends StatelessWidget {
  const _MetaPill({required this.label});

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
        return 'Fulltime';
      case MatchViewerEventType.substitution:
        return 'Substitution';
      case MatchViewerEventType.setPiece:
      case MatchViewerEventType.penalty:
        return 'Set piece';
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
      return 'Fulltime';
    case MatchViewerPhase.setPiece:
      return 'Set piece';
    case MatchViewerPhase.openPlay:
      return 'Open play';
  }
}

String _commentaryHeadline(
  MatchEvent? activeEvent,
  BroadcastSceneSnapshot scene,
) {
  if (activeEvent != null) {
    return activeEvent.bannerText;
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
  return 'Live commentary insights are waiting on richer match package data.';
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
      return 'FULLTIME BOARD';
  }
}
