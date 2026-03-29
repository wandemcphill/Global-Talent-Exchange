import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/app_feedback.dart';
import '../../core/constants/app_spacing.dart';
import '../../features/competitions/live_competitions_provider.dart';
import '../../features/profile/live_profile_provider.dart';
import '../../features/tasks/live_tasks_provider.dart';
import '../../features/transfer_market/live_market_provider.dart';
import '../../features/world/live_world_provider.dart';
import '../../navigation/app_destinations.dart';
import '../../shared/models/data_source_status.dart';
import '../../shared/providers/auth_provider.dart';
import '../../shared/widgets/app_page_layout.dart';
import '../../shared/widgets/data_source_badge.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AsyncValue<ProfileData> profileValue = ref.watch(profileDataProvider);
    final AsyncValue<CompetitionHubData> competitionsValue = ref.watch(
      competitionHubProvider,
    );
    final AsyncValue<MarketDashboardData> marketValue = ref.watch(
      marketDashboardProvider,
    );
    final AsyncValue<WorldAggregateData> worldValue = ref.watch(
      worldAggregateProvider,
    );
    final AsyncValue<LiveTasksData> tasksValue = ref.watch(liveTasksProvider);
    final bool authenticated = ref.watch(isAuthenticatedProvider);
    final bool blocked = <AsyncValue<Object?>>[
      profileValue,
      competitionsValue,
      marketValue,
      worldValue,
      tasksValue,
    ].any((AsyncValue<Object?> item) => item.hasError);

    return AppPageLayout(
      title: 'Home',
      subtitle:
          'The home surface now summarizes the live session, world, competitions, market, and daily challenge state instead of synthetic club and match cards.',
      trailing: DataSourceBadge(
        status: blocked ? DataSourceStatus.blocked : DataSourceStatus.live,
      ),
      children: <Widget>[
        Card(
          child: Padding(
            padding: const EdgeInsets.all(spacingLG),
            child: Wrap(
              spacing: spacingSM,
              runSpacing: spacingSM,
              children: <Widget>[
                FilledButton(
                  onPressed: () => context.go(AppRoutes.matches),
                  child: const Text('Matches'),
                ),
                FilledButton(
                  onPressed: () => context.go(AppRoutes.market),
                  child: const Text('Market'),
                ),
                FilledButton(
                  onPressed: () => context.push(AppRoutes.competitions),
                  child: const Text('Competitions'),
                ),
                FilledButton(
                  onPressed: () => context.push(AppRoutes.streamerEngine),
                  child: const Text('Streamer Engine'),
                ),
                FilledButton(
                  onPressed: () => context.go(AppRoutes.world),
                  child: const Text('World'),
                ),
                FilledButton(
                  onPressed: () => context.push(AppRoutes.tasks),
                  child: const Text('Tasks'),
                ),
                FilledButton(
                  onPressed: () => context.push(AppRoutes.clips),
                  child: const Text('Clips'),
                ),
                if (!authenticated)
                  OutlinedButton(
                    onPressed: () => context.push(AppRoutes.profileLogin),
                    child: const Text('Sign in'),
                  ),
              ],
            ),
          ),
        ),
        const SizedBox(height: spacingMD),
        _AsyncSummaryCard<ProfileData>(
          value: profileValue,
          title: 'Session',
          builder: (ProfileData data) {
            final String label =
                data.authenticated
                    ? data.user['display_name']?.toString() ??
                        data.user['username']?.toString() ??
                        data.user['email']?.toString() ??
                        'Authenticated user'
                    : 'Guest session';
            return _chipWrap(<String>[
              label,
              'Followers ${data.followers}',
              'Following ${data.following}',
              if (data.club != null)
                'Club ${data.club!['name'] ?? data.club!['id']}',
            ]);
          },
        ),
        const SizedBox(height: spacingMD),
        _AsyncSummaryCard<CompetitionHubData>(
          value: competitionsValue,
          title: 'Competition Pulse',
          builder:
              (CompetitionHubData data) => _chipWrap(<String>[
                'GTEX ${data.gtexCompetitions.length}',
                'Hosted ${data.hostedCompetitions.length}',
                'Creator ${data.streamerTournaments.length}',
              ]),
        ),
        const SizedBox(height: spacingMD),
        _AsyncSummaryCard<MarketDashboardData>(
          value: marketValue,
          title: 'Market Pulse',
          builder:
              (MarketDashboardData data) => _chipWrap(<String>[
                'Players ${data.playerShares.length}',
                'Listings ${data.transferListings.length}',
                'Holdings ${data.holdings.length}',
                if (data.wallet != null)
                  'Wallet ${data.wallet!.totalEquity.toStringAsFixed(2)}',
              ]),
        ),
        const SizedBox(height: spacingMD),
        _AsyncSummaryCard<WorldAggregateData>(
          value: worldValue,
          title: 'World Pulse',
          builder:
              (WorldAggregateData data) => _chipWrap(<String>[
                'Rising stars ${data.risingStars.length}',
                'Scouting feed ${data.scoutingFeed.length}',
                'Seasons ${data.seasons.length}',
                'Federations ${data.federations.length}',
              ]),
        ),
        const SizedBox(height: spacingMD),
        _AsyncSummaryCard<LiveTasksData>(
          value: tasksValue,
          title: 'Task Pulse',
          builder:
              (LiveTasksData data) => _chipWrap(<String>[
                'Challenges ${data.challenges.length}',
                'Claims today ${data.claimsToday.length}',
                'Current streak ${data.currentStreak}',
                'Longest streak ${data.longestStreak}',
              ]),
        ),
      ],
    );
  }

  Widget _chipWrap(List<String> labels) {
    return Wrap(
      spacing: spacingSM,
      runSpacing: spacingSM,
      children: labels.map((String item) => Chip(label: Text(item))).toList(),
    );
  }
}

class _AsyncSummaryCard<T> extends StatelessWidget {
  const _AsyncSummaryCard({
    required this.value,
    required this.title,
    required this.builder,
  });

  final AsyncValue<T> value;
  final String title;
  final Widget Function(T data) builder;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(spacingLG),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(title, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: spacingSM),
            value.when(
              data: builder,
              loading: () => const CircularProgressIndicator(),
              error:
                  (Object error, StackTrace stackTrace) =>
                      Text(AppFeedback.messageFor(error)),
            ),
          ],
        ),
      ),
    );
  }
}
