import 'dart:async';

import 'package:flutter/material.dart';

import '../../../core/constants/app_breakpoints.dart';
import '../../../core/constants/app_spacing.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_motion.dart';
import '../../../core/utils/app_formatters.dart';
import '../../../core/widgets/app_hover_lift.dart';
import '../../../core/widgets/app_press_scale.dart';
import '../../../core/widgets/gtex_surface_card.dart';
import '../../../core/widgets/stat_bar.dart';
import '../../../shared/models/club.dart';
import '../../../shared/models/daily_task.dart';
import '../../../shared/models/live_match.dart';
import '../../../shared/widgets/metric_pill.dart';

enum HomeCardKind { primary, gold }

extension on HomeCardKind {
  Color get color =>
      this == HomeCardKind.primary ? AppColors.primary : AppColors.gold;
}

class HomeQuickAction {
  const HomeQuickAction({
    required this.label,
    required this.caption,
    required this.icon,
    required this.kind,
    required this.onTap,
  });

  final String label;
  final String caption;
  final IconData icon;
  final HomeCardKind kind;
  final VoidCallback onTap;
}

class HomeStoryHighlight {
  const HomeStoryHighlight({
    required this.title,
    required this.caption,
    required this.imageAsset,
    required this.kind,
    required this.onTap,
  });

  final String title;
  final String caption;
  final String imageAsset;
  final HomeCardKind kind;
  final VoidCallback onTap;
}

class HomeSection extends StatelessWidget {
  const HomeSection({
    super.key,
    required this.title,
    required this.subtitle,
    required this.child,
    this.trailingLabel,
  });

  final String title;
  final String subtitle;
  final String? trailingLabel;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(title, style: Theme.of(context).textTheme.headlineSmall),
                  const SizedBox(height: spacingSM),
                  Text(
                    subtitle,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: AppColors.textSecondary,
                    ),
                  ),
                ],
              ),
            ),
            if (trailingLabel != null) ...<Widget>[
              const SizedBox(width: spacingMD),
              MetricPill(label: 'Now', value: trailingLabel!, highlight: true),
            ],
          ],
        ),
        const SizedBox(height: spacingMD),
        child,
      ],
    );
  }
}

class HomeAnimatedSection extends StatefulWidget {
  const HomeAnimatedSection({
    super.key,
    required this.delay,
    required this.child,
  });

  final Duration delay;
  final Widget child;

  @override
  State<HomeAnimatedSection> createState() => _HomeAnimatedSectionState();
}

class _HomeAnimatedSectionState extends State<HomeAnimatedSection> {
  Timer? _timer;
  bool _visible = false;

