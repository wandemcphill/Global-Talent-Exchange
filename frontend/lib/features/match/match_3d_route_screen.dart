import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/app_feedback.dart';
import '../../models/match_view_state.dart';
import '../../screens/match/gtex_match_3d_screen.dart';
import '../../services/match_3d_monetization_service.dart';
import '../../shared/models/auth_session.dart';
import '../../shared/models/data_source_status.dart';
import '../../shared/providers/auth_provider.dart';
import 'live_match_viewer_route_support.dart';
import 'match_viewer_capability.dart';

class Match3dRouteScreen extends ConsumerWidget {
  const Match3dRouteScreen({super.key, required this.matchKey});

  final String matchKey;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final String resolvedMatchKey = matchKey.trim();
    final AuthSession? session = ref.watch(authProvider);
    final Match3dUserEntitlement baseEntitlement = ref.watch(
      match3dEntitlementProvider,
    );
    final Match3dUserEntitlement entitlement = _routeEntitlement(
      session,
      baseEntitlement,
    );
    if (resolvedMatchKey.isEmpty) {
      return const MatchRouteBlockedScreen(
        title: '3D Match Viewer',
        subtitle:
            'This Flutter 3D lane opens only when the selected match can be verified from the routed live session.',
        reason:
            'The 3D lane could not open because this match route was missing its live match reference.',
        detailTitle: 'Match unavailable',
        detailSubtitle:
            'The route stays closed when the selected live match cannot be identified.',
      );
    }
    if (!(session?.isAuthenticated ?? false)) {
      return MatchRouteBlockedScreen(
        title: '3D Match Viewer',
        subtitle:
            'This Flutter 3D lane opens for signed-in sessions after the live match reference is verified.',
        reason: 'Sign in to open the live 3D viewer.',
        detailTitle: 'Sign in required',
        detailSubtitle:
            'Guest sessions stay blocked; signed-in sessions can enter the mounted Flutter 3D lane.',
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
          capability: MatchViewerCapability.flutter3d,
          child: _QualifiedMatch3dRouteView(
            key: ValueKey<String>('match-3d-route-$resolvedMatchKey'),
            matchKey: resolvedMatchKey,
            bootstrap: value.bootstrap,
            initialViewState: value.initialViewState,
            entitlement: entitlement,
            repository: repository,
          ),
        );
      },
      loading:
          () => const MatchRouteLoadingScreen(
            title: '3D Match Viewer',
            subtitle:
                'Verifying the live match-viewer session and your Flutter 3D access before opening the tactical lane.',
            capability: MatchViewerCapability.flutter3d,
          ),
      error:
          (Object error, StackTrace stackTrace) => MatchRouteCapabilityOverlay(
            capability: MatchViewerCapability.flutter3d,
            status: DataSourceStatus.demo,
            child: _FallbackMatch3dRouteView(
              matchKey: resolvedMatchKey,
              reason: AppFeedback.messageFor(
                error,
                fallback:
                    'The live Flutter 3D lane is unavailable for this match right now.',
              ),
              entitlement: entitlement,
            ),
          ),
    );
  }
}

Match3dUserEntitlement _routeEntitlement(
  AuthSession? session,
  Match3dUserEntitlement entitlement,
) {
  if (!(session?.isAuthenticated ?? false)) {
    return entitlement;
  }
  return entitlement.copyWith(
    isPremiumUser: true,
    premiumCameraAccess: true,
    fastReplayAccess: true,
  );
}

class _QualifiedMatch3dRouteView extends StatefulWidget {
  const _QualifiedMatch3dRouteView({
    super.key,
    required this.matchKey,
    required this.bootstrap,
    required this.initialViewState,
    required this.entitlement,
    required this.repository,
  });

  final String matchKey;
  final LiveMatchViewerBootstrap bootstrap;
  final MatchViewState initialViewState;
  final Match3dUserEntitlement entitlement;
  final LiveMatchViewerRepository repository;

  @override
  State<_QualifiedMatch3dRouteView> createState() =>
      _QualifiedMatch3dRouteViewState();
}

class _QualifiedMatch3dRouteViewState
    extends State<_QualifiedMatch3dRouteView> {
  bool _usedQualifiedInitialState = false;

  @override
  void didUpdateWidget(covariant _QualifiedMatch3dRouteView oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.matchKey != widget.matchKey ||
        !identical(oldWidget.initialViewState, widget.initialViewState)) {
      _usedQualifiedInitialState = false;
    }
  }

  @override
  Widget build(BuildContext context) {
    return GtexMatch3dScreen(
      key: ValueKey<String>('gtex-match-3d-${widget.matchKey}'),
      competition: widget.bootstrap.competition,
      matchKey: widget.matchKey,
      entitlement: widget.entitlement,
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

class _FallbackMatch3dRouteView extends StatelessWidget {
  const _FallbackMatch3dRouteView({
    required this.matchKey,
    required this.reason,
    required this.entitlement,
  });

  final String matchKey;
  final String reason;
  final Match3dUserEntitlement entitlement;

  @override
  Widget build(BuildContext context) {
    return GtexMatch3dScreen(
      competition: buildLiveViewerCompetition(matchKey, <String, Object?>{
        'title': '3D Match Viewer',
        'fallback_reason': reason,
      }),
      matchKey: matchKey,
      entitlement: entitlement,
      preferFallback: true,
    );
  }
}
