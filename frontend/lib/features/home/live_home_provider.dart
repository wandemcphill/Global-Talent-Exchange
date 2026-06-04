import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../compete/providers/live_competitions_provider.dart';
import '../profile/live_profile_provider.dart';
import '../tasks/live_tasks_provider.dart';
import '../transfer_market/live_market_provider.dart';
import '../world/live_world_provider.dart';

class HomeSummaryData {
  const HomeSummaryData({
    required this.market,
    required this.competitions,
    required this.world,
    required this.profile,
    required this.tasks,
  });

  final MarketDashboardData market;
  final CompetitionHubData competitions;
  final WorldAggregateData world;
  final ProfileData profile;
  final LiveTasksData tasks;
}

final FutureProvider<HomeSummaryData> homeSummaryProvider =
    FutureProvider<HomeSummaryData>((Ref ref) async {
      final List<Object> payload = await Future.wait<Object>(<Future<Object>>[
        ref.watch(marketDashboardProvider.future),
        ref.watch(competitionHubProvider.future),
        ref.watch(worldAggregateProvider.future),
        ref.watch(profileDataProvider.future),
        ref.watch(liveTasksProvider.future),
      ]);
      return HomeSummaryData(
        market: payload[0] as MarketDashboardData,
        competitions: payload[1] as CompetitionHubData,
        world: payload[2] as WorldAggregateData,
        profile: payload[3] as ProfileData,
        tasks: payload[4] as LiveTasksData,
      );
    });
