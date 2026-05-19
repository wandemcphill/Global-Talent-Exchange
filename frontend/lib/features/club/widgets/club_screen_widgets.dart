import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../../core/constants/app_breakpoints.dart';
import '../../../core/constants/app_spacing.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/utils/app_formatters.dart';
import '../../../core/widgets/gtex_surface_card.dart';
import '../../../shared/models/club.dart';
import '../../../shared/models/player.dart';
import '../../../shared/widgets/metric_pill.dart';
import '../../../widgets/player_card_avatar.dart';

class ClubFormationSlot {
  const ClubFormationSlot({
    required this.position,
    required this.alignment,
    required this.player,
  });

  final String position;
  final Alignment alignment;
  final Player player;

  ClubFormationSlot copyWith({
    String? position,
    Alignment? alignment,
    Player? player,
  }) {
    return ClubFormationSlot(
      position: position ?? this.position,
      alignment: alignment ?? this.alignment,
      player: player ?? this.player,
    );
  }
}

class ClubFinancePoint {
  const ClubFinancePoint({
    required this.label,
    required this.revenue,
    required this.wages,
  });

  final String label;
  final double revenue;
  final double wages;
}

class ClubFinanceBreakdown {
  const ClubFinanceBreakdown({
    required this.label,
    required this.value,
    required this.color,
  });

  final String label;
  final double value;
  final Color color;
}

class ClubFanSignal {
  const ClubFanSignal({
    required this.label,
    required this.value,
    required this.caption,
    required this.color,
  });

  final String label;
  final double value;
  final String caption;
  final Color color;
}

class ClubIdentityPillar {
  const ClubIdentityPillar({
    required this.label,
    required this.score,
    required this.description,
    required this.icon,
  });

  final String label;
  final double score;
  final String description;
  final IconData icon;
}

class ClubDashboardTabBar extends StatelessWidget {
  const ClubDashboardTabBar({super.key, required this.controller});

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
          Tab(key: Key('club-tab-squad'), text: 'Squad'),
          Tab(key: Key('club-tab-finance'), text: 'Finance'),
          Tab(key: Key('club-tab-fans'), text: 'Fans'),
          Tab(key: Key('club-tab-identity'), text: 'Identity'),
        ],
      ),
    );
  }
}

class ClubOverviewHeroCard extends StatelessWidget {
  const ClubOverviewHeroCard({
    super.key,
    required this.club,
    required this.fanMood,
  });

  final Club club;
  final double fanMood;

