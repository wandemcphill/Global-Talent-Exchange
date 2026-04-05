import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/gte_app_config.dart';
import '../../core/app_feedback.dart';
import '../../features/competitions/live_competitions_provider.dart';
import '../../features/profile/live_profile_provider.dart';
import '../../features/tasks/live_tasks_provider.dart';
import '../../features/transfer_market/live_market_provider.dart';
import '../../features/world/live_world_provider.dart';
import '../../data/gte_api_repository.dart';
import '../../navigation/app_destinations.dart';
import '../../shared/models/data_source_status.dart';
import '../../shared/providers/auth_provider.dart';
import '../../shared/widgets/app_page_layout.dart';
import '../../shared/widgets/data_source_badge.dart';
import '../../shared/widgets/gtex_premium_panels.dart';
import '../../widgets/gte_shell_theme.dart';
import '../../widgets/gte_state_panel.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final GteAppConfig appConfig = GteAppConfig.fromEnvironment();
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

    final ProfileData? profile = profileValue.asData?.value;
    final CompetitionHubData? competitions = competitionsValue.asData?.value;
    final MarketDashboardData? market = marketValue.asData?.value;
    final LiveTasksData? tasks = tasksValue.asData?.value;
    final String runtimeHost = _runtimeHostLabel(appConfig.apiBaseUrl);
    final String runtimeMode = _runtimeModeLabel(appConfig.backendMode);

    return AppPageLayout(
      title: 'Home',
      subtitle:
          'A clear football home for your session, scouting, world discovery, competitions, and live challenges.',
      trailing: DataSourceBadge(
        status: blocked ? DataSourceStatus.blocked : DataSourceStatus.live,
      ),
      children: <Widget>[
        GtexHeroPanel(
          eyebrow: authenticated ? 'LIVE HOME' : 'GUEST HOME',
          title:
              authenticated
                  ? 'Everything important in your football world, one step away.'
                  : 'See the live football world before you sign in.',
          description:
              'Home brings together your session, scouting, world, competitions, and live challenges without burying the next best move.',
          metrics: <Widget>[
            GtexStatTile(
              label: 'Session',
              value:
                  authenticated
                      ? profile == null
                          ? 'Loading'
                          : 'Authenticated'
                      : 'Guest',
              support:
                  profile == null
                      ? 'Live auth state syncing'
                      : '${profile.followers} followers',
              tone:
                  authenticated
                      ? GtexSurfaceTone.live
                      : GtexSurfaceTone.warning,
            ),
            GtexStatTile(
              label: 'Competitions',
              value:
                  competitions == null
                      ? '...'
                      : '${competitions.gtexCompetitions.length + competitions.hostedCompetitions.length + competitions.streamerTournaments.length}',
              support: 'Platform, hosted, and creator families',
              tone: GtexSurfaceTone.info,
            ),
            GtexStatTile(
              label: 'Scouting',
              value:
                  market == null
                      ? '...'
                      : '${market.playerShares.length} shares / ${market.transferListings.length} listings',
              support:
                  market?.wallet == null
                      ? 'Funds not loaded yet'
                      : 'Funds ${market!.wallet!.totalEquity.toStringAsFixed(0)}',
              tone: GtexSurfaceTone.success,
            ),
            GtexStatTile(
              label: 'Seasonal Tasks',
              value: tasks == null ? '...' : '${tasks.currentStreak} streak',
              support:
                  tasks == null
                      ? 'Engagement loop syncing'
                      : '${tasks.challenges.length} live challenges',
              tone: GtexSurfaceTone.warning,
            ),
          ],
          actions: <Widget>[
            _RouteLaunchButton(
              surface: appRouteSurfaceFor(AppRoutes.matches)!,
              icon: Icons.sports_soccer_rounded,
              onPressed: () => context.go(AppRoutes.matches),
            ),
            _RouteLaunchButton(
              surface: appRouteSurfaceFor(AppRoutes.market)!,
              icon: Icons.candlestick_chart_rounded,
              onPressed: () => context.go(AppRoutes.market),
            ),
            _RouteLaunchButton(
              surface: appRouteSurfaceFor(AppRoutes.competitions)!,
              icon: Icons.emoji_events_rounded,
              onPressed: () => context.push(AppRoutes.competitions),
            ),
            _RouteLaunchButton(
              surface: appRouteSurfaceFor(AppRoutes.world)!,
              icon: Icons.public_rounded,
              onPressed: () => context.go(AppRoutes.world),
            ),
            _RouteLaunchButton(
              surface: appRouteSurfaceFor(AppRoutes.tasks)!,
              icon: Icons.flag_rounded,
              onPressed: () => context.push(AppRoutes.tasks),
            ),
            _RouteLaunchButton(
              surface: appRouteSurfaceFor(AppRoutes.clips)!,
              icon: Icons.play_circle_fill_rounded,
              onPressed: () => context.push(AppRoutes.clips),
            ),
            if (!authenticated)
              FilledButton.icon(
                onPressed: () => context.push(AppRoutes.profileLogin),
                icon: const Icon(Icons.login_rounded),
                label: const Text('Sign in'),
              ),
          ],
        ),
        GtexSectionPanel(
          eyebrow: 'DEPLOYMENT SIGNAL',
          title: 'This web shell is wired to the runtime you deployed',
          subtitle:
              'This panel reflects the active web build configuration instead of hidden fixture text.',
          accentColor: GteShellTheme.accentCapital,
          emphasized: true,
          child: Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              GtexStatTile(
                label: 'Runtime',
                value: runtimeMode,
                support: 'Derived from GTE_BACKEND_MODE',
                tone: GtexSurfaceTone.live,
              ),
              GtexStatTile(
                label: 'API Host',
                value: runtimeHost,
                support: 'Derived from GTE_API_BASE_URL',
                tone: GtexSurfaceTone.info,
              ),
              GtexStatTile(
                label: 'Access',
                value: authenticated ? 'Signed in' : 'Guest',
                support:
                    authenticated
                        ? 'Live session controls unlocked'
                        : 'Guest safeguards still active',
                tone:
                    authenticated
                        ? GtexSurfaceTone.success
                        : GtexSurfaceTone.warning,
              ),
              GtexStatTile(
                label: 'Routes',
                value: '${appDestinations.length} primary lanes',
                support: 'Home, Matches, Scouting, World, and Profile',
                tone: GtexSurfaceTone.warning,
              ),
            ],
          ),
        ),
        GtexSectionPanel(
          eyebrow: 'LIVE ROUTES',
          title: 'Core football routes are mounted in the active shell',
          subtitle:
              'Federations, national teams, and the transfer center live as first-class routes instead of being buried in summaries.',
          child: Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              _RouteLaunchButton(
                surface: appRouteSurfaceFor(AppRoutes.federations)!,
                icon: Icons.account_tree_rounded,
                onPressed: () => context.push(AppRoutes.federations),
              ),
              _RouteLaunchButton(
                surface: appRouteSurfaceFor(AppRoutes.nationalTeams)!,
                icon: Icons.flag_circle_rounded,
                onPressed: () => context.push(AppRoutes.nationalTeams),
              ),
              _RouteLaunchButton(
                surface: appRouteSurfaceFor(AppRoutes.transferCenter)!,
                icon: Icons.swap_horiz_rounded,
                onPressed: () => context.push(AppRoutes.transferCenter),
              ),
            ],
          ),
        ),
        _AsyncSummaryPanel<ProfileData>(
          value: profileValue,
          title: 'Session',
          subtitle:
              'Identity, follower signal, and club context stay live-backed.',
          builder: (BuildContext context, ProfileData data) {
            final String label =
                data.authenticated
                    ? data.user['display_name']?.toString() ??
                        data.user['username']?.toString() ??
                        data.user['email']?.toString() ??
                        'Authenticated user'
                    : 'Guest session';
            return Wrap(
              spacing: 12,
              runSpacing: 12,
              children: <Widget>[
                GtexPill(
                  label: label,
                  icon: Icons.person_rounded,
                  tone:
                      data.authenticated
                          ? GtexSurfaceTone.live
                          : GtexSurfaceTone.warning,
                ),
                GtexPill(
                  label: 'Followers ${data.followers}',
                  tone: GtexSurfaceTone.info,
                ),
                GtexPill(
                  label: 'Following ${data.following}',
                  tone: GtexSurfaceTone.info,
                ),
                if (data.club != null)
                  GtexPill(
                    label: 'Club ${data.club!['name'] ?? data.club!['id']}',
                    tone: GtexSurfaceTone.success,
                  ),
              ],
            );
          },
        ),
        _AsyncSummaryPanel<CompetitionHubData>(
          value: competitionsValue,
          title: 'Competition Pulse',
          subtitle: 'Three live competition families, one hierarchy.',
          builder: (BuildContext context, CompetitionHubData data) {
            return Wrap(
              spacing: 12,
              runSpacing: 12,
              children: <Widget>[
                GtexStatTile(
                  label: 'GTEX',
                  value: '${data.gtexCompetitions.length}',
                  support: 'Platform-run football',
                  tone: GtexSurfaceTone.live,
                ),
                GtexStatTile(
                  label: 'Hosted',
                  value: '${data.hostedCompetitions.length}',
                  support: 'User-hosted football',
                  tone: GtexSurfaceTone.info,
                ),
                GtexStatTile(
                  label: 'Creator',
                  value: '${data.streamerTournaments.length}',
                  support: 'Streamer tournaments',
                  tone: GtexSurfaceTone.warning,
                ),
              ],
            );
          },
        ),
        _AsyncSummaryPanel<MarketDashboardData>(
          value: marketValue,
          title: 'Scouting Pulse',
          subtitle: 'A live read on players, transfers, and account readiness.',
          builder: (BuildContext context, MarketDashboardData data) {
            return Wrap(
              spacing: 12,
              runSpacing: 12,
              children: <Widget>[
                GtexStatTile(
                  label: 'Shares',
                  value: '${data.playerShares.length}',
                  support: 'Real-player discovery',
                  tone: GtexSurfaceTone.live,
                ),
                GtexStatTile(
                  label: 'Listings',
                  value: '${data.transferListings.length}',
                  support: 'Transfer listings',
                  tone: GtexSurfaceTone.info,
                ),
                GtexStatTile(
                  label: 'Holdings',
                  value: '${data.holdings.length}',
                  support: 'Tracked player positions',
                  tone: GtexSurfaceTone.success,
                ),
                GtexStatTile(
                  label: 'Funds',
                  value:
                      data.wallet == null
                          ? (authenticated ? 'Refreshing' : 'Login required')
                          : data.wallet!.totalEquity.toStringAsFixed(0),
                  support:
                      data.wallet == null
                          ? (authenticated
                              ? 'Session bootstrap is syncing funds access'
                              : 'Sign in to load funds access')
                          : data.wallet!.complianceMessage,
                  tone:
                      data.wallet == null
                          ? GtexSurfaceTone.warning
                          : GtexSurfaceTone.success,
                ),
              ],
            );
          },
        ),
        _AsyncSummaryPanel<WorldAggregateData>(
          value: worldValue,
          title: 'World Pulse',
          subtitle: 'Living football-universe signals and history.',
          builder: (BuildContext context, WorldAggregateData data) {
            return Wrap(
              spacing: 12,
              runSpacing: 12,
              children: <Widget>[
                GtexStatTile(
                  label: 'Rising stars',
                  value: '${data.risingStars.length}',
                  support: 'Live regen universe',
                  tone: GtexSurfaceTone.live,
                ),
                GtexStatTile(
                  label: 'Scouting',
                  value: '${data.scoutingFeed.length}',
                  support: 'Fresh scouting items',
                  tone: GtexSurfaceTone.info,
                ),
                GtexStatTile(
                  label: 'Seasons',
                  value: '${data.seasons.length}',
                  support: 'History and awards',
                  tone: GtexSurfaceTone.warning,
                ),
                GtexStatTile(
                  label: 'Federations',
                  value: '${data.federations.length}',
                  support: 'Mounted live hubs',
                  tone: GtexSurfaceTone.success,
                ),
              ],
            );
          },
        ),
        _AsyncSummaryPanel<LiveTasksData>(
          value: tasksValue,
          title: 'Task Pulse',
          subtitle:
              'Seasonal engagement stays game-like without faking rewards.',
          builder: (BuildContext context, LiveTasksData data) {
            return Wrap(
              spacing: 12,
              runSpacing: 12,
              children: <Widget>[
                GtexStatTile(
                  label: 'Challenges',
                  value: '${data.challenges.length}',
                  support: 'Live daily challenge pool',
                  tone: GtexSurfaceTone.live,
                ),
                GtexStatTile(
                  label: 'Claims today',
                  value: '${data.claimsToday.length}',
                  support: 'Reward claim events',
                  tone: GtexSurfaceTone.info,
                ),
                GtexStatTile(
                  label: 'Current streak',
                  value: '${data.currentStreak}',
                  support: 'Daily engagement momentum',
                  tone: GtexSurfaceTone.warning,
                ),
                GtexStatTile(
                  label: 'Longest streak',
                  value: '${data.longestStreak}',
                  support:
                      'Next bonus ${data.nextBonusAmount.toStringAsFixed(0)}',
                  tone: GtexSurfaceTone.success,
                ),
              ],
            );
          },
        ),
      ],
    );
  }
}

