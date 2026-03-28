import 'package:flutter/material.dart';

import '../../../core/constants/app_breakpoints.dart';
import '../../../core/constants/app_spacing.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/utils/app_formatters.dart';
import '../../../core/widgets/gtex_surface_card.dart';
import '../../../shared/models/competition.dart';
import '../../../shared/models/federation.dart';
import '../../../shared/models/player.dart';
import '../../../shared/widgets/metric_pill.dart';

enum WorldTab { regens, competitions, history, federations }

extension WorldTabPresentation on WorldTab {
  String get label {
    return switch (this) {
      WorldTab.regens => 'Regens',
      WorldTab.competitions => 'Competitions',
      WorldTab.history => 'History',
      WorldTab.federations => 'Federations',
    };
  }

  IconData get icon {
    return switch (this) {
      WorldTab.regens => Icons.auto_awesome_rounded,
      WorldTab.competitions => Icons.emoji_events_rounded,
      WorldTab.history => Icons.history_edu_rounded,
      WorldTab.federations => Icons.public_rounded,
    };
  }
}

class WorldTabBar extends StatelessWidget {
  const WorldTabBar({super.key, required this.controller, required this.onTap});

  final TabController controller;
  final ValueChanged<int> onTap;

  @override
  Widget build(BuildContext context) {
    final bool isScrollable =
        MediaQuery.sizeOf(context).width < AppBreakpoints.compact;

    return Container(
      padding: const EdgeInsets.all(spacingSM),
      decoration: BoxDecoration(
        color: AppColors.card.withValues(alpha: 0.92),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: AppColors.divider),
      ),
      child: TabBar(
        controller: controller,
        onTap: onTap,
        isScrollable: isScrollable,
        tabAlignment: isScrollable ? TabAlignment.start : TabAlignment.fill,
        dividerColor: Colors.transparent,
        overlayColor: const WidgetStatePropertyAll(Colors.transparent),
        indicator: BoxDecoration(
          borderRadius: BorderRadius.circular(18),
          gradient: LinearGradient(
            colors: <Color>[
              AppColors.primary.withValues(alpha: 0.2),
              AppColors.gold.withValues(alpha: 0.14),
            ],
          ),
          border: Border.all(color: AppColors.primary.withValues(alpha: 0.28)),
        ),
        labelColor: AppColors.textPrimary,
        unselectedLabelColor: AppColors.textSecondary,
        tabs:
            WorldTab.values
                .map(
                  (WorldTab tab) => Tab(
                    key: Key('world-tab-${tab.name}'),
                    icon: Icon(tab.icon),
                    text: tab.label,
                  ),
                )
                .toList(),
      ),
    );
  }
}

class WorldTabStatePanel extends StatelessWidget {
  const WorldTabStatePanel({
    super.key,
    required this.tab,
    required this.loading,
    required this.isEmpty,
    required this.loadingLabel,
    required this.emptyTitle,
    required this.emptyBody,
    required this.emptyIcon,
    required this.child,
  });

  final WorldTab tab;
  final bool loading;
  final bool isEmpty;
  final String loadingLabel;
  final String emptyTitle;
  final String emptyBody;
  final IconData emptyIcon;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 280),
      switchInCurve: Curves.easeOutCubic,
      switchOutCurve: Curves.easeInCubic,
      transitionBuilder: (Widget child, Animation<double> animation) {
        return FadeTransition(
          opacity: animation,
          child: SlideTransition(
            position: Tween<Offset>(
              begin: const Offset(0.03, 0),
              end: Offset.zero,
            ).animate(animation),
            child: child,
          ),
        );
      },
      child:
          loading
              ? _WorldLoadingState(
                key: ValueKey<String>('world-loading-${tab.name}'),
                tab: tab,
                label: loadingLabel,
              )
              : isEmpty
              ? _WorldEmptyState(
                key: ValueKey<String>('world-empty-${tab.name}'),
                title: emptyTitle,
                body: emptyBody,
                icon: emptyIcon,
              )
              : KeyedSubtree(
                key: ValueKey<String>('world-content-${tab.name}'),
                child: child,
              ),
    );
  }
}