  @override
  Widget build(BuildContext context) {
    return GtexSurfaceCard(
      glowColor: AppColors.primary,
      padding: const EdgeInsets.all(spacingLG),
      child: LayoutBuilder(
        builder: (BuildContext context, BoxConstraints constraints) {
          final bool wide = constraints.maxWidth >= AppBreakpoints.medium;
          final Widget crest = Container(
            width: 92,
            height: 92,
            padding: const EdgeInsets.all(spacingMD),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(24),
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: <Color>[
                  AppColors.primary.withValues(alpha: 0.14),
                  AppColors.gold.withValues(alpha: 0.1),
                  AppColors.surfaceMuted,
                ],
              ),
              border: Border.all(color: AppColors.divider),
            ),
            child: Image.asset(club.badgeAsset, fit: BoxFit.contain),
          );

          final Widget identity = Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                club.name,
                style: Theme.of(context).textTheme.headlineMedium,
              ),
              const SizedBox(height: spacingSM),
              Text(
                '${club.league} | ${club.country} | ${club.stadium}',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: spacingMD),
              Wrap(
                spacing: spacingSM,
                runSpacing: spacingSM,
                children: <Widget>[
                  MetricPill(
                    label: 'Budget',
                    value: AppFormatters.money(club.budgetInMillions),
                    highlight: true,
                  ),
                  MetricPill(label: 'XI', value: '${club.startingXiRating}'),
                  MetricPill(label: 'Academy', value: '${club.academyLevel}/5'),
                  MetricPill(
                    label: 'Fans',
                    value: AppFormatters.compact(club.fans),
                  ),
                ],
              ),
            ],
          );

          final Widget sentimentCard = Container(
            width: wide ? 260 : double.infinity,
            padding: const EdgeInsets.all(spacingMD),
            decoration: BoxDecoration(
              color: AppColors.surfaceMuted.withValues(alpha: 0.76),
              borderRadius: BorderRadius.circular(cardRadius),
              border: Border.all(color: AppColors.divider),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  'Club Pulse',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                const SizedBox(height: spacingSM),
                TweenAnimationBuilder<double>(
                  tween: Tween<double>(begin: 0, end: fanMood),
                  duration: const Duration(milliseconds: 800),
                  curve: Curves.easeOutCubic,
                  builder: (BuildContext context, double value, Widget? child) {
                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          '${(value * 100).round()}%',
                          style: Theme.of(context).textTheme.headlineSmall
                              ?.copyWith(color: AppColors.gold),
                        ),
                        const SizedBox(height: spacingSM),
                        ClipRRect(
                          borderRadius: BorderRadius.circular(999),
                          child: LinearProgressIndicator(
                            value: value,
                            minHeight: 10,
                            backgroundColor: AppColors.card,
                            valueColor: const AlwaysStoppedAnimation<Color>(
                              AppColors.primary,
                            ),
                          ),
                        ),
                      ],
                    );
                  },
                ),
                const SizedBox(height: spacingMD),
                Text(
                  fanMood >= 0.75
                      ? 'Supporters back the current sporting and commercial direction.'
                      : 'Fan confidence is stable, but sharper results would lift momentum.',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ],
            ),
          );

          if (wide) {
            return Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                crest,
                const SizedBox(width: spacingLG),
                Expanded(child: identity),
                const SizedBox(width: spacingLG),
                sentimentCard,
              ],
            );
          }

          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  crest,
                  const SizedBox(width: spacingMD),
                  Expanded(child: identity),
                ],
              ),
              const SizedBox(height: spacingLG),
              sentimentCard,
            ],
          );
        },
      ),
    );
  }
}

class ClubSquadTab extends StatelessWidget {
  const ClubSquadTab({
    super.key,
    required this.slots,
    required this.benchPlayers,
    required this.bottomPadding,
    required this.onSwapPlayers,
  });

  final List<ClubFormationSlot> slots;
  final List<Player> benchPlayers;
  final double bottomPadding;
  final void Function(int fromIndex, int toIndex) onSwapPlayers;

  @override
  Widget build(BuildContext context) {
    return ListView(
      key: const Key('club-squad-view'),
      padding: EdgeInsets.only(bottom: bottomPadding),
      physics: const BouncingScrollPhysics(
        parent: AlwaysScrollableScrollPhysics(),
      ),
      children: <Widget>[
        GtexSurfaceCard(
          child: Row(
            children: <Widget>[
              const Expanded(
                child: Text(
                  'Drag a starter onto another role to swap the shape without leaving the dashboard.',
                ),
              ),
              const SizedBox(width: spacingMD),
              const MetricPill(label: 'Shape', value: '4-3-3', highlight: true),
            ],
          ),
        ),
        const SizedBox(height: spacingLG),
        LayoutBuilder(
          builder: (BuildContext context, BoxConstraints constraints) {
            final bool wide = constraints.maxWidth >= AppBreakpoints.medium;
            final Widget pitch = _FormationBoard(
              slots: slots,
              onSwapPlayers: onSwapPlayers,
            );
            final Widget sideColumn = Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                GtexSurfaceCard(
                  glowColor: AppColors.gold,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        'Bench',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: spacingSM),
                      Text(
                        'Young depth and impact options available behind the starting group.',
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: AppColors.textSecondary,
                        ),
                      ),
                      const SizedBox(height: spacingMD),
                      ...benchPlayers
                          .take(4)
                          .map(
                            (Player player) => Padding(
                              padding: const EdgeInsets.only(bottom: spacingSM),
                              child: _ReserveTile(player: player),
                            ),
                          ),
                    ],
                  ),
                ),
                const SizedBox(height: spacingMD),
                GtexSurfaceCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        'Tactical Notes',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: spacingMD),
                      const _InsightRow(
                        label: 'Defensive line',
                        value: 'Aggressive mid-block',
                      ),
                      const SizedBox(height: spacingSM),
                      const _InsightRow(
                        label: 'Build-up',
                        value: 'Inside fullbacks',
                      ),
                      const SizedBox(height: spacingSM),
                      _InsightRow(
                        label: 'Average rating',
                        value:
                            '${(slots.map((ClubFormationSlot slot) => slot.player.rating).reduce((int a, int b) => a + b) / slots.length).round()}',
                      ),
                    ],
                  ),
                ),
              ],
            );

            if (wide) {
              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Expanded(flex: 8, child: pitch),
                  const SizedBox(width: spacingMD),
                  Expanded(flex: 4, child: sideColumn),
                ],
              );
            }

            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                pitch,
                const SizedBox(height: spacingMD),
                sideColumn,
              ],
            );
          },
        ),
      ],
    );
  }
}

