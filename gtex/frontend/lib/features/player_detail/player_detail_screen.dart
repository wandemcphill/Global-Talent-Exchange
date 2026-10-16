import 'package:flutter/material.dart';

import '../../core/constants/app_spacing.dart';
import '../../shared/models/player.dart';
import '../../shared/widgets/app_background.dart';
import 'widgets/player_detail_widgets.dart';

class PlayerDetailScreen extends StatefulWidget {
  const PlayerDetailScreen({
    super.key,
    required this.player,
    this.heroTag,
    this.storyBeats = const <PlayerStoryBeat>[],
    this.careerEntries = const <PlayerCareerEntry>[],
    this.offers = const <PlayerMarketOffer>[],
  });

  final Player player;
  final String? heroTag;
  final List<PlayerStoryBeat> storyBeats;
  final List<PlayerCareerEntry> careerEntries;
  final List<PlayerMarketOffer> offers;

  @override
  State<PlayerDetailScreen> createState() => _PlayerDetailScreenState();
}

class _PlayerDetailScreenState extends State<PlayerDetailScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabController;
  bool _entered = false;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        setState(() => _entered = true);
      }
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final Player player = widget.player;
    final String heroTag = widget.heroTag ?? playerDetailHeroTag(player);
    final List<String> badges = _buildBadges(player);
    final List<PlayerStoryBeat> storyBeats =
        widget.storyBeats.isEmpty
            ? _buildStoryBeats(player)
            : widget.storyBeats;
    final List<PlayerCareerEntry> careerEntries =
        widget.careerEntries.isEmpty
            ? _buildCareerEntries(player)
            : widget.careerEntries;
    final List<PlayerMarketOffer> offers =
        widget.offers.isEmpty ? _buildOffers(player) : widget.offers;
    final List<PlayerAttribute> attributes = _buildAttributes(player);
    final double horizontalPadding =
        MediaQuery.sizeOf(context).width >= 1024 ? spacingLG : spacingMD;
    final double bottomPadding = MediaQuery.paddingOf(context).bottom + 96;

    return AppBackground(
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(title: const Text('Player Detail')),
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
                    padding: EdgeInsets.fromLTRB(
                      horizontalPadding,
                      spacingLG,
                      horizontalPadding,
                      spacingLG,
                    ),
                    child: AnimatedSlide(
                      duration: const Duration(milliseconds: 360),
                      curve: Curves.easeOutCubic,
                      offset: _entered ? Offset.zero : const Offset(0, 0.05),
                      child: AnimatedOpacity(
                        duration: const Duration(milliseconds: 320),
                        opacity: _entered ? 1 : 0,
                        child: PlayerDetailHeader(
                          player: player,
                          heroTag: heroTag,
                          badges: badges,
                        ),
                      ),
                    ),
                  ),
                ),
                SliverPersistentHeader(
                  pinned: true,
                  delegate: _StickyTabBarDelegate(
                    child: Padding(
                      padding: EdgeInsets.fromLTRB(
                        horizontalPadding,
                        0,
                        horizontalPadding,
                        spacingMD,
                      ),
                      child: PlayerDetailTabBar(controller: _tabController),
                    ),
                  ),
                ),
              ];
            },
            body: Padding(
              padding: EdgeInsets.symmetric(horizontal: horizontalPadding),
              child: TabBarView(
                controller: _tabController,
                physics: const BouncingScrollPhysics(
                  parent: AlwaysScrollableScrollPhysics(),
                ),
                children: <Widget>[
                  PlayerStatsTab(
                    attributes: attributes,
                    bottomPadding: bottomPadding,
                  ),
                  PlayerStoryTab(
                    storyBeats: storyBeats,
                    bottomPadding: bottomPadding,
                  ),
                  PlayerCareerTab(
                    careerEntries: careerEntries,
                    bottomPadding: bottomPadding,
                  ),
                  PlayerOffersTab(offers: offers, bottomPadding: bottomPadding),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _StickyTabBarDelegate extends SliverPersistentHeaderDelegate {
  const _StickyTabBarDelegate({required this.child});

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
    return ColoredBox(color: Colors.transparent, child: child);
  }

  @override
  bool shouldRebuild(covariant _StickyTabBarDelegate oldDelegate) {
    return oldDelegate.child != child;
  }
}

List<String> _buildBadges(Player player) {
  final List<String> badges = <String>[];

  if (isElitePlayer(player)) {
    badges.add('Elite');
  }
  if (player.potential >= 90) {
    badges.add('Wonderkid');
  }
  if (player.isHot) {
    badges.add('Hot Streak');
  }
  if (player.mentality >= 0.84) {
    badges.add('Leader');
  }
  if (badges.isEmpty) {
    badges.add('Rising');
  }

  return badges;
}

List<PlayerAttribute> _buildAttributes(Player player) {
  final double developmentCurve = ((player.potential - player.rating) / 20)
      .clamp(0.25, 1.0);
  final double marketGravity =
      (player.valueInMillions / (player.valueInMillions + 20)).clamp(0.35, 1.0);

  return <PlayerAttribute>[
    PlayerAttribute(
      label: 'Pace',
      value: player.pace,
      caption: 'Transition speed and burst over short distance.',
    ),
    PlayerAttribute(
      label: 'Technique',
      value: player.technique,
      caption: 'Ball mastery, control quality, and creative execution.',
    ),
    PlayerAttribute(
      label: 'Mentality',
      value: player.mentality,
      caption: 'Game intelligence, resilience, and pressure handling.',
    ),
    PlayerAttribute(
      label: 'Potential',
      value: (player.potential / 100).clamp(0, 1),
      caption: 'Projected ceiling across the next development cycle.',
    ),
    PlayerAttribute(
      label: 'Development Curve',
      value: developmentCurve,
      caption: 'How much room remains between the current floor and ceiling.',
    ),
    PlayerAttribute(
      label: 'Market Gravity',
      value: marketGravity,
      caption: 'How strongly clubs are expected to compete for the player.',
    ),
  ];
}

List<PlayerStoryBeat> _buildStoryBeats(Player player) {
  return <PlayerStoryBeat>[
    PlayerStoryBeat(
      phase: 'Age 12',
      title: 'Grassroots spark',
      description:
          '${player.name} surfaced as a standout ${player.position} prospect in ${player.country} with early burst and clean touch.',
      icon: Icons.sports_soccer_rounded,
    ),
    PlayerStoryBeat(
      phase: 'Age 15',
      title: 'Academy leap',
      description:
          'Technical sessions accelerated rapidly as scouts flagged top-end upside and a disciplined learning profile.',
      icon: Icons.school_rounded,
      highlight: player.technique >= 0.82,
    ),
    PlayerStoryBeat(
      phase: 'Age ${player.age - 1}',
      title: 'First-team ignition',
      description:
          'The jump toward senior football sharpened decision-making and turned raw tools into repeatable production.',
      icon: Icons.flash_on_rounded,
      highlight: player.isHot,
    ),
    PlayerStoryBeat(
      phase: 'Now',
      title: 'Market pressure rising',
      description:
          'With an overall of ${player.rating} and a ceiling of ${player.potential}, the market now treats the profile as a premium growth asset.',
      icon: Icons.trending_up_rounded,
      highlight: isElitePlayer(player),
    ),
  ];
}

List<PlayerCareerEntry> _buildCareerEntries(Player player) {
  final int academyYears = (player.age - 4).clamp(8, 16);
  final int seniorAppearances = 18 + ((player.rating + player.age) % 15);
  final int goalContribution =
      player.position == 'CB' || player.position == 'GK'
          ? 3 + (player.rating % 5)
          : 10 + (player.rating % 9);

  return <PlayerCareerEntry>[
    PlayerCareerEntry(
      period: '$academyYears-${academyYears + 2}',
      club: '${player.country} Regional Academy',
      summary:
          'Foundation years built around athletic base, first-touch repetition, and position identity.',
      statLine: 'Academy captaincy track established.',
    ),
    PlayerCareerEntry(
      period: '${academyYears + 2}-${academyYears + 4}',
      club: 'GTEX Youth Select',
      summary:
          'Entered a higher-intensity pathway with more tactical structure and continental exposure.',
      statLine: 'U-19 showcase selections: 8',
    ),
    PlayerCareerEntry(
      period: '${academyYears + 4}-${academyYears + 5}',
      club: 'Senior breakthrough squad',
      summary:
          'Began translating prospect tools into senior production with more demanding game states.',
      statLine:
          'Appearances $seniorAppearances | Impact plays $goalContribution',
    ),
    PlayerCareerEntry(
      period: 'Now',
      club: 'National radar pool',
      summary:
          'Shortlisted for next-cycle international tracking as the profile gains traction across major scouting networks.',
      statLine: 'Scouting priority: Tier 1',
      current: true,
    ),
  ];
}

List<PlayerMarketOffer> _buildOffers(Player player) {
  final double base = player.valueInMillions;
  return <PlayerMarketOffer>[
    PlayerMarketOffer(
      club: 'North Star FC',
      amountInMillions: base + 4,
      structure: 'Guaranteed fee plus performance escalators',
      deadlineLabel: 'Decision window closes in 18 hours',
      status: PlayerOfferStatus.leading,
    ),
    PlayerMarketOffer(
      club: 'Emerald Union',
      amountInMillions: base + 2.5,
      structure: 'Straight cash offer with resale clause',
      deadlineLabel: 'Bid refresh expected by tomorrow',
      status: PlayerOfferStatus.active,
    ),
    PlayerMarketOffer(
      club: 'Metro Sporting',
      amountInMillions: base + 1.2,
      structure: 'Loan-to-buy structure under review',
      deadlineLabel: 'Monitoring before final move',
      status: PlayerOfferStatus.watching,
    ),
  ];
}
