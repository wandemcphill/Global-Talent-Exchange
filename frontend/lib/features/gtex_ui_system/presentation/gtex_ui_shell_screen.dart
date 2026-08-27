import 'package:flutter/material.dart';

import '../../../data/gte_api_repository.dart';
import '../../../models/match_type.dart';
import '../../../providers/gte_exchange_controller.dart';
import '../../../screens/gte_login_screen.dart';
import '../../../widgets/gte_shell_theme.dart';
import '../../../widgets/gte_surface_panel.dart';
import '../../../widgets/gtex_branding.dart';
import '../data/gtex_ui_demo_data.dart';
import '../widgets/gtex_ui_cards.dart';
import '../widgets/gtex_ui_primitives.dart';
import 'gtex_ui_detail_screens.dart';

enum GtexRootTab { home, matches, market, world, profile }

class GtexUiSystemShellScreen extends StatefulWidget {
  const GtexUiSystemShellScreen({
    super.key,
    required this.controller,
    required this.apiBaseUrl,
    required this.backendMode,
    this.initialTab = GtexRootTab.home,
  });

  final GteExchangeController controller;
  final String apiBaseUrl;
  final GteBackendMode backendMode;
  final GtexRootTab initialTab;

  @override
  State<GtexUiSystemShellScreen> createState() =>
      _GtexUiSystemShellScreenState();
}

class _GtexUiSystemShellScreenState extends State<GtexUiSystemShellScreen> {
  late int _tabIndex;
  final Set<String> _claimedTaskIds = <String>{};

  static const List<_RootTabMeta> _tabs = <_RootTabMeta>[
    _RootTabMeta(
      label: 'Home',
      title: 'Command Center',
      subtitle: 'Club pulse, live stories, and daily priorities.',
      icon: Icons.home_outlined,
      selectedIcon: Icons.home_rounded,
      tab: GtexRootTab.home,
    ),
    _RootTabMeta(
      label: 'Matches',
      title: 'Live Match Hub',
      subtitle: 'Broadcast-grade match control and commentary.',
      icon: Icons.sports_soccer_outlined,
      selectedIcon: Icons.sports_soccer_rounded,
      tab: GtexRootTab.matches,
    ),
    _RootTabMeta(
      label: 'Market',
      title: 'Transfer Market',
      subtitle: 'Search, bid, and react to live talent movement.',
      icon: Icons.storefront_outlined,
      selectedIcon: Icons.storefront_rounded,
      tab: GtexRootTab.market,
    ),
    _RootTabMeta(
      label: 'World',
      title: 'World Hub',
      subtitle: 'Regens, federations, tournaments, and history.',
      icon: Icons.public_outlined,
      selectedIcon: Icons.public_rounded,
      tab: GtexRootTab.world,
    ),
    _RootTabMeta(
      label: 'Profile',
      title: 'Profile & Club',
      subtitle: 'Social profile, identity, and long-horizon management.',
      icon: Icons.person_outline_rounded,
      selectedIcon: Icons.person_rounded,
      tab: GtexRootTab.profile,
    ),
  ];

