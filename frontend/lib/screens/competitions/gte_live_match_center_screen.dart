import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:gte_frontend/core/app_feedback.dart';
import 'package:gte_frontend/data/live_match_fixtures.dart';
import 'package:gte_frontend/data/match/match_simulation_engine.dart';
import 'package:gte_frontend/data/match/match_simulation_models.dart';
import 'package:gte_frontend/features/app_routes/gte_navigation_helpers.dart';
import 'package:gte_frontend/features/app_routes/gte_route_data.dart';
import 'package:gte_frontend/features/match/live_commentary_feed_service.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match/gtex_match_render_mode.dart';
import 'package:gte_frontend/models/match/gtex_match_view_type.dart';
import 'package:gte_frontend/models/match_viewer_presentation.dart';
import 'package:gte_frontend/services/avatar_mapper.dart';
import 'package:gte_frontend/services/match_3d_monetization_service.dart';
import 'package:gte_frontend/widgets/gte_metric_chip.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';
import 'package:gte_frontend/widgets/competitions/competition_dynamic_prize_pool_card.dart';
import 'package:gte_frontend/widgets/match/gte_highlight_player_sheet.dart';
import 'package:gte_frontend/widgets/match/match_hud_avatar.dart';
import 'package:gte_frontend/widgets/squad/squad_avatar_badge.dart';
import 'package:gte_frontend/widgets/gtex_branding.dart';

import 'gte_halftime_analytics_screen.dart';
import 'gte_match_highlights_screen.dart';
import '../match/gtex_match_broadcast_screen.dart';
import '../match/gtex_match_simulation_screen.dart';
import '../match/gtex_match_viewer_screen.dart';

enum _LiveViewMode { commentary, keyMoments }

typedef GteLiveCommentaryStreamLoader =
    Stream<List<LiveMatchEvent>> Function(LiveMatchSnapshot match);

class GteLiveMatchCenterScreen extends StatefulWidget {
  const GteLiveMatchCenterScreen({
    super.key,
    required this.competition,
    this.isAuthenticated = false,
    this.onOpenLogin,
    this.navigationDependencies,
    this.snapshotLoader,
    this.commentaryStreamLoader,
  });

  final CompetitionSummary competition;
  final bool isAuthenticated;
  final VoidCallback? onOpenLogin;
  final GteNavigationDependencies? navigationDependencies;
  final Future<LiveMatchSnapshot> Function(CompetitionSummary competition)?
  snapshotLoader;
  final GteLiveCommentaryStreamLoader? commentaryStreamLoader;

  @override
  State<GteLiveMatchCenterScreen> createState() =>
      _GteLiveMatchCenterScreenState();
}

class _GteLiveMatchCenterScreenState extends State<GteLiveMatchCenterScreen> {
  late Future<LiveMatchSnapshot> _snapshotFuture;
  late final Timer _countdownTicker;
  late DateTime _countdownStartedAt;
  _LiveViewMode _viewMode = _LiveViewMode.commentary;
  final LiveCommentaryFeedService _commentaryFeedService =
      HybridLiveCommentaryFeedService();
  final Map<String, bool> _tacticToggles = <String, bool>{
    'High press': true,
    'Overlap fullbacks': false,
    'Early crosses': false,
    'Compact mid-block': true,
  };
  Stream<List<LiveMatchEvent>>? _commentaryStream;
  StreamSubscription<List<LiveMatchEvent>>? _commentarySubscription;
  String? _commentaryBindingKey;
  final Set<String> _seenCommentaryKeys = <String>{};
  bool _commentarySeedHydrated = false;
  bool _bigMomentPromptOpen = false;

  @override
  void initState() {
    super.initState();
    _snapshotFuture = _loadSnapshot();
    _countdownStartedAt = DateTime.now();
    _countdownTicker = Timer.periodic(const Duration(seconds: 1), (
      Timer timer,
    ) {
      if (!mounted) {
        timer.cancel();
        return;
      }
      setState(() {});
    });
  }

  void _reload() {
    _disposeCommentaryFeed();
    setState(() {
      _snapshotFuture = _loadSnapshot();
      _countdownStartedAt = DateTime.now();
    });
  }

  Future<LiveMatchSnapshot> _loadSnapshot() {
    final Future<LiveMatchSnapshot> Function(CompetitionSummary competition)
    loader = widget.snapshotLoader ?? loadLiveMatchSnapshot;
    return loader(widget.competition);
  }

  Future<void> _openFeatureRoute(GteAppRouteData route) {
    final GteNavigationDependencies? dependencies =
        widget.navigationDependencies;
    if (dependencies == null) {
      return Future<void>.value();
    }
    return GteNavigationHelpers.pushRoute<void>(
      context,
      route: route,
      dependencies: dependencies,
    );
  }