class _FormationBoard extends StatelessWidget {
  const _FormationBoard({required this.slots, required this.onSwapPlayers});

  final List<ClubFormationSlot> slots;
  final void Function(int fromIndex, int toIndex) onSwapPlayers;

  @override
  Widget build(BuildContext context) {
    return GtexSurfaceCard(
      glowColor: AppColors.primary,
      padding: const EdgeInsets.all(spacingMD),
      child: LayoutBuilder(
        builder: (BuildContext context, BoxConstraints constraints) {
          final bool compact = constraints.maxWidth < AppBreakpoints.compact;
          final double slotWidth = compact ? 92 : 112;
          final double slotHeight = compact ? 86 : 98;

          return AspectRatio(
            aspectRatio: compact ? 0.76 : 0.92,
            child: Container(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(cardRadius),
                gradient: const LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: <Color>[
                    Color(0xFF0F302B),
                    Color(0xFF123E38),
                    Color(0xFF102B27),
                  ],
                ),
                border: Border.all(color: AppColors.divider),
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(cardRadius),
                child: Stack(
                  children: <Widget>[
                    Positioned.fill(
                      child: CustomPaint(painter: _PitchPainter()),
                    ),
                    ...slots.asMap().entries.map((
                      MapEntry<int, ClubFormationSlot> entry,
                    ) {
                      final int index = entry.key;
                      final ClubFormationSlot slot = entry.value;

                      return Align(
                        alignment: slot.alignment,
                        child: SizedBox(
                          width: slotWidth,
                          height: slotHeight,
                          child: _FormationSlotTarget(
                            key: Key(
                              'club-squad-slot-${slot.position.toLowerCase()}',
                            ),
                            position: slot.position,
                            player: slot.player,
                            compact: compact,
                            onAccept: (int fromIndex) {
                              onSwapPlayers(fromIndex, index);
                            },
                            dragData: index,
                          ),
                        ),
                      );
                    }),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}

class _FormationSlotTarget extends StatefulWidget {
  const _FormationSlotTarget({
    super.key,
    required this.position,
    required this.player,
    required this.compact,
    required this.onAccept,
    required this.dragData,
  });

  final String position;
  final Player player;
  final bool compact;
  final ValueChanged<int> onAccept;
  final int dragData;

  @override
  State<_FormationSlotTarget> createState() => _FormationSlotTargetState();
}

class _FormationSlotTargetState extends State<_FormationSlotTarget> {
  bool _hovering = false;

  @override
  Widget build(BuildContext context) {
    final Widget card = _FormationSlotCard(
      position: widget.position,
      player: widget.player,
      compact: widget.compact,
      highlighted: _hovering,
    );

    return DragTarget<int>(
      onWillAcceptWithDetails: (DragTargetDetails<int> details) {
        final bool shouldAccept = details.data != widget.dragData;
        if (shouldAccept != _hovering) {
          setState(() => _hovering = shouldAccept);
        }
        return shouldAccept;
      },
      onLeave: (_) {
        if (_hovering) {
          setState(() => _hovering = false);
        }
      },
      onAcceptWithDetails: (DragTargetDetails<int> details) {
        setState(() => _hovering = false);
        widget.onAccept(details.data);
      },
      builder: (
        BuildContext context,
        List<int?> candidateData,
        List<dynamic> rejectedData,
      ) {
        return LongPressDraggable<int>(
          data: widget.dragData,
          feedback: SizedBox(
            width: widget.compact ? 92 : 112,
            child: Material(
              color: Colors.transparent,
              child: _FormationSlotCard(
                position: widget.position,
                player: widget.player,
                compact: widget.compact,
                highlighted: true,
              ),
            ),
          ),
          childWhenDragging: Opacity(opacity: 0.35, child: card),
          child: card,
        );
      },
    );
  }
}

class _FormationSlotCard extends StatelessWidget {
  const _FormationSlotCard({
    required this.position,
    required this.player,
    required this.compact,
    required this.highlighted,
  });

  final String position;
  final Player player;
  final bool compact;
  final bool highlighted;

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 180),
      curve: Curves.easeOutCubic,
      padding: EdgeInsets.all(compact ? spacingXS + 2 : spacingSM),
      decoration: BoxDecoration(
        color:
            highlighted
                ? AppColors.primary.withValues(alpha: 0.18)
                : AppColors.card.withValues(alpha: 0.9),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: highlighted ? AppColors.primary : AppColors.divider,
        ),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.2),
            blurRadius: 16,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Text(
                position,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: AppColors.gold,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const Spacer(),
              Text(
                '${player.rating}',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: AppColors.primary,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
          Expanded(
            child: Align(
              alignment: Alignment.bottomLeft,
              child: Text(
                '${player.rating}',
                style: (compact
                        ? Theme.of(context).textTheme.titleSmall
                        : Theme.of(context).textTheme.titleMedium)
                    ?.copyWith(
                      color: AppColors.primary,
                      fontWeight: FontWeight.w700,
                    ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ReserveTile extends StatelessWidget {
  const _ReserveTile({required this.player});

  final Player player;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(spacingSM),
      decoration: BoxDecoration(
        color: AppColors.surfaceMuted.withValues(alpha: 0.72),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.divider),
      ),
      child: Row(
        children: <Widget>[
          PlayerCardAvatar(avatar: null, imageUrl: player.image, size: 44),
          const SizedBox(width: spacingMD),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  player.name,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(
                    context,
                  ).textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: spacingXS),
                Text(
                  '${player.position} | ${player.country}',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
          const SizedBox(width: spacingSM),
          MetricPill(
            label: 'OVR',
            value: '${player.rating}',
            highlight: player.isHot,
          ),
        ],
      ),
    );
  }
}

class ClubFinanceTab extends StatelessWidget {
  const ClubFinanceTab({
    super.key,
    required this.points,
    required this.breakdown,
    required this.bottomPadding,
  });

  final List<ClubFinancePoint> points;
  final List<ClubFinanceBreakdown> breakdown;
  final double bottomPadding;

  @override
  Widget build(BuildContext context) {
    final double latestRevenue = points.last.revenue;
    final double latestWages = points.last.wages;
    final double operatingMargin = latestRevenue - latestWages;

    return ListView(
      key: const Key('club-finance-view'),
      padding: EdgeInsets.only(bottom: bottomPadding),
      physics: const BouncingScrollPhysics(
        parent: AlwaysScrollableScrollPhysics(),
      ),
      children: <Widget>[
        Wrap(
          spacing: spacingMD,
          runSpacing: spacingMD,
          children: <Widget>[
            _FinanceMetricCard(
              label: 'Operating margin',
              value: AppFormatters.money(operatingMargin),
              color:
                  operatingMargin >= 0 ? AppColors.primary : AppColors.danger,
            ),
            _FinanceMetricCard(
              label: 'Revenue run-rate',
              value: AppFormatters.money(latestRevenue),
              color: AppColors.gold,
            ),
            _FinanceMetricCard(
              label: 'Wage pressure',
              value: AppFormatters.money(latestWages),
              color: AppColors.textPrimary,
            ),
          ],
        ),
        const SizedBox(height: spacingLG),
        GtexSurfaceCard(
          glowColor: AppColors.primary,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Cashflow trend',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: spacingSM),
              Text(
                'Revenue and wage commitments across the current reporting cycle.',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: spacingLG),
              SizedBox(
                height: 220,
                child: CustomPaint(
                  painter: _FinanceTrendPainter(points: points),
                ),
              ),
              const SizedBox(height: spacingMD),
              Row(
                children:
                    points
                        .map(
                          (ClubFinancePoint point) => Expanded(
                            child: Text(
                              point.label,
                              textAlign: TextAlign.center,
                              style: Theme.of(context).textTheme.bodySmall,
                            ),
                          ),
                        )
                        .toList(),
              ),
              const SizedBox(height: spacingMD),
              Wrap(
                spacing: spacingMD,
                runSpacing: spacingSM,
                children: const <Widget>[
                  _LegendPill(label: 'Revenue', color: AppColors.primary),
                  _LegendPill(label: 'Wages', color: AppColors.gold),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: spacingLG),
        GtexSurfaceCard(
          glowColor: AppColors.gold,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Spend allocation',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: spacingSM),
              Text(
                'Operational spend across the current dashboard cycle.',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: spacingLG),
              _FinanceBreakdownChart(items: breakdown),
            ],
          ),
        ),
      ],
    );
  }
}

class ClubFansTab extends StatelessWidget {
  const ClubFansTab({
    super.key,
    required this.sentiment,
    required this.signals,
    required this.bottomPadding,
  });

  final double sentiment;
  final List<ClubFanSignal> signals;
  final double bottomPadding;

  @override
  Widget build(BuildContext context) {
    return ListView(
      key: const Key('club-fans-view'),
      padding: EdgeInsets.only(bottom: bottomPadding),
      physics: const BouncingScrollPhysics(
        parent: AlwaysScrollableScrollPhysics(),
      ),
      children: <Widget>[
        LayoutBuilder(
          builder: (BuildContext context, BoxConstraints constraints) {
            final bool wide = constraints.maxWidth >= AppBreakpoints.medium;
            final Widget meter = GtexSurfaceCard(
              glowColor: AppColors.primary,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    'Supporter mood',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: spacingLG),
                  Center(
                    child: TweenAnimationBuilder<double>(
                      tween: Tween<double>(begin: 0, end: sentiment),
                      duration: const Duration(milliseconds: 900),
                      curve: Curves.easeOutCubic,
                      builder: (
                        BuildContext context,
                        double value,
                        Widget? child,
                      ) {
                        return SizedBox(
                          width: 170,
                          height: 170,
                          child: Stack(
                            alignment: Alignment.center,
                            children: <Widget>[
                              SizedBox(
                                width: 170,
                                height: 170,
                                child: CircularProgressIndicator(
                                  value: value,
                                  strokeWidth: 12,
                                  backgroundColor: AppColors.surfaceMuted,
                                  valueColor:
                                      const AlwaysStoppedAnimation<Color>(
                                        AppColors.primary,
                                      ),
                                ),
                              ),
                              Column(
                                mainAxisSize: MainAxisSize.min,
                                children: <Widget>[
                                  Text(
                                    '${(value * 100).round()}',
                                    style: Theme.of(context)
                                        .textTheme
                                        .headlineMedium
                                        ?.copyWith(color: AppColors.gold),
                                  ),
                                  const SizedBox(height: spacingXS),
                                  Text(
                                    value >= 0.75 ? 'Electric' : 'Stable',
                                    style:
                                        Theme.of(context).textTheme.bodySmall,
                                  ),
                                ],
                              ),
                            ],
                          ),
                        );
                      },
                    ),
                  ),
                  const SizedBox(height: spacingLG),
                  Text(
                    sentiment >= 0.75
                        ? 'The fan base is aligned with results, identity, and long-term strategy.'
                        : 'Community energy is positive, but sharper performances would lift sentiment further.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
              ),
            );

            final Widget signalsPanel = GtexSurfaceCard(
              glowColor: AppColors.gold,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    'Sentiment drivers',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: spacingMD),
                  ...signals.map(
                    (ClubFanSignal signal) => Padding(
                      padding: const EdgeInsets.only(bottom: spacingMD),
                      child: _FanSignalRow(signal: signal),
                    ),
                  ),
                ],
              ),
            );

            if (wide) {
              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Expanded(child: meter),
                  const SizedBox(width: spacingMD),
                  Expanded(child: signalsPanel),
                ],
              );
            }

            return Column(
              children: <Widget>[
                meter,
                const SizedBox(height: spacingMD),
                signalsPanel,
              ],
            );
          },
        ),
      ],
    );
  }
}

class ClubIdentityTab extends StatelessWidget {
  const ClubIdentityTab({
    super.key,
    required this.score,
    required this.philosophy,
    required this.bottomPadding,
  });

  final double score;
  final List<ClubIdentityPillar> philosophy;
  final double bottomPadding;

  @override
  Widget build(BuildContext context) {
    return ListView(
      key: const Key('club-identity-view'),
      padding: EdgeInsets.only(bottom: bottomPadding),
      physics: const BouncingScrollPhysics(
        parent: AlwaysScrollableScrollPhysics(),
      ),
      children: <Widget>[
        GtexSurfaceCard(
          glowColor: AppColors.primary,
          child: LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              final bool wide = constraints.maxWidth >= AppBreakpoints.medium;
              final Widget scoreCard = Container(
                width: wide ? 220 : double.infinity,
                padding: const EdgeInsets.all(spacingLG),
                decoration: BoxDecoration(
                  color: AppColors.primary.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(cardRadius),
                  border: Border.all(
                    color: AppColors.primary.withValues(alpha: 0.24),
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      'Identity score',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                    const SizedBox(height: spacingSM),
                    Text(
                      '${(score * 100).round()}',
                      style: Theme.of(context).textTheme.headlineLarge
                          ?.copyWith(color: AppColors.gold),
                    ),
                    const SizedBox(height: spacingSM),
                    const Text('Clear, modern, academy-first club posture.'),
                  ],
                ),
              );

              final Widget narrative = Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      'Philosophy',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: spacingSM),
                    Text(
                      'The club identity leans into proactive football, academy conversion, and a commercially credible brand layer.',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              );

              if (wide) {
                return Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    scoreCard,
                    const SizedBox(width: spacingLG),
                    narrative,
                  ],
                );
              }

              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  scoreCard,
                  const SizedBox(height: spacingLG),
                  narrative,
                ],
              );
            },
          ),
        ),
        const SizedBox(height: spacingLG),
        LayoutBuilder(
          builder: (BuildContext context, BoxConstraints constraints) {
            final double width =
                constraints.maxWidth >= AppBreakpoints.expanded
                    ? (constraints.maxWidth - (spacingMD * 2)) / 3
                    : constraints.maxWidth >= AppBreakpoints.compact
                    ? (constraints.maxWidth - spacingMD) / 2
                    : constraints.maxWidth;

            return Wrap(
              spacing: spacingMD,
              runSpacing: spacingMD,
              children:
                  philosophy
                      .map(
                        (ClubIdentityPillar pillar) => SizedBox(
                          width: width,
                          child: GtexSurfaceCard(
                            glowColor:
                                pillar.score >= 0.85 ? AppColors.gold : null,
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: <Widget>[
                                Row(
                                  children: <Widget>[
                                    Container(
                                      width: 42,
                                      height: 42,
                                      decoration: BoxDecoration(
                                        shape: BoxShape.circle,
                                        color: AppColors.primary.withValues(
                                          alpha: 0.12,
                                        ),
                                      ),
                                      child: Icon(
                                        pillar.icon,
                                        color: AppColors.primary,
                                      ),
                                    ),
                                    const SizedBox(width: spacingMD),
                                    Expanded(
                                      child: Text(
                                        pillar.label,
                                        style:
                                            Theme.of(
                                              context,
                                            ).textTheme.titleLarge,
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: spacingMD),
                                TweenAnimationBuilder<double>(
                                  tween: Tween<double>(
                                    begin: 0,
                                    end: pillar.score,
                                  ),
                                  duration: const Duration(milliseconds: 720),
                                  curve: Curves.easeOutCubic,
                                  builder: (
                                    BuildContext context,
                                    double value,
                                    Widget? child,
                                  ) {
                                    return ClipRRect(
                                      borderRadius: BorderRadius.circular(999),
                                      child: LinearProgressIndicator(
                                        value: value,
                                        minHeight: 10,
                                        backgroundColor: AppColors.surfaceMuted,
                                        valueColor:
                                            const AlwaysStoppedAnimation<Color>(
                                              AppColors.primary,
                                            ),
                                      ),
                                    );
                                  },
                                ),
                                const SizedBox(height: spacingSM),
                                Text(
                                  '${(pillar.score * 100).round()} / 100',
                                  style: Theme.of(context).textTheme.bodySmall
                                      ?.copyWith(color: AppColors.gold),
                                ),
                                const SizedBox(height: spacingSM),
                                Text(
                                  pillar.description,
                                  style: Theme.of(context).textTheme.bodyMedium,
                                ),
                              ],
                            ),
                          ),
                        ),
                      )
                      .toList(),
            );
          },
        ),
      ],
    );
  }
}

