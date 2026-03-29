import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/app_feedback.dart';
import '../../models/match_viewer_presentation.dart';
import '../../screens/match/gtex_match_viewer_screen.dart';
import '../../services/match_3d_monetization_service.dart';
import 'live_match_viewer_route_support.dart';
import 'match_viewer_capability.dart';

class MatchViewerRouteScreen extends ConsumerWidget {
  const MatchViewerRouteScreen({super.key, required this.matchKey});

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
        return MatchRouteCapabilityOverlay(
          capability: MatchViewerCapability.twoD,
          child: GtexMatchViewerScreen(
            competition: value.competition,
            matchKey: matchKey,
            presentationMode: MatchViewerPresentationMode.broadcast,
            renderMode: RenderMode.twoD,
            isSpectator: true,
            isMajorMatch: true,
            titleOverride: '2D Match Viewer',
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
            title: '2D Match Viewer',
            subtitle:
                'Verifying the live match-viewer session before opening the shipped 2D surface.',
            capability: MatchViewerCapability.twoD,
          ),
      error:
          (Object error, StackTrace stackTrace) => MatchRouteBlockedScreen(
            title: '2D Match Viewer',
            subtitle:
                'The active shell will only open this viewer when the live match-viewer backend responds.',
            reason: AppFeedback.messageFor(error),
          ),
    );
  }
}