  @override
  void initState() {
    super.initState();
    _tabIndex = widget.initialTab.index;
    widget.controller.bootstrap();
    if (widget.controller.isAuthenticated) {
      widget.controller.refreshAccount();
    }
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: widget.controller,
      builder: (BuildContext context, Widget? child) {
        final GtexUiUniverseData data = GtexUiUniverseFactory.fromController(
          widget.controller,
          claimedTaskIds: _claimedTaskIds,
        );
        final _RootTabMeta activeTab = _tabs[_tabIndex];
        return Container(
          decoration: gteBackdropDecoration(),
          child: Scaffold(
            backgroundColor: Colors.transparent,
            appBar: AppBar(
              toolbarHeight: 86,
              titleSpacing: 18,
              title: Row(
                children: <Widget>[
                  const GtexLogoMark(size: 40, compact: true),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(activeTab.title),
                        Text(
                          activeTab.subtitle,
                          style: Theme.of(context).textTheme.bodySmall,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              actions: <Widget>[
                IconButton(
                  tooltip: 'Notifications',
                  onPressed: () {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text(
                          '${data.notifications} new GTEX alerts ready.',
                        ),
                      ),
                    );
                  },
                  icon: Badge.count(
                    count: data.notifications,
                    child: const Icon(Icons.notifications_none_rounded),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: GtexMetricPill(
                    label: 'Coins',
                    value: '${data.coins}',
                    icon: Icons.monetization_on_outlined,
                    color: GteShellTheme.tokensOf(context).accentCapital,
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.only(right: 16),
                  child:
                      widget.controller.isAuthenticated
                          ? FilledButton.tonal(
                            onPressed: () async {
                              await widget.controller.signOut();
                              if (!mounted) {
                                return;
                              }
                              setState(() {
                                _tabIndex = GtexRootTab.home.index;
                              });
                            },
                            child: const Text('Sign out'),
                          )
                          : FilledButton(
                            onPressed: _openLogin,
                            child: const Text('Sign in'),
                          ),
                ),
              ],
            ),
            body: IndexedStack(
              index: _tabIndex,
              children: <Widget>[
                _HomeDashboardTab(
                  data: data,
                  onOpenMatch: _openMatchExperience,
                  onOpenMarket: () => _selectTab(GtexRootTab.market),
                  onOpenWorld: () => _selectTab(GtexRootTab.world),
                  onOpenClub: _openClubManagement,
                  onOpenPlayer: _openPlayerDetail,
                  onOpenTasks: _openDailyTasks,
                  onClaimTask: _claimTask,
                ),
                _MatchesTab(
                  data: data,
                  onOpenMatch: _openMatchExperience,
                  onOpenBroadcast: _openBroadcastView,
                ),
                _TransferMarketTab(
                  data: data,
                  onOpenPlayer: _openPlayerDetail,
                  onBid: _showBidSheet,
                ),
                _WorldTab(
                  data: data,
                  onOpenPlayer: _openPlayerDetail,
                  onOpenTournament: _openTournamentIntro,
                ),
                _ProfileTab(
                  data: data,
                  isAuthenticated: widget.controller.isAuthenticated,
                  onOpenClub: _openClubManagement,
                  onOpenNationalTeam: _openNationalTeam,
                  onOpenTasks: _openDailyTasks,
                ),
              ],
            ),
            bottomNavigationBar: NavigationBar(
              selectedIndex: _tabIndex,
              height: 78,
              onDestinationSelected: (int index) {
                setState(() {
                  _tabIndex = index;
                });
              },
              destinations: _tabs
                  .map(
                    (_RootTabMeta meta) => NavigationDestination(
                      icon: Icon(meta.icon),
                      selectedIcon: Icon(meta.selectedIcon),
                      label: meta.label,
                    ),
                  )
                  .toList(growable: false),
            ),
          ),
        );
      },
    );
  }

  void _selectTab(GtexRootTab tab) {
    setState(() {
      _tabIndex = tab.index;
    });
  }

  Future<void> _openLogin() async {
    await Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder:
            (BuildContext context) =>
                GteLoginScreen(controller: widget.controller),
      ),
    );
    if (widget.controller.isAuthenticated) {
      await widget.controller.refreshAccount();
    }
  }

