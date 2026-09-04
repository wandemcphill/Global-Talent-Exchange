import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/gte_app_config.dart';
import '../../core/app_feedback.dart';
import '../../data/gte_api_repository.dart';
import '../../features/competitions/live_competitions_provider.dart';
import '../../features/navigation/routing/gte_navigation_route.dart';
import '../../features/player_detail/gtex_player_navigator.dart';
import '../../features/profile/live_profile_provider.dart';
import '../../features/shared/data/gte_feature_support.dart';
import '../../features/tasks/live_tasks_provider.dart';
import '../../features/transfer_market/live_market_provider.dart';
import '../../features/world/live_world_provider.dart';
import '../../navigation/app_destinations.dart';
import '../../shared/models/data_source_status.dart';
import '../../shared/providers/auth_provider.dart';
import '../../shared/widgets/app_page_layout.dart';
import '../../shared/widgets/data_source_badge.dart';
import '../../ui_gtex/ui_gtex.dart';
import '../../widgets/gte_formatters.dart';
import '../../widgets/gte_state_panel.dart';
import 'data/gtex_home_digest_provider.dart';
import 'models/gtex_home_digest_models.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final GteAppConfig appConfig = ref.watch(appConfigProvider);
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
    final AsyncValue<GtexHomeDigest> digestValue = ref.watch(
      homeDigestProvider,
    );
    final bool authenticated = ref.watch(isAuthenticatedProvider);
    final bool blocked = <AsyncValue<Object?>>[
      profileValue,
      competitionsValue,
      marketValue,
      worldValue,
      tasksValue,
    ].any((AsyncValue<Object?> item) => item.hasError);

    final ProfileData? profile = profileValue.asData?.value;
    final MarketDashboardData? market = marketValue.asData?.value;
    final CompetitionHubData? competitions = competitionsValue.asData?.value;
    final LiveTasksData? tasks = tasksValue.asData?.value;
    final String managerName = _managerName(profile, authenticated);
    final _HomePersona persona = _resolvePersona(profile, authenticated);
    final _PersonaCopy personaCopy = _copyForPersona(
      persona,
      managerName: managerName,
      club: profile?.club,
    );

    return AppPageLayout(
      title: personaCopy.title,
      subtitle: personaCopy.subtitle,
      trailing: DataSourceBadge(
        status: blocked ? DataSourceStatus.blocked : DataSourceStatus.live,
      ),
      children: <Widget>[
        _TransferTicker(
          marketValue: marketValue,
          competitionsValue: competitionsValue,
          worldValue: worldValue,
        ),
        _HomeHero(
          authenticated: authenticated,
          managerName: managerName,
          runtimeHost: _runtimeHostLabel(appConfig.apiBaseUrl),
          runtimeMode: _runtimeModeLabel(appConfig.backendMode),
          profile: profile,
          market: market,
          competitions: competitions,
          tasks: tasks,
          personaCopy: personaCopy,
          onSignIn: () => context.push(AppRoutes.profileLogin),
        ),
        const SizedBox(height: 16),
        _RoleBriefPanel(personaCopy: personaCopy),
        if (authenticated) ...<Widget>[
          const SizedBox(height: 16),
          _HomeWorldTodayBanner(digestValue: digestValue),
        ],
        LayoutBuilder(
          builder: (BuildContext context, BoxConstraints constraints) {
            final bool desktop = constraints.maxWidth >= 1040;
            final Widget worldPulse = _LiveModule<WorldAggregateData>(
              value: worldValue,
              title: 'LIVE WORLD SIGNALS',
              subtitle:
                  'Most recent real world, regen, and federation signals.',
              accent: _GtexCommandColors.accentPrimary,
              builder:
                  (BuildContext context, WorldAggregateData data) =>
                      _WorldPulsePanel(world: data),
              authenticated: authenticated,
              onSignIn: () => context.push(AppRoutes.profileLogin),
            );
            final Widget centerStack = Column(
              children: <Widget>[
                if (authenticated) ...<Widget>[
                  _HomeYourPlayersPanel(digestValue: digestValue),
                  const SizedBox(height: 16),
                  _HomeWhatMovedPanel(digestValue: digestValue),
                  const SizedBox(height: 16),
                  _HomeYourClubsPanel(digestValue: digestValue),
                  const SizedBox(height: 16),
                  _HomeYourProspectsPanel(digestValue: digestValue),
                  const SizedBox(height: 16),
                  _HomeAttentionPanel(
                    digestValue: digestValue,
                    onOpen: (String location) => context.push(location),
                    onGo: (String location) => context.go(location),
                  ),
                  const SizedBox(height: 16),
                ],
                _ClubReadinessPanel(
                  profile: profile,
                  authenticated: authenticated,
                  onCreateClub:
                      () => context.push(const GteNavigationRoute.club().path),
                ),
                const SizedBox(height: 16),
                _LiveModule<CompetitionHubData>(
                  value: competitionsValue,
                  title: 'LIVE COMPETITIONS',
                  subtitle: 'Official, hosted, and creator football lanes.',
                  accent: _GtexCommandColors.accentBlue,
                  builder:
                      (BuildContext context, CompetitionHubData data) =>
                          _CompetitionPanel(data: data),
                  authenticated: authenticated,
                  onSignIn: () => context.push(AppRoutes.profileLogin),
                ),
                const SizedBox(height: 16),
                _LiveModule<MarketDashboardData>(
                  value: marketValue,
                  title: 'MARKET MOVERS',
                  subtitle: 'Transfer listings and tradable player shares.',
                  accent: _GtexCommandColors.accentAmber,
                  builder:
                      (BuildContext context, MarketDashboardData data) =>
                          _MarketPanel(data: data),
                  authenticated: authenticated,
                  onSignIn: () => context.push(AppRoutes.profileLogin),
                ),
                const SizedBox(height: 16),
                _QuickActionsPanel(
                  persona: persona,
                  onOpen: (String location) => context.push(location),
                  onGo: (String location) => context.go(location),
                ),
              ],
            );
            final Widget rightStack = Column(
              children: <Widget>[
                _WalletPanel(
                  marketValue: marketValue,
                  authenticated: authenticated,
                  onSignIn: () => context.push(AppRoutes.profileLogin),
                ),
                const SizedBox(height: 16),
                _RankingPanel(
                  worldValue: worldValue,
                  authenticated: authenticated,
                  onSignIn: () => context.push(AppRoutes.profileLogin),
                ),
                const SizedBox(height: 16),
                _TaskPanel(
                  tasksValue: tasksValue,
                  authenticated: authenticated,
                  onSignIn: () => context.push(AppRoutes.profileLogin),
                ),
                if (authenticated) ...<Widget>[
                  const SizedBox(height: 16),
                  _HomeRecentActivityPanel(digestValue: digestValue),
                ],
              ],
            );

            if (!desktop) {
              return Column(
                children: <Widget>[
                  worldPulse,
                  const SizedBox(height: 16),
                  centerStack,
                  const SizedBox(height: 16),
                  rightStack,
                ],
              );
            }
            return Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                SizedBox(width: 336, child: worldPulse),
                const SizedBox(width: 16),
                Expanded(flex: 5, child: centerStack),
                const SizedBox(width: 16),
                Expanded(flex: 3, child: rightStack),
              ],
            );
          },
        ),
      ],
    );
  }
}

enum _HomePersona { guest, noClub, clubOwner, creator, coinTrader, admin }

class _PersonaCopy {
  const _PersonaCopy({
    required this.title,
    required this.subtitle,
    required this.badge,
    required this.headline,
    required this.body,
    required this.primaryAction,
    required this.capabilities,
    required this.accent,
  });

  final String title;
  final String subtitle;
  final String badge;
  final String headline;
  final String body;
  final String primaryAction;
  final List<String> capabilities;
  final Color accent;
}