class _FinanceMetricCard extends StatelessWidget {
  const _FinanceMetricCard({
    required this.label,
    required this.value,
    required this.color,
  });

  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 220,
      child: GtexSurfaceCard(
        glowColor: color,
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
      ),
    );
  }
}

class _FinanceBreakdownChart extends StatelessWidget {
  const _FinanceBreakdownChart({required this.items});

  final List<ClubFinanceBreakdown> items;

  @override
  Widget build(BuildContext context) {
    final double maxValue = items
        .map((ClubFinanceBreakdown item) => item.value)
        .reduce(math.max);

    return Column(
      children:
          items
              .map(
                (ClubFinanceBreakdown item) => Padding(
                  padding: const EdgeInsets.only(bottom: spacingMD),
                  child: Row(
                    children: <Widget>[
                      SizedBox(
                        width: 96,
                        child: Text(
                          item.label,
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ),
                      const SizedBox(width: spacingMD),
                      Expanded(
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(999),
                          child: TweenAnimationBuilder<double>(
                            tween: Tween<double>(
                              begin: 0,
                              end: item.value / maxValue,
                            ),
                            duration: const Duration(milliseconds: 700),
                            curve: Curves.easeOutCubic,
                            builder: (
                              BuildContext context,
                              double value,
                              Widget? child,
                            ) {
                              return LinearProgressIndicator(
                                value: value,
                                minHeight: 12,
                                backgroundColor: AppColors.surfaceMuted,
                                valueColor: AlwaysStoppedAnimation<Color>(
                                  item.color,
                                ),
                              );
                            },
                          ),
                        ),
                      ),
                      const SizedBox(width: spacingMD),
                      SizedBox(
                        width: 64,
                        child: Text(
                          AppFormatters.money(item.value),
                          textAlign: TextAlign.right,
                          style: Theme.of(
                            context,
                          ).textTheme.bodySmall?.copyWith(color: item.color),
                        ),
                      ),
                    ],
                  ),
                ),
              )
              .toList(),
    );
  }
}