  @override
  void initState() {
    super.initState();
    _timer = Timer(widget.delay, () {
      if (mounted) {
        setState(() => _visible = true);
      }
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedSlide(
      duration: AppMotion.slow,
      curve: AppMotion.easeOut,
      offset: _visible ? Offset.zero : const Offset(0, 0.04),
      child: AnimatedOpacity(
        duration: AppMotion.slow,
        curve: AppMotion.easeOut,
        opacity: _visible ? 1 : 0,
        child: widget.child,
      ),
    );
  }
}

class ClubOverviewCard extends StatelessWidget {
  const ClubOverviewCard({
    super.key,
    required this.club,
    required this.onPlay,
    required this.onProfile,
  });

  final Club club;
  final VoidCallback onPlay;
  final VoidCallback onProfile;

  @override
  Widget build(BuildContext context) {
    final _FansSentiment sentiment = _FansSentiment.fromClub(club);

    return AppHoverLift(
      child: GtexSurfaceCard(
        glowColor: sentiment.kind.color,
        child: LayoutBuilder(
          builder: (BuildContext context, BoxConstraints constraints) {
            final bool wide = constraints.maxWidth >= AppBreakpoints.medium;
            final Widget identity = Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Container(
                  width: 72,
                  height: 72,
                  padding: const EdgeInsets.all(spacingSM),
                  decoration: BoxDecoration(
                    color: AppColors.background,
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: AppColors.divider),
                  ),
                  child: Image.asset(club.badgeAsset, fit: BoxFit.contain),
                ),
                const SizedBox(width: spacingMD),
                Expanded(
                  child: Column(
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
                            label: 'Fans',
                            value: AppFormatters.compact(club.fans),
                          ),
                          MetricPill(
                            label: 'Form',
                            value: club.formLabel,
                            highlight: true,
                          ),
                          MetricPill(
                            label: 'Budget',
                            value: AppFormatters.money(club.budgetInMillions),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            );
            final Widget sentimentCard = Container(
              width: wide ? 260 : double.infinity,
              padding: const EdgeInsets.all(spacingMD),
              decoration: BoxDecoration(
                color: AppColors.background.withValues(alpha: 0.64),
                borderRadius: BorderRadius.circular(cardRadius),
                border: Border.all(
                  color: sentiment.kind.color.withValues(alpha: 0.35),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Row(
                    children: <Widget>[
                      Icon(
                        sentiment.icon,
                        color: sentiment.kind.color,
                        size: 18,
                      ),
                      const SizedBox(width: spacingXS),
                      Text(
                        'Fans Sentiment',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ),
                  const SizedBox(height: spacingSM),
                  Text(
                    sentiment.label,
                    style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      color: sentiment.kind.color,
                    ),
                  ),
                  const SizedBox(height: spacingSM),
                  Text(sentiment.description),
                  const SizedBox(height: spacingMD),
                  MetricPill(
                    label: 'Swing',
                    value: sentiment.delta,
                    highlight: true,
                  ),
                ],
              ),
            );

            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                if (wide)
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Expanded(flex: 8, child: identity),
                      const SizedBox(width: spacingMD),
                      sentimentCard,
                    ],
                  )
                else ...<Widget>[
                  identity,
                  const SizedBox(height: spacingMD),
                  sentimentCard,
                ],
                const SizedBox(height: spacingLG),
                Wrap(
                  spacing: spacingMD,
                  runSpacing: spacingMD,
                  children: <Widget>[
                    AppPressScale(
                      child: FilledButton(
                        onPressed: onPlay,
                        child: const Text('Play Match'),
                      ),
                    ),
                    AppPressScale(
                      child: OutlinedButton(
                        onPressed: onProfile,
                        child: const Text('Open Profile'),
                      ),
                    ),
                  ],
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}

class QuickActionsGrid extends StatelessWidget {
  const QuickActionsGrid({super.key, required this.actions});

  final List<HomeQuickAction> actions;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final double width =
            constraints.maxWidth >= AppBreakpoints.expanded
                ? (constraints.maxWidth - (spacingMD * 3)) / 4
                : constraints.maxWidth >= AppBreakpoints.compact
                ? (constraints.maxWidth - spacingMD) / 2
                : constraints.maxWidth;
        return Wrap(
          spacing: spacingMD,
          runSpacing: spacingMD,
          children:
              actions
                  .map(
                    (HomeQuickAction action) => SizedBox(
                      width: width,
                      child: AppHoverLift(
                        child: GtexSurfaceCard(
                          key: ValueKey<String>(
                            'home-action-${action.label.toLowerCase()}',
                          ),
                          glowColor: action.kind.color,
                          onTap: action.onTap,
                          child: Row(
                            children: <Widget>[
                              Container(
                                width: 48,
                                height: 48,
                                decoration: BoxDecoration(
                                  color: action.kind.color.withValues(
                                    alpha: 0.14,
                                  ),
                                  borderRadius: BorderRadius.circular(16),
                                ),
                                child: Icon(
                                  action.icon,
                                  color: action.kind.color,
                                ),
                              ),
                              const SizedBox(width: spacingMD),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: <Widget>[
                                    Text(
                                      action.label,
                                      style:
                                          Theme.of(
                                            context,
                                          ).textTheme.titleLarge,
                                    ),
                                    const SizedBox(height: spacingXS),
                                    Text(
                                      action.caption,
                                      style: Theme.of(
                                        context,
                                      ).textTheme.bodyMedium?.copyWith(
                                        color: AppColors.textSecondary,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  )
                  .toList(),
        );
      },
    );
  }
}

class LiveMatchesCarousel extends StatelessWidget {
  const LiveMatchesCarousel({super.key, required this.matches});

  final List<LiveMatch> matches;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 304,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        physics: const BouncingScrollPhysics(
          parent: AlwaysScrollableScrollPhysics(),
        ),
        itemCount: matches.length,
        separatorBuilder: (_, _) => const SizedBox(width: spacingMD),
        itemBuilder: (BuildContext context, int index) {
          final LiveMatch match = matches[index];
          return SizedBox(
            width: 320,
            child: AppHoverLift(
              child: GtexSurfaceCard(
                glowColor: index == 0 ? AppColors.primary : null,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Row(
                      children: <Widget>[
                        Expanded(
                          child: Text(
                            '${match.homeClub} vs ${match.awayClub}',
                            style: Theme.of(context).textTheme.titleLarge,
                          ),
                        ),
                        MetricPill(
                          label: 'Live',
                          value: '${match.minute}\'',
                          highlight: true,
                        ),
                      ],
                    ),
                    const SizedBox(height: spacingMD),
                    Text(
                      '${match.homeScore} - ${match.awayScore}',
                      style: Theme.of(context).textTheme.headlineLarge
                          ?.copyWith(color: AppColors.gold),
                    ),
                    const SizedBox(height: spacingSM),
                    Text(
                      match.venue,
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                    const SizedBox(height: spacingMD),
                    Text(
                      match.headline,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const Spacer(),
                    Row(
                      children: <Widget>[
                        Expanded(child: StatBar(match.momentum)),
                        const SizedBox(width: spacingSM),
                        Text(
                          'Momentum',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ],
                    ),
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

class StoryHighlightsGrid extends StatelessWidget {
  const StoryHighlightsGrid({super.key, required this.stories});

  final List<HomeStoryHighlight> stories;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
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
              stories
                  .map(
                    (HomeStoryHighlight story) => SizedBox(
                      width: width,
                      child: AppHoverLift(
                        child: GtexSurfaceCard(
                          padding: EdgeInsets.zero,
                          glowColor: story.kind.color,
                          onTap: story.onTap,
                          child: ClipRRect(
                            borderRadius: BorderRadius.circular(cardRadius),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: <Widget>[
                                SizedBox(
                                  height: 168,
                                  child: Stack(
                                    fit: StackFit.expand,
                                    children: <Widget>[
                                      DecoratedBox(
                                        decoration: BoxDecoration(
                                          gradient: LinearGradient(
                                            begin: Alignment.topLeft,
                                            end: Alignment.bottomRight,
                                            colors: <Color>[
                                              story.kind.color.withValues(
                                                alpha: 0.24,
                                              ),
                                              AppColors.surfaceMuted,
                                              AppColors.card,
                                            ],
                                          ),
                                        ),
                                      ),
                                      Positioned.fill(
                                        child: Padding(
                                          padding: const EdgeInsets.all(
                                            spacingLG,
                                          ),
                                          child: Opacity(
                                            opacity: 0.85,
                                            child: Image.asset(
                                              story.imageAsset,
                                              fit: BoxFit.contain,
                                            ),
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                                Padding(
                                  padding: const EdgeInsets.all(spacingMD),
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: <Widget>[
                                      Text(
                                        story.title,
                                        style:
                                            Theme.of(
                                              context,
                                            ).textTheme.titleLarge,
                                      ),
                                      const SizedBox(height: spacingSM),
                                      Text(story.caption),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ),
                  )
                  .toList(),
        );
      },
    );
  }
}

class DailyTasksGrid extends StatelessWidget {
  const DailyTasksGrid({
    super.key,
    required this.tasks,
    required this.claimedTaskIds,
    required this.onClaim,
  });

  final List<DailyTask> tasks;
  final Set<String> claimedTaskIds;
  final ValueChanged<DailyTask> onClaim;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
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
              tasks
                  .map(
                    (DailyTask task) => SizedBox(
                      width: width,
                      child: _DailyTaskCard(
                        task: task,
                        claimed: claimedTaskIds.contains(task.id),
                        onClaim: () => onClaim(task),
                      ),
                    ),
                  )
                  .toList(),
        );
      },
    );
  }
}

class _DailyTaskCard extends StatelessWidget {
  const _DailyTaskCard({
    required this.task,
    required this.claimed,
    required this.onClaim,
  });

  final DailyTask task;
  final bool claimed;
  final VoidCallback onClaim;

  @override
  Widget build(BuildContext context) {
    final bool canClaim = task.isComplete && !claimed;
    return AppHoverLift(
      child: GtexSurfaceCard(
        glowColor: claimed ? AppColors.primary : null,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Expanded(
                  child: Text(
                    task.title,
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                ),
                MetricPill(
                  label: 'Progress',
                  value: '${task.current}/${task.target}',
                  highlight: task.isComplete,
                ),
              ],
            ),
            const SizedBox(height: spacingSM),
            Text(
              'Reward ${task.reward}',
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: AppColors.gold),
            ),
            const SizedBox(height: spacingMD),
            StatBar(task.progress),
            const SizedBox(height: spacingSM),
            Text(
              claimed
                  ? 'Reward claimed.'
                  : task.isComplete
                  ? 'Task complete. Claim your reward.'
                  : 'Complete the objective to unlock the reward.',
            ),
            const SizedBox(height: spacingMD),
            SizedBox(
              width: double.infinity,
              child: AppPressScale(
                enabled: canClaim,
                child: FilledButton(
                  onPressed: canClaim ? onClaim : null,
                  child: Text(
                    claimed
                        ? 'Claimed'
                        : task.isComplete
                        ? 'Claim Reward'
                        : 'Claim Locked',
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _FansSentiment {
  const _FansSentiment({
    required this.label,
    required this.description,
    required this.delta,
    required this.icon,
    required this.kind,
  });

  final String label;
  final String description;
  final String delta;
  final IconData icon;
  final HomeCardKind kind;

  factory _FansSentiment.fromClub(Club club) {
    final int wins =
        club.formLabel.split('').where((String value) => value == 'W').length;
    if (wins >= 4) {
      return const _FansSentiment(
        label: 'Electric',
        description: 'Supporters are fully behind the current run of form.',
        delta: '+18%',
        icon: Icons.bolt_rounded,
        kind: HomeCardKind.primary,
      );
    }
    if (wins >= 2) {
      return const _FansSentiment(
        label: 'Steady',
        description:
            'Confidence is healthy, but one more strong result will raise the ceiling.',
        delta: '+7%',
        icon: Icons.trending_up_rounded,
        kind: HomeCardKind.gold,
      );
    }
    return const _FansSentiment(
      label: 'Watching Closely',
      description:
          'The fan base wants a sharper response before momentum returns.',
      delta: '-3%',
      icon: Icons.insights_rounded,
      kind: HomeCardKind.gold,
    );
  }
}