class _GtexCommandColors {
  static const Color surfaceBase = Color(0xFF0A0C0F);
  static const Color surfaceRaised = Color(0xFF111418);
  static const Color surfaceOverlay = Color(0xFF181C22);
  static const Color surfaceInput = Color(0xFF1C2128);
  static const Color surfaceBorder = Color(0xFF252D38);
  static const Color surfaceBorderStrong = Color(0xFF2E3A48);
  static const Color textPrimary = Color(0xFFE8EDF4);
  static const Color textSecondary = Color(0xFF8A97A8);
  static const Color textTertiary = Color(0xFF4D5D6E);
  static const Color accentPrimary = Color(0xFF00E87A);
  static const Color accentAmber = Color(0xFFFFB800);
  static const Color accentRed = Color(0xFFFF3D3D);
  static const Color accentBlue = Color(0xFF2F80ED);
  static const Color accentViolet = Color(0xFF9B5FFF);
}

TextStyle _labelStyle(BuildContext context, {Color? color}) {
  return Theme.of(context).textTheme.labelSmall?.copyWith(
        fontFamily: 'BarlowCondensed',
        fontWeight: FontWeight.w700,
        letterSpacing: 0,
        color: color ?? _GtexCommandColors.textSecondary,
      ) ??
      TextStyle(
        fontFamily: 'BarlowCondensed',
        fontWeight: FontWeight.w700,
        color: color ?? _GtexCommandColors.textSecondary,
      );
}

TextStyle _bodyStyle(BuildContext context, {Color? color}) {
  return Theme.of(context).textTheme.bodyMedium?.copyWith(
        fontFamily: 'Inter',
        fontWeight: FontWeight.w500,
        color: color ?? _GtexCommandColors.textSecondary,
      ) ??
      TextStyle(
        fontFamily: 'Inter',
        fontWeight: FontWeight.w500,
        color: color ?? _GtexCommandColors.textSecondary,
      );
}

TextStyle _dataStyle(
  BuildContext context, {
  Color? color,
  double? size,
  FontWeight weight = FontWeight.w600,
}) {
  return Theme.of(context).textTheme.titleMedium?.copyWith(
        fontFamily: 'DMMono',
        fontWeight: weight,
        fontSize: size,
        letterSpacing: 0,
        color: color ?? _GtexCommandColors.textPrimary,
      ) ??
      TextStyle(
        fontFamily: 'DMMono',
        fontWeight: weight,
        fontSize: size,
        color: color ?? _GtexCommandColors.textPrimary,
      );
}

class _CommandPanel extends StatelessWidget {
  const _CommandPanel({
    required this.title,
    required this.subtitle,
    required this.child,
    this.accent = _GtexCommandColors.accentPrimary,
    this.trailing,
  });

  final String title;
  final String subtitle;
  final Widget child;
  final Color accent;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: _GtexCommandColors.surfaceRaised,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: _GtexCommandColors.surfaceBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Container(height: 3, color: accent),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(
                            title.toUpperCase(),
                            style: _labelStyle(context, color: accent),
                          ),
                          const SizedBox(height: 6),
                          Text(subtitle, style: _bodyStyle(context)),
                        ],
                      ),
                    ),
                    if (trailing != null) ...<Widget>[
                      const SizedBox(width: 12),
                      trailing!,
                    ],
                  ],
                ),
                const SizedBox(height: 14),
                Container(height: 1, color: _GtexCommandColors.surfaceBorder),
                const SizedBox(height: 14),
                child,
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _TransferTicker extends StatelessWidget {
  const _TransferTicker({
    required this.marketValue,
    required this.competitionsValue,
    required this.worldValue,
  });

  final AsyncValue<MarketDashboardData> marketValue;
  final AsyncValue<CompetitionHubData> competitionsValue;
  final AsyncValue<WorldAggregateData> worldValue;

  @override
  Widget build(BuildContext context) {
    final bool loading =
        marketValue.isLoading ||
        competitionsValue.isLoading ||
        worldValue.isLoading;
    final bool error =
        marketValue.hasError ||
        competitionsValue.hasError ||
        worldValue.hasError;
    final List<_TickerEntry> entries = <_TickerEntry>[
      ...?marketValue.asData?.value.transferListings
          .take(4)
          .map(
            (TransferListingSummary item) => _TickerEntry(
              chip: 'LISTED',
              text:
                  '${item.playerName} · ${item.currentClubName ?? 'Open market'}',
              metric: _formatGtc(
                item.currentHighestBid > item.basePrice
                    ? item.currentHighestBid
                    : item.basePrice,
              ),
              tone: _GtexCommandColors.accentBlue,
            ),
          ),
      ...?competitionsValue.asData?.value.gtexCompetitions
          .take(2)
          .map(
            (item) => _TickerEntry(
              chip: 'COMP',
              text: '${item.name} · ${item.participantCount}/${item.capacity}',
              metric: item.status.name.toUpperCase(),
              tone: _GtexCommandColors.accentPrimary,
            ),
          ),
      ...?worldValue.asData?.value.risingStars
          .take(2)
          .map(
            (JsonMap item) => _TickerEntry(
              chip: 'REGEN',
              text: stringValue(
                item['player_name'],
                fallback: stringValue(item['name'], fallback: 'Unnamed player'),
              ),
              metric: stringValue(
                item['position'],
                fallback: stringValue(item['nationality'], fallback: 'LIVE'),
              ),
              tone: _GtexCommandColors.accentViolet,
            ),
          ),
    ];
    return Container(
      height: 40,
      padding: const EdgeInsets.symmetric(horizontal: 12),
      decoration: BoxDecoration(
        color: _GtexCommandColors.surfaceRaised,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: _GtexCommandColors.surfaceBorder),
      ),
      child: Row(
        children: <Widget>[
          if (error)
            const Icon(
              Icons.lock_outline,
              size: 16,
              color: _GtexCommandColors.accentAmber,
            )
          else if (loading)
            const SizedBox(
              width: 14,
              height: 14,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          else
            const _LiveDot(),
          const SizedBox(width: 10),
          Text(
            error
                ? 'OFFLINE'
                : loading
                ? 'LOADING'
                : 'TRANSFER TICKER',
            style: _labelStyle(
              context,
              color:
                  error
                      ? _GtexCommandColors.accentAmber
                      : _GtexCommandColors.accentPrimary,
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child:
                error
                    ? Text(
                      'Live economy modules could not be loaded.',
                      overflow: TextOverflow.ellipsis,
                      style: _bodyStyle(context),
                    )
                    : loading
                    ? Text(
                      'Syncing market, competition, and world signals.',
                      overflow: TextOverflow.ellipsis,
                      style: _bodyStyle(context),
                    )
                    : entries.isEmpty
                    ? Text(
                      'No live ticker events returned.',
                      overflow: TextOverflow.ellipsis,
                      style: _bodyStyle(context),
                    )
                    : SingleChildScrollView(
                      scrollDirection: Axis.horizontal,
                      child: Row(
                        children: entries
                            .map(
                              (_TickerEntry item) => Padding(
                                padding: const EdgeInsets.only(right: 18),
                                child: _TickerChip(entry: item),
                              ),
                            )
                            .toList(growable: false),
                      ),
                    ),
          ),
        ],
      ),
    );
  }
}

class _TickerEntry {
  const _TickerEntry({
    required this.chip,
    required this.text,
    required this.metric,
    required this.tone,
  });

  final String chip;
  final String text;
  final String metric;
  final Color tone;
}

class _TickerChip extends StatelessWidget {
  const _TickerChip({required this.entry});

  final _TickerEntry entry;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
          decoration: BoxDecoration(
            color: entry.tone.withValues(alpha: 0.14),
            borderRadius: BorderRadius.circular(4),
            border: Border.all(color: entry.tone.withValues(alpha: 0.42)),
          ),
          child: Text(
            entry.chip,
            style: _labelStyle(context, color: entry.tone),
          ),
        ),
        const SizedBox(width: 8),
        Text(
          entry.text,
          style: _bodyStyle(context, color: _GtexCommandColors.textPrimary),
        ),
        const SizedBox(width: 8),
        Text(entry.metric, style: _dataStyle(context, size: 12)),
      ],
    );
  }
}

