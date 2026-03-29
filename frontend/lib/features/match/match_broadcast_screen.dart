import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/app_feedback.dart';
import '../../models/match/gtex_match_render_mode.dart';
import '../../models/match/gtex_match_view_type.dart';
import '../../screens/match/gtex_match_broadcast_screen.dart';
import 'live_match_viewer_route_support.dart';
import 'match_viewer_capability.dart';

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
        return MatchRouteCapabilityOverlay(
          capability: MatchViewerCapability.pseudo3d,
          child: GtexMatchBroadcastScreen(
            matchId: matchKey,
            competition: value.competition,
            competitionId: value.competition.id,
            initialMode: GtexMatchRenderMode.standard,
            viewType: GtexMatchViewType.pseudo3D,
            isPremiumUser: false,
            spectatorMode: true,
            auto3DEnabled: false,
            titleOverride: 'Broadcast+ Viewer',
            competitionLabel: value.competition.name,
            viewStateLoader: () => repository.loadViewState(matchKey),
          ),
        );
      },
      loading:
          () => const MatchRouteLoadingScreen(
            title: 'Broadcast+ Viewer',
            subtitle:
                'Verifying the live match-viewer session before opening the shipped pseudo-3D broadcast surface.',
            capability: MatchViewerCapability.pseudo3d,
          ),
      error:
          (Object error, StackTrace stackTrace) => MatchRouteBlockedScreen(
            title: 'Broadcast+ Viewer',
            subtitle:
                'The active shell will only open Broadcast+ when the live match-viewer backend responds.',
            reason: AppFeedback.messageFor(error),
          ),
    );
  }
}
