import 'package:flutter/material.dart';

import '../../core/constants/app_breakpoints.dart';
import '../../core/constants/app_spacing.dart';
import '../../core/theme/app_colors.dart';
import '../../core/widgets/gtex_surface_card.dart';
import '../../core/widgets/player_card.dart';
import '../../shared/models/competition.dart';
import '../../shared/models/player.dart';
import '../../shared/widgets/app_background.dart';
import '../../shared/widgets/metric_pill.dart';
import 'tournament_models.dart';

class TournamentScreen extends StatefulWidget {
  const TournamentScreen({
    super.key,
    required this.competition,
    this.fixtures,
    this.standings,
    this.squad,
    this.allowFixtureData = false,
  });

  final Competition competition;
  final List<TournamentFixture>? fixtures;
  final List<TournamentStanding>? standings;
  final List<Player>? squad;
  final bool allowFixtureData;

  @override
  State<TournamentScreen> createState() => _TournamentScreenState();
}

class _TournamentScreenState extends State<TournamentScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final List<TournamentFixture> fixtures =
        widget.fixtures ??
        (widget.allowFixtureData
            ? buildTournamentFixtures(widget.competition)
            : const <TournamentFixture>[]);
    final List<TournamentStanding> standings =
        widget.standings ??
        (widget.allowFixtureData
            ? buildTournamentStandings(widget.competition)
            : const <TournamentStanding>[]);
    final List<Player> squad = widget.squad ?? const <Player>[];
    final List<Player> resolvedSquad =
        squad.isEmpty && widget.allowFixtureData
            ? buildTournamentSquad(const <Player>[])
            : squad;

    if (fixtures.isEmpty || standings.isEmpty) {
      return AppBackground(
        child: Scaffold(
          backgroundColor: Colors.transparent,
          appBar: AppBar(title: Text(widget.competition.name)),
          body: const SafeArea(child: _TournamentBlockedState()),
        ),
      );
    }

    return AppBackground(
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(title: Text(widget.competition.name)),
        body: SafeArea(
          top: false,
          child: NestedScrollView(
            physics: const BouncingScrollPhysics(
              parent: AlwaysScrollableScrollPhysics(),
            ),
            headerSliverBuilder: (
              BuildContext context,
              bool innerBoxIsScrolled,
            ) {
              return <Widget>[
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(
                      spacingLG,
                      spacingLG,
                      spacingLG,
                      spacingLG,
                    ),
                    child: _TournamentHeroCard(
                      competition: widget.competition,
                      fixtures: fixtures,
                      standings: standings,
                    ),
                  ),
                ),
                SliverPersistentHeader(
                  pinned: true,
                  delegate: _StickyTournamentTabs(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(
                        spacingLG,
                        0,
                        spacingLG,
                        spacingMD,
                      ),
                      child: _TournamentTabBar(controller: _tabController),
                    ),
                  ),
                ),
              ];
            },
            body: Padding(
              padding: const EdgeInsets.symmetric(horizontal: spacingLG),
              child: TabBarView(
                controller: _tabController,
                physics: const BouncingScrollPhysics(
                  parent: AlwaysScrollableScrollPhysics(),
                ),
                children: <Widget>[
                  _FixturesTab(fixtures: fixtures),
                  _StandingsTab(standings: standings),
                  _SquadTab(squad: resolvedSquad),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _TournamentBlockedState extends StatelessWidget {
  const _TournamentBlockedState();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 560),
        child: Padding(
          padding: const EdgeInsets.all(spacingLG),
          child: GtexSurfaceCard(
            glowColor: AppColors.gold,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  'Live tournament unavailable',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: spacingSM),
                Text(
                  'Fixtures and standings must come from persisted Competition OS authority before this tournament can render.',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: AppColors.textSecondary,
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

class _TournamentHeroCard extends StatelessWidget {
  const _TournamentHeroCard({
    required this.competition,
    required this.fixtures,
    required this.standings,
  });

  final Competition competition;
  final List<TournamentFixture> fixtures;
  final List<TournamentStanding> standings;

  @override
  Widget build(BuildContext context) {
    final TournamentFixture feature = fixtures.first;

    return GtexSurfaceCard(
      glowColor: AppColors.primary,
      padding: EdgeInsets.zero,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(cardRadius),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Container(
              padding: const EdgeInsets.all(spacingLG),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: <Color>[
                    AppColors.primary.withValues(alpha: 0.24),
                    AppColors.gold.withValues(alpha: 0.16),
                    AppColors.surfaceMuted,
                  ],
                ),
              ),
              child: LayoutBuilder(
                builder: (BuildContext context, BoxConstraints constraints) {
                  final bool wide =
                      constraints.maxWidth >= AppBreakpoints.medium;
                  final Widget eventInfo = Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Wrap(
                        spacing: spacingSM,
                        runSpacing: spacingSM,
                        children: <Widget>[
                          MetricPill(
                            label: 'Region',
                            value: competition.region,
                            highlight: true,
                          ),
                          MetricPill(label: 'Stage', value: competition.stage),
                        ],
                      ),
                      const SizedBox(height: spacingLG),
                      Text(
                        competition.name,
                        style: Theme.of(context).textTheme.headlineMedium,
                      ),
                      const SizedBox(height: spacingSM),
                      Text(
                        competition.spotlight,
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: AppColors.textSecondary,
                        ),
                      ),
                    ],
                  );

                  final Widget featurePanel = Container(
                    width: wide ? 300 : double.infinity,
                    padding: const EdgeInsets.all(spacingMD),
                    decoration: BoxDecoration(
                      color: AppColors.card.withValues(alpha: 0.7),
                      borderRadius: BorderRadius.circular(cardRadius),
                      border: Border.all(color: AppColors.divider),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          'Feature Match',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                        const SizedBox(height: spacingSM),
                        Text(
                          '${feature.homeClub} vs ${feature.awayClub}',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        const SizedBox(height: spacingXS),
                        Text(feature.kickoffLabel),
                        const SizedBox(height: spacingMD),
                        Text(
                          'Group leader ${standings.first.club}',
                          style: Theme.of(context).textTheme.bodySmall
                              ?.copyWith(color: AppColors.gold),
                        ),
                      ],
                    ),
                  );

                  if (wide) {
                    return Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Expanded(child: eventInfo),
                        const SizedBox(width: spacingLG),
                        featurePanel,
                      ],
                    );
                  }

                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      eventInfo,
                      const SizedBox(height: spacingLG),
                      featurePanel,
                    ],
                  );
                },
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(spacingMD),
              child: Wrap(
                spacing: spacingMD,
                runSpacing: spacingMD,
                children: <Widget>[
                  _HeroMetric(
                    label: 'Fixtures',
                    value: '${fixtures.length}',
                    color: AppColors.primary,
                  ),
                  _HeroMetric(
                    label: 'Clubs',
                    value: '${standings.length}',
                    color: AppColors.gold,
                  ),
                  _HeroMetric(
                    label: 'Broadcast',
                    value: 'Cinematic',
                    color: AppColors.textPrimary,
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

class _TournamentTabBar extends StatelessWidget {
  const _TournamentTabBar({required this.controller});

  final TabController controller;

  @override
  Widget build(BuildContext context) {
    final bool isScrollable =
        MediaQuery.sizeOf(context).width < AppBreakpoints.compact;

    return Container(
      padding: const EdgeInsets.all(spacingSM),
      decoration: BoxDecoration(
        color: AppColors.card.withValues(alpha: 0.94),
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: AppColors.divider),
      ),
      child: TabBar(
        controller: controller,
        isScrollable: isScrollable,
        tabAlignment: isScrollable ? TabAlignment.start : TabAlignment.fill,
        dividerColor: Colors.transparent,
        indicator: BoxDecoration(
          borderRadius: BorderRadius.circular(18),
          gradient: LinearGradient(
            colors: <Color>[
              AppColors.primary.withValues(alpha: 0.18),
              AppColors.gold.withValues(alpha: 0.1),
            ],
          ),
          border: Border.all(color: AppColors.primary.withValues(alpha: 0.24)),
        ),
        labelColor: AppColors.textPrimary,
        unselectedLabelColor: AppColors.textSecondary,
        tabs: const <Tab>[
          Tab(key: Key('tournament-tab-fixtures'), text: 'Fixtures'),
          Tab(key: Key('tournament-tab-standings'), text: 'Standings'),
          Tab(key: Key('tournament-tab-squad'), text: 'Squad'),
        ],
      ),
    );
  }
}

class _FixturesTab extends StatelessWidget {
  const _FixturesTab({required this.fixtures});

  final List<TournamentFixture> fixtures;

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      key: const Key('tournament-fixtures-view'),
      padding: EdgeInsets.only(
        bottom: MediaQuery.paddingOf(context).bottom + 88,
      ),
      physics: const BouncingScrollPhysics(
        parent: AlwaysScrollableScrollPhysics(),
      ),
      itemCount: fixtures.length,
      separatorBuilder: (_, _) => const SizedBox(height: spacingMD),
      itemBuilder: (BuildContext context, int index) {
        final TournamentFixture fixture = fixtures[index];
        final Color accent = switch (fixture.status) {
          TournamentFixtureStatus.live => AppColors.primary,
          TournamentFixtureStatus.complete => AppColors.gold,
          TournamentFixtureStatus.scheduled => AppColors.textPrimary,
        };

        return GtexSurfaceCard(
          key: Key('tournament-fixture-$index'),
          glowColor:
              fixture.status == TournamentFixtureStatus.live ? accent : null,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(
                children: <Widget>[
                  MetricPill(
                    label: 'Round',
                    value: fixture.roundLabel,
                    highlight: fixture.status == TournamentFixtureStatus.live,
                  ),
                  const Spacer(),
                  _StatusChip(status: fixture.status),
                ],
              ),
              const SizedBox(height: spacingMD),
              Row(
                children: <Widget>[
                  Expanded(
                    child: Text(
                      fixture.homeClub,
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: spacingMD),
                    child: Text(
                      fixture.homeScore == null || fixture.awayScore == null
                          ? 'vs'
                          : '${fixture.homeScore} - ${fixture.awayScore}',
                      style: Theme.of(
                        context,
                      ).textTheme.headlineSmall?.copyWith(color: accent),
                    ),
                  ),
                  Expanded(
                    child: Text(
                      fixture.awayClub,
                      textAlign: TextAlign.end,
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: spacingMD),
              Text(
                '${fixture.kickoffLabel} | ${fixture.venue}',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _StandingsTab extends StatelessWidget {
  const _StandingsTab({required this.standings});

  final List<TournamentStanding> standings;

  @override
  Widget build(BuildContext context) {
    return ListView(
      key: const Key('tournament-standings-view'),
      padding: EdgeInsets.only(
        bottom: MediaQuery.paddingOf(context).bottom + 88,
      ),
      physics: const BouncingScrollPhysics(
        parent: AlwaysScrollableScrollPhysics(),
      ),
      children: <Widget>[
        GtexSurfaceCard(
          glowColor: AppColors.gold,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('Standings', style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: spacingSM),
              Text(
                'Verified tournament table with group points and goal difference.',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: spacingMD),
        GtexSurfaceCard(
          child: Column(
            children: <Widget>[
              const _StandingHeaderRow(),
              const SizedBox(height: spacingSM),
              ...standings.asMap().entries.map(
                (MapEntry<int, TournamentStanding> entry) => Padding(
                  padding: const EdgeInsets.only(bottom: spacingSM),
                  child: _StandingRow(index: entry.key, standing: entry.value),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _SquadTab extends StatelessWidget {
  const _SquadTab({required this.squad});

  final List<Player> squad;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final int crossAxisCount =
            constraints.maxWidth >= AppBreakpoints.expanded
                ? 4
                : constraints.maxWidth >= AppBreakpoints.compact
                ? 3
                : 2;

        return GridView.builder(
          key: const Key('tournament-squad-view'),
          padding: EdgeInsets.only(
            bottom: MediaQuery.paddingOf(context).bottom + 88,
          ),
          physics: const BouncingScrollPhysics(
            parent: AlwaysScrollableScrollPhysics(),
          ),
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: crossAxisCount,
            crossAxisSpacing: spacingMD,
            mainAxisSpacing: spacingMD,
            childAspectRatio: 0.92,
          ),
          itemCount: squad.length,
          itemBuilder: (BuildContext context, int index) {
            final Player player = squad[index];
            return PlayerCard(
              name: player.name,
              rating: player.rating,
              image: player.image,
              position: player.position,
              country: player.country,
              valueInMillions: player.valueInMillions,
              highlighted: player.isHot,
            );
          },
        );
      },
    );
  }
}

class _StandingHeaderRow extends StatelessWidget {
  const _StandingHeaderRow();

  @override
  Widget build(BuildContext context) {
    final TextStyle? style = Theme.of(context).textTheme.bodySmall?.copyWith(
      color: AppColors.textSecondary,
      fontWeight: FontWeight.w700,
    );

    return Row(
      children: <Widget>[
        SizedBox(width: 28, child: Text('#', style: style)),
        const SizedBox(width: spacingSM),
        const Expanded(flex: 5, child: Text('Club')),
        SizedBox(
          width: 32,
          child: Text('P', textAlign: TextAlign.center, style: style),
        ),
        SizedBox(
          width: 32,
          child: Text('W', textAlign: TextAlign.center, style: style),
        ),
        SizedBox(
          width: 32,
          child: Text('D', textAlign: TextAlign.center, style: style),
        ),
        SizedBox(
          width: 32,
          child: Text('L', textAlign: TextAlign.center, style: style),
        ),
        SizedBox(
          width: 40,
          child: Text('GD', textAlign: TextAlign.center, style: style),
        ),
        SizedBox(
          width: 40,
          child: Text('PTS', textAlign: TextAlign.center, style: style),
        ),
      ],
    );
  }
}

class _StandingRow extends StatelessWidget {
  const _StandingRow({required this.index, required this.standing});

  final int index;
  final TournamentStanding standing;

  @override
  Widget build(BuildContext context) {
    final bool topSeed = index == 0;

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: spacingSM,
        vertical: spacingSM,
      ),
      decoration: BoxDecoration(
        color:
            topSeed
                ? AppColors.primary.withValues(alpha: 0.1)
                : AppColors.surfaceMuted.withValues(alpha: 0.72),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: topSeed ? AppColors.primary : AppColors.divider,
        ),
      ),
      child: Row(
        children: <Widget>[
          SizedBox(
            width: 28,
            child: Text(
              '${index + 1}',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: topSeed ? AppColors.primary : AppColors.textPrimary,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          const SizedBox(width: spacingSM),
          Expanded(
            flex: 5,
            child: Text(
              standing.club,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          _CellValue(value: '${standing.played}'),
          _CellValue(value: '${standing.won}'),
          _CellValue(value: '${standing.drawn}'),
          _CellValue(value: '${standing.lost}'),
          _CellValue(value: '${standing.goalDifference}'),
          _CellValue(value: '${standing.points}', highlight: true),
        ],
      ),
    );
  }
}

class _CellValue extends StatelessWidget {
  const _CellValue({required this.value, this.highlight = false});

  final String value;
  final bool highlight;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 36,
      child: Text(
        value,
        textAlign: TextAlign.center,
        style: Theme.of(context).textTheme.bodySmall?.copyWith(
          color: highlight ? AppColors.gold : AppColors.textPrimary,
          fontWeight: highlight ? FontWeight.w700 : FontWeight.w500,
        ),
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({required this.status});

  final TournamentFixtureStatus status;

  @override
  Widget build(BuildContext context) {
    final (String label, Color color) = switch (status) {
      TournamentFixtureStatus.live => ('Live', AppColors.primary),
      TournamentFixtureStatus.complete => ('Complete', AppColors.gold),
      TournamentFixtureStatus.scheduled => (
        'Scheduled',
        AppColors.textSecondary,
      ),
    };

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: spacingSM,
        vertical: spacingXS,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.bodySmall?.copyWith(
          color: color,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

class _HeroMetric extends StatelessWidget {
  const _HeroMetric({
    required this.label,
    required this.value,
    required this.color,
  });

  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 160,
      padding: const EdgeInsets.all(spacingMD),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(cardRadius),
        border: Border.all(color: color.withValues(alpha: 0.22)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(label, style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: spacingSM),
          Text(
            value,
            style: Theme.of(
              context,
            ).textTheme.titleLarge?.copyWith(color: color),
          ),
        ],
      ),
    );
  }
}

class _StickyTournamentTabs extends SliverPersistentHeaderDelegate {
  const _StickyTournamentTabs({required this.child});

  final Widget child;

  @override
  double get minExtent => 78;

  @override
  double get maxExtent => 78;

  @override
  Widget build(
    BuildContext context,
    double shrinkOffset,
    bool overlapsContent,
  ) {
    return child;
  }

  @override
  bool shouldRebuild(covariant _StickyTournamentTabs oldDelegate) {
    return oldDelegate.child != child;
  }
}
