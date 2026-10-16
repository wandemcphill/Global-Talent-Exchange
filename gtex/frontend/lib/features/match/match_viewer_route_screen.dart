import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/gte_api_repository.dart';
import '../../data/match_gift_api.dart';
import '../../models/match_view_state.dart';
import '../../screens/match/gtex_match_viewer_screen.dart';
import '../../shared/models/data_source_status.dart';
import '../../shared/providers/auth_provider.dart';
import 'live_match_viewer_route_support.dart';
import 'match_viewer_capability.dart';

class MatchViewerRouteScreen extends ConsumerWidget {
  const MatchViewerRouteScreen({super.key, required this.matchKey});

  final String matchKey;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final String resolvedMatchKey = matchKey.trim();
    final bool allowFixtureFallback =
        ref.watch(criticalBackendModeProvider) == GteBackendMode.fixture;
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
        final MatchGiftClient? giftClient =
            ref.watch(isAuthenticatedProvider)
                ? MatchGiftApi(client: ref.watch(authedApiProvider))
                : null;
        return MatchRouteCapabilityOverlay(
          capability: MatchViewerCapability.twoD,
          child: _QualifiedMatchViewerRouteView(
            key: ValueKey<String>('match-viewer-route-$resolvedMatchKey'),
            matchKey: resolvedMatchKey,
            bootstrap: value.bootstrap,
            initialViewState: value.initialViewState,
            repository: repository,
            giftClient: giftClient,
          ),
        );
      },
      loading:
          () => const MatchRouteLoadingScreen(
            title: '2D Match Viewer',
            subtitle: 'Checking for a live match or an official replay.',
            capability: MatchViewerCapability.twoD,
          ),
      error: (Object error, StackTrace __) {
        if (allowFixtureFallback) {
          return MatchRouteCapabilityOverlay(
            capability: MatchViewerCapability.twoD,
            status: DataSourceStatus.demo,
            child: _FallbackMatchViewerRouteView(matchKey: resolvedMatchKey),
          );
        }
        final _MatchViewerRouteFailure failure = _MatchViewerRouteFailure.from(
          error,
        );
        return MatchRouteBlockedScreen(
          title: '2D Match Viewer',
          subtitle: failure.subtitle,
          reason: failure.reason,
          detailTitle: failure.title,
          detailSubtitle: failure.detail,
          actionLabel: failure.actionLabel,
          onAction:
              failure.isRetryable
                  ? () => ref.invalidate(
                    liveMatchViewerQualifiedRouteProvider(resolvedMatchKey),
                  )
                  : null,
        );
      },
    );
  }
}

class _MatchViewerRouteFailure {
  const _MatchViewerRouteFailure({
    required this.title,
    required this.subtitle,
    required this.reason,
    required this.detail,
    required this.actionLabel,
    required this.isRetryable,
  });

  final String title;
  final String subtitle;
  final String reason;
  final String detail;
  final String actionLabel;
  final bool isRetryable;

  factory _MatchViewerRouteFailure.from(Object error) {
    if (error is GteApiException) {
      switch (error.type) {
        case GteApiErrorType.notFound:
          return const _MatchViewerRouteFailure(
            title: 'No match available',
            subtitle: 'There is no live match or official replay available.',
            reason:
                'This match does not have a playable live session or saved replay yet.',
            detail:
                'When official match coverage is available, it will appear in Match Center.',
            actionLabel: 'Open Match Center',
            isRetryable: false,
          );
        case GteApiErrorType.unauthorized:
          return const _MatchViewerRouteFailure(
            title: 'Match access restricted',
            subtitle: 'You do not have access to this match viewer.',
            reason:
                'Sign in with an account that can access this match, then try again.',
            detail: 'Match access follows the competition and broadcast rules.',
            actionLabel: 'Open Match Center',
            isRetryable: false,
          );
        case GteApiErrorType.parsing:
          return const _MatchViewerRouteFailure(
            title: 'Match data unavailable',
            subtitle:
                'This match cannot be shown because its official data is incomplete.',
            reason:
                'GTEX will not display an incomplete or unverified match timeline.',
            detail: 'Check Match Center later for official match coverage.',
            actionLabel: 'Open Match Center',
            isRetryable: false,
          );
        case GteApiErrorType.network:
        case GteApiErrorType.unavailable:
        case GteApiErrorType.validation:
        case GteApiErrorType.unknown:
          break;
      }
    }
    return const _MatchViewerRouteFailure(
      title: 'Match viewer unavailable',
      subtitle: 'We could not load this match right now.',
      reason:
          'The match service did not respond in time or is temporarily unavailable.',
      detail: 'No match data has been shown. You can safely try again.',
      actionLabel: 'Try again',
      isRetryable: true,
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
    required this.giftClient,
  });

  final String matchKey;
  final LiveMatchViewerBootstrap bootstrap;
  final MatchViewState initialViewState;
  final LiveMatchViewerRepository repository;
  final MatchGiftClient? giftClient;

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
      giftClient: widget.giftClient,
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
