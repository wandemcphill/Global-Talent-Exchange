import 'package:flutter/material.dart';

import '../ui_gtex/ui_gtex.dart';

/// Isolated Design Lab exploration for GTEX Build 5C:
/// Exploring 3 compositions: Club Universe, Player Universe, and Football Identity.
///
/// NOTE: These fixtures are strictly isolated within the Design Lab for visual
/// inspection and testing, and are never used in live production paths.
class GtexClubPlayerProgressionDesignLabScreen extends StatefulWidget {
  const GtexClubPlayerProgressionDesignLabScreen({super.key});

  @override
  State<GtexClubPlayerProgressionDesignLabScreen> createState() =>
      _GtexClubPlayerProgressionDesignLabScreenState();
}

class _GtexClubPlayerProgressionDesignLabScreenState
    extends State<GtexClubPlayerProgressionDesignLabScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabController =
      TabController(length: 3, vsync: this);

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: GtexColors.surfaceBase,
      appBar: AppBar(
        backgroundColor: GtexColors.surfaceBase,
        foregroundColor: GtexColors.textPrimary,
        title: const Text('Design Lab · Club, Player & Progression'),
        bottom: TabBar(
          controller: _tabController,
          isScrollable: true,
          indicatorColor: GtexColors.pitch,
          labelColor: GtexColors.pitch,
          unselectedLabelColor: GtexColors.textMuted,
          tabs: const <Widget>[
            Tab(text: 'Composition 1 · Club Universe'),
            Tab(text: 'Composition 2 · Player Universe'),
            Tab(text: 'Composition 3 · Football Identity (Selected)'),
          ],
        ),
      ),
      body: Column(
        children: <Widget>[
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(
              horizontal: GtexSpacing.md,
              vertical: GtexSpacing.xs,
            ),
            color: GtexColors.gold.withValues(alpha: 0.15),
            child: Row(
              children: <Widget>[
                const Icon(Icons.science, size: 16, color: GtexColors.gold),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'ISOLATED DESIGN LAB FIXTURE · BUILD 5C VISUAL COMPOSITIONS',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                          color: GtexColors.gold,
                          fontWeight: FontWeight.w900,
                          letterSpacing: 0.8,
                        ),
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: TabBarView(
              controller: _tabController,
              children: const <Widget>[
                _ClubUniverseComposition(),
                _PlayerUniverseComposition(),
                _FootballIdentityComposition(),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ClubUniverseComposition extends StatelessWidget {
  const _ClubUniverseComposition();

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(GtexSpacing.md),
      children: <Widget>[
        const GtexIdentityHeader(
          title: 'Royal Lagos FC',
          subtitle: 'Division 1 • Owner: Amara',
          countryToken: 'NGA',
          prestigeTier: 'Global Powerhouse',
          secondaryTag: 'RLG',
          accentColor: GtexColors.pitch,
        ),
        const SizedBox(height: GtexSpacing.md),
        const GtexProgressionBar(
          label: 'Club Reputation & Prestige',
          tierLabel: 'Tier 5 Prestige',
          currentStep: 8,
          totalSteps: 10,
          accentColor: GtexColors.gold,
          helperText: 'Next milestone: Global Powerhouse Tier VI (+150 pts needed)',
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexSilverwareShelf(
          trophies: const <SilverwareItem>[
            SilverwareItem(
              name: 'West Africa Premier League',
              category: 'senior',
              count: 3,
              latestSeason: 'Season 2025/26',
              accentColor: GtexColors.gold,
            ),
            SilverwareItem(
              name: 'Continental Champions Cup',
              category: 'senior',
              count: 1,
              latestSeason: 'Season 2024/25',
              accentColor: GtexColors.pitch,
            ),
          ],
        ),
      ],
    );
  }
}

class _PlayerUniverseComposition extends StatelessWidget {
  const _PlayerUniverseComposition();

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(GtexSpacing.md),
      children: <Widget>[
        const GtexIdentityHeader(
          title: 'Ayo Mensah',
          subtitle: 'Central Midfielder • Age 23 • Lagos Comets',
          countryToken: 'GHA',
          prestigeTier: 'GSI 84',
          secondaryTag: 'CM',
          accentColor: GtexColors.pitch,
        ),
        const SizedBox(height: GtexSpacing.md),
        const GtexOwnershipIndicatorTile(
          name: 'Ayo Mensah',
          quantity: 12,
          sharePriceCoin: 18400,
          contractDurationYears: 3,
          squadTier: 'first_team',
        ),
        const SizedBox(height: GtexSpacing.md),
        const GtexProgressionBar(
          label: 'Player Career Trajectory',
          tierLabel: 'Rising Star',
          currentStep: 78,
          totalSteps: 99,
          accentColor: GtexColors.cyan,
          helperText: 'Overall Ability: 78 / Potential: 88 (+10 Headroom)',
        ),
      ],
    );
  }
}

class _FootballIdentityComposition extends StatelessWidget {
  const _FootballIdentityComposition();

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(GtexSpacing.md),
      children: <Widget>[
        const GtexIdentityHeader(
          title: 'Royal Lagos FC Universe',
          subtitle: 'Manager: Amara • 22 Squad Members • 3 Major Trophies',
          countryToken: 'NGA',
          prestigeTier: 'Continental Giant',
          secondaryTag: 'RLG',
          accentColor: GtexColors.gold,
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexSilverwareShelf(
          trophies: const <SilverwareItem>[
            SilverwareItem(
              name: 'Premier Division',
              category: 'senior',
              count: 2,
              latestSeason: 'S2026',
              accentColor: GtexColors.gold,
            ),
            SilverwareItem(
              name: 'Super Cup',
              category: 'senior',
              count: 1,
              latestSeason: 'S2025',
              accentColor: GtexColors.pitch,
            ),
            SilverwareItem(
              name: 'Youth League Shield',
              category: 'academy',
              count: 2,
              latestSeason: 'S2026',
              accentColor: GtexColors.cyan,
            ),
          ],
        ),
        const SizedBox(height: GtexSpacing.md),
        const GtexProgressionBar(
          label: 'Dynasty & Club Era Progress',
          tierLabel: 'Dominant Era',
          currentStep: 820,
          totalSteps: 1000,
          accentColor: GtexColors.gold,
          helperText: 'Dynasty Score 820 / 1000 — 180 points to Continental Dynasty',
        ),
        const SizedBox(height: GtexSpacing.md),
        const GtexOwnershipIndicatorTile(
          name: 'Featured Star: Victor Osimhen (Shareholding)',
          quantity: 25,
          sharePriceCoin: 42000,
          contractDurationYears: 4,
          squadTier: 'first_team',
        ),
      ],
    );
  }
}
