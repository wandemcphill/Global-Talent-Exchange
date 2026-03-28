import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/constants/app_breakpoints.dart';
import '../../core/constants/app_spacing.dart';
import '../../core/theme/app_colors.dart';
import '../../shared/models/club.dart';
import '../../shared/models/player.dart';
import '../../shared/providers/club_provider.dart';
import '../../shared/providers/regen_provider.dart';
import '../../shared/widgets/metric_pill.dart';
import '../../shared/widgets/section_heading.dart';
import 'widgets/club_screen_widgets.dart';

class ClubScreen extends ConsumerStatefulWidget {
  const ClubScreen({super.key});

  @override
  ConsumerState<ClubScreen> createState() => _ClubScreenState();
}

class _ClubScreenState extends ConsumerState<ClubScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabController;
  late List<ClubFormationSlot> _slots;
  late List<Player> _benchPlayers;
  bool _entered = false;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);

    final List<Player> regens = ref.read(regenProvider);
    _slots = _buildInitialSlots();
    _benchPlayers = _buildBenchPlayers(regens);

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

  void _swapPlayers(int fromIndex, int toIndex) {
    if (fromIndex == toIndex) {
      return;
    }

    setState(() {
      final Player fromPlayer = _slots[fromIndex].player;
      final Player toPlayer = _slots[toIndex].player;
      _slots[fromIndex] = _slots[fromIndex].copyWith(player: toPlayer);
      _slots[toIndex] = _slots[toIndex].copyWith(player: fromPlayer);
    });
  }

  @override
  Widget build(BuildContext context) {
    final Club club = ref.watch(clubProvider);
    final double fanMood = _buildFanMood(club);
    final List<ClubFinancePoint> financePoints = _buildFinancePoints(club);
    final List<ClubFinanceBreakdown> financeBreakdown = _buildFinanceBreakdown(
      club,
    );
    final List<ClubFanSignal> fanSignals = _buildFanSignals(club);
    final List<ClubIdentityPillar> identityPillars = _buildIdentityPillars(
      club,
    );
    final double identityScore = _buildIdentityScore(identityPillars);

    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final double horizontalPadding =
            constraints.maxWidth >= AppBreakpoints.medium
                ? spacingLG
                : spacingMD;
        final double bottomPadding = MediaQuery.paddingOf(context).bottom + 88;

        return Align(
          alignment: Alignment.topCenter,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1440),
            child: Padding(
              padding: EdgeInsets.fromLTRB(
                horizontalPadding,
                spacingLG,
                horizontalPadding,
                0,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  const SectionHeading(
                    title: 'Club HQ',
                    subtitle:
                        'Squad shape, finances, supporter energy, and club identity from one management deck.',
                    trailing: MetricPill(
                      label: 'Mode',
                      value: 'Live',
                      highlight: true,
                    ),
                  ),
                  const SizedBox(height: spacingLG),
                  AnimatedSlide(
                    duration: const Duration(milliseconds: 360),
                    curve: Curves.easeOutCubic,
                    offset: _entered ? Offset.zero : const Offset(0, 0.04),
                    child: AnimatedOpacity(
                      duration: const Duration(milliseconds: 320),
                      opacity: _entered ? 1 : 0,
                      child: ClubOverviewHeroCard(club: club, fanMood: fanMood),
                    ),
                  ),
                  const SizedBox(height: spacingLG),
                  ClubDashboardTabBar(controller: _tabController),
                  const SizedBox(height: spacingLG),
                  Expanded(
                    child: TabBarView(
                      controller: _tabController,
                      physics: const BouncingScrollPhysics(
                        parent: AlwaysScrollableScrollPhysics(),
                      ),
                      children: <Widget>[
                        ClubSquadTab(
                          slots: _slots,
                          benchPlayers: _benchPlayers,
                          bottomPadding: bottomPadding,
                          onSwapPlayers: _swapPlayers,
                        ),
                        ClubFinanceTab(
                          points: financePoints,
                          breakdown: financeBreakdown,
                          bottomPadding: bottomPadding,
                        ),
                        ClubFansTab(
                          sentiment: fanMood,
                          signals: fanSignals,
                          bottomPadding: bottomPadding,
                        ),
                        ClubIdentityTab(
                          score: identityScore,
                          philosophy: identityPillars,
                          bottomPadding: bottomPadding,
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

List<ClubFormationSlot> _buildInitialSlots() {
  const String avatar = 'assets/branding/gtex_icon.png';
  const List<ClubFormationSlot> slots = <ClubFormationSlot>[
    ClubFormationSlot(
      position: 'LW',
      alignment: Alignment(-0.72, -0.56),
      player: Player(
        id: 'club-mba',
        name: 'Kelechi Mba',
        position: 'LW',
        country: 'Nigeria',
        age: 23,
        rating: 84,
        potential: 87,
        valueInMillions: 28,
        pace: 0.88,
        technique: 0.82,
        mentality: 0.76,
        image: avatar,
      ),
    ),
    ClubFormationSlot(
      position: 'ST',
      alignment: Alignment(0, -0.84),
      player: Player(
        id: 'club-okoro',
        name: 'Daniel Okoro',
        position: 'ST',
        country: 'Nigeria',
        age: 20,
        rating: 86,
        potential: 91,
        valueInMillions: 39,
        pace: 0.89,
        technique: 0.84,
        mentality: 0.8,
        image: avatar,
        isHot: true,
      ),
    ),
    ClubFormationSlot(
      position: 'RW',
      alignment: Alignment(0.72, -0.56),
      player: Player(
        id: 'club-zerhouni',
        name: 'Yanis Zerhouni',
        position: 'RW',
        country: 'Morocco',
        age: 21,
        rating: 83,
        potential: 88,
        valueInMillions: 27,
        pace: 0.9,
        technique: 0.85,
        mentality: 0.74,
        image: avatar,
      ),
    ),
    ClubFormationSlot(
      position: 'LCM',
      alignment: Alignment(-0.48, -0.16),
      player: Player(
        id: 'club-adebayo',
        name: 'Tomi Adebayo',
        position: 'CM',
        country: 'Nigeria',
        age: 22,
        rating: 84,
        potential: 89,
        valueInMillions: 31,
        pace: 0.76,
        technique: 0.88,
        mentality: 0.83,
        image: avatar,
      ),
    ),
    ClubFormationSlot(
      position: 'CM',
      alignment: Alignment(0, -0.04),
      player: Player(
        id: 'club-onana',
        name: 'Samuel Onana',
        position: 'CAM',
        country: 'Cameroon',
        age: 23,
        rating: 85,
        potential: 88,
        valueInMillions: 34,
        pace: 0.81,
        technique: 0.89,
        mentality: 0.78,
        image: avatar,
        isHot: true,
      ),
    ),
    ClubFormationSlot(
      position: 'RCM',
      alignment: Alignment(0.48, -0.16),
      player: Player(
        id: 'club-mensah',
        name: 'Kojo Mensah',
        position: 'CM',
        country: 'Ghana',
        age: 24,
        rating: 82,
        potential: 85,
        valueInMillions: 24,
        pace: 0.72,
        technique: 0.8,
        mentality: 0.85,
        image: avatar,
      ),
    ),
    ClubFormationSlot(
      position: 'LB',
      alignment: Alignment(-0.78, 0.26),
      player: Player(
        id: 'club-kiplimo',
        name: 'Victor Kiplimo',
        position: 'LB',
        country: 'Kenya',
        age: 24,
        rating: 81,
        potential: 84,
        valueInMillions: 18,
        pace: 0.83,
        technique: 0.75,
        mentality: 0.79,
        image: avatar,
      ),
    ),
    ClubFormationSlot(
      position: 'LCB',
      alignment: Alignment(-0.28, 0.38),
      player: Player(
        id: 'club-diallo',
        name: 'Moussa Diallo',
        position: 'CB',
        country: 'Senegal',
        age: 25,
        rating: 84,
        potential: 87,
        valueInMillions: 28,
        pace: 0.75,
        technique: 0.73,
        mentality: 0.87,
        image: avatar,
      ),
    ),
    ClubFormationSlot(
      position: 'RCB',
      alignment: Alignment(0.28, 0.38),
      player: Player(
        id: 'club-kamara',
        name: 'Ibrahim Kamara',
        position: 'CB',
        country: 'Sierra Leone',
        age: 26,
        rating: 83,
        potential: 84,
        valueInMillions: 22,
        pace: 0.71,
        technique: 0.7,
        mentality: 0.86,
        image: avatar,
      ),
    ),
    ClubFormationSlot(
      position: 'RB',
      alignment: Alignment(0.78, 0.26),
      player: Player(
        id: 'club-zuma',
        name: 'Lebo Zuma',
        position: 'RB',
        country: 'South Africa',
        age: 23,
        rating: 81,
        potential: 85,
        valueInMillions: 21,
        pace: 0.82,
        technique: 0.74,
        mentality: 0.81,
        image: avatar,
      ),
    ),
    ClubFormationSlot(
      position: 'GK',
      alignment: Alignment(0, 0.82),
      player: Player(
        id: 'club-bassey',
        name: 'Ifeanyi Bassey',
        position: 'GK',
        country: 'Nigeria',
        age: 27,
        rating: 84,
        potential: 86,
        valueInMillions: 26,
        pace: 0.58,
        technique: 0.68,
        mentality: 0.9,
        image: avatar,
      ),
    ),
  ];

  return slots;
}

List<Player> _buildBenchPlayers(List<Player> regens) {
  return <Player>[
    ...regens.take(4),
    const Player(
      id: 'club-bench-1',
      name: 'Azubuike Nwosu',
      position: 'CB',
      country: 'Nigeria',
      age: 22,
      rating: 79,
      potential: 83,
      valueInMillions: 14,
      pace: 0.72,
      technique: 0.69,
      mentality: 0.8,
      image: 'assets/branding/gtex_icon.png',
    ),
  ];
}

double _buildFanMood(Club club) {
  final int wins =
      club.formLabel.split('').where((String item) => item == 'W').length;
  return (0.55 + (wins * 0.08) + (club.academyLevel * 0.03)).clamp(0.0, 0.96);
}

List<ClubFinancePoint> _buildFinancePoints(Club club) {
  final double budget = club.budgetInMillions;
  return <ClubFinancePoint>[
    ClubFinancePoint(
      label: 'Jan',
      revenue: budget * 0.12,
      wages: budget * 0.07,
    ),
    ClubFinancePoint(
      label: 'Feb',
      revenue: budget * 0.13,
      wages: budget * 0.074,
    ),
    ClubFinancePoint(
      label: 'Mar',
      revenue: budget * 0.125,
      wages: budget * 0.076,
    ),
    ClubFinancePoint(
      label: 'Apr',
      revenue: budget * 0.145,
      wages: budget * 0.078,
    ),
    ClubFinancePoint(
      label: 'May',
      revenue: budget * 0.152,
      wages: budget * 0.081,
    ),
    ClubFinancePoint(
      label: 'Jun',
      revenue: budget * 0.16,
      wages: budget * 0.084,
    ),
  ];
}

List<ClubFinanceBreakdown> _buildFinanceBreakdown(Club club) {
  final double budget = club.budgetInMillions;
  return <ClubFinanceBreakdown>[
    ClubFinanceBreakdown(
      label: 'Wages',
      value: budget * 0.48,
      color: AppColors.gold,
    ),
    ClubFinanceBreakdown(
      label: 'Facilities',
      value: budget * 0.18,
      color: AppColors.primary,
    ),
    ClubFinanceBreakdown(
      label: 'Scouting',
      value: budget * 0.11,
      color: AppColors.textPrimary,
    ),
    ClubFinanceBreakdown(
      label: 'Academy',
      value: budget * 0.15,
      color: AppColors.success,
    ),
    ClubFinanceBreakdown(
      label: 'Media',
      value: budget * 0.08,
      color: AppColors.textSecondary,
    ),
  ];
}

List<ClubFanSignal> _buildFanSignals(Club club) {
  final double mood = _buildFanMood(club);
  return <ClubFanSignal>[
    ClubFanSignal(
      label: 'Matchday atmosphere',
      value: (mood + 0.04).clamp(0.0, 0.98),
      caption: 'Home support intensity remains high after recent results.',
      color: AppColors.primary,
    ),
    ClubFanSignal(
      label: 'Social buzz',
      value: (mood - 0.03).clamp(0.0, 0.98),
      caption:
          'Digital engagement is carrying academy and transfer narratives.',
      color: AppColors.gold,
    ),
    ClubFanSignal(
      label: 'Merch momentum',
      value: (mood - 0.08).clamp(0.0, 0.98),
      caption: 'Commercial appetite is stable with room for a stronger push.',
      color: AppColors.textPrimary,
    ),
  ];
}

List<ClubIdentityPillar> _buildIdentityPillars(Club club) {
  return <ClubIdentityPillar>[
    ClubIdentityPillar(
      label: 'Academy First',
      score: (0.72 + (club.academyLevel * 0.05)).clamp(0.0, 0.98),
      description:
          'Internal pathways are expected to generate first-team minutes and resale value.',
      icon: Icons.school_rounded,
    ),
    ClubIdentityPillar(
      label: 'Aggressive Football',
      score: 0.86,
      description:
          'The match model favors front-foot pressure, fast recoveries, and vertical progression.',
      icon: Icons.flash_on_rounded,
    ),
    ClubIdentityPillar(
      label: 'Community Reach',
      score: 0.82,
      description:
          'The club brand extends beyond results into fan culture, regional pride, and creator energy.',
      icon: Icons.groups_rounded,
    ),
    ClubIdentityPillar(
      label: 'Transfer Discipline',
      score: 0.88,
      description:
          'Recruitment balances sporting upside with clear resale logic and wage control.',
      icon: Icons.gavel_rounded,
    ),
  ];
}

double _buildIdentityScore(List<ClubIdentityPillar> pillars) {
  final double total = pillars
      .map((ClubIdentityPillar pillar) => pillar.score)
      .reduce((double a, double b) => a + b);
  return total / pillars.length;
}
