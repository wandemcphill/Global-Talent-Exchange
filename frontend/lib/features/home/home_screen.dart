import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/constants/app_breakpoints.dart';
import '../../core/constants/app_spacing.dart';
import '../../core/widgets/app_press_scale.dart';
import '../../core/widgets/task_reward_pop.dart';
import '../../navigation/app_destinations.dart';
import '../../shared/models/club.dart';
import '../../shared/models/daily_task.dart';
import '../../shared/models/live_match.dart';
import '../../shared/providers/club_provider.dart';
import '../../shared/providers/match_provider.dart';
import '../../shared/providers/tasks_provider.dart';
import 'widgets/home_screen_widgets.dart';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  @override
  Widget build(BuildContext context) {
    final Club club = ref.watch(clubProvider);
    final List<LiveMatch> matches = ref.watch(matchProvider);
    final TasksState taskState = ref.watch(tasksProvider);
    final List<DailyTask> tasks = taskState.dailyTasks;

    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final double horizontalPadding =
            constraints.maxWidth >= AppBreakpoints.medium
                ? spacingLG
                : spacingMD;
        final double bottomPadding =
            MediaQuery.viewPaddingOf(context).bottom + 120;

        return Align(
          alignment: Alignment.topCenter,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1440),
            child: ListView(
              key: const PageStorageKey<String>('gtex-home-scroll'),
              physics: const BouncingScrollPhysics(
                parent: AlwaysScrollableScrollPhysics(),
              ),
              padding: EdgeInsets.fromLTRB(
                horizontalPadding,
                spacingLG,
                horizontalPadding,
                bottomPadding,
              ),
              children: <Widget>[
                HomeAnimatedSection(
                  delay: const Duration(milliseconds: 60),
                  child: ClubOverviewCard(
                    club: club,
                    onPlay: () => context.go(AppRoutes.matches),
                    onProfile: () => context.go(AppRoutes.profile),
                  ),
                ),
                const SizedBox(height: spacingLG),
                HomeAnimatedSection(
                  delay: const Duration(milliseconds: 140),
                  child: HomeSection(
                    title: 'Quick Actions',
                    subtitle:
                        'Direct access to play, market, academy tracking, and competition flow.',
                    child: QuickActionsGrid(
                      actions: <HomeQuickAction>[
                        HomeQuickAction(
                          label: 'Play',
                          caption: 'Jump into the live match deck.',
                          icon: Icons.play_circle_fill_rounded,
                          kind: HomeCardKind.primary,
                          onTap: () => context.go(AppRoutes.matches),
                        ),
                        HomeQuickAction(
                          label: 'Market',
                          caption:
                              'Open the wallet, payment rails, and player shares desk.',
                          icon: Icons.storefront_rounded,
                          kind: HomeCardKind.gold,
                          onTap: () => context.go(AppRoutes.market),
                        ),
                        HomeQuickAction(
                          label: 'Academy',
                          caption: 'Review breakout prospects and pathways.',
                          icon: Icons.school_rounded,
                          kind: HomeCardKind.primary,
                          onTap: () => context.go(AppRoutes.world),
                        ),
                        HomeQuickAction(
                          label: 'Competitions',
                          caption: 'Track brackets, fixtures, and spotlight.',
                          icon: Icons.emoji_events_rounded,
                          kind: HomeCardKind.gold,
                          onTap: () => context.go(AppRoutes.world),
                        ),
                        HomeQuickAction(
                          label: 'Tasks',
                          caption: 'Claim rewards and hold the streak flame.',
                          icon: Icons.task_alt_rounded,
                          kind: HomeCardKind.primary,
                          onTap: () => context.push(AppRoutes.tasks),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: spacingLG),
                HomeAnimatedSection(
                  delay: const Duration(milliseconds: 220),
                  child: HomeSection(
                    title: 'Live Matches',
                    subtitle:
                        'Smooth horizontal scrolling across the live match slate.',
                    trailingLabel: '${matches.length} live',
                    child: LiveMatchesCarousel(matches: matches),
                  ),
                ),
                const SizedBox(height: spacingLG),
                HomeAnimatedSection(
                  delay: const Duration(milliseconds: 300),
                  child: HomeSection(
                    title: 'Story Highlights',
                    subtitle:
                        'Visual cards for the biggest GTEX stories shaping your next move.',
                    child: StoryHighlightsGrid(
                      stories: <HomeStoryHighlight>[
                        HomeStoryHighlight(
                          title: '${club.name} academy wave lifts fan optimism',
                          caption:
                              'Youth scouting confidence is rising across the club.',
                          imageAsset: club.badgeAsset,
                          kind: HomeCardKind.primary,
                          onTap: () => context.go(AppRoutes.world),
                        ),
                        HomeStoryHighlight(
                          title:
                              'Broadcast buzz spikes after a dramatic finish',
                          caption:
                              'Live match demand is climbing after late-game chaos.',
                          imageAsset: 'assets/branding/gtex_icon.png',
                          kind: HomeCardKind.gold,
                          onTap: () => context.go(AppRoutes.matches),
                        ),
                        HomeStoryHighlight(
                          title:
                              'Transfer chatter intensifies around elite prospects',
                          caption:
                              'Market attention is closing in on your tracked names.',
                          imageAsset: 'assets/branding/gtex_logo.png',
                          kind: HomeCardKind.primary,
                          onTap: () => context.go(AppRoutes.market),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: spacingLG),
                HomeAnimatedSection(
                  delay: const Duration(milliseconds: 380),
                  child: HomeSection(
                    title: 'Daily Tasks',
                    subtitle:
                        'Progress loops with rewards, claim states, and clean feedback.',
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        DailyTasksGrid(
                          tasks: tasks,
                          claimedTaskIds: taskState.claimedTaskIds,
                          onClaim: _claimTask,
                        ),
                        const SizedBox(height: spacingMD),
                        AppPressScale(
                          child: OutlinedButton.icon(
                            onPressed: () => context.push(AppRoutes.tasks),
                            icon: const Icon(
                              Icons.local_fire_department_rounded,
                            ),
                            label: const Text('Open Tasks & Streak'),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  void _claimTask(DailyTask task) {
    final TaskClaimResult? result = ref
        .read(tasksProvider.notifier)
        .claimTask(task.id);
    if (result == null) {
      return;
    }

    showTaskRewardCelebration(context, result);
  }
}