  Future<void> _openHalftime() async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder:
            (BuildContext context) =>
                GteHalftimeAnalyticsScreen(competition: widget.competition),
      ),
    );
  }

  Future<void> _openHighlights() async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder:
            (BuildContext context) => GteMatchHighlightsScreen(
              competition: widget.competition,
              isAuthenticated: widget.isAuthenticated,
            ),
      ),
    );
  }

  Future<void> _openHighlightClip(
    LiveMatchSnapshot match,
    LiveMatchHighlightClip clip,
  ) async {
    if (!clip.hasPlayableStream) {
      await _openReplayViewer(
        match,
        presentationMode: MatchViewerPresentationMode.replay,
      );
      return;
    }
    await showGteMatchHighlightPlayerSheet(
      context,
      clip: clip,
      onWatchReplay: () {
        Navigator.of(context).pop();
        unawaited(
          _openReplayViewer(
            match,
            presentationMode: MatchViewerPresentationMode.replay,
          ),
        );
      },
    );
  }

  Future<void> _openBroadcast(LiveMatchSnapshot match) async {
    final Match3dUserEntitlement? entitlement =
        widget.navigationDependencies?.match3dEntitlement;
    final String matchKey =
        match.matchId?.trim().isNotEmpty == true
            ? match.matchId!.trim()
            : widget.competition.id;
    final bool competitionUpgrade =
        entitlement?.hasTournamentBoost(widget.competition.id) ?? false;
    final bool unlockedMatch = entitlement?.hasUnlockedMatch(matchKey) ?? false;
    final GtexMatchViewType initialViewType =
        competitionUpgrade ||
                unlockedMatch ||
                (entitlement?.isPremiumUser ?? false)
            ? GtexMatchViewType.pseudo3D
            : GtexMatchViewType.twoD;
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder:
            (BuildContext context) => GtexMatchBroadcastScreen(
              competition: widget.competition,
              competitionId: widget.competition.id,
              matchId: matchKey,
              fallbackSnapshot: match,
              initialMode: GtexMatchRenderMode.standard,
              viewType: initialViewType,
              isPremiumUser: entitlement?.isPremiumUser ?? false,
              spectatorMode: true,
              auto3DEnabled: competitionUpgrade,
              entitlement: entitlement,
              competitionLabel: widget.competition.name,
              onOpenHighlights:
                  match.highlightsAvailable ? _openHighlights : null,
            ),
      ),
    );
  }

  Future<void> _openReplayViewer(
    LiveMatchSnapshot match, {
    required MatchViewerPresentationMode presentationMode,
  }) async {
    final Match3dUserEntitlement? entitlement =
        widget.navigationDependencies?.match3dEntitlement;
    final String matchKey =
        match.matchId?.trim().isNotEmpty == true
            ? match.matchId!.trim()
            : widget.competition.id;
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder:
            (BuildContext context) => GtexMatchViewerScreen(
              competition: widget.competition,
              matchKey: matchKey,
              fallbackSnapshot: match,
              presentationMode: presentationMode,
              isSpectator:
                  presentationMode == MatchViewerPresentationMode.broadcast,
              renderMode: RenderMode.auto,
              entitlement: entitlement,
            ),
      ),
    );
  }

  void _bindCommentaryFeed(LiveMatchSnapshot match) {
    final String matchKey =
        match.matchId?.trim().isNotEmpty == true
            ? match.matchId!.trim()
            : widget.competition.id;
    final String bindingKey = <Object>[
      matchKey,
      match.minute,
      match.homeScore,
      match.awayScore,
      match.commentary.length,
    ].join('|');
    if (_commentaryBindingKey == bindingKey && _commentaryStream != null) {
      return;
    }
    _disposeCommentaryFeed(clearBindingKey: false);
    _commentaryBindingKey = bindingKey;
    final GteLiveCommentaryStreamLoader loader =
        widget.commentaryStreamLoader ??
        (LiveMatchSnapshot snapshot) {
          return _commentaryFeedService.watch(
            matchId: matchKey,
            seedEvents: snapshot.commentary,
          );
        };
    final Stream<List<LiveMatchEvent>> stream =
        loader(match).asBroadcastStream();
    _commentaryStream = stream;
    _commentarySubscription = stream.listen(
      (List<LiveMatchEvent> events) => _handleCommentaryUpdate(match, events),
      onError: (_) {},
    );
  }

  void _disposeCommentaryFeed({bool clearBindingKey = true}) {
    _commentarySubscription?.cancel();
    _commentarySubscription = null;
    _commentaryStream = null;
    _seenCommentaryKeys.clear();
    _commentarySeedHydrated = false;
    if (clearBindingKey) {
      _commentaryBindingKey = null;
    }
  }

  void _handleCommentaryUpdate(
    LiveMatchSnapshot match,
    List<LiveMatchEvent> events,
  ) {
    final List<LiveMatchEvent> normalized = _normalizeCommentary(events);
    if (normalized.isEmpty) {
      return;
    }
    if (!_commentarySeedHydrated) {
      _seenCommentaryKeys.addAll(normalized.map(_liveCommentaryEventKey));
      _commentarySeedHydrated = true;
      return;
    }
    final List<LiveMatchEvent> newEvents = normalized
        .where(
          (LiveMatchEvent event) =>
              !_seenCommentaryKeys.contains(_liveCommentaryEventKey(event)),
        )
        .toList(growable: false);
    if (newEvents.isEmpty) {
      return;
    }
    _seenCommentaryKeys.addAll(newEvents.map(_liveCommentaryEventKey));
    final List<LiveMatchEvent> bigMoments = newEvents
        .where(_isBigMoment)
        .toList(growable: false);
    if (bigMoments.isEmpty) {
      return;
    }
    final LiveMatchEvent spotlight = bigMoments.last;
    if (spotlight.type == LiveMatchEventType.goal) {
      unawaited(HapticFeedback.heavyImpact());
      unawaited(SystemSound.play(SystemSoundType.click));
    }
    if (!mounted) {
      return;
    }
    unawaited(_showBigMomentPrompt(match, spotlight));
  }

  Future<void> _showBigMomentPrompt(
    LiveMatchSnapshot match,
    LiveMatchEvent event,
  ) async {
    if (_bigMomentPromptOpen || !mounted) {
      return;
    }
    _bigMomentPromptOpen = true;
    final LiveMatchHighlightClip? relatedClip = _relatedClipForEvent(
      match,
      event,
    );
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (BuildContext context) {
        return SafeArea(
          top: false,
          child: Container(
            margin: const EdgeInsets.fromLTRB(16, 0, 16, 16),
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: const Color(0xFF08111B),
              borderRadius: BorderRadius.circular(22),
              border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  'Big moment',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  "${event.minute}' ${event.title}",
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 6),
                Text(
                  event.detail,
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: 14),
                Wrap(
                  spacing: 10,
                  runSpacing: 10,
                  children: <Widget>[
                    FilledButton.icon(
                      onPressed: () {
                        Navigator.of(context).pop();
                        unawaited(
                          _openReplayViewer(
                            match,
                            presentationMode:
                                MatchViewerPresentationMode.replay,
                          ),
                        );
                      },
                      icon: const Icon(Icons.sports_soccer_rounded),
                      label: const Text('Watch Replay'),
                    ),
                    if (relatedClip != null)
                      OutlinedButton.icon(
                        onPressed: () {
                          Navigator.of(context).pop();
                          if (relatedClip.hasPlayableStream) {
                            unawaited(_openHighlightClip(match, relatedClip));
                            return;
                          }
                          unawaited(_openHighlights());
                        },
                        icon: const Icon(Icons.play_circle_outline),
                        label: Text(
                          relatedClip.hasPlayableStream
                              ? 'Play Highlight'
                              : 'Highlights Hub',
                        ),
                      ),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );
    _bigMomentPromptOpen = false;
  }

  LiveMatchHighlightClip? _relatedClipForEvent(
    LiveMatchSnapshot match,
    LiveMatchEvent event,
  ) {
    final Iterable<LiveMatchHighlightClip> clips = <LiveMatchHighlightClip>[
      ...match.keyMoments,
      ...match.highlights,
    ];
    LiveMatchHighlightClip? selected;
    int? bestMinuteDelta;
    for (final LiveMatchHighlightClip clip in clips) {
      final int delta = (clip.minute - event.minute).abs();
      if (bestMinuteDelta == null || delta < bestMinuteDelta) {
        bestMinuteDelta = delta;
        selected = clip;
      }
    }
    if (bestMinuteDelta == null || bestMinuteDelta > 3) {
      return null;
    }
    return selected;
  }

  Future<void> _openSimulation(LiveMatchSnapshot match) async {
    final MatchSimulationImportance importance =
        widget.competition.capacity <= 2
            ? MatchSimulationImportance.finalMatch
            : MatchSimulationImportance.tournament;
    final MatchSimulationRequest request =
        MatchSimulationRequestFactory.fromLiveSnapshot(
          match,
          matchId:
              match.matchId?.trim().isNotEmpty == true
                  ? match.matchId!.trim()
                  : widget.competition.id,
          importance: importance,
        );
    final MatchSimulationResult result = const MatchSimulationEngine().simulate(
      request,
    );
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder:
            (BuildContext context) => GtexMatchSimulationScreen(
              result: result,
              title: '${match.homeTeam} vs ${match.awayTeam}',
              competitionLabel: widget.competition.name,
            ),
      ),
    );
  }

  String? _jackpotCountdownLabel(LiveMatchSnapshot match) {
    final CompetitionDynamicPrizePool? dynamicPrizePool =
        widget.competition.dynamicPrizePool;
    if (dynamicPrizePool?.enabled != true) {
      return null;
    }
    if (match.isFinal) {
      return 'Draw in: 00:00';
    }
    final int baseSeconds;
    if (match.phase == LiveMatchPhase.preMatch) {
      baseSeconds = 300;
    } else if (match.phase == LiveMatchPhase.halftime) {
      baseSeconds = 150;
    } else {
      final int clampedMinute = match.minute.clamp(0, 90);
      baseSeconds = (((90 - clampedMinute) / 90) * 300).round();
    }
    final int elapsed =
        DateTime.now().difference(_countdownStartedAt).inSeconds;
    final int seconds = (baseSeconds - elapsed).clamp(0, 300);
    final int minutesPart = seconds ~/ 60;
    final int secondsPart = seconds % 60;
    final String mm = minutesPart.toString().padLeft(2, '0');
    final String ss = secondsPart.toString().padLeft(2, '0');
    return 'Draw in: $mm:$ss';
  }

  @override
  void dispose() {
    _countdownTicker.cancel();
    _disposeCommentaryFeed();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: const Text('Live match center'),
          actions: <Widget>[
            IconButton(
              tooltip: 'Halftime analytics',
              onPressed: _openHalftime,
              icon: const Icon(Icons.analytics_outlined),
            ),
            IconButton(
              tooltip: 'Highlights',
              onPressed: _openHighlights,
              icon: const Icon(Icons.play_circle_outline),
            ),
          ],
        ),
        body: FutureBuilder<LiveMatchSnapshot>(
          future: _snapshotFuture,
          builder: (
            BuildContext context,
            AsyncSnapshot<LiveMatchSnapshot> snapshot,
          ) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Padding(
                padding: EdgeInsets.all(20),
                child: GteStatePanel(
                  eyebrow: 'LIVE MATCH CENTER',
                  title: 'Loading match stream',
                  message:
                      'Warming the arena feed, tactical overlay, and key moments.',
                  icon: Icons.live_tv_outlined,
                  accentColor: GteShellTheme.accentArena,
                  isLoading: true,
                ),
              );
            }
            if (!snapshot.hasData) {
              return Padding(
                padding: const EdgeInsets.all(20),
                child: GteStatePanel(
                  title: 'Live match unavailable',
                  message:
                      'Unable to load the match stream right now. Please retry.',
                  icon: Icons.warning_amber_outlined,
                  actionLabel: 'Retry',
                  onAction: _reload,
                ),
              );
            }

            final LiveMatchSnapshot match = snapshot.data!;
            _bindCommentaryFeed(match);
            final Stream<List<LiveMatchEvent>>? commentaryStream =
                _commentaryStream;
            final CompetitionDynamicPrizePool? dynamicPrizePool =
                widget.competition.dynamicPrizePool;
            final String? jackpotCountdown = _jackpotCountdownLabel(match);
            return ListView(
              padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
              children: <Widget>[
                _LiveScoreboardCard(match: match),
                if (dynamicPrizePool?.enabled == true) ...<Widget>[
                  const SizedBox(height: 16),
                  CompetitionDynamicPrizePoolCard(
                    dynamicPrizePool: dynamicPrizePool!,
                    currency: widget.competition.currency,
                    title: 'Live jackpot pulse',
                    subtitle:
                        'This pool swells with platform activity and unresolved rollover rewards while the match is still alive.',
                    countdownLabel: jackpotCountdown,
                    accentColor: GteShellTheme.accentArena,
                  ),
                ],
                const SizedBox(height: 16),
                GteSurfacePanel(
                  accentColor: GteShellTheme.accentArena,
                  emphasized: true,
                  child: Row(
                    children: <Widget>[
                      const Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Text(
                              'Live broadcast layer',
                              style: TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            SizedBox(height: 6),
                            Text(
                              'Open the immersive broadcast presentation with the live clock, masked scoreboard, camera cuts, and commentary overlays.',
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 16),
                      FilledButton.icon(
                        onPressed: () => _openBroadcast(match),
                        icon: const Icon(Icons.live_tv_outlined),
                        label: const Text('Watch broadcast'),
                      ),
                    ],
                  ),
                ),
                if (match.isFinal ||
                    match.highlightsAvailable ||
                    match.keyMomentsAvailable) ...<Widget>[
                  const SizedBox(height: 16),
                  GteSurfacePanel(
                    accentColor: GteShellTheme.accentArena,
                    child: Row(
                      children: <Widget>[
                        const Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Text(
                                '2D replay viewer',
                                style: TextStyle(
                                  fontSize: 18,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              SizedBox(height: 6),
                              Text(
                                'Open the replay-style top-down viewer to inspect marker movement, event emphasis, and the authoritative timeline.',
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 16),
                        FilledButton.icon(
                          onPressed:
                              () => _openReplayViewer(
                                match,
                                presentationMode:
                                    MatchViewerPresentationMode.replay,
                              ),
                          icon: const Icon(Icons.sports_soccer),
                          label: const Text('Open replay'),
                        ),
                      ],
                    ),
                  ),
                ],
                const SizedBox(height: 16),
                GteSurfacePanel(
                  accentColor: GteShellTheme.accentArena,
                  child: Row(
                    children: <Widget>[
                      const Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Text(
                              'Tactical match simulation',
                              style: TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            SizedBox(height: 6),
                            Text(
                              'Run the controlled realism engine with tactical causality, live 2D movement, commentary, and post-match value impact.',
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 16),
                      FilledButton.icon(
                        onPressed: () => _openSimulation(match),
                        icon: const Icon(Icons.bolt_outlined),
                        label: const Text('Run simulation'),
                      ),
                    ],
                  ),
                ),
                if (widget.navigationDependencies != null) ...<Widget>[
                  const SizedBox(height: 16),
                  GteSurfacePanel(
                    accentColor: GteShellTheme.accentArena,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          'Match extensions',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Prediction and creator-stadium routes only open from a resolved match id. This live center uses the match snapshot id instead of a placeholder.',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                        const SizedBox(height: 14),
                        Wrap(
                          spacing: 12,
                          runSpacing: 12,
                          children: <Widget>[
                            FilledButton.tonalIcon(
                              onPressed:
                                  match.matchId == null ||
                                          match.matchId!.trim().isEmpty
                                      ? null
                                      : () => _openFeatureRoute(
                                        FanPredictionMatchRouteData(
                                          matchId: match.matchId!.trim(),
                                        ),
                                      ),
                              icon: const Icon(Icons.insights_outlined),
                              label: const Text('Fan predictions'),
                            ),
                            FilledButton.tonalIcon(
                              onPressed:
                                  match.matchId == null ||
                                          match.matchId!.trim().isEmpty
                                      ? null
                                      : () => _openFeatureRoute(
                                        CreatorStadiumMatchRouteData(
                                          matchId: match.matchId!.trim(),
                                        ),
                                      ),
                              icon: const Icon(Icons.stadium_outlined),
                              label: const Text('Stadium monetization'),
                            ),
                            FilledButton.tonalIcon(
                              onPressed:
                                  () => _openFeatureRoute(
                                    WorldCompetitionContextRouteData(
                                      competitionId: widget.competition.id,
                                    ),
                                  ),
                              icon: const Icon(Icons.public_outlined),
                              label: const Text('World context'),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ],
                const SizedBox(height: 16),
                GteSurfacePanel(
                  accentColor: GteShellTheme.accentArena,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        'Spectator modes',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 10),
                      Text(
                        'Pick the view that fits the moment. The 2D commentary is free. Key-moment video is a paid, premium stream.',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 12),
                      SegmentedButton<_LiveViewMode>(
                        segments: const <ButtonSegment<_LiveViewMode>>[
                          ButtonSegment<_LiveViewMode>(
                            value: _LiveViewMode.commentary,
                            label: Text('2D commentary'),
                            icon: Icon(Icons.toc_outlined),
                          ),
                          ButtonSegment<_LiveViewMode>(
                            value: _LiveViewMode.keyMoments,
                            label: Text('Key-moment video'),
                            icon: Icon(Icons.videocam_outlined),
                          ),
                        ],
                        selected: <_LiveViewMode>{_viewMode},
                        onSelectionChanged: (Set<_LiveViewMode> value) {
                          setState(() => _viewMode = value.first);
                        },
                      ),
                      const SizedBox(height: 14),
                      if (_viewMode == _LiveViewMode.commentary)
                        StreamBuilder<List<LiveMatchEvent>>(
                          stream: commentaryStream,
                          initialData: match.commentary,
                          builder: (
                            BuildContext context,
                            AsyncSnapshot<List<LiveMatchEvent>> snapshot,
                          ) {
                            return _CommentaryPanel(
                              events: _normalizeCommentary(
                                snapshot.data ?? match.commentary,
                              ),
                              onWatchReplay: (LiveMatchEvent _) {
                                unawaited(
                                  _openReplayViewer(
                                    match,
                                    presentationMode:
                                        MatchViewerPresentationMode.replay,
                                  ),
                                );
                              },
                            );
                          },
                        )
                      else
                        _KeyMomentPanel(
                          match: match,
                          isAuthenticated: widget.isAuthenticated,
                          onOpenLogin: widget.onOpenLogin,
                          onPlayClip: (LiveMatchHighlightClip clip) {
                            unawaited(_openHighlightClip(match, clip));
                          },
                          onWatchReplay: () {
                            unawaited(
                              _openReplayViewer(
                                match,
                                presentationMode:
                                    MatchViewerPresentationMode.replay,
                              ),
                            );
                          },
                        ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                GteSurfacePanel(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        'Live momentum',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Momentum reads update in real time. Browsing tactics and stats never pauses the match stream.',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 14),
                      _MomentumStrip(values: match.momentum),
                    ],
                  ),
                ),
                const SizedBox(height: 20),
                const GtexSectionHeader(
                  eyebrow: 'TACTICS + STATS',
                  title: 'Stay in the match while managing tactics live.',
                  description:
                      'Spectators can scan tactics, stats, and incidents without pausing the action.',
                  accent: GteShellTheme.accentArena,
                ),
                const SizedBox(height: 14),
                GteSurfacePanel(
                  child: DefaultTabController(
                    length: 4,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        const TabBar(
                          isScrollable: true,
                          tabAlignment: TabAlignment.start,
                          tabs: <Tab>[
                            Tab(text: 'Stats'),
                            Tab(text: 'Tactics'),
                            Tab(text: 'Lineups'),
                            Tab(text: 'Incidents'),
                          ],
                        ),
                        const SizedBox(height: 12),
                        SizedBox(
                          height: 360,
                          child: TabBarView(
                            children: <Widget>[
                              _MatchStatsView(match: match),
                              _TacticsView(
                                toggles: _tacticToggles,
                                onToggle: (String key, bool value) {
                                  setState(() => _tacticToggles[key] = value);
                                },
                                onApply: () {
                                  AppFeedback.showSuccess(
                                    context,
                                    'Tactical changes applied without pausing the match.',
                                  );
                                },
                              ),
                              _LineupsView(match: match),
                              _IncidentView(match: match),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _LiveScoreboardCard extends StatelessWidget {
  const _LiveScoreboardCard({required this.match});

  final LiveMatchSnapshot match;

  @override
  Widget build(BuildContext context) {
    final String status =
        match.isFinal
            ? 'FINAL'
            : match.isHalftime
            ? 'HALFTIME'
            : match.isLive
            ? 'LIVE ${match.minute}\''
            : 'PRE-MATCH';
    return GteSurfacePanel(
      accentColor: GteShellTheme.accentArena,
      emphasized: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: <Widget>[
              _StatusChip(label: status),
              const GteMetricChip(label: 'Spectator', value: 'OPEN'),
              const GteMetricChip(label: 'Video', value: 'KEY MOMENTS'),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: <Widget>[
              Expanded(
                child: _TeamScore(
                  team: match.homeTeam,
                  score: match.homeScore,
                  alignRight: false,
                  featuredPlayer: _featuredPlayer(match.homeLineup),
                  matchId: match.matchId,
                ),
              ),
              const SizedBox(width: 10),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 14,
                  vertical: 10,
                ),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(16),
                  color: Colors.white.withValues(alpha: 0.06),
                  border: Border.all(
                    color: Colors.white.withValues(alpha: 0.14),
                  ),
                ),
                child: Text(
                  '${match.homeScore} : ${match.awayScore}',
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _TeamScore(
                  team: match.awayTeam,
                  score: match.awayScore,
                  alignRight: true,
                  featuredPlayer: _featuredPlayer(match.awayLineup),
                  matchId: match.matchId,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            'Tactical changes apply instantly, without pausing the match feed.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }

  LiveMatchLineupPlayer? _featuredPlayer(List<LiveMatchLineupPlayer> players) {
    for (final LiveMatchLineupPlayer player in players) {
      if (player.captain) {
        return player;
      }
    }
    if (players.isEmpty) {
      return null;
    }
    return players.first;
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: GteShellTheme.accentArena.withValues(alpha: 0.18),
        border: Border.all(
          color: GteShellTheme.accentArena.withValues(alpha: 0.4),
        ),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelLarge?.copyWith(
          color: GteShellTheme.accentArena,
          letterSpacing: 1.1,
        ),
      ),
    );
  }
}

class _TeamScore extends StatelessWidget {
  const _TeamScore({
    required this.team,
    required this.score,
    required this.alignRight,
    required this.featuredPlayer,
    required this.matchId,
  });

  final String team;
  final int score;
  final bool alignRight;
  final LiveMatchLineupPlayer? featuredPlayer;
  final String? matchId;

  @override
  Widget build(BuildContext context) {
    final avatar =
        featuredPlayer == null
            ? null
            : AvatarMapper.fromLiveLineupPlayer(
              featuredPlayer!,
              teamName: team,
              matchId: matchId,
            );
    return Column(
      crossAxisAlignment:
          alignRight ? CrossAxisAlignment.end : CrossAxisAlignment.start,
      children: <Widget>[
        if (avatar != null) ...<Widget>[
          MatchHudAvatar(avatar: avatar),
          const SizedBox(height: 8),
        ],
        Text(
          team,
          style: Theme.of(context).textTheme.titleMedium,
          textAlign: alignRight ? TextAlign.right : TextAlign.left,
        ),
        const SizedBox(height: 6),
        Text(
          'Scoreline focus',
          style: Theme.of(context).textTheme.bodySmall,
          textAlign: alignRight ? TextAlign.right : TextAlign.left,
        ),
      ],
    );
  }
}

class _CommentaryPanel extends StatefulWidget {
  const _CommentaryPanel({required this.events, required this.onWatchReplay});

  final List<LiveMatchEvent> events;
  final ValueChanged<LiveMatchEvent> onWatchReplay;

  @override
  State<_CommentaryPanel> createState() => _CommentaryPanelState();
}

class _CommentaryPanelState extends State<_CommentaryPanel> {
  late final ScrollController _scrollController;

  @override
  void initState() {
    super.initState();
    _scrollController = ScrollController();
    _scheduleAutoScroll();
  }

  @override
  void didUpdateWidget(covariant _CommentaryPanel oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.events.length != widget.events.length) {
      _scheduleAutoScroll();
    }
  }

  void _scheduleAutoScroll() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scrollController.hasClients) {
        return;
      }
      final double target = _scrollController.position.maxScrollExtent;
      if ((_scrollController.offset - target).abs() < 4) {
        _scrollController.jumpTo(target);
        return;
      }
      _scrollController.animateTo(
        target,
        duration: const Duration(milliseconds: 280),
        curve: Curves.easeOutCubic,
      );
    });
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final List<LiveMatchEvent> events =
        widget.events.length > 14
            ? widget.events.sublist(widget.events.length - 14)
            : widget.events;
    if (events.isEmpty) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            '2D commentary feed',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          Text(
            'No live commentary yet. Check back after kickoff.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          '2D commentary feed',
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 8),
        Text(
          'The feed stays pinned to the latest moment automatically.',
          style: Theme.of(context).textTheme.bodySmall,
        ),
        const SizedBox(height: 10),
        SizedBox(
          height: 300,
          child: Scrollbar(
            controller: _scrollController,
            thumbVisibility: true,
            child: ListView.separated(
              controller: _scrollController,
              itemCount: events.length,
              itemBuilder: (BuildContext context, int index) {
                final LiveMatchEvent event = events[index];
                final Color accent = _commentaryAccentFor(event.type);
                final bool replayable = _isBigMoment(event);
                return Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(14),
                    color: accent.withValues(alpha: 0.12),
                    border: Border.all(color: accent.withValues(alpha: 0.38)),
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Container(
                        width: 36,
                        height: 36,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: accent.withValues(alpha: 0.18),
                        ),
                        child: Icon(
                          _commentaryIconFor(event.type),
                          size: 18,
                          color: accent,
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Text(
                              "${event.minute}'  ${event.title}",
                              style: Theme.of(context).textTheme.titleSmall,
                            ),
                            const SizedBox(height: 4),
                            Text(
                              event.detail,
                              style: Theme.of(context).textTheme.bodySmall,
                            ),
                            if (replayable) ...<Widget>[
                              const SizedBox(height: 10),
                              TextButton.icon(
                                onPressed: () => widget.onWatchReplay(event),
                                icon: const Icon(Icons.play_circle_outline),
                                label: const Text('Watch Replay'),
                              ),
                            ],
                          ],
                        ),
                      ),
                    ],
                  ),
                );
              },
              separatorBuilder: (_, __) => const SizedBox(height: 8),
            ),
          ),
        ),
      ],
    );
  }
}

class _KeyMomentPanel extends StatelessWidget {
  const _KeyMomentPanel({
    required this.match,
    required this.isAuthenticated,
    required this.onOpenLogin,
    required this.onPlayClip,
    required this.onWatchReplay,
  });

  final LiveMatchSnapshot match;
  final bool isAuthenticated;
  final VoidCallback? onOpenLogin;
  final ValueChanged<LiveMatchHighlightClip> onPlayClip;
  final VoidCallback onWatchReplay;

  @override
  Widget build(BuildContext context) {
    if (!isAuthenticated) {
      return Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          color: Colors.white.withValues(alpha: 0.04),
          border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              'Key-moment video locked',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 6),
            Text(
              'Sign in and unlock the premium key-moment stream for the current match.',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 10),
            FilledButton(
              onPressed: onOpenLogin,
              child: const Text('Unlock with Arena Pass'),
            ),
          ],
        ),
      );
    }

    if (match.keyMoments.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          color: Colors.white.withValues(alpha: 0.04),
          border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              'Key-moment video',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 6),
            Text(
              'No premium key moments yet. The stream will populate as the match progresses.',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          'Key-moment video',
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 8),
        ...match.keyMoments.map(
          (LiveMatchHighlightClip clip) => Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(14),
                color: Colors.white.withValues(alpha: 0.04),
                border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
              ),
              child: Row(
                children: <Widget>[
                  const Icon(Icons.videocam_outlined),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          clip.title,
                          style: Theme.of(context).textTheme.titleSmall,
                        ),
                        const SizedBox(height: 4),
                        Text(
                          "${clip.minute}' | ${clip.durationLabel}",
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                        const SizedBox(height: 4),
                        Text(
                          clip.hasPlayableStream
                              ? 'Highlight stream ready now.'
                              : 'Clip render pending. Replay is available now.',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ],
                    ),
                  ),
                  FilledButton.tonal(
                    onPressed:
                        () =>
                            clip.hasPlayableStream
                                ? onPlayClip(clip)
                                : onWatchReplay(),
                    child: Text(
                      clip.hasPlayableStream ? 'Play' : 'Watch Replay',
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}

List<LiveMatchEvent> _normalizeCommentary(List<LiveMatchEvent> events) {
  final List<LiveMatchEvent> sorted = events.toList(growable: false);
  sorted.sort((LiveMatchEvent left, LiveMatchEvent right) {
    final int minuteCompare = left.minute.compareTo(right.minute);
    if (minuteCompare != 0) {
      return minuteCompare;
    }
    final int typeCompare = left.type.index.compareTo(right.type.index);
    if (typeCompare != 0) {
      return typeCompare;
    }
    final int titleCompare = left.title.compareTo(right.title);
    if (titleCompare != 0) {
      return titleCompare;
    }
    return left.detail.compareTo(right.detail);
  });
  return sorted;
}

String _liveCommentaryEventKey(LiveMatchEvent event) {
  return <Object>[
    event.minute,
    event.type.name,
    event.team.trim().toLowerCase(),
    event.title.trim().toLowerCase(),
    event.detail.trim().toLowerCase(),
    event.isKeyMoment,
  ].join('|');
}

bool _isBigMoment(LiveMatchEvent event) {
  return event.type == LiveMatchEventType.goal || event.isKeyMoment;
}

Color _commentaryAccentFor(LiveMatchEventType type) {
  switch (type) {
    case LiveMatchEventType.goal:
      return GteShellTheme.accentCommunity;
    case LiveMatchEventType.card:
      return GteShellTheme.accentWarm;
    case LiveMatchEventType.substitution:
      return GteShellTheme.accentArena;
    case LiveMatchEventType.incident:
      return Colors.white;
  }
}

IconData _commentaryIconFor(LiveMatchEventType type) {
  switch (type) {
    case LiveMatchEventType.goal:
      return Icons.sports_soccer_rounded;
    case LiveMatchEventType.card:
      return Icons.crop_portrait_rounded;
    case LiveMatchEventType.substitution:
      return Icons.swap_horiz_rounded;
    case LiveMatchEventType.incident:
      return Icons.graphic_eq_rounded;
  }
}

class _MomentumStrip extends StatelessWidget {
  const _MomentumStrip({required this.values});

  final List<int> values;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 68,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: values
            .map(
              (int value) => Expanded(
                child: Container(
                  margin: const EdgeInsets.symmetric(horizontal: 3),
                  height: 10 + (value.abs() * 12).toDouble(),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(8),
                    color:
                        value >= 0
                            ? GteShellTheme.accentArena.withValues(alpha: 0.6)
                            : GteShellTheme.accentWarm.withValues(alpha: 0.6),
                  ),
                ),
              ),
            )
            .toList(growable: false),
      ),
    );
  }
}