String _runtimeHostLabel(String apiBaseUrl) {
  final Uri? uri = Uri.tryParse(apiBaseUrl.trim());
  final String? host = uri?.host.trim();
  if (host != null && host.isNotEmpty) {
    return host;
  }
  final String raw = apiBaseUrl.trim();
  if (raw.isEmpty) {
    return 'not configured';
  }
  return raw.replaceFirst(RegExp(r'^https?://'), '');
}

String _runtimeModeLabel(GteBackendMode backendMode) {
  switch (backendMode) {
    case GteBackendMode.live:
      return 'Live';
    case GteBackendMode.fixture:
      return 'Fixture';
    case GteBackendMode.liveThenFixture:
      return 'Hybrid';
  }
}

class _RouteLaunchButton extends StatelessWidget {
  const _RouteLaunchButton({
    required this.surface,
    required this.icon,
    required this.onPressed,
  });

  final AppRouteSurface surface;
  final IconData icon;
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
      AppRouteSurfaceState.live => FilledButton.icon(
        onPressed: onPressed,
        icon: Icon(icon),
        label: Text(label),
      ),
      AppRouteSurfaceState.partiallyWired => OutlinedButton.icon(
        onPressed: onPressed,
        icon: Icon(icon),
        label: Text(label),
      ),
      AppRouteSurfaceState.placeholder => OutlinedButton.icon(
        onPressed: null,
        icon: Icon(icon),
        label: Text(label),
      ),
      AppRouteSurfaceState.hidden => const SizedBox.shrink(),
    };
  }
}

