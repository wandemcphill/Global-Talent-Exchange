import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/constants/app_breakpoints.dart';
import '../../core/constants/app_spacing.dart';
import '../../core/theme/app_colors.dart';
import '../../core/utils/app_formatters.dart';
import '../../core/widgets/app_hover_lift.dart';
import '../../core/widgets/app_press_scale.dart';
import '../../core/widgets/gtex_surface_card.dart';
import '../../shared/models/auth_session.dart';
import '../../shared/models/club.dart';
import '../../shared/models/live_match.dart';
import '../../shared/providers/auth_provider.dart';
import '../../shared/providers/club_provider.dart';
import '../../shared/providers/match_provider.dart';
import '../../shared/providers/transfer_provider.dart';
import '../../shared/widgets/app_page_layout.dart';
import '../../shared/widgets/metric_pill.dart';

class ProfileScreen extends ConsumerStatefulWidget {
  const ProfileScreen({super.key});

  @override
  ConsumerState<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends ConsumerState<ProfileScreen> {
  bool _isFollowing = false;

  @override
  Widget build(BuildContext context) {
    final AuthSession auth = ref.watch(authProvider);
    final Club club = ref.watch(clubProvider);
    final List<LiveMatch> liveMatches = ref.watch(matchProvider);
    final TransferMarketState marketState = ref.watch(transferProvider);
    final TransferMarketListing? featuredTransfer = _featuredListing(
      marketState.listings,
    );
    final LiveMatch? featuredMatch = _featuredMatch(liveMatches, club);
    final int formWins = _countWins(club.formLabel);
    final int followers = _baseFollowerCount(
      club: club,
      liveMatches: liveMatches.length,
      formWins: formWins,
      marketWatchers: featuredTransfer?.watcherCount ?? 0,
    );
    final int visibleFollowers = followers + (_isFollowing ? 1 : 0);

    final List<_ProfileAchievement> achievements = <_ProfileAchievement>[
      _ProfileAchievement(
        title: 'Follower Reach',
        value: _formatCount(visibleFollowers),
        description:
            'Audience lift is compounding across matchday noise, academy credibility, and market interest.',
        icon: Icons.groups_rounded,
        glowColor: AppColors.primary,
      ),
      _ProfileAchievement(
        title: 'Winning Form',
        value: '$formWins/${club.formLabel.length}',
        description:
            'Recent results keep ${club.name} circulating in supporter and scout conversations.',
        icon: Icons.emoji_events_rounded,
        glowColor: AppColors.gold,
      ),
      _ProfileAchievement(
        title: 'Academy Prestige',
        value: 'Tier ${club.academyLevel}',
        description:
            'A top-tier youth setup gives every profile update more long-horizon trust.',
        icon: Icons.school_rounded,
        glowColor: AppColors.primary,
      ),
      _ProfileAchievement(
        title: 'Transfer Gravity',
        value:
            featuredTransfer == null
                ? '${marketState.listings.length} rooms'
                : '${featuredTransfer.watcherCount} watchers',
        description:
            featuredTransfer == null
                ? 'Scouting pressure is active across the current market slate.'
                : '${featuredTransfer.player.name} is anchoring the loudest transfer conversation right now.',
        icon: Icons.swap_horiz_rounded,
        glowColor: AppColors.gold,
      ),
    ];

    final List<_ProfileFeedEntry> feedEntries = <_ProfileFeedEntry>[
      if (featuredTransfer != null)
        _ProfileFeedEntry(
          type: _ProfileFeedType.transfer,
          title: 'Transfer pressure rises',
          body:
              '${club.name} is tracking ${featuredTransfer.player.name} as bidding climbs to ${AppFormatters.money(featuredTransfer.currentBidInMillions)} with ${featuredTransfer.watcherCount} active watchers.',
          timestamp: '18m ago',
        ),
      _ProfileFeedEntry(
        type: _ProfileFeedType.win,
        title: 'Winning momentum holds',
        body:
            featuredMatch == null
                ? '${club.name} has banked $formWins wins from the last ${club.formLabel.length} fixtures and keeps the profile trending upward.'
                : '${club.name} has $formWins wins in the last ${club.formLabel.length} matches and is now ${_matchScoreline(featuredMatch, club)} at ${featuredMatch.minute}\'.',
        timestamp: featuredMatch == null ? '2h ago' : 'Live now',
      ),
      _ProfileFeedEntry(
        type: _ProfileFeedType.milestone,
        title: 'Follower milestone unlocked',
        body:
            'The profile pushed through ${_formatCount(visibleFollowers)} followers behind academy tier ${club.academyLevel}, ${AppFormatters.compact(club.fans)} fans, and sustained matchday attention.',
        timestamp: 'Today',
      ),
    ];

    return AppPageLayout(
      title: 'Profile',
      subtitle:
          'Social presence, achievements, and public-facing activity for the club identity.',
      trailing: MetricPill(
        label: 'Reach',
        value: AppFormatters.compact(visibleFollowers),
        highlight: true,
      ),
      children: <Widget>[
        _ProfileHeaderCard(
          auth: auth,
          club: club,
          followers: visibleFollowers,
          liveMatches: liveMatches.length,
          formWins: formWins,
          isFollowing: _isFollowing,
          onFollowToggle: () => _toggleFollow(club.name),
        ),
        _SectionBlock(
          title: 'Achievements',
          subtitle:
              'Proof points that make the profile feel earned instead of empty.',
          child: _AchievementsGrid(achievements: achievements),
        ),
        _ActivityFeedCard(feedEntries: feedEntries),
      ],
    );
  }

  void _toggleFollow(String clubName) {
    setState(() {
      _isFollowing = !_isFollowing;
    });

    final String action = _isFollowing ? 'Following' : 'Stopped following';
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text('$action $clubName.')));
  }
}

