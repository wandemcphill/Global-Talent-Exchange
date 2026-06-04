import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../shared/providers/auth_provider.dart';
import 'live_match_viewer_route_support.dart';
import 'match_viewer_capability.dart';
import 'presentation/gte_live_match_center_screen.dart';

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
            'Pick a backend-routed match to open the live 2D viewer.',
      );
    }

    final AsyncValue<LiveMatchViewerQualifiedRoute> qualifiedRoute = ref.watch(
      liveMatchViewerQualifiedRouteProvider(resolvedMatchKey),
    );

    return qualifiedRoute.when(
      data: (LiveMatchViewerQualifiedRoute value) {
        final spectateSession = value.bootstrap.spectateSession;
        return MatchRouteCapabilityOverlay(
          capability: MatchViewerCapability.twoD,
          child: GteLiveMatchCenterScreen(
            key: ValueKey<String>('match-viewer-route-$resolvedMatchKey'),
            competition: value.bootstrap.competition,
            matchId: resolvedMatchKey,
            isAuthenticated: ref.watch(isAuthenticatedProvider),
            snapshotLoader:
                (competition, {matchId}) async =>
                    liveMatchSnapshotFromQualifiedViewState(
                      value.initialViewState,
                    ),
            sessionResolver:
                spectateSession == null
                    ? null
                    : (String matchId) async {
                      return matchId.trim() == spectateSession.matchId.trim()
                          ? spectateSession
                          : null;
                    },
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
          (Object _, StackTrace __) => const MatchRouteBlockedScreen(
            title: '2D Match Viewer',
            subtitle:
                'The 2D route opens only after the live match-viewer contract confirms the requested match.',
            reason:
                'The live match-viewer contract could not qualify this match key. Match state remains blocked until backend truth is available.',
            detailTitle: 'Live route unavailable',
          ),
    );
  }
}