class _HomeHero extends StatelessWidget {
  const _HomeHero({
    required this.authenticated,
    required this.managerName,
    required this.runtimeHost,
    required this.runtimeMode,
    required this.profile,
    required this.market,
    required this.competitions,
    required this.tasks,
    required this.personaCopy,
    required this.onSignIn,
  });

  final bool authenticated;
  final String managerName;
  final String runtimeHost;
  final String runtimeMode;
  final ProfileData? profile;
  final MarketDashboardData? market;
  final CompetitionHubData? competitions;
  final LiveTasksData? tasks;
  final _PersonaCopy personaCopy;
  final VoidCallback onSignIn;

  @override
  Widget build(BuildContext context) {
    return _CommandPanel(
      title: personaCopy.badge,
      subtitle:
          authenticated
              ? 'Good session, $managerName. ${personaCopy.subtitle}'
              : personaCopy.subtitle,
      trailing: _StatusBadge(
        label: runtimeMode.toUpperCase(),
        color: personaCopy.accent,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            personaCopy.headline,
            style: Theme.of(context).textTheme.displaySmall?.copyWith(
              fontFamily: 'BarlowCondensed',
              fontWeight: FontWeight.w800,
              letterSpacing: 0,
              color: _GtexCommandColors.textPrimary,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            personaCopy.body,
            style: _bodyStyle(context, color: _GtexCommandColors.textPrimary),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: <Widget>[
              _StatusBadge(
                label: 'WORLD PULSE RAIL',
                color: _GtexCommandColors.accentPrimary,
              ),
              _StatusBadge(
                label: 'Watch matchday',
                color: _GtexCommandColors.accentBlue,
              ),
              _StatusBadge(
                label: 'Read transfer hub',
                color: _GtexCommandColors.accentAmber,
              ),
              ...personaCopy.capabilities.map(
                (String capability) => _StatusBadge(
                  label: capability.toUpperCase(),
                  color: personaCopy.accent,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              _MetricCard(
                label: 'WALLET',
                value:
                    market == null
                        ? 'LOADING'
                        : market!.wallet == null
                        ? 'LOCKED'
                        : _formatGtc(market!.wallet!.totalEquity),
                support:
                    market?.wallet == null
                        ? 'Sign in or wait for wallet authority'
                        : market!.wallet!.complianceMessage,
                tone:
                    market?.wallet == null
                        ? _GtexCommandColors.accentAmber
                        : _GtexCommandColors.accentPrimary,
              ),
              _MetricCard(
                label: 'PLAYERS',
                value:
                    market == null
                        ? 'LOADING'
                        : '${market!.playerShares.length}',
                support: 'Market discovery universe',
                tone: _GtexCommandColors.accentBlue,
              ),
              _MetricCard(
                label: 'COMPETITIONS',
                value:
                    competitions == null
                        ? 'LOADING'
                        : '${competitions!.gtexCompetitions.length + competitions!.hostedCompetitions.length + competitions!.streamerTournaments.length}',
                support: 'Official, hosted, creator',
                tone: _GtexCommandColors.accentPrimary,
              ),
              _MetricCard(
                label: 'TASK STREAK',
                value: tasks == null ? 'LOADING' : '${tasks!.currentStreak}',
                support: 'Daily command rhythm',
                tone: _GtexCommandColors.accentAmber,
              ),
            ],
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: <Widget>[
              _StatusBadge(
                label: 'HOST $runtimeHost',
                color: _GtexCommandColors.textSecondary,
              ),
              _StatusBadge(
                label: authenticated ? 'SIGNED IN' : 'GUEST',
                color:
                    authenticated
                        ? _GtexCommandColors.accentPrimary
                        : _GtexCommandColors.accentAmber,
              ),
              if (profile?.club != null)
                _StatusBadge(
                  label:
                      'CLUB ${profile!.club!['name'] ?? profile!.club!['id']}',
                  color: _GtexCommandColors.accentPrimary,
                ),
              if (!authenticated)
                FilledButton.icon(
                  onPressed: onSignIn,
                  icon: const Icon(Icons.login_rounded),
                  label: const Text('Sign in'),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _RoleBriefPanel extends StatelessWidget {
  const _RoleBriefPanel({required this.personaCopy});

  final _PersonaCopy personaCopy;

  @override
  Widget build(BuildContext context) {
    return _CommandPanel(
      title: 'ROLE DESK',
      subtitle:
          'Home adapts to the live session role returned by backend authority.',
      accent: personaCopy.accent,
      trailing: _StatusBadge(
        label: personaCopy.badge,
        color: personaCopy.accent,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            personaCopy.primaryAction,
            style: _bodyStyle(context, color: _GtexCommandColors.textPrimary),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: personaCopy.capabilities
                .map(
                  (String capability) => _StatusBadge(
                    label: 'FOCUS ${capability.toUpperCase()}',
                    color: personaCopy.accent,
                  ),
                )
                .toList(growable: false),
          ),
        ],
      ),
    );
  }
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({
    required this.label,
    required this.value,
    required this.support,
    required this.tone,
  });

  final String label;
  final String value;
  final String support;
  final Color tone;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 210,
      constraints: const BoxConstraints(minHeight: 112),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: _GtexCommandColors.surfaceOverlay,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: tone.withValues(alpha: 0.34)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(label, style: _labelStyle(context, color: tone)),
          const SizedBox(height: 10),
          Text(value, style: _dataStyle(context, size: 20)),
          const SizedBox(height: 8),
          Text(support, style: _bodyStyle(context)),
        ],
      ),
    );
  }
}

/// Shared empty/error renderer for the home panels.
///
/// Guests see an inviting "sign in to unlock" teaser (the feature is gated, not
/// broken); signed-in members hitting a genuine failure see a soft, retryable
/// notice — never an alarming red "blocked" wall.
Widget _memberGateOrError({
  required bool authenticated,
  required VoidCallback? onSignIn,
  required String feature,
  required String invite,
  required Color accent,
  required Object error,
}) {
  if (!authenticated) {
    return GteStatePanel(
      eyebrow: 'MEMBERS',
      title: 'Sign in to unlock $feature',
      message: invite,
      icon: Icons.lock_open_rounded,
      accentColor: accent,
      actionLabel: onSignIn == null ? null : 'Sign in',
      onAction: onSignIn,
    );
  }
  return GteStatePanel(
    title: "We couldn't load $feature",
    message: AppFeedback.messageFor(error),
    icon: Icons.refresh_rounded,
    accentColor: _GtexCommandColors.accentAmber,
  );
}

class _LiveModule<T> extends StatelessWidget {
  const _LiveModule({
    required this.value,
    required this.title,
    required this.subtitle,
    required this.accent,
    required this.builder,
    required this.authenticated,
    this.onSignIn,
  });

  final AsyncValue<T> value;
  final String title;
  final String subtitle;
  final Color accent;
  final Widget Function(BuildContext context, T data) builder;
  final bool authenticated;
  final VoidCallback? onSignIn;

  @override
  Widget build(BuildContext context) {
    final _StatusBadge errorBadge =
        authenticated
            ? const _StatusBadge(
              label: 'OFFLINE',
              color: _GtexCommandColors.accentAmber,
            )
            : _StatusBadge(label: 'MEMBERS', color: accent);
    return _CommandPanel(
      title: title,
      subtitle: subtitle,
      accent: value.hasError && authenticated
          ? _GtexCommandColors.accentAmber
          : accent,
      trailing:
          value.hasError
              ? errorBadge
              : value.isLoading
              ? const _StatusBadge(
                label: 'LOADING',
                color: _GtexCommandColors.accentBlue,
              )
              : const _StatusBadge(
                label: 'LIVE',
                color: _GtexCommandColors.accentPrimary,
              ),
      child: value.when(
        data: (T data) => builder(context, data),
        loading:
            () => GteStatePanel(
              title: 'Loading $title',
              message: 'Just a moment…',
              isLoading: true,
              accentColor: _GtexCommandColors.accentBlue,
            ),
        error:
            (Object error, StackTrace stackTrace) => _memberGateOrError(
              authenticated: authenticated,
              onSignIn: onSignIn,
              feature: title.toLowerCase(),
              invite: subtitle,
              accent: accent,
              error: error,
            ),
      ),
    );
  }
}

class _WorldPulsePanel extends StatelessWidget {
  const _WorldPulsePanel({required this.world});

  final WorldAggregateData world;

  @override
  Widget build(BuildContext context) {
    final List<_PulseLine> lines = <_PulseLine>[
      ...world.risingStars
          .take(4)
          .map(
            (JsonMap item) => _PulseLine(
              label: stringValue(
                item['player_name'],
                fallback: stringValue(item['name'], fallback: 'Unnamed player'),
              ),
              detail: stringValue(
                item['position'],
                fallback: stringValue(
                  item['nationality'],
                  fallback: 'Regen signal',
                ),
              ),
              metric: 'REGEN',
              color: _GtexCommandColors.accentViolet,
            ),
          ),
      ...world.scoutingFeed
          .take(3)
          .map(
            (JsonMap item) => _PulseLine(
              label: stringValue(
                item['headline'],
                fallback: stringValue(
                  item['player_name'],
                  fallback: 'Scouting note',
                ),
              ),
              detail: item.entries
                  .take(2)
                  .map(
                    (MapEntry<String, Object?> entry) =>
                        '${entry.key}: ${entry.value}',
                  )
                  .join(' · '),
              metric: 'SCOUT',
              color: _GtexCommandColors.accentBlue,
            ),
          ),
      ...world.federations
          .take(3)
          .map(
            (JsonMap item) => _PulseLine(
              label: stringValue(
                item['name'],
                fallback: stringValue(item['id'], fallback: 'Federation'),
              ),
              detail: world.federationJoinReason,
              metric: 'FED',
              color: _GtexCommandColors.accentPrimary,
            ),
          ),
    ];
    if (lines.isEmpty) {
      return Text(
        'No live world pulse events returned.',
        style: _bodyStyle(context),
      );
    }
    return Column(
      children: lines
          .map((_PulseLine line) => _PulseRow(line: line))
          .toList(growable: false),
    );
  }
}

class _MarketPanel extends StatelessWidget {
  const _MarketPanel({required this.data});

  final MarketDashboardData data;

  @override
  Widget build(BuildContext context) {
    final List<_PulseLine> lines = <_PulseLine>[
      ...data.transferListings
          .take(5)
          .map(
            (TransferListingSummary item) => _PulseLine(
              label: item.playerName,
              detail:
                  '${item.bidCount} bids · ${item.watchlistCount} watchlists · ${item.status}',
              metric: _formatGtc(
                item.currentHighestBid > item.basePrice
                    ? item.currentHighestBid
                    : item.basePrice,
              ),
              color: _GtexCommandColors.accentBlue,
            ),
          ),
      ...data.tradablePlayerShares
          .take(4)
          .map(
            (PlayerShareSummary item) => _PulseLine(
              label: item.playerName,
              detail:
                  '${item.currentClubName ?? 'Club not returned'} · ${item.marketMessage}',
              metric:
                  item.sharePriceCoin == null
                      ? '${item.marketInterestScore ?? 0} HEAT'
                      : _formatGtc(item.sharePriceCoin!),
              color: _GtexCommandColors.accentAmber,
            ),
          ),
    ];
    if (lines.isEmpty) {
      return Text(
        'No market movers returned by the live feed.',
        style: _bodyStyle(context),
      );
    }
    return Column(
      children: lines
          .map((_PulseLine line) => _PulseRow(line: line))
          .toList(growable: false),
    );
  }
}

class _CompetitionPanel extends StatelessWidget {
  const _CompetitionPanel({required this.data});

  final CompetitionHubData data;

  @override
  Widget build(BuildContext context) {
    final List<_PulseLine> lines = <_PulseLine>[
      ...data.gtexCompetitions
          .take(3)
          .map(
            (item) => _PulseLine(
              label: item.name,
              detail:
                  '${item.participantCount}/${item.capacity} clubs · ${item.status.name}',
              metric: 'GTEX',
              color: _GtexCommandColors.accentPrimary,
            ),
          ),
      ...data.hostedCompetitions
          .take(2)
          .map(
            (item) => _PulseLine(
              label: item.title,
              detail: '${item.maxParticipants} slots · ${item.status}',
              metric: 'HOSTED',
              color: _GtexCommandColors.accentBlue,
            ),
          ),
      ...data.streamerTournaments
          .take(2)
          .map(
            (item) => _PulseLine(
              label: item.title,
              detail:
                  '${item.entries.length}/${item.maxParticipants} creator clubs · ${item.status}',
              metric: 'CREATOR',
              color: _GtexCommandColors.accentAmber,
            ),
          ),
    ];
    if (lines.isEmpty) {
      return Text('No live competitions returned.', style: _bodyStyle(context));
    }
    return Column(
      children: lines
          .map((_PulseLine line) => _PulseRow(line: line))
          .toList(growable: false),
    );
  }
}

class _PulseLine {
  const _PulseLine({
    required this.label,
    required this.detail,
    required this.metric,
    required this.color,
  });

  final String label;
  final String detail;
  final String metric;
  final Color color;
}

class _PulseRow extends StatelessWidget {
  const _PulseRow({required this.line});

  final _PulseLine line;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: _GtexCommandColors.surfaceOverlay,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: _GtexCommandColors.surfaceBorder),
      ),
      child: Row(
        children: <Widget>[
          Container(
            width: 3,
            height: 36,
            decoration: BoxDecoration(
              color: line.color,
              borderRadius: BorderRadius.circular(4),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  line.label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: _bodyStyle(
                    context,
                    color: _GtexCommandColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  line.detail,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: _bodyStyle(context),
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          Text(
            line.metric,
            style: _dataStyle(context, size: 12, color: line.color),
          ),
        ],
      ),
    );
  }
}

class _ClubReadinessPanel extends StatelessWidget {
  const _ClubReadinessPanel({
    required this.profile,
    required this.authenticated,
    required this.onCreateClub,
  });

  final ProfileData? profile;
  final bool authenticated;
  final VoidCallback onCreateClub;

  @override
  Widget build(BuildContext context) {
    final JsonMap? club = profile?.club;
    return _CommandPanel(
      title: 'CLUB READINESS',
      subtitle:
          club == null
              ? 'No club context is active for this session.'
              : 'Club context is mounted and ready for economy actions.',
      accent:
          club == null
              ? _GtexCommandColors.accentAmber
              : _GtexCommandColors.accentPrimary,
      child: Row(
        children: <Widget>[
          Icon(
            club == null ? Icons.lock_outline : Icons.shield_outlined,
            color:
                club == null
                    ? _GtexCommandColors.accentAmber
                    : _GtexCommandColors.accentPrimary,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              club == null
                  ? authenticated
                      ? 'Create or join a club to unlock club-backed readiness, tactics, and federation actions.'
                      : 'Sign in to create a club and unlock the owner command stack.'
                  : '${club['name'] ?? club['id']} is the active club context.',
              style: _bodyStyle(context, color: _GtexCommandColors.textPrimary),
            ),
          ),
          const SizedBox(width: 12),
          OutlinedButton(
            onPressed: onCreateClub,
            child: Text(club == null ? 'Create club' : 'Open club'),
          ),
        ],
      ),
    );
  }
}

class _WalletPanel extends StatelessWidget {
  const _WalletPanel({
    required this.marketValue,
    required this.authenticated,
    this.onSignIn,
  });