class _MatchStatsView extends StatelessWidget {
  const _MatchStatsView({required this.match});

  final LiveMatchSnapshot match;

  @override
  Widget build(BuildContext context) {
    final int homeMomentum =
        match.momentum.where((int value) => value > 0).length;
    final int awayMomentum =
        match.momentum.where((int value) => value < 0).length;
    final int total = homeMomentum + awayMomentum + 1;
    final int homePossession = (45 + (homeMomentum / total * 20)).round();
    final int awayPossession = 100 - homePossession;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Wrap(
          spacing: 10,
          runSpacing: 10,
          children: <Widget>[
            GteMetricChip(
              label: '${match.homeTeam} Poss',
              value: '$homePossession%',
            ),
            GteMetricChip(
              label: '${match.awayTeam} Poss',
              value: '$awayPossession%',
            ),
            GteMetricChip(
              label: 'Shots',
              value: '${3 + match.homeScore + match.awayScore}',
            ),
            GteMetricChip(
              label: 'xG (est)',
              value: '${1.1 + match.homeScore * 0.4}',
            ),
            GteMetricChip(label: 'Pressing', value: 'Aggressive'),
          ],
        ),
        const SizedBox(height: 16),
        Text(
          'Stats update in real time while the match continues.',
          style: Theme.of(context).textTheme.bodySmall,
        ),
      ],
    );
  }
}

