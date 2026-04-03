import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/app_feedback.dart';
import '../../models/match_view_state.dart';
import '../../screens/match/gtex_match_3d_screen.dart';
import '../../services/match_3d_monetization_service.dart';
import '../../shared/models/auth_session.dart';
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
    final Match3dUserEntitlement entitlement = ref.watch(
      match3dEntitlementProvider,
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
    if (!_hasQualified3dEntitlement(session, entitlement)) {
      final bool isAuthenticated = session?.isAuthenticated ?? false;
      return MatchRouteBlockedScreen(
        title: '3D Match Viewer',
        subtitle:
            'This Flutter 3D lane opens for signed-in production sessions after the live match reference is verified.',
        reason:
            isAuthenticated
                ? 'This signed-in account does not include Flutter 3D access for live match routes.'
                : 'Sign in to open the live 3D viewer.',
        detailTitle:
            isAuthenticated
                ? '3D access unavailable'
                : 'Sign in required',
        detailSubtitle:
            'The route stays closed instead of falling back to a believable non-3D viewer.',
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
          (Object error, StackTrace stackTrace) => MatchRouteBlockedScreen(
            title: '3D Match Viewer',
            subtitle:
                'This Flutter 3D lane opens only when the selected match exposes a verified live viewer session.',
            reason: AppFeedback.messageFor(
              error,
              fallback:
                  'The live Flutter 3D lane is unavailable for this match right now.',
            ),
            detailTitle: 'Live session unavailable',
            detailSubtitle:
                'The route stays closed until the selected match can provide a verified live session.',
          ),
    );
  }
}

bool _hasQualified3dEntitlement(
  AuthSession? session,
  Match3dUserEntitlement entitlement,
) {
  return (session?.isAuthenticated ?? false) &&
      (entitlement.isPremiumUser ||
          entitlement.premiumCameraAccess ||
          entitlement.fastReplayAccess);
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
