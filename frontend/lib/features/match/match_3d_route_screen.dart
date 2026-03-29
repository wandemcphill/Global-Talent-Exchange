import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/app_feedback.dart';
import '../../screens/match/gtex_match_3d_screen.dart';
import '../../services/match_3d_bridge.dart';
import '../../services/match_3d_monetization_service.dart';
import 'live_match_viewer_route_support.dart';
import 'match_viewer_capability.dart';

final Provider<Match3DBridge> match3dBridgeProvider = Provider<Match3DBridge>(
  (Ref ref) => Match3DBridge(),
);

final match3dNativeAvailabilityProvider =
    FutureProvider.autoDispose<bool>((Ref ref) {
      return ref.watch(match3dBridgeProvider).isNativeAvailable();
    });

class Match3dRouteScreen extends ConsumerWidget {
  const Match3dRouteScreen({super.key, required this.matchKey});

  final String matchKey;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AsyncValue<LiveMatchViewerBootstrap> bootstrap = ref.watch(
      liveMatchViewerBootstrapProvider(matchKey),
    );
    final AsyncValue<bool> nativeAvailable = ref.watch(
      match3dNativeAvailabilityProvider,
    );

    return bootstrap.when(
      data: (LiveMatchViewerBootstrap value) {
        return nativeAvailable.when(
          data: (bool available) {
            final LiveMatchViewerRepository repository = ref.read(
              liveMatchViewerRepositoryProvider,
            );
            final Match3DBridge bridge = ref.read(match3dBridgeProvider);
            final MatchViewerCapability capability =
                available
                    ? MatchViewerCapability.native3d
                    : MatchViewerCapability.flutter3d;
            return MatchRouteCapabilityOverlay(
              capability: capability,
              child: GtexMatch3dScreen(
                competition: value.competition,
                matchKey: matchKey,
                entitlement: const Match3dUserEntitlement(),
                engineBridge: available ? bridge : null,
                viewStateLoader: () => repository.loadViewState(matchKey),
                continuationLoader: ({
                  required String matchKey,
                  required String continuationToken,
                }) {
                  return repository.loadViewState(
                    matchKey,
                    continuationToken: continuationToken,
                  );
                },
              ),
            );
          },
          loading:
              () => const MatchRouteLoadingScreen(
                title: '3D Match Viewer',
                subtitle:
                    'Verifying the live session and native bridge state before opening the shipped 3D surface.',
                capability: MatchViewerCapability.flutter3d,
              ),
          error:
              (Object error, StackTrace stackTrace) => MatchRouteBlockedScreen(
                title: '3D Match Viewer',
                subtitle:
                    'The active shell could not verify whether the native 3D bridge is available.',
                reason: 'native 3D bridge unavailable',
              ),
        );
      },
      loading:
          () => const MatchRouteLoadingScreen(
            title: '3D Match Viewer',
            subtitle:
                'Verifying the live match-viewer session before opening the shipped 3D surface.',
            capability: MatchViewerCapability.flutter3d,
          ),
      error:
          (Object error, StackTrace stackTrace) => MatchRouteBlockedScreen(
            title: '3D Match Viewer',
            subtitle:
                'The active shell will only open this viewer when the live match-viewer backend responds.',
            reason: AppFeedback.messageFor(error),
          ),
    );
  }
}