class _FanSignalRow extends StatelessWidget {
  const _FanSignalRow({required this.signal});

  final ClubFanSignal signal;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          children: <Widget>[
            Expanded(
              child: Text(
                signal.label,
                style: Theme.of(
                  context,
                ).textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w700),
              ),
            ),
            const SizedBox(width: spacingSM),
            Text(
              '${(signal.value * 100).round()}%',
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: signal.color),
            ),
          ],
        ),
        const SizedBox(height: spacingSM),
        ClipRRect(
          borderRadius: BorderRadius.circular(999),
          child: LinearProgressIndicator(
            value: signal.value,
            minHeight: 10,
            backgroundColor: AppColors.surfaceMuted,
            valueColor: AlwaysStoppedAnimation<Color>(signal.color),
          ),
        ),
        const SizedBox(height: spacingSM),
        Text(
          signal.caption,
          style: Theme.of(
            context,
          ).textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
        ),
      ],
    );
  }
}

class _FinanceTrendPainter extends CustomPainter {
  const _FinanceTrendPainter({required this.points});

  final List<ClubFinancePoint> points;

  @override
  void paint(Canvas canvas, Size size) {
    const double topPadding = 16;
    const double bottomPadding = 18;
    const double leftPadding = 8;
    const double rightPadding = 8;
    final double chartWidth = size.width - leftPadding - rightPadding;
    final double chartHeight = size.height - topPadding - bottomPadding;
    final Rect chartRect = Rect.fromLTWH(
      leftPadding,
      topPadding,
      chartWidth,
      chartHeight,
    );

    final Paint gridPaint =
        Paint()
          ..color = AppColors.divider.withValues(alpha: 0.45)
          ..strokeWidth = 1;

    for (int i = 0; i < 4; i++) {
      final double dy = chartRect.top + ((chartRect.height / 3) * i);
      canvas.drawLine(
        Offset(chartRect.left, dy),
        Offset(chartRect.right, dy),
        gridPaint,
      );
    }

    final double maxValue = points
        .expand<double>(
          (ClubFinancePoint point) => <double>[point.revenue, point.wages],
        )
        .reduce(math.max);

    Offset pointToOffset(int index, double value) {
      final double dx =
          chartRect.left + (chartRect.width * (index / (points.length - 1)));
      final double normalized = value / maxValue;
      final double dy = chartRect.bottom - (chartRect.height * normalized);
      return Offset(dx, dy);
    }

    void drawSeries(
      Color color,
      double Function(ClubFinancePoint point) select,
    ) {
      final Paint paint =
          Paint()
            ..color = color
            ..strokeWidth = 3
            ..style = PaintingStyle.stroke
            ..strokeCap = StrokeCap.round;

      final Path path = Path();
      for (int index = 0; index < points.length; index++) {
        final Offset offset = pointToOffset(index, select(points[index]));
        if (index == 0) {
          path.moveTo(offset.dx, offset.dy);
        } else {
          path.lineTo(offset.dx, offset.dy);
        }
      }
      canvas.drawPath(path, paint);

      final Paint dotPaint =
          Paint()
            ..color = color
            ..style = PaintingStyle.fill;
      for (int index = 0; index < points.length; index++) {
        final Offset offset = pointToOffset(index, select(points[index]));
        canvas.drawCircle(offset, 4, dotPaint);
      }
    }

    drawSeries(AppColors.primary, (ClubFinancePoint point) => point.revenue);
    drawSeries(AppColors.gold, (ClubFinancePoint point) => point.wages);
  }