  final AsyncValue<MarketDashboardData> marketValue;
  final bool authenticated;
  final VoidCallback? onSignIn;

  @override
  Widget build(BuildContext context) {
    return _CommandPanel(
      title: 'WALLET SUMMARY',
      subtitle: 'GTC, FNC, and live trade permission stay visibly separate.',
      accent: _GtexCommandColors.accentPrimary,
      child: marketValue.when(
        data: (MarketDashboardData data) {
          final MarketWalletSnapshot? wallet = data.wallet;
          if (wallet == null) {
            return Text(
              data.authenticated
                  ? 'Wallet authority has not returned a balance yet.'
                  : 'Wallet balance is locked for guest sessions.',
              style: _bodyStyle(context),
            );
          }
          return Column(
            children: <Widget>[
              _MetricCard(
                label: 'GTC BALANCE',
                value: _formatGtc(wallet.coinBalance),
                support: 'GTEX Coin available for trading and signings',
                tone: _GtexCommandColors.accentAmber,
              ),
              const SizedBox(height: 10),
              _MetricCard(
                label: 'FNC BALANCE',
                value: _formatFanCoin(wallet.creditBalance),
                support: 'Fan Coin/community credit balance',
                tone: _GtexCommandColors.accentBlue,
              ),
              const SizedBox(height: 10),
              _MetricCard(
                label: 'GTC EQUITY',
                value: _formatGtc(wallet.totalEquity),
                support: wallet.complianceMessage,
                tone:
                    wallet.canTradeMarket
                        ? _GtexCommandColors.accentPrimary
                        : _GtexCommandColors.accentAmber,
              ),
            ],
          );
        },
        loading:
            () => GteStatePanel(
              title: 'Loading wallet',
              message: 'Wallet values are hidden until the live feed returns.',
              isLoading: true,
              accentColor: _GtexCommandColors.accentBlue,
            ),
        error:
            (Object error, StackTrace stackTrace) => _memberGateOrError(
              authenticated: authenticated,
              onSignIn: onSignIn,
              feature: 'your wallet',
              invite:
                  'See your GTC and Fan Coin balances, trades, and signings.',
              accent: _GtexCommandColors.accentPrimary,
              error: error,
            ),
      ),
    );
  }
}

class _RankingPanel extends StatelessWidget {
  const _RankingPanel({
    required this.worldValue,
    required this.authenticated,
    this.onSignIn,
  });

