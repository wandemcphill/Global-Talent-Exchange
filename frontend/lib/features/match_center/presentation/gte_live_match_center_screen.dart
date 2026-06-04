import 'package:flutter/material.dart';
import 'package:gte_frontend/features/match_center/data/live_match_fixtures.dart';
import 'package:gte_frontend/features/match_center/match_center.dart';
import 'package:gte_frontend/features/match_center/live_match_session.dart';
import 'package:gte_frontend/features/match_center/live_match_session_service.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';
import 'package:gte_frontend/features/compete/domain/competition_models.dart';
import 'package:gte_frontend/features/match_center/realtime/realtime.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

typedef GteLiveMatchSnapshotLoader =
    Future<LiveMatchSnapshot> Function(
      CompetitionSummary competition, {
      String? matchId,
    });
typedef GteLiveMatchSessionResolver =
    Future<LiveMatchSpectateSession?> Function(String matchId);
typedef GteLiveMatchWebSocketResolver = Uri? Function(String? websocketPath);
typedef GteLiveMatchRealtimeWatcher =
    Stream<LiveMatchRealtimeFrame> Function(LiveMatchRealtimeRequest request);

class GteLiveMatchCenterScreen extends StatefulWidget {
  const GteLiveMatchCenterScreen({
    super.key,
    required this.competition,
    this.matchId,
    this.isAuthenticated = false,
    this.onOpenLogin,
    this.snapshotLoader,
    this.sessionResolver,
    this.webSocketResolver,
    this.realtimeWatcher,
    this.navigationDependencies,
  });

  final CompetitionSummary competition;
  final String? matchId;
  final bool isAuthenticated;
  final VoidCallback? onOpenLogin;
  final GteLiveMatchSnapshotLoader? snapshotLoader;
  final GteLiveMatchSessionResolver? sessionResolver;
  final GteLiveMatchWebSocketResolver? webSocketResolver;
  final GteLiveMatchRealtimeWatcher? realtimeWatcher;
  final GteNavigationDependencies? navigationDependencies;

  @override
  State<GteLiveMatchCenterScreen> createState() =>
      _GteLiveMatchCenterScreenState();
}

class _GteLiveMatchCenterScreenState extends State<GteLiveMatchCenterScreen> {
  late Future<LiveMatchSnapshot> _snapshotFuture;

  @override
  void initState() {
    super.initState();
    _snapshotFuture = _loadSnapshot();
  }

  @override
  void didUpdateWidget(covariant GteLiveMatchCenterScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.competition.id != widget.competition.id ||
        oldWidget.matchId != widget.matchId ||
        oldWidget.snapshotLoader != widget.snapshotLoader) {
      _snapshotFuture = _loadSnapshot();
    }
  }

  Future<LiveMatchSnapshot> _loadSnapshot() {
    final GteLiveMatchSnapshotLoader? loader = widget.snapshotLoader;
    if (loader != null) {
      return loader(widget.competition, matchId: widget.matchId);
    }
    return loadLiveMatchSnapshot(widget.competition, matchId: widget.matchId);
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(title: const Text('Live match center')),
        body: FutureBuilder<LiveMatchSnapshot>(
          future: _snapshotFuture,
          builder: (
            BuildContext context,
            AsyncSnapshot<LiveMatchSnapshot> snapshot,
          ) {
            if (snapshot.connectionState != ConnectionState.done) {
              return const _MatchCenterLoadingShell();
            }
            if (snapshot.hasError || !snapshot.hasData) {
              return _MatchCenterErrorShell(
                onRetry: () {
                  setState(() {
                    _snapshotFuture = _loadSnapshot();
                  });
                },
              );
            }
            return _RealtimeMatchCenterCompositionShell(
              competition: widget.competition,
              requestedMatchId: widget.matchId,
              match: snapshot.data!,
              sessionResolver: widget.sessionResolver,
              webSocketResolver: widget.webSocketResolver,
              realtimeWatcher: widget.realtimeWatcher,
            );
          },
        ),
      ),
    );
  }
}

class _RealtimeMatchCenterCompositionShell extends StatefulWidget {
  const _RealtimeMatchCenterCompositionShell({
    required this.competition,
    required this.requestedMatchId,
    required this.match,
    required this.sessionResolver,
    required this.webSocketResolver,
    required this.realtimeWatcher,
  });

