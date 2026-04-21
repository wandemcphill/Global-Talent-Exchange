import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/app_feedback.dart';
import '../../data/match_gift_api.dart';
import '../../shared/providers/auth_provider.dart';
import 'live_match_viewer_route_support.dart';
import 'match_viewer_capability.dart';
import 'presentation/broadcast_package_screen.dart';

class MatchBroadcastScreen extends ConsumerWidget {
  const MatchBroadcastScreen({super.key, required this.matchKey});

  final String matchKey;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AsyncValue<LiveMatchViewerBootstrap> bootstrap = ref.watch(
      liveMatchViewerBootstrapProvider(matchKey),
    );
    return bootstrap.when(
      data: (LiveMatchViewerBootstrap value) {
        final LiveMatchViewerRepository repository = ref.read(
          liveMatchViewerRepositoryProvider,
        );
        final MatchGiftClient? giftClient =
            ref.watch(isAuthenticatedProvider)
                ? MatchGiftApi(client: ref.watch(authedApiProvider))
                : null;
        return MatchRouteCapabilityOverlay(
          capability: MatchViewerCapability.pseudo3d,
          child: BroadcastPackageScreen(
            matchKey: matchKey,
            competition: value.competition,
            initialViewState: value.initialViewState,
            viewStateLoader: () => repository.loadViewState(matchKey),
            giftClient: giftClient,
          ),
        );
      },
      loading:
          () => const MatchRouteLoadingScreen(
            title: 'Broadcast Package',
            subtitle:
                'Verifying the live match-viewer session before opening the match-day broadcast package.',
            capability: MatchViewerCapability.pseudo3d,
          ),
      error:
          (Object error, StackTrace stackTrace) => MatchRouteBlockedScreen(
            title: 'Broadcast Package',
            subtitle:
                'The active shell will only open the broadcast package when the live match-viewer backend responds.',
            reason: AppFeedback.messageFor(error),
          ),
    );
  }
}