  void _claimTask(GtexTaskData task) {
    if (_claimedTaskIds.contains(task.id)) {
      return;
    }
    setState(() {
      _claimedTaskIds.add(task.id);
    });
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text('${task.rewardLabel} claimed.')));
  }

  Future<void> _openPlayerDetail(GtexPlayerCardData player) {
    return Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder:
            (BuildContext context) => GtexPlayerDetailScreen(player: player),
      ),
    );
  }

  Future<void> _openMatchExperience(GtexLiveMatchData match) {
    return Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder:
            (BuildContext context) => GtexMatchExperienceScreen(
              match: match,
              onOpenBroadcast: () => _openBroadcastView(match),
            ),
      ),
    );
  }

  Future<void> _openBroadcastView(GtexLiveMatchData match) {
    final GtexUiUniverseData data = GtexUiUniverseFactory.fromController(
      widget.controller,
      claimedTaskIds: _claimedTaskIds,
    );
    return Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder:
            (BuildContext context) =>
                GtexBroadcastViewScreen(match: match, feed: data.profileFeed),
      ),
    );
  }

  Future<void> _openClubManagement() {
    final GtexUiUniverseData data = GtexUiUniverseFactory.fromController(
      widget.controller,
      claimedTaskIds: _claimedTaskIds,
    );
    return Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => GtexClubManagementScreen(data: data),
      ),
    );
  }

  Future<void> _openNationalTeam() {
    final GtexUiUniverseData data = GtexUiUniverseFactory.fromController(
      widget.controller,
      claimedTaskIds: _claimedTaskIds,
    );
    return Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => GtexNationalTeamScreen(data: data),
      ),
    );
  }

  Future<void> _openDailyTasks() {
    final GtexUiUniverseData data = GtexUiUniverseFactory.fromController(
      widget.controller,
      claimedTaskIds: _claimedTaskIds,
    );
    return Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder:
            (BuildContext context) =>
                GtexDailyTasksScreen(tasks: data.tasks, onClaim: _claimTask),
      ),
    );
  }

  Future<void> _openTournamentIntro(GtexTournamentCardData tournament) {
    return Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder:
            (BuildContext context) =>
                GtexTournamentIntroScreen(tournament: tournament),
      ),
    );
  }

  Future<void> _showBidSheet(GtexPlayerCardData player) {
    final TextEditingController controller = TextEditingController(
      text: gtexCompactCurrency(player.price),
    );
    return showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (BuildContext context) {
        return Padding(
          padding: EdgeInsets.only(
            bottom: MediaQuery.viewInsetsOf(context).bottom,
          ),
          child: GtexModalSheet(
            title: 'Place bid for ${player.name}',
            subtitle:
                'Highest bid ${player.offers.first.valueLabel} • ${player.timerLabel}',
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                TextField(
                  controller: controller,
                  decoration: const InputDecoration(
                    labelText: 'Bid amount',
                    prefixText: 'CR ',
                  ),
                ),
                const SizedBox(height: 16),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton(
                    onPressed: () {
                      Navigator.of(context).pop();
                      ScaffoldMessenger.of(this.context).showSnackBar(
                        SnackBar(
                          content: Text(
                            'Bid submitted for ${player.name}: ${controller.text}',
                          ),
                        ),
                      );
                    },
                    child: const Text('Place Bid'),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _RootTabMeta {
  const _RootTabMeta({
    required this.label,
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.selectedIcon,
    required this.tab,
  });

  final String label;
  final String title;
  final String subtitle;
  final IconData icon;
  final IconData selectedIcon;
  final GtexRootTab tab;
}

class _HomeDashboardTab extends StatelessWidget {
  const _HomeDashboardTab({
    required this.data,
    required this.onOpenMatch,
    required this.onOpenMarket,
    required this.onOpenWorld,
    required this.onOpenClub,
    required this.onOpenPlayer,
    required this.onOpenTasks,
    required this.onClaimTask,
  });

  final GtexUiUniverseData data;
  final ValueChanged<GtexLiveMatchData> onOpenMatch;
  final VoidCallback onOpenMarket;
  final VoidCallback onOpenWorld;
  final VoidCallback onOpenClub;
  final ValueChanged<GtexPlayerCardData> onOpenPlayer;
  final VoidCallback onOpenTasks;
  final ValueChanged<GtexTaskData> onClaimTask;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return SafeArea(
      top: false,
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            _UserClubCard(data: data, onOpenClub: onOpenClub),
            const SizedBox(height: 18),
            _NextActionRecommendationCard(
              data: data,
              onOpenMarket: onOpenMarket,
              onOpenMatch: () => onOpenMatch(data.liveMatches.first),
            ),
            const SizedBox(height: 18),
            _MarketPulsePanel(data: data, onOpenMarket: onOpenMarket),
            const SizedBox(height: 18),
            _EconomySignalPanel(data: data),
            const SizedBox(height: 18),
            _QuickActionsRow(
              onOpenMatch: () => onOpenMatch(data.liveMatches.first),
              onOpenMarket: onOpenMarket,
              onOpenAcademy: onOpenClub,
              onOpenCompetitions: onOpenWorld,
            ),
            const SizedBox(height: 22),
            Text('Live matches', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 12),
            SizedBox(
              height: 196,
              child: PageView.builder(
                controller: PageController(viewportFraction: 0.92),
                itemCount: data.liveMatches.length,
                itemBuilder: (BuildContext context, int index) {
                  final GtexLiveMatchData match = data.liveMatches[index];
                  return Padding(
                    padding: const EdgeInsets.only(right: 12),
                    child: _LiveMatchCard(
                      match: match,
                      onOpen: () => onOpenMatch(match),
                    ),
                  );
                },
              ),
            ),
            const SizedBox(height: 22),
            Text(
              'Story highlights',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 12),
            SizedBox(
              height: 170,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: data.stories.length,
                separatorBuilder: (_, __) => const SizedBox(width: 12),
                itemBuilder:
                    (BuildContext context, int index) =>
                        GtexStoryCard(story: data.stories[index]),
              ),
            ),
            const SizedBox(height: 22),
            Row(
              children: <Widget>[
                Expanded(
                  child: Text(
                    'Daily tasks',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                ),
                TextButton(
                  onPressed: onOpenTasks,
                  child: const Text('View all'),
                ),
              ],
            ),
            const SizedBox(height: 12),
            ...data.tasks
                .take(2)
                .map(
                  (GtexTaskData task) => Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: GtexTaskCard(
                      task: task,
                      onClaim: () => onClaimTask(task),
                    ),
                  ),
                ),
            const SizedBox(height: 22),
            Text(
              'Transfer alerts',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 12),
            ...data.transferAlerts.map(
              (GtexTransferAlertData alert) => Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: GtexTransferAlertTile(alert: alert),
              ),
            ),
            const SizedBox(height: 22),
            Row(
              children: <Widget>[
                Expanded(
                  child: Text(
                    'Regen Discovery Carousel',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                ),
                TextButton(
                  onPressed: onOpenWorld,
                  child: const Text('Scout All'),
                ),
              ],
            ),
            const SizedBox(height: 12),
            SizedBox(
              height: 380,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: data.trendingRegens.length,
                separatorBuilder: (_, __) => const SizedBox(width: 14),
                itemBuilder: (BuildContext context, int index) => SizedBox(
                  width: 280,
                  child: GtexRegenCard(
                    player: data.trendingRegens[index],
                    onOpen: () => onOpenPlayer(data.trendingRegens[index]),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 12),
            GteSurfacePanel(
              accentColor: tokens.accentCommunity,
              child: Row(
                children: <Widget>[
                  const Expanded(
                    child: Text(
                      'The Home dashboard now behaves like a football command center, not a generic admin board.',
                    ),
                  ),
                  const SizedBox(width: 12),
                  FilledButton.tonal(
                    onPressed: onOpenWorld,
                    child: const Text('Open World'),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _MatchesTab extends StatelessWidget {
  const _MatchesTab({
    required this.data,
    required this.onOpenMatch,
    required this.onOpenBroadcast,
  });

  final GtexUiUniverseData data;
  final ValueChanged<GtexLiveMatchData> onOpenMatch;
  final ValueChanged<GtexLiveMatchData> onOpenBroadcast;

  @override
  Widget build(BuildContext context) {
    final GtexLiveMatchData featured = data.liveMatches.first;
    return SafeArea(
      top: false,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
        children: <Widget>[
          GteSurfacePanel(
            emphasized: true,
            accentColor: GteShellTheme.tokensOf(context).accentArena,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  'Featured live match',
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const SizedBox(height: 10),
                Text(
                  '${featured.homeClub} vs ${featured.awayClub}',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 6),
                Text(
                  featured.commentaryLine,
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: 18),
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: <Widget>[
                    GtexMetricPill(
                      label: 'Score',
                      value: '${featured.homeScore}-${featured.awayScore}',
                      icon: Icons.scoreboard_outlined,
                      color: GteShellTheme.tokensOf(context).accentArena,
                    ),
                    GtexMetricPill(
                      label: 'Minute',
                      value: '${featured.minute}\'',
                      icon: Icons.timer_outlined,
                      color: GteShellTheme.tokensOf(context).accentClub,
                    ),
                    GtexMetricPill(
                      label: 'xG',
                      value:
                          '${featured.xgHome.toStringAsFixed(1)}-${featured.xgAway.toStringAsFixed(1)}',
                      icon: Icons.analytics_outlined,
                      color: GteShellTheme.tokensOf(context).accentCommunity,
                    ),
                    GtexMetricPill(
                      label: 'Entry lane',
                      value: _entryLabel(featured),
                      icon: Icons.account_balance_wallet_outlined,
                      color: _matchTypeAccent(context, featured.matchType),
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                GteSurfacePanel(
                  accentColor: _matchTypeAccent(context, featured.matchType),
                  child: Text(
                    featured.matchType.walletNotice,
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ),
                const SizedBox(height: 18),
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: <Widget>[
                    FilledButton.icon(
                      onPressed: () => onOpenMatch(featured),
                      icon: const Icon(Icons.play_circle_outline_rounded),
                      label: Text(featured.matchType.actionLabel),
                    ),
                    FilledButton.tonalIcon(
                      onPressed: () => onOpenBroadcast(featured),
                      icon: const Icon(Icons.live_tv_outlined),
                      label: const Text('Broadcast'),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 18),
          ...data.liveMatches.map(
            (GtexLiveMatchData match) => Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: _LiveMatchCard(
                match: match,
                onOpen: () => onOpenMatch(match),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _TransferMarketTab extends StatefulWidget {
  const _TransferMarketTab({
    required this.data,
    required this.onOpenPlayer,
    required this.onBid,
  });

  final GtexUiUniverseData data;
  final ValueChanged<GtexPlayerCardData> onOpenPlayer;
  final ValueChanged<GtexPlayerCardData> onBid;

  @override
  State<_TransferMarketTab> createState() => _TransferMarketTabState();
}

class _TransferMarketTabState extends State<_TransferMarketTab> {
  final TextEditingController _searchController = TextEditingController();
  String _filter = 'All';

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final String search = _searchController.text.trim().toLowerCase();
    final List<GtexPlayerCardData> players = widget.data.marketPlayers
        .where((GtexPlayerCardData player) {
          final bool matchesSearch =
              search.isEmpty ||
              player.name.toLowerCase().contains(search) ||
              player.position.toLowerCase().contains(search) ||
              player.country.toLowerCase().contains(search);
          final bool matchesFilter =
              _filter == 'All' ||
              (_filter == 'Elite' && player.potential >= 90) ||
              (_filter == 'Fast' && player.attributes['Pace']! >= 85) ||
              (_filter == 'Value' && player.price < 2000000);
          return matchesSearch && matchesFilter;
        })
        .toList(growable: false);
    return SafeArea(
      top: false,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
        children: <Widget>[
          TextField(
            controller: _searchController,
            onChanged: (_) => setState(() {}),
            decoration: const InputDecoration(
              hintText: 'Search players, positions, countries',
              prefixIcon: Icon(Icons.search_rounded),
            ),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: <String>['All', 'Elite', 'Fast', 'Value', 'Risers', 'Bargains']
                .map(
                  (String filter) => ChoiceChip(
                    label: Text(filter),
                    selected: _filter == filter,
                    onSelected: (_) => setState(() => _filter = filter),
                  ),
                )
                .toList(growable: false),
          ),
          const SizedBox(height: 14),
          GteSurfacePanel(
            accentColor: GteShellTheme.tokensOf(context).accentCapital,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Row(
                  children: <Widget>[
                    Text(
                      'Exchange Pulse & Order Book',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const Spacer(),
                    GtexBadgeIcon(
                      label:
                          '${players.where((GtexPlayerCardData player) => player.liquidityLabel.contains('High')).length} High-Liquidity',
                      color: GteShellTheme.tokensOf(context).accentCapital,
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  'Liquidity is live. High-fire cards move fast, thin books need patience. Instant execution supported for listed ask orders.',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: <Widget>[
                    GtexMetricPill(
                      label: 'Avg Spread',
                      value: '1.2%',
                      icon: Icons.sync_alt_rounded,
                      color: GteShellTheme.tokensOf(context).accentCapital,
                    ),
                    GtexMetricPill(
                      label: '24h Trades',
                      value: '1,420 orders',
                      icon: Icons.receipt_long_rounded,
                      color: GteShellTheme.tokensOf(context).accentArena,
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 18),
          LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              final int columnCount =
                  constraints.maxWidth >= 1180
                      ? 3
                      : constraints.maxWidth >= 760
                      ? 2
                      : 1;
              return GridView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: players.length,
                gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: columnCount,
                  mainAxisExtent: 380,
                  crossAxisSpacing: 14,
                  mainAxisSpacing: 14,
                ),
                itemBuilder: (BuildContext context, int index) {
                  final GtexPlayerCardData player = players[index];
                  return GtexPlayerTile(
                    player: player,
                    onOpen: () => widget.onOpenPlayer(player),
                    onBid: () => widget.onBid(player),
                  );
                },
              );
            },
          ),
        ],
      ),
    );
  }
}

class _WorldTab extends StatelessWidget {
  const _WorldTab({
    required this.data,
    required this.onOpenPlayer,
    required this.onOpenTournament,
  });

  final GtexUiUniverseData data;
  final ValueChanged<GtexPlayerCardData> onOpenPlayer;
  final ValueChanged<GtexTournamentCardData> onOpenTournament;

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 4,
      child: Column(
        children: <Widget>[
          const SizedBox(height: 8),
          const TabBar(
            isScrollable: true,
            tabs: <Tab>[
              Tab(text: 'Regens'),
              Tab(text: 'Competitions'),
              Tab(text: 'Federations'),
              Tab(text: 'History'),
            ],
          ),
          Expanded(
            child: TabBarView(
              children: <Widget>[
                _RegensWorldView(data: data, onOpenPlayer: onOpenPlayer),
                _CompetitionsWorldView(
                  data: data,
                  onOpenTournament: onOpenTournament,
                ),
                _FederationsWorldView(data: data),
                _HistoryWorldView(data: data),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ProfileTab extends StatelessWidget {
  const _ProfileTab({
    required this.data,
    required this.isAuthenticated,
    required this.onOpenClub,
    required this.onOpenNationalTeam,
    required this.onOpenTasks,
  });

  final GtexUiUniverseData data;
  final bool isAuthenticated;
  final VoidCallback onOpenClub;
  final VoidCallback onOpenNationalTeam;
  final VoidCallback onOpenTasks;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return SafeArea(
      top: false,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
        children: <Widget>[
          GteSurfacePanel(
            emphasized: true,
            accentColor: tokens.accentClub,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Row(
                  children: <Widget>[
                    GtexAnimatedAvatar(
                      label: data.userName,
                      size: 84,
                      accent: tokens.accentClub,
                      badges: const <String>['🏆', '🔥'],
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(
                            data.userName,
                            style: Theme.of(context).textTheme.headlineSmall,
                          ),
                          const SizedBox(height: 6),
                          Text(
                            isAuthenticated ? data.club.name : 'Guest preview',
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 18),
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: <Widget>[
                    GtexMetricPill(
                      label: 'Followers',
                      value: '128K',
                      icon: Icons.groups_outlined,
                      color: tokens.accentCommunity,
                    ),
                    GtexMetricPill(
                      label: 'Achievements',
                      value: '24',
                      icon: Icons.emoji_events_outlined,
                      color: tokens.accentArena,
                    ),
                    GtexMetricPill(
                      label: 'Activity',
                      value: 'Live',
                      icon: Icons.flash_on_outlined,
                      color: tokens.accentCapital,
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 18),
          GteSurfacePanel(
            accentColor: tokens.accentCapital,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Row(
                  children: <Widget>[
                    Text(
                      'Football Portfolio & Valuation',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const Spacer(),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 4,
                      ),
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(12),
                        color: Colors.green.withValues(alpha: 0.16),
                      ),
                      child: Text(
                        '+12.4% ALL TIME',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: Colors.green,
                              fontWeight: FontWeight.w800,
                            ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: <Widget>[
                    GtexMetricPill(
                      label: 'Total Net Worth',
                      value: '₦68.2M',
                      icon: Icons.account_balance_outlined,
                      color: tokens.accentCapital,
                    ),
                    GtexMetricPill(
                      label: 'Player Assets (14)',
                      value: '₦42.5M',
                      icon: Icons.sports_soccer_outlined,
                      color: tokens.accentArena,
                    ),
                    GtexMetricPill(
                      label: 'Club Equity',
                      value: '₦18.0M',
                      icon: Icons.pie_chart_outline_rounded,
                      color: tokens.accentClub,
                    ),
                    GtexMetricPill(
                      label: 'GTEX Coins',
                      value: '${data.coins}',
                      icon: Icons.monetization_on_outlined,
                      color: tokens.accentWarm,
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                Row(
                  children: <Widget>[
                    Expanded(
                      child: FilledButton.icon(
                        onPressed: () {
                          _showGiftingModal(context, data);
                        },
                        icon: const Icon(Icons.card_giftcard_rounded),
                        label: const Text('Gift Assets / Coins'),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 18),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              FilledButton.tonalIcon(
                onPressed: onOpenClub,
                icon: const Icon(Icons.shield_outlined),
                label: const Text('Club Management'),
              ),
              FilledButton.tonalIcon(
                onPressed: onOpenNationalTeam,
                icon: const Icon(Icons.flag_outlined),
                label: const Text('National Team'),
              ),
              FilledButton.tonalIcon(
                onPressed: onOpenTasks,
                icon: const Icon(Icons.task_alt_outlined),
                label: const Text('Daily Tasks'),
              ),
            ],
          ),
          const SizedBox(height: 18),
          Text('Activity feed', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 12),
          ...data.profileFeed.map(
            (GtexActivityFeedItem item) => Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: GteSurfacePanel(
                accentColor: tokens.accentClub,
                child: Row(
                  children: <Widget>[
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(
                            item.body,
                            style: Theme.of(context).textTheme.bodyLarge,
                          ),
                          const SizedBox(height: 6),
                          Text(
                            item.timeLabel,
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _RegensWorldView extends StatelessWidget {
  const _RegensWorldView({required this.data, required this.onOpenPlayer});

  final GtexUiUniverseData data;
  final ValueChanged<GtexPlayerCardData> onOpenPlayer;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final int columnCount =
            constraints.maxWidth >= 1180
                ? 3
                : constraints.maxWidth >= 760
                ? 2
                : 1;
        return GridView.builder(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 120),
          itemCount: data.trendingRegens.length,
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: columnCount,
            mainAxisExtent: 250,
            crossAxisSpacing: 14,
            mainAxisSpacing: 14,
          ),
          itemBuilder: (BuildContext context, int index) {
            final GtexPlayerCardData player = data.trendingRegens[index];
            return GtexRegenCard(
              player: player,
              onOpen: () => onOpenPlayer(player),
            );
          },
        );
      },
    );
  }
}

class _CompetitionsWorldView extends StatelessWidget {
  const _CompetitionsWorldView({
    required this.data,
    required this.onOpenTournament,
  });

  final GtexUiUniverseData data;
  final ValueChanged<GtexTournamentCardData> onOpenTournament;

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 120),
      itemCount: data.tournaments.length,
      separatorBuilder: (_, __) => const SizedBox(height: 14),
      itemBuilder: (BuildContext context, int index) {
        final GtexTournamentCardData tournament = data.tournaments[index];
        return GtexTournamentCard(
          tournament: tournament,
          onJoin: () => onOpenTournament(tournament),
        );
      },
    );
  }
}

class _FederationsWorldView extends StatelessWidget {
  const _FederationsWorldView({required this.data});

  final GtexUiUniverseData data;

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 120),
      itemCount: data.federations.length,
      separatorBuilder: (_, __) => const SizedBox(height: 14),
      itemBuilder: (BuildContext context, int index) {
        final GtexFederationCardData federation = data.federations[index];
        return GtexFederationCard(
          federation: federation,
          onJoin: () {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text('Joined ${federation.name}.')),
            );
          },
        );
      },
    );
  }
}

class _HistoryWorldView extends StatelessWidget {
  const _HistoryWorldView({required this.data});

  final GtexUiUniverseData data;

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 120),
      itemCount: data.historyRecords.length,
      separatorBuilder: (_, __) => const SizedBox(height: 14),
      itemBuilder:
          (BuildContext context, int index) =>
              GtexRecordCard(record: data.historyRecords[index]),
    );
  }
}

class _UserClubCard extends StatelessWidget {
  const _UserClubCard({required this.data, required this.onOpenClub});

  final GtexUiUniverseData data;
  final VoidCallback onOpenClub;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return GteSurfacePanel(
      emphasized: true,
      accentColor: tokens.accentClub,
      child: Row(
        children: <Widget>[
          GtexAnimatedAvatar(
            label: data.club.name,
            size: 82,
            accent: tokens.accentClub,
            badges: const <String>['🏟️'],
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  data.club.name,
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const SizedBox(height: 6),
                Text(
                  'League position #${data.club.leaguePosition} • ${data.club.regionLabel}',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: 10),
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: <Widget>[
                    GtexMetricPill(
                      label: 'Fan sentiment',
                      value:
                          '${data.club.fanSentiment}% ${data.club.sentimentEmoji}',
                      icon: Icons.sentiment_satisfied_alt_outlined,
                      color: tokens.accentWarm,
                    ),
                    GtexMetricPill(
                      label: 'Points',
                      value: '${data.club.points}',
                      icon: Icons.emoji_events_outlined,
                      color: tokens.accentArena,
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(width: 16),
          FilledButton.tonal(
            onPressed: onOpenClub,
            child: const Text('Manage'),
          ),
        ],
      ),
    );
  }
}

class _NextActionRecommendationCard extends StatelessWidget {
  const _NextActionRecommendationCard({
    required this.data,
    required this.onOpenMarket,
    required this.onOpenMatch,
  });

  final GtexUiUniverseData data;
  final VoidCallback onOpenMarket;
  final VoidCallback onOpenMatch;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final GtexPlayerCardData topRegen = data.trendingRegens.first;
    return GteSurfacePanel(
      accentColor: tokens.accentArena,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              GtexBadgeIcon(
                label: 'COMMAND CENTER AI',
                color: tokens.accentArena,
              ),
              const Spacer(),
              Text(
                'WHAT TO DO NEXT',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: tokens.accentArena,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            'Prospect Alert: ${topRegen.name} (${topRegen.potential} POT)',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 6),
          Text(
            'Your scouting network flagged a high-trajectory Regen in ${topRegen.country}. Next match kicks off shortly.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: <Widget>[
              FilledButton.icon(
                onPressed: onOpenMarket,
                icon: const Icon(Icons.flash_on_rounded),
                label: const Text('Scout Prospect'),
              ),
              OutlinedButton.icon(
                onPressed: onOpenMatch,
                icon: const Icon(Icons.sports_soccer_rounded),
                label: const Text('Enter Matchday'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _MarketPulsePanel extends StatelessWidget {
  const _MarketPulsePanel({required this.data, required this.onOpenMarket});

  final GtexUiUniverseData data;
  final VoidCallback onOpenMarket;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return GteSurfacePanel(
      accentColor: tokens.accentCapital,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Text(
                'Market Pulse',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const Spacer(),
              TextButton(
                onPressed: onOpenMarket,
                child: const Text('View Exchange'),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              GtexMetricPill(
                label: 'Top Riser',
                value: '+14.2% (Victor O.)',
                icon: Icons.trending_up_rounded,
                color: Colors.green,
              ),
              GtexMetricPill(
                label: 'High Liquidity',
                value: '18 active books',
                icon: Icons.water_drop_outlined,
                color: tokens.accentCapital,
              ),
              GtexMetricPill(
                label: 'Market Volume',
                value: '4.8M GTEX',
                icon: Icons.bar_chart_rounded,
                color: tokens.accentWarm,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _QuickActionsRow extends StatelessWidget {
  const _QuickActionsRow({
    required this.onOpenMatch,
    required this.onOpenMarket,
    required this.onOpenAcademy,
    required this.onOpenCompetitions,
  });

  final VoidCallback onOpenMatch;
  final VoidCallback onOpenMarket;
  final VoidCallback onOpenAcademy;
  final VoidCallback onOpenCompetitions;

  @override
  Widget build(BuildContext context) {
    final List<_QuickActionData> actions = <_QuickActionData>[
      _QuickActionData('Play Match', Icons.play_arrow_rounded, onOpenMatch),
      _QuickActionData('Transfers', Icons.swap_horiz_rounded, onOpenMarket),
      _QuickActionData('Academy', Icons.school_outlined, onOpenAcademy),
      _QuickActionData(
        'Competitions',
        Icons.emoji_events_outlined,
        onOpenCompetitions,
      ),
    ];
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final int columnCount = constraints.maxWidth >= 960 ? 4 : 2;
        return GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: actions.length,
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: columnCount,
            mainAxisExtent: 84,
            crossAxisSpacing: 12,
            mainAxisSpacing: 12,
          ),
          itemBuilder: (BuildContext context, int index) {
            final _QuickActionData action = actions[index];
            return GteSurfacePanel(
              accentColor: gtexAccentForIndex(context, index),
              onTap: action.onTap,
              padding: const EdgeInsets.all(14),
              child: Row(
                children: <Widget>[
                  Icon(action.icon, color: gtexAccentForIndex(context, index)),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      action.label,
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }
}

class _EconomySignalPanel extends StatelessWidget {
  const _EconomySignalPanel({required this.data});

  final GtexUiUniverseData data;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final int freeMatches =
        data.liveMatches
            .where((GtexLiveMatchData match) => match.matchType.isFree)
            .length;
    final int paidMatches = data.liveMatches.length - freeMatches;
    return GteSurfacePanel(
      accentColor: tokens.accentCapital,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Economy lane', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 10),
          Text(
            'This board should always tell the player whether they are paying or playing free.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              GtexMetricPill(
                label: 'Wallet',
                value: '${data.coins} GTex',
                icon: Icons.account_balance_wallet_outlined,
                color: tokens.accentCapital,
              ),
              GtexMetricPill(
                label: 'Free comps',
                value: '$freeMatches live',
                icon: Icons.celebration_outlined,
                color: Colors.green,
              ),
              GtexMetricPill(
                label: 'Paid lanes',
                value: '$paidMatches active',
                icon: Icons.payments_outlined,
                color: tokens.accentWarm,
              ),
            ],
          ),
          const SizedBox(height: 14),
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(18),
              color: Colors.green.withValues(alpha: 0.10),
              border: Border.all(color: Colors.green.withValues(alpha: 0.28)),
            ),
            child: Text(
              'GTEX competitions are FREE. Win real money. User matches require entry fees.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ),
        ],
      ),
    );
  }
}

class _LiveMatchCard extends StatelessWidget {
  const _LiveMatchCard({required this.match, required this.onOpen});

  final GtexLiveMatchData match;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      accentColor: _matchTypeAccent(context, match.matchType),
      onTap: onOpen,
      child: SingleChildScrollView(
        physics: const NeverScrollableScrollPhysics(),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Row(
              children: <Widget>[
                GtexBadgeIcon(
                  label: match.stageLabel,
                  color: GteShellTheme.tokensOf(context).accentArena,
                ),
                const SizedBox(width: 8),
                GtexBadgeIcon(
                  label: _entryLabel(match),
                  color: _matchTypeAccent(context, match.matchType),
                ),
                const Spacer(),
                Text(
                  '${match.minute}\'',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              '${match.homeClub} ${match.homeScore} - ${match.awayScore} ${match.awayClub}',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 6),
            Text(
              match.commentaryLine,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 12),
            Text(
              match.matchType.walletNotice,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: _matchTypeAccent(context, match.matchType),
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 12),
            Text(
              'xG ${match.xgHome.toStringAsFixed(1)}-${match.xgAway.toStringAsFixed(1)} • Shots ${match.shotsHome}-${match.shotsAway}',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
      ),
    );
  }
}

void _showGiftingModal(BuildContext context, GtexUiUniverseData data) {
  final TextEditingController recipientController = TextEditingController();
  final TextEditingController amountController = TextEditingController(text: '500');
  showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    builder: (BuildContext context) {
      return Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.viewInsetsOf(context).bottom,
        ),
        child: GtexModalSheet(
          title: 'Gift GTEX Assets or Coins',
          subtitle: 'Send player contracts or GTEX coins directly to another manager in your federation.',
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              TextField(
                controller: recipientController,
                decoration: const InputDecoration(
                  labelText: 'Recipient Tag or Email',
                  hintText: 'e.g. manager_alex@gtex.io',
                  prefixIcon: Icon(Icons.person_outline_rounded),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: amountController,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'GTEX Coins Amount',
                  prefixText: 'CR ',
                ),
              ),
              const SizedBox(height: 18),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: () {
                    Navigator.of(context).pop();
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text(
                          'Gift of ${amountController.text} GTEX coins sent to ${recipientController.text.isEmpty ? "recipient" : recipientController.text}!',
                        ),
                      ),
                    );
                  },
                  icon: const Icon(Icons.card_giftcard_rounded),
                  label: const Text('Confirm & Send Gift'),
                ),
              ),
            ],
          ),
        ),
      );
    },
  );
}

class _QuickActionData {
  const _QuickActionData(this.label, this.icon, this.onTap);

  final String label;
  final IconData icon;
  final VoidCallback onTap;
}

String _entryLabel(GtexLiveMatchData match) {
  if (match.matchType.isFree) {
    return 'FREE ENTRY';
  }
  final String amount =
      match.entryFee == match.entryFee.roundToDouble()
          ? match.entryFee.toStringAsFixed(0)
          : match.entryFee.toStringAsFixed(1);
  return '$amount GTex';
}

Color _matchTypeAccent(BuildContext context, MatchType matchType) {
  final tokens = GteShellTheme.tokensOf(context);
  switch (matchType) {
    case MatchType.gtexHosted:
      return Colors.green;
    case MatchType.userHosted:
      return tokens.accentCapital;
    case MatchType.fastMatch:
      return tokens.accentWarm;
  }
}
