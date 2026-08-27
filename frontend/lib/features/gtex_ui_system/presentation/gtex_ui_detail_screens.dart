import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../../widgets/gte_shell_theme.dart';
import '../../../widgets/gte_surface_panel.dart';
import '../../../widgets/gtex_branding.dart';
import '../../../widgets/player_card_avatar.dart';
import '../data/gtex_ui_demo_data.dart';
import '../widgets/gtex_ui_primitives.dart';

class GtexMatchExperienceScreen extends StatefulWidget {
  const GtexMatchExperienceScreen({
    super.key,
    required this.match,
    this.onOpenBroadcast,
  });

  final GtexLiveMatchData match;
  final VoidCallback? onOpenBroadcast;

  @override
  State<GtexMatchExperienceScreen> createState() =>
      _GtexMatchExperienceScreenState();
}

class _GtexMatchExperienceScreenState extends State<GtexMatchExperienceScreen> {
  bool _showStats = true;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: Text('${widget.match.homeClub} vs ${widget.match.awayClub}'),
          actions: <Widget>[
            IconButton(
              tooltip: 'Broadcast view',
              onPressed: widget.onOpenBroadcast,
              icon: const Icon(Icons.live_tv_outlined),
            ),
            IconButton(
              tooltip: _showStats ? 'Hide stats' : 'Show stats',
              onPressed: () => setState(() => _showStats = !_showStats),
              icon: Icon(
                _showStats
                    ? Icons.keyboard_arrow_down_rounded
                    : Icons.keyboard_arrow_up_rounded,
              ),
            ),
          ],
        ),
        body: SafeArea(
          top: false,
          child: Stack(
            children: <Widget>[
              Positioned.fill(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
                  child: _MatchPitchScene(match: widget.match),
                ),
              ),
              Positioned(
                top: 18,
                left: 18,
                right: 18,
                child: GteSurfacePanel(
                  accentColor: tokens.accentArena,
                  padding: const EdgeInsets.all(14),
                  child: Row(
                    children: <Widget>[
                      Expanded(
                        child: _ScoreSide(
                          club: widget.match.homeClub,
                          score: widget.match.homeScore,
                          alignEnd: false,
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 16,
                          vertical: 12,
                        ),
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(18),
                          color: tokens.panelStrong.withValues(alpha: 0.82),
                        ),
                        child: Column(
                          children: <Widget>[
                            Text(
                              '${widget.match.minute}\'',
                              style: Theme.of(context)
                                  .textTheme
                                  .titleMedium
                                  ?.copyWith(color: tokens.accentArena),
                            ),
                            const SizedBox(height: 8),
                            SizedBox(
                              width: 140,
                              child: GtexStatBar(
                                label: 'Possession',
                                value:
                                    '${widget.match.possessionHome}-${100 - widget.match.possessionHome}',
                                progress: widget.match.possessionHome / 100,
                                color: tokens.accentArena,
                              ),
                            ),
                          ],
                        ),
                      ),
                      Expanded(
                        child: _ScoreSide(
                          club: widget.match.awayClub,
                          score: widget.match.awayScore,
                          alignEnd: true,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              Positioned(
                top: 126,
                right: 18,
                child: SizedBox(
                  width: 220,
                  child: GteSurfacePanel(
                    accentColor: tokens.accentClub,
                    padding: const EdgeInsets.all(14),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text('Highlight',
                            style: Theme.of(context).textTheme.labelLarge),
                        const SizedBox(height: 8),
                        Text(
                          widget.match.highlightPlayer,
                          style: Theme.of(context)
                              .textTheme
                              .titleMedium
                              ?.copyWith(color: tokens.accentClub),
                        ),
                        const SizedBox(height: 6),
                        Text(
                          widget.match.highlightSummary,
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              Positioned(
                left: 18,
                right: 18,
                bottom: 18,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: <Widget>[
                    AnimatedSlide(
                      duration: const Duration(milliseconds: 220),
                      offset: _showStats ? Offset.zero : const Offset(0, 0.28),
                      child: AnimatedOpacity(
                        duration: const Duration(milliseconds: 220),
                        opacity: _showStats ? 1 : 0,
                        child: IgnorePointer(
                          ignoring: !_showStats,
                          child: Padding(
                            padding: const EdgeInsets.only(bottom: 12),
                            child: GteSurfacePanel(
                              accentColor: tokens.accentArena,
                              padding: const EdgeInsets.all(16),
                              child: Row(
                                children: <Widget>[
                                  Expanded(
                                    child: GtexStatBar(
                                      label: 'xG',
                                      value:
                                          '${widget.match.xgHome.toStringAsFixed(1)} - ${widget.match.xgAway.toStringAsFixed(1)}',
                                      progress: widget.match.xgHome /
                                          math.max(
                                            0.1,
                                            widget.match.xgHome +
                                                widget.match.xgAway,
                                          ),
                                      color: tokens.accentArena,
                                    ),
                                  ),
                                  const SizedBox(width: 16),
                                  Expanded(
                                    child: GtexStatBar(
                                      label: 'Shots',
                                      value:
                                          '${widget.match.shotsHome} - ${widget.match.shotsAway}',
                                      progress: widget.match.shotsHome /
                                          math.max(
                                            1,
                                            widget.match.shotsHome +
                                                widget.match.shotsAway,
                                          ),
                                      color: tokens.accentClub,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                    GteSurfacePanel(
                      accentColor: tokens.accentWarm,
                      padding: const EdgeInsets.all(14),
                      child: Row(
                        children: <Widget>[
                          Icon(Icons.mic_none_rounded,
                              color: tokens.accentWarm),
                          const SizedBox(width: 12),
                          Expanded(
                            child: AnimatedSwitcher(
                              duration: const Duration(milliseconds: 260),
                              child: Text(
                                widget.match.commentaryLine,
                                key: ValueKey<String>(
                                  widget.match.commentaryLine,
                                ),
                                style: Theme.of(context)
                                    .textTheme
                                    .titleMedium
                                    ?.copyWith(color: tokens.textPrimary),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class GtexPlayerDetailScreen extends StatelessWidget {
  const GtexPlayerDetailScreen({
    super.key,
    required this.player,
  });

  final GtexPlayerCardData player;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final String trajectory =
        '${player.rating - 3} → ${player.rating} → ${player.potential} POT';

    return DefaultTabController(
      length: 4,
      child: Container(
        decoration: gteBackdropDecoration(),
        child: Scaffold(
          backgroundColor: Colors.transparent,
          appBar: AppBar(
            title: Text('${player.name} Asset Intelligence'),
            actions: <Widget>[
              IconButton(
                tooltip: 'Share Asset',
                onPressed: () {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text('Asset link for ${player.name} copied.'),
                    ),
                  );
                },
                icon: const Icon(Icons.share_outlined),
              ),
            ],
          ),
          body: SafeArea(
            top: false,
            child: Column(
              children: <Widget>[
                Padding(
                  padding: const EdgeInsets.fromLTRB(20, 12, 20, 0),
                  child: GteSurfacePanel(
                    emphasized: true,
                    accentColor: tokens.accentArena,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Row(
                          children: <Widget>[
                            const PlayerCardAvatar(avatar: null, size: 90),
                            const SizedBox(width: 18),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: <Widget>[
                                  Text(
                                    player.name,
                                    style: Theme.of(context)
                                        .textTheme
                                        .headlineSmall,
                                  ),
                                  const SizedBox(height: 6),
                                  Text(
                                    '${player.position} • ${player.clubName} • ${player.country} • Age ${player.age}',
                                    style:
                                        Theme.of(context).textTheme.bodyMedium,
                                  ),
                                  const SizedBox(height: 8),
                                  Container(
                                    padding: const EdgeInsets.symmetric(
                                      horizontal: 10,
                                      vertical: 4,
                                    ),
                                    decoration: BoxDecoration(
                                      borderRadius: BorderRadius.circular(12),
                                      color: tokens.accentArena.withValues(alpha: 0.16),
                                      border: Border.all(
                                        color: tokens.accentArena.withValues(alpha: 0.32),
                                      ),
                                    ),
                                    child: Text(
                                      'Trajectory: $trajectory',
                                      style: Theme.of(context)
                                          .textTheme
                                          .bodySmall
                                          ?.copyWith(
                                            color: tokens.accentArena,
                                            fontWeight: FontWeight.w700,
                                          ),
                                    ),
                                  ),
                                  const SizedBox(height: 10),
                                  Wrap(
                                    spacing: 8,
                                    runSpacing: 8,
                                    children: player.badges
                                        .map(
                                          (String badge) => GtexBadgeIcon(
                                            label: badge,
                                            color: tokens.accentArena,
                                          ),
                                        )
                                        .toList(growable: false),
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
                              label: 'OVR Rating',
                              value: '${player.rating}',
                              icon: Icons.star_outline_rounded,
                              color: tokens.accentArena,
                            ),
                            GtexMetricPill(
                              label: 'Potential',
                              value: '${player.potential}',
                              icon: Icons.auto_awesome_outlined,
                              color: tokens.accentCommunity,
                            ),
                            GtexMetricPill(
                              label: 'Market Price',
                              value: gtexCompactCurrency(player.price),
                              icon: Icons.payments_outlined,
                              color: tokens.accentCapital,
                            ),
                            GtexMetricPill(
                              label: 'Liquidity',
                              value: player.liquidityLabel,
                              icon: Icons.water_drop_outlined,
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
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(
                                      content: Text(
                                        'Order placed for ${player.name} at ${gtexCompactCurrency(player.price)}.',
                                      ),
                                    ),
                                  );
                                },
                                icon: const Icon(Icons.flash_on_rounded),
                                label: const Text('Buy Now'),
                              ),
                            ),
                            const SizedBox(width: 10),
                            OutlinedButton.icon(
                              onPressed: () {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  SnackBar(
                                    content: Text(
                                      '${player.name} added to your watchlist.',
                                    ),
                                  ),
                                );
                              },
                              icon: const Icon(Icons.star_border_rounded),
                              label: const Text('Watch'),
                            ),
                            const SizedBox(width: 10),
                            OutlinedButton.icon(
                              onPressed: () {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  SnackBar(
                                    content: Text(
                                      'Gifting flow initiated for ${player.name}.',
                                    ),
                                  ),
                                );
                              },
                              icon: const Icon(Icons.card_giftcard_rounded),
                              label: const Text('Gift'),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                const TabBar(
                  isScrollable: true,
                  tabs: <Tab>[
                    Tab(text: 'Stats & Radar'),
                    Tab(text: 'Story Arc'),
                    Tab(text: 'Career Path'),
                    Tab(text: 'Order Book'),
                  ],
                ),
                Expanded(
                  child: TabBarView(
                    children: <Widget>[
                      _StatsTab(player: player),
                      _TimelineTab(
                        title: 'Story Arc & Development',
                        items: player.storyMoments,
                        color: tokens.accentArena,
                      ),
                      _TimelineTab(
                        title: 'Career & Club History',
                        items: player.careerMoments,
                        color: tokens.accentClub,
                      ),
                      _OffersTab(player: player),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class GtexClubManagementScreen extends StatelessWidget {
  const GtexClubManagementScreen({
    super.key,
    required this.data,
  });

  final GtexUiUniverseData data;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final List<GtexPlayerCardData> squad =
        data.marketPlayers.take(math.min(11, data.marketPlayers.length)).toList(
              growable: false,
            );
    return DefaultTabController(
      length: 5,
      child: Container(
        decoration: gteBackdropDecoration(),
        child: Scaffold(
          backgroundColor: Colors.transparent,
          appBar: AppBar(
            title: Text('${data.club.name} Football Club Operations'),
            actions: <Widget>[
              IconButton(
                tooltip: 'Trade Club Shares',
                onPressed: () {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text('Club share order book opened for ${data.club.name}.'),
                    ),
                  );
                },
                icon: const Icon(Icons.show_chart_rounded),
              ),
            ],
          ),
          body: Column(
            children: <Widget>[
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 0),
                child: GteSurfacePanel(
                  emphasized: true,
                  accentColor: tokens.accentClub,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Row(
                        children: <Widget>[
                          GtexAnimatedAvatar(
                            label: data.club.name,
                            accent: tokens.accentClub,
                            size: 72,
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
                                  'League Position #${data.club.leaguePosition} • ${data.club.regionLabel} • ${data.club.points} pts',
                                  style: Theme.of(context).textTheme.bodyMedium,
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 14),
                      Wrap(
                        spacing: 12,
                        runSpacing: 12,
                        children: <Widget>[
                          GtexMetricPill(
                            label: 'Squad Rating',
                            value: '84 OVR',
                            icon: Icons.shield_outlined,
                            color: tokens.accentClub,
                          ),
                          GtexMetricPill(
                            label: 'Club Valuation',
                            value: '₦48.5M',
                            icon: Icons.account_balance_outlined,
                            color: tokens.accentCapital,
                          ),
                          GtexMetricPill(
                            label: 'Share Price',
                            value: '₦125.0 (+4.2%)',
                            icon: Icons.trending_up_rounded,
                            color: Colors.green,
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 12),
              const TabBar(
                isScrollable: true,
                tabs: <Tab>[
                  Tab(text: 'Squad'),
                  Tab(text: 'Academy & Regens'),
                  Tab(text: 'Club Shares'),
                  Tab(text: 'Finances'),
                  Tab(text: 'Identity'),
                ],
              ),
              Expanded(
                child: TabBarView(
                  children: <Widget>[
                    _ClubSquadTab(squad: squad),
                    _ClubAcademyTab(data: data),
                    _ClubSharesTab(data: data),
                    _ClubFinanceTab(data: data),
                    _ClubIdentityTab(data: data),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class GtexNationalTeamScreen extends StatefulWidget {
  const GtexNationalTeamScreen({
    super.key,
    required this.data,
  });

  final GtexUiUniverseData data;

  @override
  State<GtexNationalTeamScreen> createState() => _GtexNationalTeamScreenState();
}

class _GtexNationalTeamScreenState extends State<GtexNationalTeamScreen> {
  final Set<String> _selectedIds = <String>{};

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final List<GtexPlayerCardData> players = widget.data.marketPlayers;
    final double usedBudget = players
        .where((GtexPlayerCardData player) => _selectedIds.contains(player.id))
        .fold<double>(0, (double sum, GtexPlayerCardData player) {
      return sum + (player.rentalCost / 1000000);
    });
    final int freePicksLeft =
        math.max(0, widget.data.freeNationalTeamPicks - _selectedIds.length);
    final double remainingBudget =
        math.max(0, widget.data.nationalBudget - usedBudget);
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: const Text('National Team Builder'),
        ),
        body: Padding(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 20),
          child: Column(
            children: <Widget>[
              GteSurfacePanel(
                emphasized: true,
                accentColor: tokens.accentCommunity,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      children: <Widget>[
                        GtexMetricPill(
                          label: 'Budget',
                          value: '${remainingBudget.toStringAsFixed(1)}M left',
                          icon: Icons.account_balance_wallet_outlined,
                          color: tokens.accentCapital,
                        ),
                        GtexMetricPill(
                          label: 'Free picks',
                          value: '$freePicksLeft left',
                          icon: Icons.star_border_rounded,
                          color: tokens.accentCommunity,
                        ),
                        GtexMetricPill(
                          label: 'Squad size',
                          value: '${_selectedIds.length}/23',
                          icon: Icons.groups_outlined,
                          color: tokens.accentClub,
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    Text(
                      'Squad slots',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 10,
                      runSpacing: 10,
                      children: List<Widget>.generate(18, (int index) {
                        final bool isFilled = index < _selectedIds.length;
                        return Container(
                          width: 68,
                          height: 68,
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(16),
                            color: isFilled
                                ? tokens.accentCommunity.withValues(alpha: 0.14)
                                : tokens.panelStrong.withValues(alpha: 0.72),
                            border: Border.all(
                              color: isFilled
                                  ? tokens.accentCommunity
                                      .withValues(alpha: 0.34)
                                  : tokens.stroke.withValues(alpha: 0.72),
                            ),
                          ),
                          child: Center(
                            child: Text(
                              isFilled ? 'ON' : '${index + 1}',
                              style: Theme.of(context).textTheme.labelLarge,
                            ),
                          ),
                        );
                      }),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              Expanded(
                child: ListView.separated(
                  itemCount: players.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 12),
                  itemBuilder: (BuildContext context, int index) {
                    final GtexPlayerCardData player = players[index];
                    final bool isSelected = _selectedIds.contains(player.id);
                    final bool canAdd = _selectedIds.length < 23 &&
                        (remainingBudget >= (player.rentalCost / 1000000) ||
                            freePicksLeft > 0);
                    return GteSurfacePanel(
                      accentColor: isSelected
                          ? tokens.accentCommunity
                          : tokens.accentCapital,
                      padding: const EdgeInsets.all(14),
                      child: Row(
                        children: <Widget>[
                          const PlayerCardAvatar(avatar: null, size: 58),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: <Widget>[
                                Text(
                                  player.name,
                                  style:
                                      Theme.of(context).textTheme.titleMedium,
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  '${player.position} • Rental ${gtexCompactCurrency(player.rentalCost)}',
                                  style: Theme.of(context).textTheme.bodyMedium,
                                ),
                              ],
                            ),
                          ),
                          FilledButton.tonal(
                            onPressed: isSelected
                                ? () {
                                    setState(() {
                                      _selectedIds.remove(player.id);
                                    });
                                  }
                                : canAdd
                                    ? () {
                                        setState(() {
                                          _selectedIds.add(player.id);
                                        });
                                      }
                                    : null,
                            child: Text(isSelected ? 'Remove' : 'Add'),
                          ),
                        ],
                      ),
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class GtexTournamentIntroScreen extends StatelessWidget {
  const GtexTournamentIntroScreen({
    super.key,
    required this.tournament,
  });

  final GtexTournamentCardData tournament;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return Scaffold(
      body: Stack(
        fit: StackFit.expand,
        children: <Widget>[
          DecoratedBox(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: <Color>[
                  tokens.background,
                  tokens.accentArena.withValues(alpha: 0.84),
                  tokens.accent.withValues(alpha: 0.92),
                  tokens.panelElevated,
                ],
              ),
            ),
          ),
          Positioned.fill(
            child: DecoratedBox(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: <Color>[
                    Colors.transparent,
                    Colors.black.withValues(alpha: 0.30),
                    Colors.black.withValues(alpha: 0.46),
                  ],
                ),
              ),
            ),
          ),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  const GtexLogoMark(size: 48, compact: true),
                  const Spacer(),
                  Text(
                    tournament.themeLabel.toUpperCase(),
                    style: Theme.of(context).textTheme.labelLarge?.copyWith(
                          color: tokens.textInverse,
                          letterSpacing: 2,
                        ),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    tournament.name,
                    style: Theme.of(context).textTheme.displaySmall?.copyWith(
                          color: tokens.textInverse,
                        ),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    tournament.rewardLabel,
                    style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                          color: tokens.textInverse.withValues(alpha: 0.88),
                        ),
                  ),
                  const SizedBox(height: 24),
                  FilledButton.icon(
                    onPressed: () => Navigator.of(context).pop(),
                    icon: const Icon(Icons.play_arrow_rounded),
                    label: const Text('Start'),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class GtexBroadcastViewScreen extends StatelessWidget {
  const GtexBroadcastViewScreen({
    super.key,
    required this.match,
    required this.feed,
  });

  final GtexLiveMatchData match;
  final List<GtexActivityFeedItem> feed;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: const Text('Broadcast View'),
        ),
        body: Padding(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 20),
          child: LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              final bool stacked = constraints.maxWidth < 940;
              final Widget video = GteSurfacePanel(
                emphasized: true,
                accentColor: tokens.accentArena,
                child: AspectRatio(
                  aspectRatio: 16 / 9,
                  child: Stack(
                    fit: StackFit.expand,
                    children: <Widget>[
                      DecoratedBox(
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(28),
                          gradient: LinearGradient(
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                            colors: <Color>[
                              tokens.panelElevated,
                              tokens.accentArena.withValues(alpha: 0.45),
                              tokens.panelStrong,
                            ],
                          ),
                        ),
                      ),
                      Center(
                        child: Icon(
                          Icons.play_circle_fill_rounded,
                          size: 86,
                          color: Colors.white.withValues(alpha: 0.82),
                        ),
                      ),
                      Positioned(
                        left: 16,
                        right: 16,
                        bottom: 16,
                        child: Text(
                          '${match.homeClub} ${match.homeScore} - ${match.awayScore} ${match.awayClub}',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                      ),
                    ],
                  ),
                ),
              );
              final Widget side = Column(
                children: <Widget>[
                  Expanded(
                    child: GteSurfacePanel(
                      accentColor: tokens.accentCommunity,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(
                            'Live chat',
                            style: Theme.of(context).textTheme.titleLarge,
                          ),
                          const SizedBox(height: 12),
                          Expanded(
                            child: ListView.separated(
                              itemCount: feed.length,
                              separatorBuilder: (_, __) =>
                                  const SizedBox(height: 12),
                              itemBuilder: (BuildContext context, int index) {
                                final GtexActivityFeedItem item = feed[index];
                                return Container(
                                  padding: const EdgeInsets.all(12),
                                  decoration: BoxDecoration(
                                    borderRadius: BorderRadius.circular(16),
                                    color: tokens.panelStrong
                                        .withValues(alpha: 0.70),
                                  ),
                                  child: Text(
                                    item.body,
                                    style:
                                        Theme.of(context).textTheme.bodyMedium,
                                  ),
                                );
                              },
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 14),
                  GteSurfacePanel(
                    accentColor: tokens.accentClub,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          'Match stats',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        const SizedBox(height: 12),
                        GtexStatBar(
                          label: 'Possession',
                          value:
                              '${match.possessionHome}-${100 - match.possessionHome}',
                          progress: match.possessionHome / 100,
                          color: tokens.accentClub,
                        ),
                        const SizedBox(height: 12),
                        GtexStatBar(
                          label: 'Shots',
                          value: '${match.shotsHome}-${match.shotsAway}',
                          progress: match.shotsHome /
                              math.max(1, match.shotsHome + match.shotsAway),
                          color: tokens.accentArena,
                        ),
                      ],
                    ),
                  ),
                ],
              );
              if (stacked) {
                return Column(
                  children: <Widget>[
                    video,
                    const SizedBox(height: 14),
                    Expanded(child: side),
                  ],
                );
              }
              return Row(
                children: <Widget>[
                  Expanded(flex: 7, child: video),
                  const SizedBox(width: 14),
                  Expanded(flex: 4, child: side),
                ],
              );
            },
          ),
        ),
      ),
    );
  }
}

class GtexDailyTasksScreen extends StatelessWidget {
  const GtexDailyTasksScreen({
    super.key,
    required this.tasks,
    required this.onClaim,
  });

  final List<GtexTaskData> tasks;
  final ValueChanged<GtexTaskData> onClaim;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: const Text('Daily Tasks & Streak'),
        ),
        body: Padding(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 20),
          child: Column(
            children: <Widget>[
              GteSurfacePanel(
                emphasized: true,
                accentColor: tokens.accentCapital,
                child: Row(
                  children: <Widget>[
                    Container(
                      width: 74,
                      height: 74,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: tokens.accentCapital.withValues(alpha: 0.16),
                      ),
                      child: Icon(
                        Icons.local_fire_department_outlined,
                        size: 34,
                        color: tokens.accentCapital,
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(
                            '7-day streak',
                            style: Theme.of(context).textTheme.headlineSmall,
                          ),
                          const SizedBox(height: 6),
                          Text(
                            'Bonus multiplier: 1.5x',
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              Expanded(
                child: ListView.separated(
                  itemCount: tasks.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 12),
                  itemBuilder: (BuildContext context, int index) {
                    final GtexTaskData task = tasks[index];
                    return GteSurfacePanel(
                      accentColor: tokens.accentCapital,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(
                            task.title,
                            style: Theme.of(context).textTheme.titleMedium,
                          ),
                          const SizedBox(height: 8),
                          Text(
                            task.detail,
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                          const SizedBox(height: 12),
                          GtexStatBar(
                            label: 'Progress',
                            value: '${(task.progress * 100).round()}%',
                            progress: task.progress,
                            color: tokens.accentCapital,
                          ),
                          const SizedBox(height: 12),
                          Align(
                            alignment: Alignment.centerRight,
                            child: task.isClaimed
                                ? FilledButton.tonal(
                                    onPressed: null,
                                    child: const Text('Claimed'),
                                  )
                                : FilledButton(
                                    onPressed: () => onClaim(task),
                                    child: const Text('Claim'),
                                  ),
                          ),
                        ],
                      ),
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _StatsTab extends StatelessWidget {
  const _StatsTab({
    required this.player,
  });

  final GtexPlayerCardData player;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final List<MapEntry<String, int>> attributes =
        player.attributes.entries.toList(growable: false);
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 20),
      children: <Widget>[
        LayoutBuilder(
          builder: (BuildContext context, BoxConstraints constraints) {
            final bool stacked = constraints.maxWidth < 820;
            final Widget chart = GteSurfacePanel(
              accentColor: tokens.accentArena,
              child: Center(
                child: GtexRadarChart(
                  attributes: player.attributes,
                  color: tokens.accentArena,
                ),
              ),
            );
            final Widget metrics = GteSurfacePanel(
              accentColor: tokens.accentClub,
              child: Column(
                children: attributes
                    .map(
                      (MapEntry<String, int> entry) => Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: GtexStatBar(
                          label: entry.key,
                          value: '${entry.value}',
                          progress: entry.value / 100,
                          color: tokens.accentClub,
                        ),
                      ),
                    )
                    .toList(growable: false),
              ),
            );
            if (stacked) {
              return Column(
                children: <Widget>[
                  chart,
                  const SizedBox(height: 14),
                  metrics,
                ],
              );
            }
            return Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Expanded(child: chart),
                const SizedBox(width: 14),
                Expanded(child: metrics),
              ],
            );
          },
        ),
      ],
    );
  }
}

class _TimelineTab extends StatelessWidget {
  const _TimelineTab({
    required this.title,
    required this.items,
    required this.color,
  });

  final String title;
  final List<String> items;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 20),
      children: <Widget>[
        Text(title, style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 14),
        ...items.map(
          (String item) => GtexTimelineTile(
            title: item,
            subtitle:
                'This milestone changed how the GTEX world sees the player.',
            color: color,
          ),
        ),
      ],
    );
  }
}

class _OffersTab extends StatelessWidget {
  const _OffersTab({
    required this.player,
  });

  final GtexPlayerCardData player;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 20),
      children: player.offers
          .map(
            (GtexOfferData offer) => Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: GteSurfacePanel(
                accentColor: tokens.accentCapital,
                child: Row(
                  children: <Widget>[
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(
                            offer.title,
                            style: Theme.of(context).textTheme.titleMedium,
                          ),
                          const SizedBox(height: 6),
                          Text(
                            offer.valueLabel,
                            style: Theme.of(context)
                                .textTheme
                                .bodyLarge
                                ?.copyWith(color: tokens.accentCapital),
                          ),
                        ],
                      ),
                    ),
                    GtexBadgeIcon(
                      label: offer.status,
                      color: tokens.accentCapital,
                    ),
                  ],
                ),
              ),
            ),
          )
          .toList(growable: false),
    );
  }
}

class _ClubSquadTab extends StatelessWidget {
  const _ClubSquadTab({
    required this.squad,
  });

  final List<GtexPlayerCardData> squad;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final List<String> labels = <String>[
      'GK',
      'LB',
      'CB',
      'CB',
      'RB',
      'CM',
      'CM',
      'AM',
      'LW',
      'ST',
      'RW',
    ];
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 20),
      children: <Widget>[
        AspectRatio(
          aspectRatio: 1.1,
          child: GteSurfacePanel(
            accentColor: tokens.accentClub,
            child: Stack(
              children: List<Widget>.generate(labels.length, (int index) {
                final GtexPlayerCardData player = squad[index % squad.length];
                final Offset position = _formationPosition(index);
                return Positioned(
                  left: position.dx,
                  top: position.dy,
                  child: Column(
                    children: <Widget>[
                      Stack(
                        alignment: Alignment.center,
                        children: <Widget>[
                          const PlayerCardAvatar(avatar: null, size: 44),
                          Text(
                            labels[index],
                            style: Theme.of(context)
                                .textTheme
                                .labelSmall
                                ?.copyWith(
                                  color: tokens.accentClub,
                                  fontWeight: FontWeight.w900,
                                ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      SizedBox(
                        width: 92,
                        child: Text(
                          player.name,
                          maxLines: 2,
                          textAlign: TextAlign.center,
                          overflow: TextOverflow.ellipsis,
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ),
                    ],
                  ),
                );
              }),
            ),
          ),
        ),
        const SizedBox(height: 16),
        Text(
          'Drag and drop squad planning',
          style: Theme.of(context).textTheme.titleLarge,
        ),
        const SizedBox(height: 10),
        ...squad.map(
          (GtexPlayerCardData player) => Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: GteSurfacePanel(
              accentColor: tokens.accentClub,
              padding: const EdgeInsets.all(14),
              child: Row(
                children: <Widget>[
                  const PlayerCardAvatar(avatar: null, size: 54),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          player.name,
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 4),
                        Text(
                          '${player.position} • ${player.rating} OVR',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                      ],
                    ),
                  ),
                  const Icon(Icons.drag_indicator_rounded),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }

  Offset _formationPosition(int index) {
    const List<Offset> positions = <Offset>[
      Offset(128, 240),
      Offset(26, 180),
      Offset(92, 162),
      Offset(164, 162),
      Offset(228, 180),
      Offset(66, 110),
      Offset(130, 102),
      Offset(194, 110),
      Offset(36, 38),
      Offset(128, 24),
      Offset(222, 38),
    ];
    return positions[index];
  }
}

class _ClubFinanceTab extends StatelessWidget {
  const _ClubFinanceTab({
    required this.data,
  });

  final GtexUiUniverseData data;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 20),
      children: <Widget>[
        GteSurfacePanel(
          emphasized: true,
          accentColor: tokens.accentCapital,
          child: Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              GtexMetricPill(
                label: 'Balance',
                value: '${data.coins} coins',
                icon: Icons.account_balance_wallet_outlined,
                color: tokens.accentCapital,
              ),
              GtexMetricPill(
                label: 'Income lanes',
                value: '${data.incomeStreams.length}',
                icon: Icons.north_east_rounded,
                color: tokens.accentCommunity,
              ),
              GtexMetricPill(
                label: 'Expense lanes',
                value: '${data.expenseStreams.length}',
                icon: Icons.south_east_rounded,
                color: tokens.negative,
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        GteSurfacePanel(
          accentColor: tokens.accentCommunity,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('Income streams',
                  style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 12),
              ...data.incomeStreams.map(
                (GtexFinanceMetric metric) => Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: GtexStatBar(
                    label: metric.label,
                    value: '${metric.value.toStringAsFixed(1)}M',
                    progress: metric.progress,
                    color: tokens.accentCommunity,
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        GteSurfacePanel(
          accentColor: tokens.negative,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('Expenses chart',
                  style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 12),
              ...data.expenseStreams.map(
                (GtexFinanceMetric metric) => Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: GtexStatBar(
                    label: metric.label,
                    value: '${metric.value.toStringAsFixed(1)}M',
                    progress: metric.progress,
                    color: tokens.negative,
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _ClubFansTab extends StatelessWidget {
  const _ClubFansTab({
    required this.data,
  });

  final GtexUiUniverseData data;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 20),
      children: <Widget>[
        GteSurfacePanel(
          accentColor: tokens.accentWarm,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('Fan sentiment meter',
                  style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 12),
              GtexStatBar(
                label: 'Sentiment',
                value: '${data.club.fanSentiment}% ${data.club.sentimentEmoji}',
                progress: data.club.fanSentiment / 100,
                color: tokens.accentWarm,
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        ...data.fanReactions.map(
          (GtexFanReactionData reaction) => Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: GteSurfacePanel(
              accentColor: tokens.accentWarm,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    reaction.author,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 6),
                  Text(
                    reaction.body,
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _ClubAcademyTab extends StatelessWidget {
  const _ClubAcademyTab({
    required this.data,
  });

  final GtexUiUniverseData data;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final List<GtexPlayerCardData> prospects = data.trendingRegens;
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 20),
      children: <Widget>[
        GteSurfacePanel(
          emphasized: true,
          accentColor: tokens.accentArena,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Youth Academy & Regen Pipeline',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 8),
              Text(
                'Develop local talent and uncover high-potential Regens before they hit the open market.',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 14),
              GtexStatBar(
                label: 'Academy Capacity',
                value: '14 / 20 Prospects',
                progress: 0.70,
                color: tokens.accentArena,
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        Text(
          'Top Academy Prospects',
          style: Theme.of(context).textTheme.titleLarge,
        ),
        const SizedBox(height: 12),
        ...prospects.map(
          (GtexPlayerCardData player) => Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: GteSurfacePanel(
              accentColor: tokens.accentArena,
              child: Row(
                children: <Widget>[
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          player.name,
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 4),
                        Text(
                          '${player.position} • Age ${player.age} • Potential ${player.potential}',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                      ],
                    ),
                  ),
                  FilledButton.tonal(
                    onPressed: () {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text(
                            '${player.name} promoted to First Team squad!',
                          ),
                        ),
                      );
                    },
                    child: const Text('Promote'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _ClubSharesTab extends StatelessWidget {
  const _ClubSharesTab({
    required this.data,
  });

  final GtexUiUniverseData data;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 20),
      children: <Widget>[
        GteSurfacePanel(
          emphasized: true,
          accentColor: tokens.accentCapital,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Club Share Market & Equity',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 12,
                runSpacing: 12,
                children: <Widget>[
                  GtexMetricPill(
                    label: 'Share Price',
                    value: '₦125.0',
                    icon: Icons.show_chart_rounded,
                    color: tokens.accentCapital,
                  ),
                  GtexMetricPill(
                    label: '24h Change',
                    value: '+4.2%',
                    icon: Icons.trending_up_rounded,
                    color: Colors.green,
                  ),
                  GtexMetricPill(
                    label: 'Shares Issued',
                    value: '100,000',
                    icon: Icons.pie_chart_outline_rounded,
                    color: tokens.accentCommunity,
                  ),
                ],
              ),
              const SizedBox(height: 16),
              Row(
                children: <Widget>[
                  Expanded(
                    child: FilledButton.icon(
                      onPressed: () {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text('Buy order submitted for 100 shares.'),
                          ),
                        );
                      },
                      icon: const Icon(Icons.add_shopping_cart_rounded),
                      label: const Text('Buy Shares'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: () {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text('Sell order submitted for 50 shares.'),
                          ),
                        );
                      },
                      icon: const Icon(Icons.sell_outlined),
                      label: const Text('Sell Shares'),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _ClubIdentityTab extends StatelessWidget {
  const _ClubIdentityTab({
    required this.data,
  });

  final GtexUiUniverseData data;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 20),
      children: <Widget>[
        GteSurfacePanel(
          accentColor: tokens.accentClub,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('Philosophy', style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 8),
              Text(
                'Build fast wide attackers, defend aggressively in midfield, and keep the badge visually loud.',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        GteSurfacePanel(
          accentColor: tokens.accentCommunity,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('Culture score',
                  style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 12),
              GtexStatBar(
                label: 'Identity cohesion',
                value: '91',
                progress: 0.91,
                color: tokens.accentCommunity,
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        GteSurfacePanel(
          accentColor: tokens.accentArena,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('Tactical style',
                  style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 8),
              Text(
                'High press 4-3-3 with inverted fullbacks and front-foot transitions.',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _MatchPitchScene extends StatelessWidget {
  const _MatchPitchScene({
    required this.match,
  });

  final GtexLiveMatchData match;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return ClipRRect(
      borderRadius: BorderRadius.circular(32),
      child: DecoratedBox(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: <Color>[
              const Color(0xFF143C2C),
              const Color(0xFF0E2D22),
              tokens.background,
            ],
          ),
        ),
        child: Stack(
          children: <Widget>[
            Positioned.fill(
              child: CustomPaint(
                painter: _PitchPainter(
                  lineColor: Colors.white.withValues(alpha: 0.26),
                ),
              ),
            ),
            ..._buildPlayers(tokens.accentClub, const <Offset>[
              Offset(0.16, 0.76),
              Offset(0.24, 0.56),
              Offset(0.34, 0.66),
              Offset(0.45, 0.50),
              Offset(0.25, 0.34),
            ]),
            ..._buildPlayers(tokens.accentArena, const <Offset>[
              Offset(0.72, 0.18),
              Offset(0.66, 0.38),
              Offset(0.58, 0.24),
              Offset(0.54, 0.60),
              Offset(0.78, 0.48),
            ]),
            Align(
              alignment: const Alignment(-0.05, 0.1),
              child: Container(
                width: 16,
                height: 16,
                decoration: const BoxDecoration(
                  shape: BoxShape.circle,
                  color: Colors.white,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  List<Widget> _buildPlayers(Color color, List<Offset> positions) {
    return positions
        .map(
          (Offset offset) => Align(
            alignment: Alignment((offset.dx * 2) - 1, (offset.dy * 2) - 1),
            child: Container(
              width: 26,
              height: 26,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: color,
                boxShadow: <BoxShadow>[
                  BoxShadow(
                    color: color.withValues(alpha: 0.32),
                    blurRadius: 16,
                    spreadRadius: 2,
                  ),
                ],
              ),
            ),
          ),
        )
        .toList(growable: false);
  }
}

class _PitchPainter extends CustomPainter {
  _PitchPainter({required this.lineColor});

  final Color lineColor;

  @override
  void paint(Canvas canvas, Size size) {
    final Paint paint = Paint()
      ..color = lineColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2;
    canvas.drawRect(
      Rect.fromLTWH(18, 18, size.width - 36, size.height - 36),
      paint,
    );
    canvas.drawLine(
      Offset(size.width / 2, 18),
      Offset(size.width / 2, size.height - 18),
      paint,
    );
    canvas.drawCircle(
      Offset(size.width / 2, size.height / 2),
      50,
      paint,
    );
  }

  @override
  bool shouldRepaint(covariant _PitchPainter oldDelegate) {
    return oldDelegate.lineColor != lineColor;
  }
}

class _ScoreSide extends StatelessWidget {
  const _ScoreSide({
    required this.club,
    required this.score,
    required this.alignEnd,
  });

  final String club;
  final int score;
  final bool alignEnd;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment:
          alignEnd ? CrossAxisAlignment.end : CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          club,
          textAlign: alignEnd ? TextAlign.right : TextAlign.left,
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 4),
        Text(
          '$score',
          style: Theme.of(context).textTheme.displaySmall,
        ),
      ],
    );
  }
}