class _ProfileHeaderCard extends StatelessWidget {
  const _ProfileHeaderCard({
    required this.auth,
    required this.club,
    required this.followers,
    required this.liveMatches,
    required this.formWins,
    required this.isFollowing,
    required this.onFollowToggle,
  });

  final AuthSession auth;
  final Club club;
  final int followers;
  final int liveMatches;
  final int formWins;
  final bool isFollowing;
  final VoidCallback onFollowToggle;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final bool wide = constraints.maxWidth >= AppBreakpoints.medium;
        final Widget identity = Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Stack(
              clipBehavior: Clip.none,
              children: <Widget>[
                CircleAvatar(
                  radius: 38,
                  backgroundColor: AppColors.surfaceMuted,
                  backgroundImage: AssetImage(auth.avatarAsset),
                ),
                Positioned(
                  right: -4,
                  bottom: -4,
                  child: Container(
                    padding: const EdgeInsets.all(3),
                    decoration: BoxDecoration(
                      color: AppColors.background,
                      borderRadius: BorderRadius.circular(999),
                      border: Border.all(color: AppColors.divider),
                    ),
                    child: CircleAvatar(
                      radius: 15,
                      backgroundColor: AppColors.card,
                      backgroundImage: AssetImage(club.badgeAsset),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(width: spacingMD),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    auth.userName,
                    style: Theme.of(context).textTheme.headlineMedium,
                  ),
                  const SizedBox(height: spacingXS),
                  Text(
                    '${auth.role} | ${club.name}',
                    style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                      color: AppColors.textSecondary,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: spacingSM),
                  Text(
                    '${_formatCount(followers)} followers',
                    style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      color: AppColors.textPrimary,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: spacingXS),
                  Text(
                    'Matchday visibility, transfer chatter, and academy reputation all feed this public profile.',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: AppColors.textSecondary,
                    ),
                  ),
                ],
              ),
            ),
          ],
        );

        final Widget stats = Wrap(
          spacing: spacingSM,
          runSpacing: spacingSM,
          children: <Widget>[
            MetricPill(
              label: 'Fans',
              value: AppFormatters.compact(club.fans),
              highlight: true,
            ),
            MetricPill(
              label: 'Form',
              value: '$formWins/${club.formLabel.length}',
            ),
            MetricPill(label: 'Live', value: '$liveMatches'),
            MetricPill(label: 'League', value: club.league),
          ],
        );

        final Widget action = Align(
          alignment: wide ? Alignment.topRight : Alignment.centerLeft,
          child: AppPressScale(
            child: FilledButton.icon(
              onPressed: onFollowToggle,
              style: FilledButton.styleFrom(
                backgroundColor:
                    isFollowing ? AppColors.surfaceMuted : AppColors.primary,
                foregroundColor:
                    isFollowing ? AppColors.textPrimary : AppColors.background,
                padding: const EdgeInsets.symmetric(
                  horizontal: spacingLG,
                  vertical: spacingMD,
                ),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(999),
                ),
              ),
              icon: Icon(
                isFollowing
                    ? Icons.check_circle_rounded
                    : Icons.person_add_alt_1_rounded,
              ),
              label: Text(isFollowing ? 'Following' : 'Follow'),
            ),
          ),
        );

        if (!wide) {
          return GtexSurfaceCard(
            glowColor: AppColors.primary,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                identity,
                const SizedBox(height: spacingLG),
                stats,
                const SizedBox(height: spacingLG),
                action,
              ],
            ),
          );
        }

        return GtexSurfaceCard(
          glowColor: AppColors.primary,
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Expanded(
                flex: 3,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    identity,
                    const SizedBox(height: spacingLG),
                    stats,
                  ],
                ),
              ),
              const SizedBox(width: spacingLG),
              Expanded(flex: 1, child: action),
            ],
          ),
        );
      },
    );
  }
}