  @override
  bool shouldRepaint(covariant _FinanceTrendPainter oldDelegate) {
    return oldDelegate.points != points;
  }
}

class _LegendPill extends StatelessWidget {
  const _LegendPill({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: spacingSM,
        vertical: spacingXS,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.28)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Container(
            width: 10,
            height: 10,
            decoration: BoxDecoration(color: color, shape: BoxShape.circle),
          ),
          const SizedBox(width: spacingXS),
          Text(
            label,
            style: Theme.of(
              context,
            ).textTheme.bodySmall?.copyWith(color: color),
          ),
        ],
      ),
    );
  }
}

class _InsightRow extends StatelessWidget {
  const _InsightRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: <Widget>[
        Expanded(
          child: Text(label, style: Theme.of(context).textTheme.bodySmall),
        ),
        const SizedBox(width: spacingSM),
        Text(
          value,
          style: Theme.of(
            context,
          ).textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w700),
        ),
      ],
    );
  }
}

class _PitchPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final Paint linePaint =
        Paint()
          ..color = Colors.white.withValues(alpha: 0.16)
          ..strokeWidth = 2
          ..style = PaintingStyle.stroke;

    final Rect fullRect = Offset.zero & size;
    final Rect safeRect = fullRect.deflate(18);
    canvas.drawRect(safeRect, linePaint);
    canvas.drawLine(
      Offset(size.width / 2, safeRect.top),
      Offset(size.width / 2, safeRect.bottom),
      linePaint,
    );
    canvas.drawCircle(Offset(size.width / 2, size.height / 2), 44, linePaint);

    final Rect topBox = Rect.fromCenter(
      center: Offset(size.width / 2, safeRect.top + 60),
      width: size.width * 0.42,
      height: 94,
    );
    final Rect bottomBox = Rect.fromCenter(
      center: Offset(size.width / 2, safeRect.bottom - 60),
      width: size.width * 0.42,
      height: 94,
    );
    canvas.drawRect(topBox, linePaint);
    canvas.drawRect(bottomBox, linePaint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