  final AsyncValue<WorldAggregateData> worldValue;
  final bool authenticated;
  final VoidCallback? onSignIn;

  @override
  Widget build(BuildContext context) {
    return _CommandPanel(
      title: 'RANKING MOVEMENT',
      subtitle: 'Hall of fame and rising profile movement from world data.',
      accent: _GtexCommandColors.accentViolet,
      child: worldValue.when(
        data: (WorldAggregateData data) {
          final List<JsonMap> rows = <JsonMap>[
            ...data.hallOfFame,
            ...data.risingStars,
          ].take(4).toList(growable: false);
          if (rows.isEmpty) {
            return Text(
              'No ranking movement returned.',
              style: _bodyStyle(context),
            );
          }
          return Column(
            children: rows
                .map(
                  (JsonMap item) => _PulseRow(
                    line: _PulseLine(
                      label: stringValue(
                        item['player_name'],
                        fallback: stringValue(
                          item['name'],
                          fallback: 'Tracked profile',
                        ),
                      ),
                      detail: stringValue(
                        item['legacy_tier'],
                        fallback: stringValue(
                          item['position'],
                          fallback: 'World ranking profile',
                        ),
                      ),
                      metric: stringValue(
                        item['rank_delta'],
                        fallback: stringValue(item['rank'], fallback: 'LIVE'),
                      ),
                      color: _GtexCommandColors.accentViolet,
                    ),
                  ),
                )
                .toList(growable: false),
          );
        },
        loading:
            () => GteStatePanel(
              title: 'Loading rankings',
              message: 'Waiting for live world ranking data.',
              isLoading: true,
              accentColor: _GtexCommandColors.accentBlue,
            ),
        error:
            (Object error, StackTrace stackTrace) => _memberGateOrError(
              authenticated: authenticated,
              onSignIn: onSignIn,
              feature: 'the leaderboard',
              invite:
                  'Track the hall of fame, rising stars, and club rankings.',
              accent: _GtexCommandColors.accentViolet,
              error: error,
            ),
      ),
    );
  }
}

class _TaskPanel extends StatelessWidget {
  const _TaskPanel({
    required this.tasksValue,
    required this.authenticated,
    this.onSignIn,
  });

  final AsyncValue<LiveTasksData> tasksValue;
  final bool authenticated;
  final VoidCallback? onSignIn;

  @override
  Widget build(BuildContext context) {
    return _CommandPanel(
      title: 'COMMAND RHYTHM',
      subtitle: 'Daily challenge and claim state from the active backend.',
      accent: _GtexCommandColors.accentAmber,
      child: tasksValue.when(
        data:
            (LiveTasksData data) => Wrap(
              spacing: 10,
              runSpacing: 10,
              children: <Widget>[
                _MetricCard(
                  label: 'CHALLENGES',
                  value: '${data.challenges.length}',
                  support: 'Live daily pool',
                  tone: _GtexCommandColors.accentAmber,
                ),
                _MetricCard(
                  label: 'CLAIMS TODAY',
                  value: '${data.claimsToday.length}',
                  support: 'Reward events',
                  tone: _GtexCommandColors.accentBlue,
                ),
              ],
            ),
        loading:
            () => GteStatePanel(
              title: 'Loading command rhythm',
              message: 'Waiting for live task state.',
              isLoading: true,
              accentColor: _GtexCommandColors.accentBlue,
            ),
        error:
            (Object error, StackTrace stackTrace) => _memberGateOrError(
              authenticated: authenticated,
              onSignIn: onSignIn,
              feature: 'daily challenges',
              invite: 'Play daily challenges and claim rewards every day.',
              accent: _GtexCommandColors.accentAmber,
              error: error,
            ),
      ),
    );
  }
}

class _QuickActionsPanel extends StatelessWidget {
  const _QuickActionsPanel({
    required this.persona,
    required this.onOpen,
    required this.onGo,
  });

  final _HomePersona persona;
  final ValueChanged<String> onOpen;
  final ValueChanged<String> onGo;

  @override
  Widget build(BuildContext context) {
    final List<_QuickActionSpec> actions = _actionsForPersona(persona);
    return _CommandPanel(
      title: 'ROLE ACTIONS',
      subtitle: 'Primary routes change with the active session role.',
      accent: _GtexCommandColors.accentBlue,
      child: Wrap(
        spacing: 10,
        runSpacing: 10,
        // A quick action whose destination is not published has no surface
        // to describe it, and asserting one into existence took the whole
        // panel down with a null-check error rather than costing a single
        // button. An unpublished destination is dropped instead; the route
        // inventory test is what keeps that from going unnoticed.
        children: actions
            .map((_QuickActionSpec action) {
              final AppRouteSurface? surface = appRouteSurfaceFor(
                action.location,
              );
              if (surface == null) {
                return null;
              }
              return _RouteLaunchButton(
                surface: surface,
                icon: action.icon,
                labelOverride: action.label,
                onPressed:
                    action.useGo
                        ? () => onGo(action.location)
                        : () => onOpen(action.location),
              );
            })
            .whereType<Widget>()
            .toList(growable: false),
      ),
    );
  }
}

class _QuickActionSpec {
  const _QuickActionSpec({
    required this.location,
    required this.label,
    required this.icon,
    this.useGo = false,
  });

  final String location;
  final String label;
  final IconData icon;
  final bool useGo;
}

class _RouteLaunchButton extends StatelessWidget {
  const _RouteLaunchButton({
    required this.surface,
    required this.icon,
    required this.onPressed,
    this.labelOverride,
  });

  final AppRouteSurface surface;
  final IconData icon;
  final VoidCallback onPressed;
  final String? labelOverride;