class RegensGrid extends StatelessWidget {
  const RegensGrid({
    super.key,
    required this.regens,
    required this.bottomPadding,
  });

  final List<Player> regens;
  final double bottomPadding;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final int crossAxisCount =
            constraints.maxWidth >= AppBreakpoints.expanded
                ? 3
                : constraints.maxWidth >= AppBreakpoints.compact
                ? 2
                : 1;

        return GridView.builder(
          key: const Key('world-regens-grid'),
          padding: EdgeInsets.only(bottom: bottomPadding),
          physics: const BouncingScrollPhysics(
            parent: AlwaysScrollableScrollPhysics(),
          ),
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: crossAxisCount,
            crossAxisSpacing: spacingMD,
            mainAxisSpacing: spacingMD,
            childAspectRatio:
                constraints.maxWidth >= AppBreakpoints.compact ? 0.94 : 1.1,
          ),
          itemCount: regens.length,
          itemBuilder: (BuildContext context, int index) {
            final Player player = regens[index];
            return _HoverLift(
              child: GtexSurfaceCard(
                key: Key('world-regen-card-${player.id}'),
                glowColor: player.isHot ? AppColors.primary : AppColors.gold,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Row(
                      children: <Widget>[
                        Container(
                          width: 62,
                          height: 62,
                          padding: const EdgeInsets.all(spacingSM),
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(18),
                            gradient: LinearGradient(
                              begin: Alignment.topLeft,
                              end: Alignment.bottomRight,
                              colors: <Color>[
                                AppColors.primary.withValues(alpha: 0.12),
                                AppColors.gold.withValues(alpha: 0.08),
                              ],
                            ),
                            border: Border.all(color: AppColors.divider),
                          ),
                          child: Image.asset(player.image, fit: BoxFit.contain),
                        ),
                        const SizedBox(width: spacingMD),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Text(
                                player.name,
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                                style: Theme.of(context).textTheme.titleLarge,
                              ),
                              const SizedBox(height: spacingXS),
                              Text(
                                '${player.position} | ${player.country}',
                                style: Theme.of(context).textTheme.bodySmall,
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: spacingMD),
                    Wrap(
                      spacing: spacingSM,
                      runSpacing: spacingSM,
                      children: <Widget>[
                        MetricPill(
                          label: 'OVR',
                          value: '${player.rating}',
                          highlight: true,
                        ),
                        MetricPill(
                          label: 'Potential',
                          value: '${player.potential}',
                        ),
                        MetricPill(label: 'Age', value: '${player.age}'),
                      ],
                    ),
                    const SizedBox(height: spacingMD),
                    Container(
                      padding: const EdgeInsets.all(spacingMD),
                      decoration: BoxDecoration(
                        color: AppColors.surfaceMuted.withValues(alpha: 0.82),
                        borderRadius: BorderRadius.circular(cardRadius),
                        border: Border.all(color: AppColors.divider),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(
                            'Projected Market Value',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                          const SizedBox(height: spacingXS),
                          Text(
                            AppFormatters.money(player.valueInMillions),
                            style: Theme.of(context).textTheme.headlineSmall
                                ?.copyWith(color: AppColors.gold),
                          ),
                        ],
                      ),
                    ),
                    const Spacer(),
                    Text(
                      player.isHot
                          ? 'Hot projection signal. Scout priority elevated.'
                          : 'Steady developmental curve with strong upside.',
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }
}

class CompetitionsList extends StatelessWidget {
  const CompetitionsList({
    super.key,
    required this.competitions,
    required this.bottomPadding,
  });

  final List<Competition> competitions;
  final double bottomPadding;

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      key: const Key('world-competitions-list'),
      padding: EdgeInsets.only(bottom: bottomPadding),
      physics: const BouncingScrollPhysics(
        parent: AlwaysScrollableScrollPhysics(),
      ),
      itemCount: competitions.length,
      separatorBuilder: (_, _) => const SizedBox(height: spacingMD),
      itemBuilder: (BuildContext context, int index) {
        final Competition competition = competitions[index];
        return _HoverLift(
          child: GtexSurfaceCard(
            key: Key('world-competition-card-$index'),
            padding: EdgeInsets.zero,
            glowColor: index.isEven ? AppColors.primary : AppColors.gold,
            child: ClipRRect(
              borderRadius: BorderRadius.circular(cardRadius),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Container(
                    height: 148,
                    padding: const EdgeInsets.all(spacingLG),
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                        colors: <Color>[
                          index.isEven
                              ? AppColors.primary.withValues(alpha: 0.28)
                              : AppColors.gold.withValues(alpha: 0.18),
                          AppColors.surfaceMuted,
                          AppColors.card,
                        ],
                      ),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Row(
                          children: <Widget>[
                            MetricPill(
                              label: 'Region',
                              value: competition.region,
                              highlight: true,
                            ),
                            const Spacer(),
                            Icon(
                              index.isEven
                                  ? Icons.stadium_rounded
                                  : Icons.videocam_rounded,
                              color:
                                  index.isEven
                                      ? AppColors.primary
                                      : AppColors.gold,
                            ),
                          ],
                        ),
                        const Spacer(),
                        Text(
                          competition.name,
                          style: Theme.of(context).textTheme.headlineSmall,
                        ),
                        const SizedBox(height: spacingXS),
                        Text(
                          competition.stage,
                          style: Theme.of(
                            context,
                          ).textTheme.bodyLarge?.copyWith(
                            color: AppColors.textPrimary,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.all(spacingMD),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          competition.nextFixture,
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        const SizedBox(height: spacingSM),
                        Text(
                          competition.spotlight,
                          style: Theme.of(context).textTheme.bodyMedium
                              ?.copyWith(color: AppColors.textSecondary),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

class HistoryRecordsList extends StatelessWidget {
  const HistoryRecordsList({
    super.key,
    required this.records,
    required this.bottomPadding,
  });

  final List<String> records;
  final double bottomPadding;

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      key: const Key('world-history-list'),
      padding: EdgeInsets.only(bottom: bottomPadding),
      physics: const BouncingScrollPhysics(
        parent: AlwaysScrollableScrollPhysics(),
      ),
      itemCount: records.length,
      separatorBuilder: (_, _) => const SizedBox(height: spacingMD),
      itemBuilder: (BuildContext context, int index) {
        final String record = records[index];
        final List<String> parts = record.split(':');
        final String year = parts.first.trim();
        final String detail =
            parts.length > 1 ? parts.sublist(1).join(':').trim() : record;

        return GtexSurfaceCard(
          key: Key('world-history-record-$index'),
          glowColor: index == 0 ? AppColors.primary : null,
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Container(
                width: 54,
                height: 54,
                decoration: BoxDecoration(
                  color: AppColors.primary.withValues(alpha: 0.14),
                  borderRadius: BorderRadius.circular(18),
                ),
                alignment: Alignment.center,
                child: Text(
                  year,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: AppColors.primary,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              const SizedBox(width: spacingMD),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      'World Record ${index + 1}',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: spacingSM),
                    Text(detail, style: Theme.of(context).textTheme.bodyMedium),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class FederationsList extends StatelessWidget {
  const FederationsList({
    super.key,
    required this.federations,
    required this.joinedFederations,
    required this.onJoin,
    required this.bottomPadding,
  });

  final List<Federation> federations;
  final Set<String> joinedFederations;
  final ValueChanged<String> onJoin;
  final double bottomPadding;

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      key: const Key('world-federations-list'),
      padding: EdgeInsets.only(bottom: bottomPadding),
      physics: const BouncingScrollPhysics(
        parent: AlwaysScrollableScrollPhysics(),
      ),
      itemCount: federations.length,
      separatorBuilder: (_, _) => const SizedBox(height: spacingMD),
      itemBuilder: (BuildContext context, int index) {
        final Federation federation = federations[index];
        final bool joined = joinedFederations.contains(federation.name);

        return GtexSurfaceCard(
          key: Key('world-federation-card-$index'),
          glowColor: joined ? AppColors.primary : AppColors.gold,
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
                          federation.name,
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        const SizedBox(height: spacingXS),
                        Text(
                          federation.region,
                          style: Theme.of(context).textTheme.bodyMedium
                              ?.copyWith(color: AppColors.gold),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: spacingMD),
                  MetricPill(label: 'Rank', value: '${federation.ranking}'),
                ],
              ),
              const SizedBox(height: spacingMD),
              Text(
                federation.focus,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: spacingMD),
              Wrap(
                spacing: spacingSM,
                runSpacing: spacingSM,
                children: <Widget>[
                  MetricPill(
                    label: 'Clubs',
                    value: '${federation.memberClubs}',
                    highlight: true,
                  ),
                  MetricPill(
                    label: 'Status',
                    value: joined ? 'Joined' : 'Open',
                  ),
                ],
              ),
              const SizedBox(height: spacingMD),
              Align(
                alignment: Alignment.centerLeft,
                child: FilledButton(
                  key: Key('world-federation-join-$index'),
                  onPressed: joined ? null : () => onJoin(federation.name),
                  child: Text(joined ? 'Joined' : 'Join Federation'),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _WorldLoadingState extends StatelessWidget {
  const _WorldLoadingState({super.key, required this.tab, required this.label});

  final WorldTab tab;
  final String label;

  @override
  Widget build(BuildContext context) {
    return ListView(
      physics: const BouncingScrollPhysics(
        parent: AlwaysScrollableScrollPhysics(),
      ),
      children: <Widget>[
        const SizedBox(height: 96),
        Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: GtexSurfaceCard(
              glowColor: AppColors.primary,
              child: Column(
                children: <Widget>[
                  const CircularProgressIndicator(),
                  const SizedBox(height: spacingMD),
                  Text(
                    label,
                    style: Theme.of(context).textTheme.titleLarge,
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: spacingSM),
                  Text(
                    'Streaming world data into the active tab.',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: AppColors.textSecondary,
                    ),
                    textAlign: TextAlign.center,
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

class _WorldEmptyState extends StatelessWidget {
  const _WorldEmptyState({
    super.key,
    required this.title,
    required this.body,
    required this.icon,
  });

  final String title;
  final String body;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return ListView(
      physics: const BouncingScrollPhysics(
        parent: AlwaysScrollableScrollPhysics(),
      ),
      children: <Widget>[
        const SizedBox(height: 96),
        Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: GtexSurfaceCard(
              child: Column(
                children: <Widget>[
                  Icon(icon, size: 48, color: AppColors.gold),
                  const SizedBox(height: spacingMD),
                  Text(
                    title,
                    style: Theme.of(context).textTheme.titleLarge,
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: spacingSM),
                  Text(
                    body,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: AppColors.textSecondary,
                    ),
                    textAlign: TextAlign.center,
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

class _HoverLift extends StatefulWidget {
  const _HoverLift({required this.child});

  final Widget child;

  @override
  State<_HoverLift> createState() => _HoverLiftState();
}

class _HoverLiftState extends State<_HoverLift> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: AnimatedScale(
        duration: const Duration(milliseconds: 180),
        curve: Curves.easeOutCubic,
        scale: _hovered ? 1.015 : 1,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          curve: Curves.easeOutCubic,
          transform: Matrix4.translationValues(0, _hovered ? -4 : 0, 0),
          child: widget.child,
        ),
      ),
    );
  }
}