  final CompetitionSummary competition;
  final String? requestedMatchId;
  final LiveMatchSnapshot match;
  final GteLiveMatchSessionResolver? sessionResolver;
  final GteLiveMatchWebSocketResolver? webSocketResolver;
  final GteLiveMatchRealtimeWatcher? realtimeWatcher;

  @override
  State<_RealtimeMatchCenterCompositionShell> createState() =>
      _RealtimeMatchCenterCompositionShellState();
}

class _RealtimeMatchCenterCompositionShellState
    extends State<_RealtimeMatchCenterCompositionShell> {
  late final LiveMatchSessionService _sessionService =
      LiveMatchSessionService();
  late final BackendLiveMatchRealtimeProvider _realtimeProvider =
      BackendLiveMatchRealtimeProvider();
  late Future<_ResolvedLiveMatchSession> _sessionFuture;
  LiveMatchRealtimeRequest? _activeRealtimeRequest;
  Stream<LiveMatchRealtimeFrame>? _activeRealtimeStream;

  String get _resolvedMatchId {
    final String? requested = widget.requestedMatchId?.trim();
    if (requested != null && requested.isNotEmpty) {
      return requested;
    }
    final String? snapshotMatchId = widget.match.matchId?.trim();
    if (snapshotMatchId != null && snapshotMatchId.isNotEmpty) {
      return snapshotMatchId;
    }
    return widget.competition.id;
  }

  @override
  void initState() {
    super.initState();
    _sessionFuture = _resolveSession();
  }

  @override
  void didUpdateWidget(
    covariant _RealtimeMatchCenterCompositionShell oldWidget,
  ) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.requestedMatchId != widget.requestedMatchId ||
        oldWidget.match.matchId != widget.match.matchId ||
        oldWidget.sessionResolver != widget.sessionResolver ||
        oldWidget.webSocketResolver != widget.webSocketResolver ||
        oldWidget.realtimeWatcher != widget.realtimeWatcher) {
      _sessionFuture = _resolveSession();
    }
  }

  Future<_ResolvedLiveMatchSession> _resolveSession() async {
    final GteLiveMatchSessionResolver sessionResolver =
        widget.sessionResolver ?? _sessionService.resolveSession;
    final GteLiveMatchWebSocketResolver webSocketResolver =
        widget.webSocketResolver ?? _sessionService.resolveWebSocketUri;
    final LiveMatchSpectateSession? session = await sessionResolver(
      _resolvedMatchId,
    );
    final Uri? snapshotWebSocketUri = webSocketResolver(session?.websocketPath);
    final Uri? commentaryWebSocketUri = webSocketResolver(
      session?.commentaryWebsocketPath,
    );
    return _ResolvedLiveMatchSession(
      snapshotWebSocketUri: snapshotWebSocketUri,
      commentaryWebSocketUri: commentaryWebSocketUri,
    );
  }

  Stream<LiveMatchRealtimeFrame> _watchRealtime(
    LiveMatchRealtimeRequest request,
  ) {
    final LiveMatchRealtimeRequest? activeRequest = _activeRealtimeRequest;
    final Stream<LiveMatchRealtimeFrame>? activeStream = _activeRealtimeStream;
    if (activeRequest == request && activeStream != null) {
      return activeStream;
    }
    final GteLiveMatchRealtimeWatcher? watcher = widget.realtimeWatcher;
    if (watcher != null) {
      final Stream<LiveMatchRealtimeFrame> stream = watcher(request);
      _activeRealtimeRequest = request;
      _activeRealtimeStream = stream;
      return stream;
    }
    final Stream<LiveMatchRealtimeFrame> stream = _realtimeProvider.watch(
      request,
    );
    _activeRealtimeRequest = request;
    _activeRealtimeStream = stream;
    return stream;
  }

  LiveMatchRealtimeFrame _frame(
    LiveMatchRealtimeStatus status,
    LiveMatchRealtimeSource source, {
    String? code,
    String? message,
  }) {
    return LiveMatchRealtimeFrame.fromSnapshot(
      snapshot: widget.match,
      status: status,
      source: source,
      hasBackendSnapshotTruth: false,
      issue:
          code == null || message == null
              ? null
              : LiveMatchRealtimeIssue(
                code: code,
                message: message,
                source: source,
              ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final MatchCenterReadiness readiness = MatchCenterReadiness.fromSnapshot(
      widget.match,
    );
    return FutureBuilder<_ResolvedLiveMatchSession>(
      future: _sessionFuture,
      builder: (
        BuildContext context,
        AsyncSnapshot<_ResolvedLiveMatchSession> sessionSnapshot,
      ) {
        final Widget body;
        if (sessionSnapshot.connectionState != ConnectionState.done) {
          body = MatchCenterSurface.fromRealtimeFrame(
            frame: _frame(
              LiveMatchRealtimeStatus.connecting,
              LiveMatchRealtimeSource.transport,
              code: 'resolving_live_session',
              message:
                  'Resolving the backend spectate session before opening the realtime 2D lane.',
            ),
          );
        } else if (sessionSnapshot.hasError ||
            !sessionSnapshot.hasData ||
            sessionSnapshot.data!.snapshotWebSocketUri == null) {
          body = MatchCenterSurface.fromRealtimeFrame(
            frame: _frame(
              LiveMatchRealtimeStatus.blocked,
              LiveMatchRealtimeSource.snapshotWebSocket,
              code: 'missing_snapshot_websocket',
              message:
                  'The backend did not provide a live snapshot websocket for this match.',
            ),
          );
        } else {
          final _ResolvedLiveMatchSession resolved = sessionSnapshot.data!;
          final LiveMatchRealtimeRequest request = LiveMatchRealtimeRequest(
            seed: widget.match,
            snapshotWebSocketUri: resolved.snapshotWebSocketUri,
            commentaryWebSocketUri: resolved.commentaryWebSocketUri,
          );
          body = StreamBuilder<LiveMatchRealtimeFrame>(
            stream: _watchRealtime(request),
            builder: (
              BuildContext context,
              AsyncSnapshot<LiveMatchRealtimeFrame> realtimeSnapshot,
            ) {
              final LiveMatchRealtimeFrame frame =
                  realtimeSnapshot.data ??
                  _frame(
                    LiveMatchRealtimeStatus.connecting,
                    LiveMatchRealtimeSource.snapshotWebSocket,
                    code: 'awaiting_backend_snapshot',
                    message:
                        'Live websocket route is open; waiting for a backend score-clock frame.',
                  );
              return MatchCenterSurface.fromRealtimeFrame(frame: frame);
            },
          );
        }
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
          children: <Widget>[
            GteSurfacePanel(
              emphasized: true,
              accentColor: GteShellTheme.accentArena,
              child: Wrap(
                spacing: 10,
                runSpacing: 10,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: <Widget>[
                  _RouteMetric(
                    label: 'Competition',
                    value: widget.competition.name,
                  ),
                  _RouteMetric(label: 'Match', value: _resolvedMatchId),
                  _RouteMetric(
                    label: 'Scorebug',
                    value: readiness.scorebug.label,
                  ),
                  _RouteMetric(
                    label: 'Timeline',
                    value: readiness.timeline.label,
                  ),
                  _RouteMetric(
                    label: 'Realtime',
                    value:
                        sessionSnapshot.hasData &&
                                sessionSnapshot.data!.snapshotWebSocketUri !=
                                    null
                            ? 'WEBSOCKET'
                            : 'BLOCKED',
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            body,
          ],
        );
      },
    );
  }
}

class _ResolvedLiveMatchSession {
  const _ResolvedLiveMatchSession({
    required this.snapshotWebSocketUri,
    required this.commentaryWebSocketUri,
  });

  final Uri? snapshotWebSocketUri;
  final Uri? commentaryWebSocketUri;
}

class _MatchCenterLoadingShell extends StatelessWidget {
  const _MatchCenterLoadingShell();

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
      children: <Widget>[
        GteStatePanel(
          title: 'Loading live match',
          message: 'Fetching the backend-authored match center snapshot.',
          isLoading: true,
        ),
      ],
    );
  }
}

class _MatchCenterErrorShell extends StatelessWidget {
  const _MatchCenterErrorShell({required this.onRetry});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
      children: <Widget>[
        GteStatePanel(
          title: 'Live match unavailable',
          message:
              'The canonical match center could not load a backend-authored snapshot.',
          icon: Icons.error_outline,
          accentColor: Theme.of(context).colorScheme.error,
          actionLabel: 'Retry',
          onAction: onRetry,
        ),
      ],
    );
  }
}

class _RouteMetric extends StatelessWidget {
  const _RouteMetric({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return Container(
      constraints: const BoxConstraints(minWidth: 132),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Text(
            label,
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: tokens.textMuted,
              letterSpacing: 0,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            value,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: tokens.textPrimary,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }
}