  @override
  Widget build(BuildContext context) {
    final String baseLabel = labelOverride ?? surface.label;
    final String label = switch (surface.state) {
      AppRouteSurfaceState.partiallyWired =>
        '$baseLabel ${surface.state.disclosureLabel}',
      AppRouteSurfaceState.placeholder =>
        '$baseLabel ${surface.state.disclosureLabel}',
      _ => baseLabel,
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
        onPressed: () {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                '${surface.label} is coming soon.',
              ),
            ),
          );
        },
        icon: Icon(icon),
        label: Text(label),
      ),
      AppRouteSurfaceState.hidden =>
        labelOverride == null
            ? const SizedBox.shrink()
            : OutlinedButton.icon(
              onPressed: onPressed,
              icon: Icon(icon),
              label: Text(label),
            ),
    };
  }
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: color.withValues(alpha: 0.38)),
      ),
      child: Text(label, style: _labelStyle(context, color: color)),
    );
  }
}

class _LiveDot extends StatelessWidget {
  const _LiveDot();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 8,
      height: 8,
      decoration: const BoxDecoration(
        color: _GtexCommandColors.accentPrimary,
        shape: BoxShape.circle,
      ),
    );
  }
}

_HomePersona _resolvePersona(ProfileData? profile, bool authenticated) {
  if (!authenticated) {
    return _HomePersona.guest;
  }
  final Set<String> signals = _identitySignals(profile);

  if (_hasIdentitySignal(signals, <String>['admin', 'super_admin'])) {
    return _HomePersona.admin;
  }
  if (_hasIdentitySignal(signals, <String>[
    'coin_trader',
    'coin-trader',
    'trader',
    'liquidity_partner',
  ])) {
    return _HomePersona.coinTrader;
  }
  if (_hasIdentitySignal(signals, <String>['creator', 'publisher'])) {
    return _HomePersona.creator;
  }
  if (profile?.club != null) {
    return _HomePersona.clubOwner;
  }
  return _HomePersona.noClub;
}

Set<String> _identitySignals(ProfileData? profile) {
  final JsonMap user = profile?.user ?? const <String, Object?>{};
  final JsonMap affinity =
      profile?.affinityProfile ?? const <String, Object?>{};
  return <String>{
    stringValue(user['role']).toLowerCase(),
    stringValue(user['account_type']).toLowerCase(),
    stringValue(user['accountType']).toLowerCase(),
    stringValue(user['profile_type']).toLowerCase(),
    stringValue(user['profileType']).toLowerCase(),
    stringValue(user['creator_profile_status']).toLowerCase(),
    stringValue(user['coin_trader_profile_status']).toLowerCase(),
    stringValue(affinity['role']).toLowerCase(),
    stringValue(affinity['account_type']).toLowerCase(),
    stringValue(affinity['creator_profile_status']).toLowerCase(),
    stringValue(affinity['coin_trader_profile_status']).toLowerCase(),
    ..._stringSet(user['roles']),
    ..._stringSet(user['permissions']),
    ..._stringSet(user['capabilities']),
    ..._stringSet(affinity['roles']),
    ..._stringSet(affinity['permissions']),
    ..._stringSet(affinity['capabilities']),
  }..removeWhere((String value) => value.trim().isEmpty);
}

bool _hasIdentitySignal(Set<String> signals, List<String> needles) {
  final Set<String> normalizedNeedles =
      needles.map(_normalizeIdentitySignal).toSet();
  return signals.any((String raw) {
    final String signal = _normalizeIdentitySignal(raw);
    return normalizedNeedles.any((String needle) => signal.contains(needle));
  });
}

String _normalizeIdentitySignal(String raw) {
  return raw.trim().toLowerCase().replaceAll('-', '_').replaceAll(' ', '_');
}

Set<String> _stringSet(Object? value) {
  if (value is Iterable) {
    return value
        .map((Object? item) => item?.toString().trim().toLowerCase() ?? '')
        .where((String item) => item.isNotEmpty)
        .toSet();
  }
  final String text = value?.toString().trim().toLowerCase() ?? '';
  if (text.isEmpty) {
    return const <String>{};
  }
  return text
      .split(RegExp(r'[,| ]+'))
      .where((String item) => item.isNotEmpty)
      .toSet();
}

_PersonaCopy _copyForPersona(
  _HomePersona persona, {
  required String managerName,
  required JsonMap? club,
}) {
  final String clubName = stringValue(
    club?['name'],
    fallback: stringValue(club?['id'], fallback: 'your club'),
  );
  switch (persona) {
    case _HomePersona.guest:
      return const _PersonaCopy(
        title: 'Welcome to GTEX',
        subtitle:
            'Browse live scores, clubs, players, and news for free. Sign in to sign players, play matches, trade, and run your own club.',
        badge: 'GUEST',
        headline: 'YOUR CLUB. YOUR PLAYERS. YOUR GAME.',
        body:
            'Take a look around. When you\'re ready, create a free account to start building your club.',
        primaryAction:
            'Create a free account to sign players, rent national squads, trade coins, gift reactions, and build your club.',
        capabilities: <String>[
          'Read clubs',
          'View markets',
          'Watch matches',
          'Read news',
        ],
        accent: _GtexCommandColors.accentAmber,
      );
    case _HomePersona.noClub:
      return _PersonaCopy(
        title: 'No-club user command desk',
        subtitle:
            'Your account is live. Build a wallet, search players, follow regens, read news, and choose a club path.',
        badge: 'USER DESK',
        headline: 'GET READY TO OWN A FOOTBALL OPERATION',
        body:
            '$managerName, this account can browse, save, fund, rent, and prepare. Club creation turns this into an owner dashboard.',
        primaryAction:
            'Next move: open a club, fund GTC/FNC routes, or scout the transfer hub before entering competitions.',
        capabilities: <String>[
          'Wallet',
          'Transfers',
          'Regens',
          'National rental',
          'Newsroom',
        ],
        accent: _GtexCommandColors.accentBlue,
      );
    case _HomePersona.clubOwner:
      return _PersonaCopy(
        title: '$clubName operations desk',
        subtitle:
            'Run squad readiness, competitions, wallet pressure, transfer movement, and matchday signals from one live desk.',
        badge: 'CLUB OWNER',
        headline: 'RUN $clubName LIKE A REAL FOOTBALL OFFICE',
        body:
            'Your club context is active, so the home desk prioritizes squad readiness, fixtures, market moves, rankings, and finance.',
        primaryAction:
            'Protect the club wallet, sign players, prepare fixtures, and keep the ranking ledger moving.',
        capabilities: <String>[
          'Squad',
          'Fixtures',
          'Transfers',
          'Ranking',
          'Club wallet',
        ],
        accent: _GtexCommandColors.accentPrimary,
      );
    case _HomePersona.creator:
      return _PersonaCopy(
        title: 'Creator football media desk',
        subtitle:
            'Track live topics, matches, transfer movement, wallet context, and publishing routes from your creator session.',
        badge: 'CREATOR DESK',
        headline: 'TURN LIVE FOOTBALL INTO STORIES AND REACTIONS',
        body:
            '$managerName, use market signals, match activity, regens, and club movement as publishing fuel.',
        primaryAction:
            'Open the studio, cover transfers, publish football stories, and route engagement into creator earnings.',
        capabilities: <String>[
          'Publish',
          'Newsroom',
          'Reactions',
          'Audience',
          'Wallet',
        ],
        accent: _GtexCommandColors.accentViolet,
      );
    case _HomePersona.coinTrader:
      return _PersonaCopy(
        title: 'Coin trader market desk',
        subtitle:
            'Keep GTEX Coin and Fan Coin liquidity visible, monitor trades, respond quickly, and protect settlement status.',
        badge: 'TRADER DESK',
        headline: 'MAKE THE COIN MARKET FEEL ONLINE',
        body:
            '$managerName, this desk centers live liquidity, trader reputation, wallet readiness, and market pressure.',
        primaryAction:
            'Review active offers, keep liquidity funded, watch buyer/seller pressure, and respond before volume moves.',
        capabilities: <String>[
          'GTC',
          'FNC',
          'Offers',
          'Liquidity',
          'Trade history',
        ],
        accent: _GtexCommandColors.accentAmber,
      );
    case _HomePersona.admin:
      return const _PersonaCopy(
        title: 'Admin platform operations desk',
        subtitle:
            'Monitor readiness, payments, traders, competitions, queues, settlements, and blocked states with backend permissions.',
        badge: 'ADMIN DESK',
        headline: 'CONTROL THE LIVE FOOTBALL ECONOMY SAFELY',
        body:
            'Admin sessions see operational pressure, but protected actions still require backend RBAC and audit authority.',
        primaryAction:
            'Review payment proofs, trader liquidity, hosted competitions, settlement queues, and platform health.',
        capabilities: <String>[
          'Payments',
          'Traders',
          'Competitions',
          'Queues',
          'Audit',
        ],
        accent: _GtexCommandColors.accentRed,
      );
  }
}

