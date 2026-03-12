import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_controller.dart';
import 'package:gte_frontend/features/club_hub/widgets/club_hub_components.dart';
import 'package:gte_frontend/features/club_hub/widgets/club_hub_header_card.dart';
import 'package:gte_frontend/features/club_identity/dynasty/data/dynasty_profile_dto.dart';
import 'package:gte_frontend/features/club_identity/dynasty/data/dynasty_types.dart';
import 'package:gte_frontend/features/club_identity/jerseys/widgets/identity_color_utils.dart';
import 'package:gte_frontend/features/club_identity/reputation/data/reputation_models.dart';
import 'package:gte_frontend/features/club_identity/trophies/data/trophy_item_dto.dart';
import 'package:gte_frontend/features/club_navigation/club_navigation.dart';
import 'package:gte_frontend/models/club_catalog_models.dart';
import 'package:gte_frontend/models/club_models.dart';
import 'package:gte_frontend/widgets/clubs/featured_trophy_card.dart';
import 'package:gte_frontend/widgets/clubs/reputation_progress_card.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class ClubHubContent extends StatelessWidget {
  const ClubHubContent({
    super.key,
    required this.controller,
    required this.data,
    required this.selectedTab,
    required this.onTabSelected,
    required this.isAuthenticated,
    required this.noticeMessage,
    required this.onOpenIdentity,
    required this.onOpenReputation,
    required this.onOpenTrophies,
    required this.onOpenDynasty,
    required this.onOpenEraHistory,
    required this.onOpenPurchaseHistory,
    this.onOpenLogin,
  });

  final ClubController controller;
  final ClubDashboardData data;
  final ClubNavigationTab selectedTab;
  final ValueChanged<ClubNavigationTab> onTabSelected;
  final bool isAuthenticated;
  final String? noticeMessage;
  final VoidCallback? onOpenLogin;
  final VoidCallback onOpenIdentity;
  final VoidCallback onOpenReputation;
  final VoidCallback onOpenTrophies;
  final VoidCallback onOpenDynasty;
  final VoidCallback onOpenEraHistory;
  final VoidCallback onOpenPurchaseHistory;

  @override
  Widget build(BuildContext context) {
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
      children: <Widget>[
        GteSurfacePanel(
          emphasized: true,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Club hub',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 8),
              Text(
                'Run the badge from one surface: squad posture, tactical language, identity, reputation, trophies, dynasty, and history.',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ],
          ),
        ),
        if (!isAuthenticated && onOpenLogin != null) ...<Widget>[
          const SizedBox(height: 18),
          GteSurfacePanel(
            child: Row(
              children: <Widget>[
                const Icon(Icons.lock_outline),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    'Sign in to persist club updates. The club hub stays readable while signed out.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ),
                const SizedBox(width: 12),
                FilledButton.tonal(
                  onPressed: onOpenLogin,
                  child: const Text('Sign in'),
                ),
              ],
            ),
          ),
        ],
        if (noticeMessage != null) ...<Widget>[
          const SizedBox(height: 18),
          GteSurfacePanel(
            child: Text(
              noticeMessage!,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ),
        ],
        const SizedBox(height: 18),
        ClubHubHeaderCard(
          data: data,
          currentLeagueLabel: _currentLeagueLabel(data),
        ),
        const SizedBox(height: 18),
        ClubQuickActionRow(
          selectedTab: selectedTab,
          onSelected: onTabSelected,
        ),
        const SizedBox(height: 18),
        ClubTopTabs(
          selectedTab: selectedTab,
          onSelected: onTabSelected,
        ),
        const SizedBox(height: 18),
        AnimatedSwitcher(
          duration: const Duration(milliseconds: 220),
          switchInCurve: Curves.easeOut,
          switchOutCurve: Curves.easeIn,
          child: _buildTabBody(context),
        ),
      ],
    );
  }

  Widget _buildTabBody(BuildContext context) {
    switch (selectedTab) {
      case ClubNavigationTab.squad:
        return _buildSquadTab(context);
      case ClubNavigationTab.tactics:
        return _buildTacticsTab(context);
      case ClubNavigationTab.identity:
        return _buildIdentityTab(context);
      case ClubNavigationTab.reputation:
        return _buildReputationTab(context);
      case ClubNavigationTab.trophies:
        return _buildTrophiesTab(context);
      case ClubNavigationTab.dynasty:
        return _buildDynastyTab(context);
      case ClubNavigationTab.history:
        return _buildHistoryTab(context);
    }
  }

  Widget _buildSquadTab(BuildContext context) {
    final TrophyItemDto? spotlightHonor = _primarySpotlightHonor(data);
    final int squadSize = data.playerCount ?? 0;

    return Column(
      key: const ValueKey<String>('club-tab-squad'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        GteSurfacePanel(
          emphasized: true,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Squad overview',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 8),
              Text(
                'The squad shell keeps recruitment, standards, and matchday expectations visible without leaving the club tab.',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ],
          ),
        ),
        const SizedBox(height: 18),
        Wrap(
          spacing: 14,
          runSpacing: 14,
          children: <Widget>[
            ClubHubStatCard(
              label: 'Registered players',
              value: squadSize > 0 ? '$squadSize' : '--',
              detail: 'The current club list driving selection depth.',
              icon: Icons.groups_outlined,
            ),
            ClubHubStatCard(
              label: 'Senior honors',
              value: '${data.trophyCabinet.seniorHonorsCount}',
              detail: 'Winning experience already in the environment.',
              icon: Icons.workspace_premium_outlined,
            ),
            ClubHubStatCard(
              label: 'Academy honors',
              value: '${data.trophyCabinet.academyHonorsCount}',
              detail: 'Youth standards feeding the first-team profile.',
              icon: Icons.school_outlined,
            ),
          ],
        ),
        const SizedBox(height: 18),
        GteSurfacePanel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Locker room signals',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 12),
              ClubHubMetricRow(
                label: 'Club posture',
                value: _squadPostureLabel(data),
              ),
              ClubHubMetricRow(
                label: 'Matchday spotlight',
                value: spotlightHonor?.topPerformerName ??
                    spotlightHonor?.captainName ??
                    'Collective discipline',
              ),
              ClubHubMetricRow(
                label: 'Identity anchor',
                value: data.branding.selectedTheme.name,
              ),
              ClubHubMetricRow(
                label: 'Dynasty pressure',
                value: _dynastyPressureLabel(data.dynastyProfile),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildTacticsTab(BuildContext context) {
    final TacticsBlueprint blueprint = _buildTacticsBlueprint(data);

    return Column(
      key: const ValueKey<String>('club-tab-tactics'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        GteSurfacePanel(
          emphasized: true,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Tactical board',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 8),
              Text(
                'The club shell frames how the team should look on the ball, without fragmenting the badge into admin surfaces.',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 16),
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: blueprint.tags
                    .map((String tag) => ClubHubPill(label: tag))
                    .toList(growable: false),
              ),
            ],
          ),
        ),
        const SizedBox(height: 18),
        Wrap(
          spacing: 14,
          runSpacing: 14,
          children: <Widget>[
            ClubHubStatCard(
              label: 'Shape',
              value: blueprint.shape,
              detail: blueprint.shapeDetail,
              icon: Icons.grid_view_outlined,
            ),
            ClubHubStatCard(
              label: 'Press',
              value: blueprint.pressLine,
              detail: blueprint.pressDetail,
              icon: Icons.bolt_outlined,
            ),
            ClubHubStatCard(
              label: 'Tempo',
              value: blueprint.tempo,
              detail: blueprint.tempoDetail,
              icon: Icons.speed_outlined,
            ),
            ClubHubStatCard(
              label: 'Width',
              value: blueprint.width,
              detail: blueprint.widthDetail,
              icon: Icons.swap_horiz_outlined,
            ),
          ],
        ),
        const SizedBox(height: 18),
        GteSurfacePanel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Tactical notes',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 12),
              ...blueprint.notes.map(
                (String note) => Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      const Padding(
                        padding: EdgeInsets.only(top: 2),
                        child: Icon(
                          Icons.subdirectory_arrow_right_outlined,
                          size: 16,
                          color: GteShellTheme.accent,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          note,
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildIdentityTab(BuildContext context) {
    final List<Color> previewColors = <Color>[
      identityColorFromHex(data.branding.selectedTheme.primaryColor),
      identityColorFromHex(data.branding.selectedTheme.secondaryColor),
      identityColorFromHex(data.branding.selectedTheme.accentColor),
    ];

    return Column(
      key: const ValueKey<String>('club-tab-identity'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        GteSurfacePanel(
          emphasized: true,
          padding: EdgeInsets.zero,
          child: Container(
            padding: const EdgeInsets.all(22),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(28),
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: previewColors,
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  'Identity direction',
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const SizedBox(height: 8),
                Text(
                  data.branding.motto,
                  style: Theme.of(context).textTheme.bodyLarge,
                ),
                const SizedBox(height: 18),
                FilledButton.tonalIcon(
                  onPressed: onOpenIdentity,
                  icon: const Icon(Icons.edit_outlined),
                  label: const Text('Edit identity'),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 18),
        Wrap(
          spacing: 14,
          runSpacing: 14,
          children: <Widget>[
            ClubHubStatCard(
              label: 'Theme',
              value: data.branding.selectedTheme.name,
              detail: data.branding.selectedTheme.description,
              icon: Icons.palette_outlined,
            ),
            ClubHubStatCard(
              label: 'Backdrop',
              value: data.branding.selectedBackdrop.name,
              detail: data.branding.selectedBackdrop.caption,
              icon: Icons.wallpaper_outlined,
            ),
            ClubHubStatCard(
              label: 'Review state',
              value: data.branding.reviewStatus,
              detail: data.branding.reviewNote,
              icon: Icons.fact_check_outlined,
            ),
          ],
        ),
        const SizedBox(height: 18),
        GteSurfacePanel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Palette system',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: <Widget>[
                  ClubColorPill(
                    label: 'Primary',
                    colorHex: data.identity.colorPalette.primaryColor,
                  ),
                  ClubColorPill(
                    label: 'Secondary',
                    colorHex: data.identity.colorPalette.secondaryColor,
                  ),
                  ClubColorPill(
                    label: 'Accent',
                    colorHex: data.identity.colorPalette.accentColor,
                  ),
                ],
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildReputationTab(BuildContext context) {
    final PrestigeTierProgress progress = data.reputation.profile.progress;

    return Column(
      key: const ValueKey<String>('club-tab-reputation'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        ReputationProgressCard(reputation: data.reputation),
        const SizedBox(height: 18),
        Wrap(
          spacing: 14,
          runSpacing: 14,
          children: <Widget>[
            ClubHubStatCard(
              label: 'Current score',
              value: '${data.reputation.profile.currentScore}',
              detail: progress.pointsToNextTier == null
                  ? 'Top prestige tier already secured.'
                  : '${progress.pointsToNextTier} points to ${progress.nextTier!.label}.',
              icon: Icons.insights_outlined,
            ),
            ClubHubStatCard(
              label: 'Regional rank',
              value: data.reputation.regionalRank == null
                  ? '--'
                  : '#${data.reputation.regionalRank!.rank}',
              detail: data.reputation.regionalRank?.regionLabel ??
                  'Regional leaderboard not published yet.',
              icon: Icons.public_outlined,
            ),
            ClubHubStatCard(
              label: 'Global rank',
              value: data.reputation.globalRank == null
                  ? '--'
                  : '#${data.reputation.globalRank!.rank}',
              detail: data.reputation.globalRank == null
                  ? 'Global board not available yet.'
                  : '${data.reputation.globalRank!.currentScore} prestige score.',
              icon: Icons.language_outlined,
            ),
          ],
        ),
        const SizedBox(height: 18),
        GteSurfacePanel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(
                children: <Widget>[
                  Expanded(
                    child: Text(
                      'Recent reputation swings',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                  ),
                  FilledButton.tonalIcon(
                    onPressed: onOpenReputation,
                    icon: const Icon(Icons.open_in_new_outlined),
                    label: const Text('Open reputation'),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              ...data.reputation.recentEvents.map(
                (ReputationEventDto event) => Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: TimelineListTile(
                    icon: event.category.icon,
                    title: event.title,
                    subtitle:
                        '${event.seasonLabel} | ${event.category.label} | ${event.description}',
                    value:
                        '${event.delta >= 0 ? '+' : ''}${event.delta.toString()}',
                    valueColor: event.delta >= 0
                        ? GteShellTheme.positive
                        : GteShellTheme.negative,
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildTrophiesTab(BuildContext context) {
    final trophyCabinet = data.trophyCabinet;
    if (trophyCabinet.isEmpty) {
      return const Padding(
        key: ValueKey<String>('club-tab-trophies'),
        padding: EdgeInsets.zero,
        child: GteStatePanel(
          title: 'No trophies in the cabinet yet',
          message:
              'The shell is ready for the first breakthrough. Honors, timelines, and dynasty pressure will populate here as results land.',
          icon: Icons.auto_awesome_outlined,
        ),
      );
    }

    final TrophyItemDto featured = trophyCabinet.featuredHonors().first;
    return Column(
      key: const ValueKey<String>('club-tab-trophies'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        FeaturedTrophyCard(
          trophy: featured,
          onTap: onOpenTrophies,
        ),
        const SizedBox(height: 18),
        Wrap(
          spacing: 14,
          runSpacing: 14,
          children: <Widget>[
            ClubHubStatCard(
              label: 'Total honors',
              value: '${trophyCabinet.totalHonorsCount}',
              detail: 'Every competition, archive, and elite title tracked.',
              icon: Icons.inventory_2_outlined,
            ),
            ClubHubStatCard(
              label: 'Major honors',
              value: '${trophyCabinet.majorHonorsCount}',
              detail: 'League titles, continental crowns, and elite wins.',
              icon: Icons.workspace_premium_outlined,
            ),
            ClubHubStatCard(
              label: 'Elite honors',
              value: '${trophyCabinet.eliteHonorsCount}',
              detail: 'Top-end trophies that change legacy conversations.',
              icon: Icons.auto_awesome_outlined,
            ),
            ClubHubStatCard(
              label: 'Academy honors',
              value: '${trophyCabinet.academyHonorsCount}',
              detail: 'Proof the pipeline is winning on its own track.',
              icon: Icons.school_outlined,
            ),
          ],
        ),
        const SizedBox(height: 18),
        GteSurfacePanel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(
                children: <Widget>[
                  Expanded(
                    child: Text(
                      'Cabinet summary',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                  ),
                  FilledButton.tonalIcon(
                    onPressed: onOpenTrophies,
                    icon: const Icon(Icons.open_in_new_outlined),
                    label: const Text('View trophies'),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              ...trophyCabinet.summaryOutputs.take(3).map(
                (String summary) => Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      const Padding(
                        padding: EdgeInsets.only(top: 2),
                        child: Icon(
                          Icons.emoji_events_outlined,
                          size: 16,
                          color: GteShellTheme.accentWarm,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          summary,
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildDynastyTab(BuildContext context) {
    final DynastyProfileDto profile = data.dynastyProfile;

    return Column(
      key: const ValueKey<String>('club-tab-dynasty'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        GteSurfacePanel(
          emphasized: true,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                profile.currentEraLabel.label,
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 8),
              Text(
                _dynastySummary(profile),
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 16),
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: <Widget>[
                  ClubHubPill(label: 'Dynasty score ${profile.dynastyScore}'),
                  ClubHubPill(
                    label:
                        '${profile.activeStreaks.topFour}-season top-four streak',
                  ),
                  ClubHubPill(
                    label:
                        '${profile.activeStreaks.trophySeasons} trophy seasons',
                  ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 18),
        Wrap(
          spacing: 14,
          runSpacing: 14,
          children: <Widget>[
            ClubHubStatCard(
              label: 'League titles',
              value: '${profile.currentSnapshot?.metrics.leagueTitles ?? 0}',
              detail: 'Titles inside the active dynasty evaluation window.',
              icon: Icons.looks_one_outlined,
            ),
            ClubHubStatCard(
              label: 'Continental titles',
              value:
                  '${profile.currentSnapshot?.metrics.championsLeagueTitles ?? 0}',
              detail: 'Continental weight behind the current era label.',
              icon: Icons.public_outlined,
            ),
            ClubHubStatCard(
              label: 'World qualifications',
              value: '${profile.activeStreaks.worldSuperCupQualification}',
              detail: 'Consecutive windows reaching the world stage.',
              icon: Icons.language_outlined,
            ),
            ClubHubStatCard(
              label: 'Positive reputation run',
              value: '${profile.activeStreaks.positiveReputation}',
              detail: 'Seasons where prestige kept climbing.',
              icon: Icons.trending_up_outlined,
            ),
          ],
        ),
        const SizedBox(height: 18),
        GteSurfacePanel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(
                children: <Widget>[
                  Expanded(
                    child: Text(
                      'Dynasty pulse',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                  ),
                  FilledButton.tonalIcon(
                    onPressed: onOpenDynasty,
                    icon: const Icon(Icons.open_in_new_outlined),
                    label: const Text('View dynasty'),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              ...profile.reasons.take(3).map(
                (String reason) => Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      const Padding(
                        padding: EdgeInsets.only(top: 2),
                        child: Icon(
                          Icons.timeline_outlined,
                          size: 16,
                          color: GteShellTheme.accent,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          reason,
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildHistoryTab(BuildContext context) {
    final List<ClubHistoryEntry> entries = _buildHistoryEntries(context, data);

    return Column(
      key: const ValueKey<String>('club-tab-history'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        GteSurfacePanel(
          emphasized: true,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Club history',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 8),
              Text(
                _historySummary(data),
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 16),
              Wrap(
                spacing: 12,
                runSpacing: 12,
                children: <Widget>[
                  FilledButton.tonalIcon(
                    onPressed: onOpenEraHistory,
                    icon: const Icon(Icons.history_edu_outlined),
                    label: const Text('Era history'),
                  ),
                  OutlinedButton.icon(
                    onPressed: onOpenPurchaseHistory,
                    icon: const Icon(Icons.receipt_long_outlined),
                    label: const Text('Purchase history'),
                  ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 18),
        if (entries.isEmpty)
          const GteStatePanel(
            title: 'History is still forming',
            message:
                'Once the club records events, honors, or cosmetic activity, the archive stream will begin to fill out here.',
            icon: Icons.history_toggle_off_outlined,
          )
        else
          GteSurfacePanel(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  'Archive stream',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 12),
                ...entries.map(
                  (ClubHistoryEntry entry) => Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: TimelineListTile(
                      icon: entry.icon,
                      title: entry.title,
                      subtitle: entry.subtitle,
                      value: entry.whenLabel,
                      valueColor: GteShellTheme.textMuted,
                    ),
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }

  String _currentLeagueLabel(ClubDashboardData value) {
    final String regionLabel = value.reputation.profile.regionLabel.trim();
    if (regionLabel.isNotEmpty && regionLabel.toLowerCase() != 'global') {
      return '$regionLabel League';
    }
    if (value.countryName != null && value.countryName!.trim().isNotEmpty) {
      return '${value.countryName!.trim()} Premier';
    }
    for (final TrophyItemDto honor in value.trophyCabinet.recentHonors) {
      if (honor.competitionTier.contains('domestic')) {
        return '${honor.competitionRegion} League';
      }
    }
    return 'Club League';
  }

  TrophyItemDto? _primarySpotlightHonor(ClubDashboardData value) {
    if (value.trophyCabinet.recentHonors.isNotEmpty) {
      return value.trophyCabinet.recentHonors.first;
    }
    if (value.trophyCabinet.historicHonorsTimeline.isNotEmpty) {
      return value.trophyCabinet.historicHonorsTimeline.first;
    }
    return null;
  }

  String _squadPostureLabel(ClubDashboardData value) {
    if (value.dynastyProfile.activeDynastyFlag) {
      return 'Expecting silverware';
    }
    if (value.reputation.profile.currentPrestigeTier.index >=
        PrestigeTier.elite.index) {
      return 'Competing for top tables';
    }
    return 'Building competitive depth';
  }

  String _dynastyPressureLabel(DynastyProfileDto profile) {
    if (profile.activeDynastyFlag) {
      return 'Protect the era';
    }
    if (profile.isRisingClub) {
      return 'One run from a breakthrough';
    }
    return 'Legacy still taking shape';
  }

  String _dynastySummary(DynastyProfileDto profile) {
    if (profile.reasons.isNotEmpty) {
      return profile.reasons.first;
    }
    if (profile.activeDynastyFlag) {
      return 'The badge is operating inside a live dynasty window.';
    }
    if (profile.isRisingClub) {
      return 'The club is close enough to a breakthrough that every season matters.';
    }
    return 'This era is still being written.';
  }

  String _historySummary(ClubDashboardData value) {
    final List<DynastySeasonSummaryDto> seasons =
        value.dynastyProfile.lastFourSeasonSummary;
    if (seasons.isNotEmpty) {
      final DynastySeasonSummaryDto first = seasons.last;
      final DynastySeasonSummaryDto last = seasons.first;
      return 'The archive spans ${first.seasonLabel} to ${last.seasonLabel}, blending reputation swings, honors, and club-side activity.';
    }
    return 'The archive blends reputation swings, honors, and club-side activity into one running story.';
  }

  List<ClubHistoryEntry> _buildHistoryEntries(
    BuildContext context,
    ClubDashboardData value,
  ) {
    final List<ClubHistoryEntry> entries = <ClubHistoryEntry>[
      ...value.reputation.recentEvents.take(3).map(
        (ReputationEventDto event) => ClubHistoryEntry(
          title: event.title,
          subtitle: '${event.category.label} | ${event.description}',
          when: event.occurredAt,
          whenLabel: event.seasonLabel,
          icon: event.category.icon,
        ),
      ),
      ...value.trophyCabinet.recentHonors.take(3).map(
        (TrophyItemDto honor) => ClubHistoryEntry(
          title: honor.trophyName,
          subtitle:
              '${honor.seasonLabel} | ${honor.competitionRegion} | ${honor.finalResultSummary}',
          when: honor.earnedAt,
          whenLabel: honor.seasonLabel,
          icon: Icons.emoji_events_outlined,
        ),
      ),
      ...controller.purchaseHistory.take(2).map(
        (ClubPurchaseRecord record) => ClubHistoryEntry(
          title: record.itemTitle,
          subtitle: '${record.category} | ${record.statusLabel}',
          when: record.purchasedAt,
          whenLabel: MaterialLocalizations.of(context)
              .formatShortDate(record.purchasedAt),
          icon: Icons.receipt_long_outlined,
        ),
      ),
    ];

    entries.sort((ClubHistoryEntry left, ClubHistoryEntry right) {
      return right.when.compareTo(left.when);
    });
    return entries;
  }

  TacticsBlueprint _buildTacticsBlueprint(ClubDashboardData value) {
    final PrestigeTier tier = value.reputation.profile.currentPrestigeTier;
    if (value.dynastyProfile.activeDynastyFlag) {
      return const TacticsBlueprint(
        shape: '4-2-3-1',
        shapeDetail: 'Keeps the badge balanced while still pressing for control.',
        pressLine: 'Front-foot press',
        pressDetail: 'The club sets traps high and squeezes exits immediately.',
        tempo: 'Quick circulation',
        tempoDetail: 'Possession moves fast enough to pin elite opponents back.',
        width: 'Wide overloads',
        widthDetail: 'Full width creates isolation for top-end finishers.',
        tags: <String>['Era protection', 'Control', 'Pressure'],
        notes: <String>[
          'The current legacy profile supports proactive football rather than reactive block defending.',
          'Major honors and prestige allow the club to set tempo instead of waiting on moments.',
          'The tactical shell is built to scale into deeper editing later without changing navigation.',
        ],
      );
    }
    if (tier.index >= PrestigeTier.elite.index) {
      return const TacticsBlueprint(
        shape: '4-3-3',
        shapeDetail: 'A flexible triangle through midfield keeps the game vertical.',
        pressLine: 'Counter press',
        pressDetail: 'The first five seconds after turnovers are the main trigger.',
        tempo: 'Balanced vertical',
        tempoDetail: 'The club can settle but still attacks space early.',
        width: 'Touchline discipline',
        widthDetail: 'Wingers stay honest to stretch the line before cutting in.',
        tags: <String>['Progression', 'Balance', 'Transition'],
        notes: <String>[
          'Prestige has reached the point where the club can dictate stretches of the game.',
          'The shape protects central buildup while keeping enough width for identity-driven football.',
          'This surface gives the club tab a home for future tactical adjustments.',
        ],
      );
    }
    return const TacticsBlueprint(
      shape: '4-4-2',
      shapeDetail: 'A stable frame while the club compounds reputation and depth.',
      pressLine: 'Mid-block',
      pressDetail: 'The team waits for clear triggers instead of chasing chaos.',
      tempo: 'Measured build',
      tempoDetail: 'Circulation is patient enough to avoid exposing the back line.',
      width: 'Compact first',
      widthDetail: 'The block protects central lanes before expanding outward.',
      tags: <String>['Structure', 'Growth', 'Discipline'],
      notes: <String>[
        'The shell emphasizes clarity and repeatable roles while the club stack matures.',
        'Identity and reputation cues are visible here even before a dedicated tactics editor lands.',
        'This layout keeps tactical ownership inside the club hub rather than scattering it across routes.',
      ],
    );
  }
}

class ClubQuickActionRow extends StatelessWidget {
  const ClubQuickActionRow({
    super.key,
    required this.selectedTab,
    required this.onSelected,
  });

  final ClubNavigationTab selectedTab;
  final ValueChanged<ClubNavigationTab> onSelected;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Quick actions',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          Text(
            'Jump straight to the club surfaces managers open most often.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              _QuickActionButton(
                label: 'Edit Tactics',
                icon: Icons.dashboard_customize_outlined,
                selected: selectedTab == ClubNavigationTab.tactics,
                onPressed: () => onSelected(ClubNavigationTab.tactics),
              ),
              _QuickActionButton(
                label: 'Edit Identity',
                icon: Icons.shield_outlined,
                selected: selectedTab == ClubNavigationTab.identity,
                onPressed: () => onSelected(ClubNavigationTab.identity),
              ),
              _QuickActionButton(
                label: 'View Trophies',
                icon: Icons.emoji_events_outlined,
                selected: selectedTab == ClubNavigationTab.trophies,
                onPressed: () => onSelected(ClubNavigationTab.trophies),
              ),
              _QuickActionButton(
                label: 'View Dynasty',
                icon: Icons.timeline_outlined,
                selected: selectedTab == ClubNavigationTab.dynasty,
                onPressed: () => onSelected(ClubNavigationTab.dynasty),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _QuickActionButton extends StatelessWidget {
  const _QuickActionButton({
    required this.label,
    required this.icon,
    required this.selected,
    required this.onPressed,
  });

  final String label;
  final IconData icon;
  final bool selected;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    if (selected) {
      return FilledButton.icon(
        onPressed: onPressed,
        icon: Icon(icon),
        label: Text(label),
      );
    }
    return FilledButton.tonalIcon(
      onPressed: onPressed,
      icon: Icon(icon),
      label: Text(label),
    );
  }
}

class TacticsBlueprint {
  const TacticsBlueprint({
    required this.shape,
    required this.shapeDetail,
    required this.pressLine,
    required this.pressDetail,
    required this.tempo,
    required this.tempoDetail,
    required this.width,
    required this.widthDetail,
    required this.tags,
    required this.notes,
  });

  final String shape;
  final String shapeDetail;
  final String pressLine;
  final String pressDetail;
  final String tempo;
  final String tempoDetail;
  final String width;
  final String widthDetail;
  final List<String> tags;
  final List<String> notes;
}

class ClubHistoryEntry {
  const ClubHistoryEntry({
    required this.title,
    required this.subtitle,
    required this.when,
    required this.whenLabel,
    required this.icon,
  });

  final String title;
  final String subtitle;
  final DateTime when;
  final String whenLabel;
  final IconData icon;
}
