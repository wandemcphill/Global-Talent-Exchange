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
                _QuickRouteButton(
                  surface: appRouteSurfaceFor(AppRoutes.matches)!,
                  onPressed: () => context.go(AppRoutes.matches),
                ),
                _QuickRouteButton(
                  surface: appRouteSurfaceFor(AppRoutes.market)!,
                  onPressed: () => context.go(AppRoutes.market),
                ),
                _QuickRouteButton(
                  surface: appRouteSurfaceFor(AppRoutes.competitions)!,
                  onPressed: () => context.push(AppRoutes.competitions),
                ),
                _QuickRouteButton(
                  surface: appRouteSurfaceFor(AppRoutes.streamerEngine)!,
                  onPressed: () => context.push(AppRoutes.streamerEngine),
                ),
                _QuickRouteButton(
                  surface: appRouteSurfaceFor(AppRoutes.world)!,
                  onPressed: () => context.go(AppRoutes.world),
                ),
                _QuickRouteButton(
                  surface: appRouteSurfaceFor(AppRoutes.tasks)!,
                  onPressed: () => context.push(AppRoutes.tasks),
                ),
                _QuickRouteButton(
                  surface: appRouteSurfaceFor(AppRoutes.clips)!,
                  onPressed: () => context.push(AppRoutes.clips),
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
        Card(
          child: Padding(
            padding: const EdgeInsets.all(spacingLG),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  'Wave 1 modules',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: spacingXS),
                const Text(
                  'Federations, national teams, and transfer center now have explicit entry points instead of staying buried behind summary cards.',
                ),
                const SizedBox(height: spacingMD),
                Wrap(
                  spacing: spacingSM,
                  runSpacing: spacingSM,
                  children: <Widget>[
                    _QuickRouteButton(
                      surface: appRouteSurfaceFor(AppRoutes.federations)!,
                      onPressed: () => context.push(AppRoutes.federations),
                    ),
                    _QuickRouteButton(
                      surface: appRouteSurfaceFor(AppRoutes.nationalTeams)!,
                      onPressed: () => context.push(AppRoutes.nationalTeams),
                    ),
                    _QuickRouteButton(
                      surface: appRouteSurfaceFor(AppRoutes.transferCenter)!,
                      onPressed: () => context.push(AppRoutes.transferCenter),
                    ),
                  ],
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

class _QuickRouteButton extends StatelessWidget {
  const _QuickRouteButton({required this.surface, required this.onPressed});

  final AppRouteSurface surface;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    final String label = switch (surface.state) {
      AppRouteSurfaceState.partiallyWired =>
        '${surface.label} ${surface.state.disclosureLabel}',
      AppRouteSurfaceState.placeholder =>
        '${surface.label} ${surface.state.disclosureLabel}',
      _ => surface.label,
    };

    return switch (surface.state) {
      AppRouteSurfaceState.live => FilledButton(
        onPressed: onPressed,
        child: Text(label),
      ),
      AppRouteSurfaceState.partiallyWired => OutlinedButton(
        onPressed: onPressed,
        child: Text(label),
      ),
      AppRouteSurfaceState.placeholder => OutlinedButton(
        onPressed: null,
        child: Text(label),
      ),
      AppRouteSurfaceState.hidden => const SizedBox.shrink(),
    };
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