List<_QuickActionSpec> _actionsForPersona(_HomePersona persona) {
  switch (persona) {
    case _HomePersona.guest:
      return const <_QuickActionSpec>[
        _QuickActionSpec(
          location: AppRoutes.matches,
          label: 'Watch matchday',
          icon: Icons.sports_soccer_rounded,
          useGo: true,
        ),
        _QuickActionSpec(
          location: AppRoutes.market,
          label: 'Read transfer hub',
          icon: Icons.storefront_rounded,
          useGo: true,
        ),
        _QuickActionSpec(
          location: AppRoutes.profileLogin,
          label: 'Sign in',
          icon: Icons.login_rounded,
        ),
      ];
    case _HomePersona.noClub:
      return const <_QuickActionSpec>[
        _QuickActionSpec(
          location: AppRoutes.transferCenter,
          label: 'Buy players',
          icon: Icons.person_search_rounded,
        ),
        _QuickActionSpec(
          location: AppRoutes.nationalTeams,
          label: 'National rental',
          icon: Icons.flag_rounded,
        ),
        _QuickActionSpec(
          location: AppRoutes.regens,
          label: 'Search regens',
          icon: Icons.auto_awesome_rounded,
        ),
        _QuickActionSpec(
          location: AppRoutes.profile,
          label: 'Wallet and profile',
          icon: Icons.account_balance_wallet_rounded,
        ),
      ];
    case _HomePersona.clubOwner:
      return const <_QuickActionSpec>[
        _QuickActionSpec(
          location: AppRoutes.competitions,
          label: 'Enter competitions',
          icon: Icons.emoji_events_rounded,
        ),
        _QuickActionSpec(
          location: AppRoutes.transferCenter,
          label: 'Sign players',
          icon: Icons.storefront_rounded,
        ),
        _QuickActionSpec(
          location: AppRoutes.coaches,
          label: 'Hire coaches',
          icon: Icons.sports_rounded,
        ),
        _QuickActionSpec(
          location: AppRoutes.lineup,
          label: 'Set lineup',
          icon: Icons.dashboard_customize_rounded,
        ),
        _QuickActionSpec(
          location: AppRoutes.matches,
          label: 'Prepare matchday',
          icon: Icons.sports_soccer_rounded,
          useGo: true,
        ),
        _QuickActionSpec(
          location: AppRoutes.profile,
          label: 'Club wallet',
          icon: Icons.account_balance_wallet_rounded,
        ),
      ];
    case _HomePersona.creator:
      return const <_QuickActionSpec>[
        _QuickActionSpec(
          location: AppRoutes.clips,
          label: 'Open football feed',
          icon: Icons.dynamic_feed_rounded,
        ),
        _QuickActionSpec(
          location: AppRoutes.market,
          label: 'Track transfer stories',
          icon: Icons.storefront_rounded,
        ),
        _QuickActionSpec(
          location: AppRoutes.matches,
          label: 'React to matchday',
          icon: Icons.sports_soccer_rounded,
          useGo: true,
        ),
      ];
    case _HomePersona.coinTrader:
      return const <_QuickActionSpec>[
        _QuickActionSpec(
          location: AppRoutes.profile,
          label: 'Trader wallet',
          icon: Icons.account_balance_wallet_rounded,
        ),
        _QuickActionSpec(
          location: AppRoutes.market,
          label: 'Market pressure',
          icon: Icons.candlestick_chart_rounded,
        ),
        _QuickActionSpec(
          location: AppRoutes.tasks,
          label: 'Trader rhythm',
          icon: Icons.flag_rounded,
        ),
      ];
    case _HomePersona.admin:
      return const <_QuickActionSpec>[
        _QuickActionSpec(
          location: AppRoutes.profileAdmin,
          label: 'Admin controls',
          icon: Icons.admin_panel_settings_rounded,
        ),
        _QuickActionSpec(
          location: AppRoutes.competitions,
          label: 'Competition OS',
          icon: Icons.emoji_events_rounded,
        ),
        _QuickActionSpec(
          location: AppRoutes.profile,
          label: 'Payments and profile',
          icon: Icons.payments_rounded,
        ),
      ];
  }
}

String _managerName(ProfileData? profile, bool authenticated) {
  if (!authenticated) {
    return 'Guest';
  }
  final JsonMap? user = profile?.user;
  return stringValue(
    user?['display_name'],
    fallback: stringValue(
      user?['username'],
      fallback: stringValue(user?['email'], fallback: 'Manager'),
    ),
  );
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
      return 'Live';
  }
}

String _formatGtc(double value) {
  if (value <= 0) {
    return 'LOCKED';
  }
  if (value >= 1000000) {
    return 'GTC ${(value / 1000000).toStringAsFixed(1)}M';
  }
  if (value >= 1000) {
    return 'GTC ${(value / 1000).toStringAsFixed(1)}K';
  }
  return 'GTC ${value.toStringAsFixed(value == value.roundToDouble() ? 0 : 1)}';
}

String _formatFanCoin(double value) {
  if (value <= 0) {
    return 'LOCKED';
  }
  if (value >= 1000000) {
    return 'FNC ${(value / 1000000).toStringAsFixed(1)}M';
  }
  if (value >= 1000) {
    return 'FNC ${(value / 1000).toStringAsFixed(1)}K';
  }
  return 'FNC ${value.toStringAsFixed(value == value.roundToDouble() ? 0 : 1)}';
}

// ---------------------------------------------------------------------------
// PHASE 4F — Personalized Home digest sections.
//
// Every section below reads the single `homeDigestProvider` AsyncValue and
// composes it strictly from PHASE4-B/A/D/C/E's published models (see
// `data/gtex_home_digest_provider.dart`). A section hides entirely once the
// digest has loaded and its own list is genuinely empty, rather than
// rendering an empty-state wall for an asset class the user does not
// participate in (P6 / Step 11).
// ---------------------------------------------------------------------------

class _HomeWorldTodayBanner extends StatelessWidget {
  const _HomeWorldTodayBanner({required this.digestValue});

  final AsyncValue<GtexHomeDigest> digestValue;

  @override
  Widget build(BuildContext context) {
    return _LiveModule<GtexHomeDigest>(
      value: digestValue,
      title: 'YOUR WORLD TODAY',
      subtitle: 'What happened to your GTEX football world.',
      accent: _GtexCommandColors.accentPrimary,
      authenticated: true,
      builder: (BuildContext context, GtexHomeDigest digest) {
        return Text(
          digest.headline,
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
            fontFamily: 'BarlowCondensed',
            fontWeight: FontWeight.w800,
            color: _GtexCommandColors.textPrimary,
          ),
        );
      },
    );
  }
}

class _HomeYourPlayersPanel extends StatelessWidget {
  const _HomeYourPlayersPanel({required this.digestValue});

  final AsyncValue<GtexHomeDigest> digestValue;

  @override
  Widget build(BuildContext context) {
    final GtexHomeDigest? data = digestValue.asData?.value;
    if (data != null && data.ownedPlayers.isEmpty) {
      return const SizedBox.shrink();
    }
    return _LiveModule<GtexHomeDigest>(
      value: digestValue,
      title: 'YOUR PLAYERS',
      subtitle: 'Owned players and what is moving their value.',
      accent: _GtexCommandColors.accentPrimary,
      authenticated: true,
      builder:
          (BuildContext context, GtexHomeDigest digest) => Column(
            children: digest.ownedPlayers
                .map(
                  (GtexHomePlayerHighlight highlight) =>
                      _HomePlayerHighlightTile(highlight: highlight),
                )
                .toList(growable: false),
          ),
    );
  }
}

