import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../models/match_view_state.dart';
import '../../screens/match/gtex_match_viewer_screen.dart';
import '../../shared/models/data_source_status.dart';
import 'live_match_viewer_route_support.dart';
import 'match_viewer_capability.dart';

class MatchViewerRouteScreen extends ConsumerWidget {
  const MatchViewerRouteScreen({super.key, required this.matchKey});

  final String matchKey;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final String resolvedMatchKey = matchKey.trim();
    if (resolvedMatchKey.isEmpty) {
      return const MatchRouteBlockedScreen(
        title: '2D Match Viewer',
        subtitle:
            'This 2D route opens only after the selected match is identified from the active viewer contract.',
        reason:
            'The 2D route could not open because the selected match reference was missing.',
        detailTitle: 'Match unavailable',
        detailSubtitle:
            'Pick a routed match to open the live 2D viewer or its truthful demo fallback.',
      );
    }

    final AsyncValue<LiveMatchViewerQualifiedRoute> qualifiedRoute = ref.watch(
      liveMatchViewerQualifiedRouteProvider(resolvedMatchKey),
    );

    return qualifiedRoute.when(
      data: (LiveMatchViewerQualifiedRoute value) {
        final LiveMatchViewerRepository repository = ref.read(
          liveMatchViewerRepositoryProvider,
        );
        return MatchRouteCapabilityOverlay(
          capability: MatchViewerCapability.twoD,
          child: _QualifiedMatchViewerRouteView(
            key: ValueKey<String>('match-viewer-route-$resolvedMatchKey'),
            matchKey: resolvedMatchKey,
            bootstrap: value.bootstrap,
            initialViewState: value.initialViewState,
            repository: repository,
          ),
        );
      },
      loading:
          () => const MatchRouteLoadingScreen(
            title: '2D Match Viewer',
            subtitle:
                'Verifying the live match-viewer session before opening the tactical 2D lane.',
            capability: MatchViewerCapability.twoD,
          ),
      error:
          (Object _, StackTrace __) => MatchRouteCapabilityOverlay(
            capability: MatchViewerCapability.twoD,
            status: DataSourceStatus.demo,
            child: _FallbackMatchViewerRouteView(matchKey: resolvedMatchKey),
          ),
    );
  }
}

class _QualifiedMatchViewerRouteView extends StatefulWidget {
  const _QualifiedMatchViewerRouteView({
    super.key,
    required this.matchKey,
    required this.bootstrap,
    required this.initialViewState,
    required this.repository,
  });

  final String matchKey;
  final LiveMatchViewerBootstrap bootstrap;
  final MatchViewState initialViewState;
  final LiveMatchViewerRepository repository;

  @override
  State<_QualifiedMatchViewerRouteView> createState() =>
      _QualifiedMatchViewerRouteViewState();
}

class _QualifiedMatchViewerRouteViewState
    extends State<_QualifiedMatchViewerRouteView> {
  bool _usedQualifiedInitialState = false;

  @override
  void didUpdateWidget(covariant _QualifiedMatchViewerRouteView oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.matchKey != widget.matchKey ||
        !identical(oldWidget.initialViewState, widget.initialViewState)) {
      _usedQualifiedInitialState = false;
    }
  }

  @override
  Widget build(BuildContext context) {
    return GtexMatchViewerScreen(
      competition: widget.bootstrap.competition,
      matchKey: widget.matchKey,
      titleOverride: '2D Match Viewer',
      viewStateLoader: _loadInitialViewState,
      continuationLoader: _loadContinuation,
    );
  }

  Future<MatchViewState> _loadInitialViewState() async {
    if (!_usedQualifiedInitialState) {
      _usedQualifiedInitialState = true;
      return widget.initialViewState;
    }
    return qualifyLiveMatchViewerState(
      matchKey: widget.matchKey,
      state: await widget.repository.loadViewState(widget.matchKey),
    );
  }

  Future<MatchViewState> _loadContinuation({
    required String matchKey,
    required String continuationToken,
  }) async {
    return qualifyLiveMatchViewerState(
      matchKey: widget.matchKey,
      state: await widget.repository.loadViewState(
        widget.matchKey,
        continuationToken: continuationToken,
      ),
    );
  }
}

class _FallbackMatchViewerRouteView extends StatelessWidget {
  const _FallbackMatchViewerRouteView({required this.matchKey});

  final String matchKey;

  @override
  Widget build(BuildContext context) {
    return GtexMatchViewerScreen(
      competition: buildLiveViewerCompetition(matchKey, <String, Object?>{
        'title': '2D Match Viewer',
      }),
      matchKey: matchKey,
      preferFallback: true,
      titleOverride: '2D Match Viewer',
    );
  }
}