class _AsyncSummaryPanel<T> extends StatelessWidget {
  const _AsyncSummaryPanel({
    required this.value,
    required this.title,
    required this.subtitle,
    required this.builder,
  });

  final AsyncValue<T> value;
  final String title;
  final String subtitle;
  final Widget Function(BuildContext context, T data) builder;

  @override
  Widget build(BuildContext context) {
    return GtexSectionPanel(
      eyebrow: 'LIVE MODULE',
      title: title,
      subtitle: subtitle,
      child: value.when(
        data: (T data) => builder(context, data),
        loading:
            () => GteStatePanel(
              title: 'Loading $title',
              message: 'The active shell is syncing live $title data.',
              isLoading: true,
              accentColor: GtexSurfaceTone.info.color(context),
            ),
        error:
            (Object error, StackTrace stackTrace) => GteStatePanel(
              title: '$title blocked',
              message: AppFeedback.messageFor(error),
              icon: Icons.error_outline_rounded,
              accentColor: GtexSurfaceTone.danger.color(context),
            ),
      ),
    );
  }
}

extension on GtexSurfaceTone {
  Color color(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    switch (this) {
      case GtexSurfaceTone.neutral:
        return Theme.of(context).disabledColor;
      case GtexSurfaceTone.live:
        return Theme.of(context).colorScheme.primary;
      case GtexSurfaceTone.info:
        return Theme.of(context).colorScheme.secondary;
      case GtexSurfaceTone.success:
        return tokens.positive;
      case GtexSurfaceTone.warning:
        return tokens.warning;
      case GtexSurfaceTone.danger:
        return Theme.of(context).colorScheme.error;
    }
  }
}