class _SectionBlock extends StatelessWidget {
  const _SectionBlock({
    required this.title,
    required this.subtitle,
    required this.child,
  });

  final String title;
  final String subtitle;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(title, style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: spacingXS),
        Text(
          subtitle,
          style: Theme.of(
            context,
          ).textTheme.bodyMedium?.copyWith(color: AppColors.textSecondary),
        ),
        const SizedBox(height: spacingMD),
        child,
      ],
    );
  }
}

class _AchievementsGrid extends StatelessWidget {
  const _AchievementsGrid({required this.achievements});

  final List<_ProfileAchievement> achievements;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final double cardWidth = _cardWidthFor(constraints.maxWidth);

        return Wrap(
          spacing: spacingMD,
          runSpacing: spacingMD,
          children:
              achievements
                  .map(
                    (_ProfileAchievement achievement) => SizedBox(
                      width: cardWidth,
                      child: AppHoverLift(
                        child: GtexSurfaceCard(
                          glowColor: achievement.glowColor,
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Container(
                                width: 48,
                                height: 48,
                                decoration: BoxDecoration(
                                  color: achievement.glowColor.withValues(
                                    alpha: 0.14,
                                  ),
                                  borderRadius: BorderRadius.circular(14),
                                  border: Border.all(
                                    color: achievement.glowColor.withValues(
                                      alpha: 0.35,
                                    ),
                                  ),
                                ),
                                child: Icon(
                                  achievement.icon,
                                  color: achievement.glowColor,
                                ),
                              ),
                              const SizedBox(height: spacingLG),
                              Text(
                                achievement.value,
                                style: Theme.of(context).textTheme.headlineSmall
                                    ?.copyWith(fontWeight: FontWeight.w800),
                              ),
                              const SizedBox(height: spacingXS),
                              Text(
                                achievement.title,
                                style: Theme.of(context).textTheme.titleLarge,
                              ),
                              const SizedBox(height: spacingSM),
                              Text(
                                achievement.description,
                                style: Theme.of(context).textTheme.bodyMedium
                                    ?.copyWith(color: AppColors.textSecondary),
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

  double _cardWidthFor(double maxWidth) {
    if (maxWidth >= AppBreakpoints.expanded) {
      return (maxWidth - (spacingMD * 3)) / 4;
    }
    if (maxWidth >= AppBreakpoints.compact) {
      return (maxWidth - spacingMD) / 2;
    }
    return maxWidth;
  }
}

class _ActivityFeedCard extends StatelessWidget {
  const _ActivityFeedCard({required this.feedEntries});

  final List<_ProfileFeedEntry> feedEntries;

  @override
  Widget build(BuildContext context) {
    return GtexSurfaceCard(
      glowColor: AppColors.gold,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Activity Feed',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: spacingXS),
          Text(
            'Transfers, wins, and milestones all land in the public timeline here.',
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(color: AppColors.textSecondary),
          ),
          const SizedBox(height: spacingLG),
          for (int index = 0; index < feedEntries.length; index++) ...<Widget>[
            _ActivityFeedItem(entry: feedEntries[index]),
            if (index != feedEntries.length - 1) ...<Widget>[
              const SizedBox(height: spacingMD),
              Divider(color: AppColors.divider, height: 1),
              const SizedBox(height: spacingMD),
            ],
          ],
        ],
      ),
    );
  }
}

class _ActivityFeedItem extends StatelessWidget {
  const _ActivityFeedItem({required this.entry});

  final _ProfileFeedEntry entry;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Container(
          width: 48,
          height: 48,
          decoration: BoxDecoration(
            color: entry.type.color.withValues(alpha: 0.14),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: entry.type.color.withValues(alpha: 0.35)),
          ),
          child: Icon(entry.type.icon, color: entry.type.color),
        ),
        const SizedBox(width: spacingMD),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Wrap(
                spacing: spacingSM,
                runSpacing: spacingSM,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: <Widget>[
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: spacingSM,
                      vertical: 6,
                    ),
                    decoration: BoxDecoration(
                      color: entry.type.color.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(999),
                      border: Border.all(
                        color: entry.type.color.withValues(alpha: 0.25),
                      ),
                    ),
                    child: Text(
                      entry.type.label,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: entry.type.color,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  Text(
                    entry.timestamp,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: AppColors.textSecondary,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: spacingSM),
              Text(
                entry.title,
                style: Theme.of(
                  context,
                ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: spacingXS),
              Text(
                entry.body,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: AppColors.textSecondary,
                  height: 1.45,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _ProfileAchievement {
  const _ProfileAchievement({
    required this.title,
    required this.value,
    required this.description,
    required this.icon,
    required this.glowColor,
  });

  final String title;
  final String value;
  final String description;
  final IconData icon;
  final Color glowColor;
}

class _ProfileFeedEntry {
  const _ProfileFeedEntry({
    required this.type,
    required this.title,
    required this.body,
    required this.timestamp,
  });

  final _ProfileFeedType type;
  final String title;
  final String body;
  final String timestamp;
}

enum _ProfileFeedType { transfer, win, milestone }

extension on _ProfileFeedType {
  String get label {
    return switch (this) {
      _ProfileFeedType.transfer => 'Transfer',
      _ProfileFeedType.win => 'Win',
      _ProfileFeedType.milestone => 'Milestone',
    };
  }

  IconData get icon {
    return switch (this) {
      _ProfileFeedType.transfer => Icons.swap_horiz_rounded,
      _ProfileFeedType.win => Icons.emoji_events_rounded,
      _ProfileFeedType.milestone => Icons.auto_awesome_rounded,
    };
  }

  Color get color {
    return switch (this) {
      _ProfileFeedType.transfer => AppColors.primary,
      _ProfileFeedType.win => AppColors.gold,
      _ProfileFeedType.milestone => AppColors.success,
    };
  }
}

int _baseFollowerCount({
  required Club club,
  required int liveMatches,
  required int formWins,
  required int marketWatchers,
}) {
  return (club.fans ~/ 8) +
      (club.academyLevel * 24000) +
      (formWins * 8500) +
      (liveMatches * 3200) +
      (marketWatchers * 180);
}

int _countWins(String formLabel) {
  return formLabel
      .toUpperCase()
      .split('')
      .where((String result) => result == 'W')
      .length;
}

TransferMarketListing? _featuredListing(List<TransferMarketListing> listings) {
  if (listings.isEmpty) {
    return null;
  }

  TransferMarketListing featured = listings.first;
  for (final TransferMarketListing listing in listings.skip(1)) {
    if (listing.watcherCount > featured.watcherCount ||
        (listing.watcherCount == featured.watcherCount &&
            listing.currentBidInMillions > featured.currentBidInMillions)) {
      featured = listing;
    }
  }
  return featured;
}

LiveMatch? _featuredMatch(List<LiveMatch> liveMatches, Club club) {
  if (liveMatches.isEmpty) {
    return null;
  }

  final String clubLabel = club.name.toLowerCase().replaceAll(' fc', '');
  for (final LiveMatch match in liveMatches) {
    final String homeClub = match.homeClub.toLowerCase();
    final String awayClub = match.awayClub.toLowerCase();
    if (homeClub.contains(clubLabel) || awayClub.contains(clubLabel)) {
      return match;
    }
  }

  return liveMatches.first;
}

String _matchScoreline(LiveMatch match, Club club) {
  final String clubLabel = club.name.toLowerCase().replaceAll(' fc', '');
  final bool isHomeClub = match.homeClub.toLowerCase().contains(clubLabel);
  final String opponent = isHomeClub ? match.awayClub : match.homeClub;
  final int goalsFor = isHomeClub ? match.homeScore : match.awayScore;
  final int goalsAgainst = isHomeClub ? match.awayScore : match.homeScore;

  return '$goalsFor-$goalsAgainst versus $opponent';
}

String _formatCount(int value) {
  final String raw = value.abs().toString();
  final StringBuffer buffer = StringBuffer();

  for (int index = 0; index < raw.length; index++) {
    if (index > 0 && (raw.length - index) % 3 == 0) {
      buffer.write(',');
    }
    buffer.write(raw[index]);
  }

  return value < 0 ? '-${buffer.toString()}' : buffer.toString();
}