class _TacticsView extends StatelessWidget {
  const _TacticsView({
    required this.toggles,
    required this.onToggle,
    required this.onApply,
  });

  final Map<String, bool> toggles;
  final void Function(String key, bool value) onToggle;
  final VoidCallback onApply;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          'Tactical changes can be applied at any time without pausing the match.',
          style: Theme.of(context).textTheme.bodySmall,
        ),
        const SizedBox(height: 12),
        ...toggles.entries.map(
          (MapEntry<String, bool> entry) => SwitchListTile(
            value: entry.value,
            onChanged: (bool value) => onToggle(entry.key, value),
            title: Text(entry.key),
            dense: true,
            contentPadding: EdgeInsets.zero,
          ),
        ),
        const SizedBox(height: 8),
        FilledButton.icon(
          onPressed: onApply,
          icon: const Icon(Icons.tune_outlined),
          label: const Text('Apply tactical changes'),
        ),
      ],
    );
  }
}

class _LineupsView extends StatelessWidget {
  const _LineupsView({required this.match});

  final LiveMatchSnapshot match;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(match.homeTeam, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 6),
          ...match.homeLineup.map((LiveMatchLineupPlayer player) {
            return _LineupTile(
              player: player,
              teamName: match.homeTeam,
              matchId: match.matchId,
            );
          }),
          const SizedBox(height: 16),
          Text(match.awayTeam, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 6),
          ...match.awayLineup.map((LiveMatchLineupPlayer player) {
            return _LineupTile(
              player: player,
              teamName: match.awayTeam,
              matchId: match.matchId,
            );
          }),
        ],
      ),
    );
  }
}