class _HomePlayerHighlightTile extends StatelessWidget {
  const _HomePlayerHighlightTile({required this.highlight});

  final GtexHomePlayerHighlight highlight;

  @override
  Widget build(BuildContext context) {
    final String ownershipLabel =
        highlight.quantityLabel == '1'
            ? 'You own 1 share'
            : 'You own ${highlight.quantityLabel} shares';
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          GtexPlayerCard(
            name: highlight.playerName,
            position: '—',
            clubName: highlight.clubName ?? 'Club unknown',
            nationality: '',
            priceLabel: highlight.priceLabel,
            scale: GtexPlayerCardScale.compact,
            isOwned: true,
            ownershipLabel: ownershipLabel,
            onTap: GtexPlayerNavigator.tapToOpen(context, highlight.playerId),
          ),
          if (highlight.unrealizedPlPercent != null ||
              highlight.formTrendLabel != null)
            Padding(
              padding: const EdgeInsets.only(top: 4, left: 4),
              child: Text(
                <String>[
                  if (highlight.unrealizedPlPercent != null)
                    'Your position: ${highlight.movementLabel}',
                  if (highlight.formTrendLabel != null)
                    highlight.formTrendLabel!,
                ].join(' · '),
                style: _bodyStyle(context),
              ),
            ),
        ],
      ),
    );
  }
}

class _HomeWhatMovedPanel extends StatelessWidget {
  const _HomeWhatMovedPanel({required this.digestValue});

  final AsyncValue<GtexHomeDigest> digestValue;

  @override
  Widget build(BuildContext context) {
    final GtexHomeDigest? data = digestValue.asData?.value;
    if (data != null &&
        data.yourMoversToday.isEmpty &&
        data.opportunityMovers.isEmpty) {
      return const SizedBox.shrink();
    }
    return _LiveModule<GtexHomeDigest>(
      value: digestValue,
      title: 'WHAT MOVED',
      subtitle: 'Real price movement from the live market.',
      accent: _GtexCommandColors.accentBlue,
      authenticated: true,
      builder: (BuildContext context, GtexHomeDigest digest) {
        final List<Widget> rows = <Widget>[
          ...digest.yourMoversToday.map(
            (GtexHomeMoverHighlight mover) => _PulseRow(
              line: _PulseLine(
                label: mover.playerName,
                detail: 'You own this player',
                metric: mover.movementLabel,
                color:
                    mover.isRising
                        ? _GtexCommandColors.accentPrimary
                        : _GtexCommandColors.accentRed,
              ),
            ),
          ),
          ...digest.opportunityMovers.map(
            (GtexHomeMoverHighlight mover) => _PulseRow(
              line: _PulseLine(
                label: mover.playerName,
                detail: 'Opportunity · not in your squad',
                metric: mover.movementLabel,
                color: _GtexCommandColors.accentAmber,
              ),
            ),
          ),
        ];
        return Column(children: rows);
      },
    );
  }
}

class _HomeYourClubsPanel extends StatelessWidget {
  const _HomeYourClubsPanel({required this.digestValue});

  final AsyncValue<GtexHomeDigest> digestValue;

  @override
  Widget build(BuildContext context) {
    final GtexHomeDigest? data = digestValue.asData?.value;
    if (data != null && data.clubs.isEmpty) {
      return const SizedBox.shrink();
    }
    return _LiveModule<GtexHomeDigest>(
      value: digestValue,
      title: 'YOUR CLUBS',
      subtitle: 'Club shares you hold and their live price.',
      accent: _GtexCommandColors.accentPrimary,
      authenticated: true,
      builder:
          (BuildContext context, GtexHomeDigest digest) => Column(
            children: digest.clubs
                .map(
                  (GtexHomeClubHighlight club) => _PulseRow(
                    line: _PulseLine(
                      label: club.clubName,
                      detail:
                          '${club.sharesLabel} · ${club.sharePriceLabel} · '
                          '${club.hasPerformanceHistory ? 'Club form is being tracked' : 'No settled GTEX matches yet — the share price sits at its base'}',
                      metric: club.plLabel,
                      color:
                          club.isInProfit
                              ? _GtexCommandColors.accentPrimary
                              : _GtexCommandColors.accentRed,
                    ),
                  ),
                )
                .toList(growable: false),
          ),
    );
  }
}

class _HomeYourProspectsPanel extends StatelessWidget {
  const _HomeYourProspectsPanel({required this.digestValue});

  final AsyncValue<GtexHomeDigest> digestValue;

  @override
  Widget build(BuildContext context) {
    final GtexHomeDigest? data = digestValue.asData?.value;
    if (data != null && data.regens.isEmpty) {
      return const SizedBox.shrink();
    }
    return _LiveModule<GtexHomeDigest>(
      value: digestValue,
      title: 'YOUR PROSPECTS',
      subtitle: 'Regens you own on the live leaderboard.',
      accent: _GtexCommandColors.accentViolet,
      authenticated: true,
      builder:
          (BuildContext context, GtexHomeDigest digest) => Column(
            children: digest.regens
                .map(
                  (GtexHomeRegenHighlight regen) => _PulseRow(
                    line: _PulseLine(
                      label: regen.playerName,
                      detail: '${regen.category} ranking',
                      metric: regen.rankLabel,
                      color: _GtexCommandColors.accentViolet,
                    ),
                  ),
                )
                .toList(growable: false),
          ),
    );
  }
}

class _HomeAttentionPanel extends StatelessWidget {
  const _HomeAttentionPanel({
    required this.digestValue,
    required this.onOpen,
    required this.onGo,
  });

  final AsyncValue<GtexHomeDigest> digestValue;
  final ValueChanged<String> onOpen;
  final ValueChanged<String> onGo;

  @override
  Widget build(BuildContext context) {
    final GtexHomeDigest? data = digestValue.asData?.value;
    if (data != null && data.attentionItems.isEmpty) {
      return const SizedBox.shrink();
    }
    return _LiveModule<GtexHomeDigest>(
      value: digestValue,
      title: 'WHAT NEEDS YOUR ATTENTION',
      subtitle: 'A short list of real, actionable next moves.',
      accent: _GtexCommandColors.accentAmber,
      authenticated: true,
      builder:
          (BuildContext context, GtexHomeDigest digest) => Wrap(
            spacing: 10,
            runSpacing: 10,
            children: digest.attentionItems
                .map(
                  (GtexHomeAttentionItem item) => OutlinedButton(
                    onPressed:
                        item.useGo
                            ? () => onGo(item.routeLocation)
                            : () => onOpen(item.routeLocation),
                    child: Text(item.label),
                  ),
                )
                .toList(growable: false),
          ),
    );
  }
}

class _HomeRecentActivityPanel extends StatelessWidget {
  const _HomeRecentActivityPanel({required this.digestValue});

  final AsyncValue<GtexHomeDigest> digestValue;

  @override
  Widget build(BuildContext context) {
    final GtexHomeDigest? data = digestValue.asData?.value;
    if (data != null && data.recentActivity.isEmpty) {
      return const SizedBox.shrink();
    }
    return _LiveModule<GtexHomeDigest>(
      value: digestValue,
      title: 'RECENT OWNERSHIP CHANGES',
      subtitle: 'Settled trades from your account.',
      accent: _GtexCommandColors.accentBlue,
      authenticated: true,
      builder:
          (BuildContext context, GtexHomeDigest digest) => Column(
            children: digest.recentActivity
                .map(
                  (GtexHomeActivityItem item) => _PulseRow(
                    line: _PulseLine(
                      label: item.label,
                      detail: item.timestampLabel,
                      metric: '',
                      color: _GtexCommandColors.textSecondary,
                    ),
                  ),
                )
                .toList(growable: false),
          ),
    );
  }
}
