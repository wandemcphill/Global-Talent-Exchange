import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_controller.dart';
import 'package:gte_frontend/controllers/club_ops_controller.dart';
import 'package:gte_frontend/features/app_routes/gte_navigation_helpers.dart';
import 'package:gte_frontend/features/app_routes/gte_route_data.dart';
import 'package:gte_frontend/features/club_hub/formation/formation_editor_panel.dart';
import 'package:gte_frontend/features/club_hub/widgets/club_hub_components.dart';
import 'package:gte_frontend/features/club_hub/widgets/club_hub_header_card.dart';
import 'package:gte_frontend/features/club_hub/widgets/squad_readiness_panel.dart';
import 'package:gte_frontend/features/club_identity/dynasty/data/dynasty_profile_dto.dart';
import 'package:gte_frontend/features/club_identity/dynasty/data/dynasty_types.dart';
import 'package:gte_frontend/features/club_identity/jerseys/widgets/identity_color_utils.dart';
import 'package:gte_frontend/features/club_identity/reputation/data/reputation_models.dart';
import 'package:gte_frontend/features/club_identity/trophies/data/trophy_item_dto.dart';
import 'package:gte_frontend/features/club_navigation/club_navigation.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';
import 'package:gte_frontend/features/shell/shell.dart' as shell;
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
    this.navigationDependencies,
    this.operationsController,
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
  final GteNavigationDependencies? navigationDependencies;
  final ClubOpsController? operationsController;

  @override
  Widget build(BuildContext context) {
    final bool canOpenOwnerOffers =
        isAuthenticated && navigationDependencies?.currentClubId == data.clubId;
    final String ownerOffersMessage =
        !isAuthenticated
            ? 'Sign in as the club owner to open club offers.'
            : 'Switch to this club before opening club offers.';
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
      children: <Widget>[
        GteSurfacePanel(
          emphasized: true,
          accentColor: GteShellTheme.accentClub,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: const <Widget>[
                  ClubHubPill(label: 'Club HQ'),
                  ClubHubPill(label: 'Live board'),
                ],
              ),
              const SizedBox(height: 14),
              Text(
                'Club room',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 8),
              Text(
                'Run your squad, tactics, badge, trophies, dynasty, and history from one place.',
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
                    'Sign in to save club changes. The club room stays open while signed out, but live actions stay on the bench.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ),
                const SizedBox(width: 12),
                FilledButton.icon(
                  onPressed: onOpenLogin,
                  icon: const Icon(Icons.login_outlined),
                  label: const Text('Sign in'),
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
        _ClubOperatingReadinessPanel(
          data: data,
          controller: controller,
          navigationDependencies: navigationDependencies,
        ),
        const SizedBox(height: 18),
        ClubHqOperationsPanel(
          data: data,
          operationsController: operationsController,
          onRefresh: operationsController?.refreshClubData,
        ),
        const SizedBox(height: 18),
        ClubQuickActionRow(selectedTab: selectedTab, onSelected: onTabSelected),
        const SizedBox(height: 18),
        ClubTopTabs(selectedTab: selectedTab, onSelected: onTabSelected),
        if (navigationDependencies != null) ...<Widget>[
          const SizedBox(height: 18),
          _ClubRoutePanel(
            onOpenCreatorStadium:
                () => _openFeatureRoute(
                  context,
                  CreatorStadiumClubRouteData(
                    clubId: data.clubId,
                    clubName: data.clubName,
                  ),
                ),
            onOpenClubSaleDetail:
                () => _openFeatureRoute(
                  context,
                  ClubSaleMarketDetailRouteData(
                    clubId: data.clubId,
                    clubName: data.clubName,
                  ),
                ),
            onOpenOwnerOffers:
                canOpenOwnerOffers
                    ? () => _openFeatureRoute(
                      context,
                      ClubSaleMarketOwnerOffersRouteData(
                        clubId: data.clubId,
                        clubName: data.clubName,
                      ),
                    )
                    : null,
            ownerOffersMessage: ownerOffersMessage,
            onOpenWorldContext:
                () => _openFeatureRoute(
                  context,
                  WorldClubContextRouteData(
                    clubId: data.clubId,
                    clubName: data.clubName,
                  ),
                ),
          ),
        ],
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

  Future<void> _openFeatureRoute(BuildContext context, GteAppRouteData route) {
    final GteNavigationDependencies? dependencies = navigationDependencies;
    if (dependencies == null) {
      return Future<void>.value();
    }
    return GteNavigationHelpers.pushRoute<void>(
      context,
      route: route,
      dependencies: dependencies,
    );
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
                'Keep recruitment, standards, and matchday expectations in view.',
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
        SquadReadinessPanel(
          snapshot: SquadReadinessSnapshot.fromDashboard(
            data,
            isSyncing: controller.isLoading,
            errorMessage: controller.errorMessage,
          ),
        ),
        const SizedBox(height: 18),
        GteSurfacePanel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Dressing room buzz',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 12),
              ClubHubMetricRow(
                label: 'Squad mood',
                value: _squadPostureLabel(data),
              ),
              ClubHubMetricRow(
                label: 'Matchday spotlight',
                value:
                    spotlightHonor?.topPerformerName ??
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
    return FormationEditorPanel(
      key: const ValueKey<String>('club-tab-tactics'),
      clubId: data.clubId,
      clubName: data.clubName,
      navigationDependencies: navigationDependencies,
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
                  label: const Text('Edit club look'),
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
                'Club colours',
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
              detail:
                  progress.pointsToNextTier == null
                      ? 'Top prestige tier already secured.'
                      : '${progress.pointsToNextTier} points to ${progress.nextTier!.label}.',
              icon: Icons.insights_outlined,
            ),
            ClubHubStatCard(
              label: 'Regional rank',
              value:
                  data.reputation.regionalRank == null
                      ? '--'
                      : '#${data.reputation.regionalRank!.rank}',
              detail:
                  data.reputation.regionalRank?.regionLabel ??
                  'Regional leaderboard not published yet.',
              icon: Icons.public_outlined,
            ),
            ClubHubStatCard(
              label: 'Global rank',
              value:
                  data.reputation.globalRank == null
                      ? '--'
                      : '#${data.reputation.globalRank!.rank}',
              detail:
                  data.reputation.globalRank == null
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
                    valueColor:
                        event.delta >= 0
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
      return Padding(
        key: ValueKey<String>('club-tab-trophies'),
        padding: EdgeInsets.zero,
        child: GteStatePanel(
          title: 'No trophies in the cabinet yet',
          message:
              'The shell is ready for the first breakthrough. Honors, timelines, and dynasty pressure will populate here as results land.',
          icon: Icons.auto_awesome_outlined,
          actionLabel: 'View trophies',
          onAction: onOpenTrophies,
        ),
      );
    }

    final TrophyItemDto featured = trophyCabinet.featuredHonors().first;
    return Column(
      key: const ValueKey<String>('club-tab-trophies'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        FeaturedTrophyCard(trophy: featured, onTap: onOpenTrophies),
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
              ...trophyCabinet.summaryOutputs
                  .take(3)
                  .map(
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
              ...profile.reasons
                  .take(3)
                  .map(
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
      ...value.reputation.recentEvents
          .take(3)
          .map(
            (ReputationEventDto event) => ClubHistoryEntry(
              title: event.title,
              subtitle: '${event.category.label} | ${event.description}',
              when: event.occurredAt,
              whenLabel: event.seasonLabel,
              icon: event.category.icon,
            ),
          ),
      ...value.trophyCabinet.recentHonors
          .take(3)
          .map(
            (TrophyItemDto honor) => ClubHistoryEntry(
              title: honor.trophyName,
              subtitle:
                  '${honor.seasonLabel} | ${honor.competitionRegion} | ${honor.finalResultSummary}',
              when: honor.earnedAt,
              whenLabel: honor.seasonLabel,
              icon: Icons.emoji_events_outlined,
            ),
          ),
      ...controller.purchaseHistory
          .take(2)
          .map(
            (ClubPurchaseRecord record) => ClubHistoryEntry(
              title: record.itemTitle,
              subtitle: '${record.category} | ${record.statusLabel}',
              when: record.purchasedAt,
              whenLabel: MaterialLocalizations.of(
                context,
              ).formatShortDate(record.purchasedAt),
              icon: Icons.receipt_long_outlined,
            ),
          ),
    ];

    entries.sort((ClubHistoryEntry left, ClubHistoryEntry right) {
      return right.when.compareTo(left.when);
    });
    return entries;
  }
}

class _ClubOperatingReadinessPanel extends StatelessWidget {
  const _ClubOperatingReadinessPanel({
    required this.data,
    required this.controller,
    required this.navigationDependencies,
  });

  final ClubDashboardData data;
  final ClubController controller;
  final GteNavigationDependencies? navigationDependencies;

  @override
  Widget build(BuildContext context) {
    final List<_ClubReadinessSignal> signals = <_ClubReadinessSignal>[
      _ClubReadinessSignal(
        title: 'Squad readiness',
        value: data.playerCount == null ? 'UNKNOWN' : '${data.playerCount}',
        state:
            data.playerCount == null
                ? shell.GtexSurfaceState.degraded
                : data.playerCount! > 0
                ? shell.GtexSurfaceState.confirmed
                : shell.GtexSurfaceState.empty,
        message:
            data.playerCount == null
                ? 'The dashboard did not return registered player count.'
                : data.playerCount! > 0
                ? 'Registered player count is confirmed by the club payload.'
                : 'The club payload returned no registered players.',
        icon: Icons.groups_outlined,
      ),
      _ClubReadinessSignal(
        title: 'Scouting',
        value:
            data.reputation.recentEvents.isEmpty
                ? 'EMPTY'
                : '${data.reputation.recentEvents.length}',
        state:
            data.reputation.recentEvents.isEmpty
                ? shell.GtexSurfaceState.empty
                : shell.GtexSurfaceState.confirmed,
        message:
            data.reputation.recentEvents.isEmpty
                ? 'No scouting or reputation events are present in this snapshot.'
                : 'Recent reputation events are available for scouting review.',
        icon: Icons.manage_search_outlined,
      ),
      _ClubReadinessSignal(
        title: 'Finance',
        value:
            controller.purchaseHistory.isEmpty
                ? 'PENDING'
                : '${controller.purchaseHistory.length}',
        state:
            controller.purchaseHistory.isEmpty
                ? shell.GtexSurfaceState.pending
                : shell.GtexSurfaceState.confirmed,
        message:
            controller.purchaseHistory.isEmpty
                ? 'No club finance payload is mounted here yet; the hub will not invent cashflow.'
                : 'Purchase history is available as the current commerce signal.',
        icon: Icons.account_balance_wallet_outlined,
      ),
      _ClubReadinessSignal(
        title: 'Academy',
        value: '${data.trophyCabinet.academyHonorsCount}',
        state:
            data.trophyCabinet.academyHonorsCount > 0
                ? shell.GtexSurfaceState.confirmed
                : shell.GtexSurfaceState.empty,
        message:
            data.trophyCabinet.academyHonorsCount > 0
                ? 'Academy honors are confirmed in the trophy cabinet payload.'
                : 'No academy honors are present in this club payload.',
        icon: Icons.school_outlined,
      ),
      _ClubReadinessSignal(
        title: 'Sponsorships',
        value: data.catalog.any(_isSponsorshipCatalogItem) ? 'FOUND' : 'EMPTY',
        state:
            data.catalog.any(_isSponsorshipCatalogItem)
                ? shell.GtexSurfaceState.confirmed
                : shell.GtexSurfaceState.empty,
        message:
            data.catalog.any(_isSponsorshipCatalogItem)
                ? 'Sponsorship catalog entries are available in the club payload.'
                : 'No sponsorship block is present in this club payload.',
        icon: Icons.handshake_outlined,
      ),
    ];

    return GteSurfacePanel(
      key: const Key('club-operating-readiness-panel'),
      accentColor: GteShellTheme.accentClub,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Club operating board',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          Text(
            'The HQ exposes readiness, blockers, and missing backend lanes before the club expands into deeper operating screens.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 14),
          LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              final bool compact = constraints.maxWidth < 760;
              final double width =
                  compact
                      ? constraints.maxWidth
                      : (constraints.maxWidth - 24) / 3;
              return Wrap(
                spacing: 12,
                runSpacing: 12,
                children: signals
                    .map<Widget>(
                      (_ClubReadinessSignal signal) => SizedBox(
                        width: width,
                        child: _ClubReadinessTile(signal: signal),
                      ),
                    )
                    .followedBy(<Widget>[
                      SizedBox(
                        width: width,
                        child: FormationHealthSignal(
                          clubId: data.clubId,
                          navigationDependencies: navigationDependencies,
                        ),
                      ),
                    ])
                    .toList(growable: false),
              );
            },
          ),
        ],
      ),
    );
  }

  static bool _isSponsorshipCatalogItem(ClubCatalogItem item) {
    final String category = item.category.toLowerCase();
    final String title = item.title.toLowerCase();
    return category.contains('sponsor') || title.contains('sponsor');
  }
}

class _ClubReadinessSignal {
  const _ClubReadinessSignal({
    required this.title,
    required this.value,
    required this.state,
    required this.message,
    required this.icon,
  });

  final String title;
  final String value;
  final shell.GtexSurfaceState state;
  final String message;
  final IconData icon;
}

class _ClubReadinessTile extends StatelessWidget {
  const _ClubReadinessTile({required this.signal});

  final _ClubReadinessSignal signal;

  @override
  Widget build(BuildContext context) {
    final Color color = _colorFor(signal.state);
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: color.withValues(alpha: 0.24)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Icon(signal.icon, color: color, size: 18),
              const SizedBox(width: 8),
              Text(
                signal.state.name.toUpperCase(),
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: color,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(signal.title, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          Text(signal.value, style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 8),
          Text(signal.message, style: Theme.of(context).textTheme.bodyMedium),
        ],
      ),
    );
  }

  Color _colorFor(shell.GtexSurfaceState state) {
    switch (state) {
      case shell.GtexSurfaceState.confirmed:
      case shell.GtexSurfaceState.data:
        return GteShellTheme.positive;
      case shell.GtexSurfaceState.blocked:
      case shell.GtexSurfaceState.error:
        return GteShellTheme.negative;
      case shell.GtexSurfaceState.pending:
      case shell.GtexSurfaceState.degraded:
        return GteShellTheme.warning;
      case shell.GtexSurfaceState.loading:
      case shell.GtexSurfaceState.syncing:
      case shell.GtexSurfaceState.reconnecting:
        return GteShellTheme.accentClub;
      case shell.GtexSurfaceState.empty:
        return GteShellTheme.textMuted;
    }
  }
}

class _ClubRoutePanel extends StatelessWidget {
  const _ClubRoutePanel({
    required this.onOpenCreatorStadium,
    required this.onOpenClubSaleDetail,
    required this.onOpenOwnerOffers,
    required this.ownerOffersMessage,
    required this.onOpenWorldContext,
  });

  final VoidCallback onOpenCreatorStadium;
  final VoidCallback onOpenClubSaleDetail;
  final VoidCallback? onOpenOwnerOffers;
  final String ownerOffersMessage;
  final VoidCallback onOpenWorldContext;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      accentColor: const Color(0xFF85B8FF),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'More club routes',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          Text(
            'Jump from the club room into transfers, stadium, offers, and the wider world.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              FilledButton.icon(
                onPressed: onOpenClubSaleDetail,
                icon: const Icon(Icons.sell_outlined),
                label: const Text('Club Market'),
              ),
              FilledButton.tonalIcon(
                onPressed: onOpenCreatorStadium,
                icon: const Icon(Icons.stadium_outlined),
                label: const Text('Creator stadium'),
              ),
              FilledButton.tonalIcon(
                onPressed: onOpenOwnerOffers,
                icon: const Icon(Icons.inbox_outlined),
                label: const Text('Club offers'),
              ),
              FilledButton.tonalIcon(
                onPressed: onOpenWorldContext,
                icon: const Icon(Icons.public_outlined),
                label: const Text('World view'),
              ),
            ],
          ),
          if (onOpenOwnerOffers == null) ...<Widget>[
            const SizedBox(height: 10),
            Text(
              ownerOffersMessage,
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ],
      ),
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
            'Locker room shortcuts',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          Text(
            'Jump to the tabs managers reach for most often without scanning every tab first.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              _QuickActionButton(
                label: 'Set Tactics',
                icon: Icons.dashboard_customize_outlined,
                selected: selectedTab == ClubNavigationTab.tactics,
                onPressed: () => onSelected(ClubNavigationTab.tactics),
              ),
              _QuickActionButton(
                label: 'Club Look',
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