class _LineupTile extends StatelessWidget {
  const _LineupTile({
    required this.player,
    required this.teamName,
    required this.matchId,
  });

  final LiveMatchLineupPlayer player;
  final String teamName;
  final String? matchId;

  @override
  Widget build(BuildContext context) {
    final avatar = AvatarMapper.fromLiveLineupPlayer(
      player,
      teamName: teamName,
      matchId: matchId,
    );
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: <Widget>[
          SizedBox(
            width: 32,
            child: Text(
              player.position,
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ),
          SquadAvatarBadge(avatar: avatar, size: 32),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              player.captain ? '${player.name} (C)' : player.name,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ),
          Text(
            player.rating.toStringAsFixed(1),
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }
}

class _IncidentView extends StatelessWidget {
  const _IncidentView({required this.match});

  final LiveMatchSnapshot match;

  @override
  Widget build(BuildContext context) {
    if (match.cards.isEmpty && match.substitutions.isEmpty) {
      return Text(
        'No incidents logged yet.',
        style: Theme.of(context).textTheme.bodySmall,
      );
    }
    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          if (match.cards.isNotEmpty) ...<Widget>[
            Text('Cards', style: Theme.of(context).textTheme.titleSmall),
            const SizedBox(height: 6),
            ...match.cards.map(
              (LiveMatchEvent event) => _IncidentTile(event: event),
            ),
            const SizedBox(height: 12),
          ],
          if (match.substitutions.isNotEmpty) ...<Widget>[
            Text(
              'Substitutions',
              style: Theme.of(context).textTheme.titleSmall,
            ),
            const SizedBox(height: 6),
            ...match.substitutions.map(
              (LiveMatchEvent event) => _IncidentTile(event: event),
            ),
          ],
        ],
      ),
    );
  }
}

class _IncidentTile extends StatelessWidget {
  const _IncidentTile({required this.event});

  final LiveMatchEvent event;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: <Widget>[
          Text(
            '${event.minute}\'',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  event.title,
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                Text(
                  event.detail,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
