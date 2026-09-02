import 'package:flutter/material.dart';
import 'package:gte_frontend/features/club_growth_redesign/club_growth_redesign.dart';
import 'package:gte_frontend/features/club_lifecycle_redesign/club_lifecycle_redesign.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

import '../models/gtex_club_redesign_models.dart';
import '../widgets/gtex_club_workspace_widgets.dart';
import 'gtex_club_workspace_controller.dart';

class GtexClubOwnerDashboardV2 extends StatefulWidget {
  const GtexClubOwnerDashboardV2({
    super.key,
    required this.clubId,
    this.clubName,
    this.baseUrl,
    this.backendMode,
    this.isAuthenticated = true,
    this.onOpenLogin,
    this.initialSnapshot,
    this.lifecycleDashboard,
    this.lifecycleLoading = false,
    this.lifecycleError,
    this.onRefreshLifecycle,
    this.onSyncSquadRegistration,
    this.onSubmitSquadRegistration,
    this.onLockSquadRegistration,
    this.onAdvanceLifecycle,
    this.growthDashboard,
    this.growthLoading = false,
    this.growthError,
    this.onRefreshGrowth,
    this.onHireStaff,
    this.onGenerateAcademyProspects,
    this.onOfferAcademyContract,
    this.onPromoteAcademyProspect,
    this.onOpenMarket,
    this.onCreateCompetition,
  });

  final String clubId;
  final String? clubName;
  final String? baseUrl;
  final Object? backendMode;
  final bool isAuthenticated;
  final VoidCallback? onOpenLogin;
  final GtexClubWorkspaceSnapshot? initialSnapshot;
  final GtexClubOperatingDashboard? lifecycleDashboard;
  final bool lifecycleLoading;
  final String? lifecycleError;
  final VoidCallback? onRefreshLifecycle;
  final VoidCallback? onSyncSquadRegistration;
  final VoidCallback? onSubmitSquadRegistration;
  final VoidCallback? onLockSquadRegistration;
  final VoidCallback? onAdvanceLifecycle;
  final GtexClubGrowthDashboard? growthDashboard;
  final bool growthLoading;
  final String? growthError;
  final VoidCallback? onRefreshGrowth;
  final ValueChanged<String>? onHireStaff;
  final VoidCallback? onGenerateAcademyProspects;
  final ValueChanged<String>? onOfferAcademyContract;
  final ValueChanged<String>? onPromoteAcademyProspect;
  final VoidCallback? onOpenMarket;
  final VoidCallback? onCreateCompetition;

  @override
  State<GtexClubOwnerDashboardV2> createState() =>
      _GtexClubOwnerDashboardV2State();
}

class _GtexClubOwnerDashboardV2State extends State<GtexClubOwnerDashboardV2> {
  late final GtexClubWorkspaceController _controller;

  @override
  void initState() {
    super.initState();
    _controller = GtexClubWorkspaceController(
      clubId: widget.clubId,
      clubName: widget.clubName,
      initialSnapshot: widget.initialSnapshot,
    );
  }

  @override
  void didUpdateWidget(covariant GtexClubOwnerDashboardV2 oldWidget) {
    super.didUpdateWidget(oldWidget);
    final GtexClubWorkspaceSnapshot? snapshot = widget.initialSnapshot;
    if (snapshot != null && snapshot != oldWidget.initialSnapshot) {
      _controller.replaceSnapshot(snapshot);
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.isAuthenticated) {
      return GtexFocusFlowScaffold(
        title: 'Club command locked',
        subtitle: 'Sign in to open your owner-facing club dashboard.',
        accent: GtexColors.pitch,
        leading: const Icon(
          Icons.lock_outline,
          color: GtexColors.pitch,
          size: 52,
        ),
        footer: Align(
          alignment: Alignment.center,
          child: GtexActionButton(
            label: 'Sign in',
            icon: Icons.login_outlined,
            onPressed: widget.onOpenLogin,
            accent: GtexColors.pitch,
          ),
        ),
        child: const Text(
          'GTEX needs an authenticated owner session before club funds, player orders, shares, squad, and competition operations can open.',
          textAlign: TextAlign.center,
          style: TextStyle(color: GtexColors.textMuted),
        ),
      );
    }
    if (widget.initialSnapshot == null &&
        widget.lifecycleDashboard == null &&
        widget.growthDashboard == null) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(GtexSpacing.lg),
          child: GtexEmptyState(
            title: 'Live club data required',
            message:
                'This owner dashboard no longer opens with generated demo club data. Load it through the live club workspace route.',
            icon: Icons.shield_outlined,
          ),
        ),
      );
    }

    return AnimatedBuilder(
      animation: _controller,
      builder: (BuildContext context, _) {
        final GtexClubWorkspaceSnapshot snapshot = _controller.snapshot;
        return GtexMasterDetailScaffold(
          title: 'Club command',
          subtitle: '${snapshot.clubName} - owner workspace',
          accent: GtexColors.pitch,
          mobileLeftTitle: 'Club sections',
          leftPanel: GtexClubSectionList<GtexClubOwnerSection>(
            items: GtexClubOwnerSection.values,
            selected: _controller.ownerSection,
            labelBuilder: (GtexClubOwnerSection section) => section.label,
            descriptionBuilder:
                (GtexClubOwnerSection section) => section.description,
            onSelected: _controller.selectOwnerSection,
          ),
          detail: _OwnerDetail(
            snapshot: snapshot,
            section: _controller.ownerSection,
            lifecycleDashboard: widget.lifecycleDashboard,
            lifecycleLoading: widget.lifecycleLoading,
            lifecycleError: widget.lifecycleError,
            onRefreshLifecycle: widget.onRefreshLifecycle,
            onSyncSquadRegistration: widget.onSyncSquadRegistration,
            onSubmitSquadRegistration: widget.onSubmitSquadRegistration,
            onLockSquadRegistration: widget.onLockSquadRegistration,
            onAdvanceLifecycle: widget.onAdvanceLifecycle,
            growthDashboard: widget.growthDashboard,
            growthLoading: widget.growthLoading,
            growthError: widget.growthError,
            onRefreshGrowth: widget.onRefreshGrowth,
            onHireStaff: widget.onHireStaff,
            onGenerateAcademyProspects: widget.onGenerateAcademyProspects,
            onOfferAcademyContract: widget.onOfferAcademyContract,
            onPromoteAcademyProspect: widget.onPromoteAcademyProspect,
          ),
          rightPanel: GtexClubRightRail(snapshot: snapshot, ownerFacing: true),
          actions: <Widget>[
            _CommandAction(
              label: 'Market',
              icon: Icons.shopping_basket_outlined,
              message: 'Browse and sign players in the Transfer Hub.',
              accent: GtexColors.pitch,
              onPressed: widget.onOpenMarket,
            ),
            _CommandAction(
              label: 'Create competition',
              icon: Icons.add_circle_outline,
              message:
                  'Create and manage a hosted competition. Requires host access.',
              accent: GtexColors.gold,
              onPressed: widget.onCreateCompetition,
            ),
          ],
        );
      },
    );
  }
}

class _CommandAction extends StatelessWidget {
  const _CommandAction({
    required this.label,
    required this.icon,
    required this.message,
    required this.accent,
    this.onPressed,
  });

  final String label;
  final IconData icon;
  final String message;
  final Color accent;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    // An action with no flow behind it is shown as unavailable rather than
    // firing a snackbar that reads like something happened.
    final bool available = onPressed != null;
    return Tooltip(
      message: message,
      child: Semantics(
        enabled: available,
        button: true,
        label: available ? label : '$label. Unavailable. $message',
        child: GtexActionButton(
          label: available ? label : '$label (unavailable)',
          icon: available ? icon : Icons.lock_outline,
          onPressed: onPressed,
          accent: accent,
        ),
      ),
    );
  }
}

class _OwnerDetail extends StatelessWidget {
  const _OwnerDetail({
    required this.snapshot,
    required this.section,
    required this.lifecycleDashboard,
    required this.lifecycleLoading,
    required this.lifecycleError,
    required this.onRefreshLifecycle,
    required this.onSyncSquadRegistration,
    required this.onSubmitSquadRegistration,
    required this.onLockSquadRegistration,
    required this.onAdvanceLifecycle,
    required this.growthDashboard,
    required this.growthLoading,
    required this.growthError,
    required this.onRefreshGrowth,
    required this.onHireStaff,
    required this.onGenerateAcademyProspects,
    required this.onOfferAcademyContract,
    required this.onPromoteAcademyProspect,
  });

  final GtexClubWorkspaceSnapshot snapshot;
  final GtexClubOwnerSection section;
  final GtexClubOperatingDashboard? lifecycleDashboard;
  final bool lifecycleLoading;
  final String? lifecycleError;
  final VoidCallback? onRefreshLifecycle;
  final VoidCallback? onSyncSquadRegistration;
  final VoidCallback? onSubmitSquadRegistration;
  final VoidCallback? onLockSquadRegistration;
  final VoidCallback? onAdvanceLifecycle;
  final GtexClubGrowthDashboard? growthDashboard;
  final bool growthLoading;
  final String? growthError;
  final VoidCallback? onRefreshGrowth;
  final ValueChanged<String>? onHireStaff;
  final VoidCallback? onGenerateAcademyProspects;
  final ValueChanged<String>? onOfferAcademyContract;
  final ValueChanged<String>? onPromoteAcademyProspect;

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: <Widget>[
        if (section == GtexClubOwnerSection.overview) ...<Widget>[
          GtexClubHero(snapshot: snapshot, ownerFacing: true),
          const SizedBox(height: GtexSpacing.md),
          _LifecycleOverviewPanel(
            dashboard: lifecycleDashboard,
            loading: lifecycleLoading,
            error: lifecycleError,
            onRefresh: onRefreshLifecycle,
          ),
          const SizedBox(height: GtexSpacing.md),
          _GrowthOverviewPanel(
            dashboard: growthDashboard,
            loading: growthLoading,
            error: growthError,
            onRefresh: onRefreshGrowth,
          ),
          const SizedBox(height: GtexSpacing.md),
          _OwnerMetrics(snapshot: snapshot),
          const SizedBox(height: GtexSpacing.md),
          GtexPanel(
            title: 'Today inside your club',
            subtitle: 'A calm view of what needs attention.',
            accent: GtexColors.pitch,
            child: Column(
              children: snapshot.activity
                  .map(
                    (String item) => ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: const Icon(
                        Icons.bolt_outlined,
                        color: GtexColors.pitch,
                      ),
                      title: Text(
                        item,
                        style: const TextStyle(color: GtexColors.text),
                      ),
                      subtitle: const Text(
                        'Actionable club signal',
                        style: TextStyle(color: GtexColors.textMuted),
                      ),
                    ),
                  )
                  .toList(growable: false),
            ),
          ),
        ] else if (section == GtexClubOwnerSection.readiness) ...<Widget>[
          _LifecycleReadinessPanel(
            dashboard: lifecycleDashboard,
            loading: lifecycleLoading,
            error: lifecycleError,
            onRefresh: onRefreshLifecycle,
            onSyncSquadRegistration: onSyncSquadRegistration,
            onSubmitSquadRegistration: onSubmitSquadRegistration,
            onLockSquadRegistration: onLockSquadRegistration,
            onAdvanceLifecycle: onAdvanceLifecycle,
          ),
        ] else if (section == GtexClubOwnerSection.squad) ...<Widget>[
          _SectionHeader(
            title: 'Squad room',
            subtitle: 'Owned real players and regens attached to this club.',
            icon: Icons.groups_2_outlined,
          ),
          const SizedBox(height: GtexSpacing.md),
          GtexClubSquadList(squad: snapshot.squad),
        ] else if (section == GtexClubOwnerSection.staff) ...<Widget>[
          _StaffMarketplacePanel(
            dashboard: growthDashboard,
            loading: growthLoading,
            error: growthError,
            onRefresh: onRefreshGrowth,
            onHireStaff: onHireStaff,
          ),
        ] else if (section == GtexClubOwnerSection.academy) ...<Widget>[
          _AcademyPipelinePanel(
            dashboard: growthDashboard,
            loading: growthLoading,
            error: growthError,
            onRefresh: onRefreshGrowth,
            onGenerateProspects: onGenerateAcademyProspects,
            onOfferContract: onOfferAcademyContract,
            onPromoteProspect: onPromoteAcademyProspect,
          ),
        ] else if (section == GtexClubOwnerSection.sponsorships) ...<Widget>[
          _SponsorshipGrowthPanel(
            dashboard: growthDashboard,
            loading: growthLoading,
            error: growthError,
            onRefresh: onRefreshGrowth,
          ),
        ] else if (section == GtexClubOwnerSection.transfers) ...<Widget>[
          _SectionHeader(
            title: 'Transfer room',
            subtitle: 'Shortlist basket, open orders, and market next actions.',
            icon: Icons.swap_horiz_outlined,
          ),
          const SizedBox(height: GtexSpacing.md),
          GtexPanel(
            title: 'Shortlist basket',
            subtitle:
                'Keep total cost visible while users pick players from league -> club lists.',
            accent: GtexColors.pitch,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  'Open orders: ${gtexFormatCredits(snapshot.finances.openOrdersCredits)}',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    color: GtexColors.text,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: GtexSpacing.sm),
                const Text(
                  'Open transfer orders are live here; shortlist totals appear once the player market returns basket rows for this club.',
                  style: TextStyle(color: GtexColors.textMuted),
                ),
              ],
            ),
          ),
          const SizedBox(height: GtexSpacing.md),
          _OrdersList(snapshot: snapshot),
        ] else if (section == GtexClubOwnerSection.finances) ...<Widget>[
          _SectionHeader(
            title: 'Club finance',
            subtitle: 'Wallet, share price, orders and monthly club movement.',
            icon: Icons.account_balance_wallet_outlined,
          ),
          const SizedBox(height: GtexSpacing.md),
          _OwnerMetrics(snapshot: snapshot),
        ] else if (section == GtexClubOwnerSection.competitions) ...<Widget>[
          _CompetitionOpsPanel(snapshot: snapshot),
        ] else if (section == GtexClubOwnerSection.identity) ...<Widget>[
          _SectionHeader(
            title: 'Club identity',
            subtitle:
                'Badge, jersey, short code, and public-facing brand assets.',
            icon: Icons.shield_outlined,
          ),
          const SizedBox(height: GtexSpacing.md),
          GtexClubHero(snapshot: snapshot, ownerFacing: true),
        ] else if (section == GtexClubOwnerSection.trophies) ...<Widget>[
          _SectionHeader(
            title: 'Trophy cabinet',
            subtitle: 'Honors and dynasty history.',
            icon: Icons.workspace_premium_outlined,
          ),
          const SizedBox(height: GtexSpacing.md),
          GtexClubTrophyGrid(trophies: snapshot.trophies),
        ] else if (section == GtexClubOwnerSection.news) ...<Widget>[
          _SectionHeader(
            title: 'Club newsroom',
            subtitle: 'AI-generated stories about your club and players.',
            icon: Icons.newspaper_outlined,
          ),
          const SizedBox(height: GtexSpacing.md),
          GtexClubNewsList(news: snapshot.news),
        ] else if (section == GtexClubOwnerSection.orders) ...<Widget>[
          _SectionHeader(
            title: 'Club orders',
            subtitle: 'Purchases, rental payments, share-related operations.',
            icon: Icons.receipt_long_outlined,
          ),
          const SizedBox(height: GtexSpacing.md),
          _OrdersList(snapshot: snapshot),
        ] else ...<Widget>[_ClubSettingsPanel(snapshot: snapshot)],
      ],
    );
  }
}

class _LifecycleOverviewPanel extends StatelessWidget {
  const _LifecycleOverviewPanel({
    required this.dashboard,
    required this.loading,
    required this.error,
    required this.onRefresh,
  });

  final GtexClubOperatingDashboard? dashboard;
  final bool loading;
  final String? error;
  final VoidCallback? onRefresh;

  @override
  Widget build(BuildContext context) {
    final GtexClubOperatingDashboard? current = dashboard;
    if (current == null) {
      return GtexPanel(
        title: 'Launch readiness',
        subtitle:
            loading ? 'Syncing Batch 24 club lifecycle' : 'Lifecycle sync',
        accent: GtexColors.cyan,
        trailing:
            loading
                ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
                : IconButton(
                  tooltip: 'Refresh readiness',
                  onPressed: onRefresh,
                  icon: const Icon(Icons.refresh_outlined),
                  color: GtexColors.text,
                ),
        child: Text(
          error ??
              'Readiness will appear here once the live club lifecycle API returns.',
          style: const TextStyle(color: GtexColors.textMuted),
        ),
      );
    }

    final GtexClubReadiness readiness = current.readiness;
    return GtexPanel(
      title: 'Launch readiness',
      subtitle:
          '${readiness.completedCount}/${readiness.checklist.length} checklist items complete',
      accent:
          readiness.competitionEligible ? GtexColors.pitch : GtexColors.cyan,
      trailing: GtexStatusChip(
        label: gtexClubLifecycleStateLabel(current.lifecycle.state),
        icon:
            readiness.competitionEligible
                ? Icons.verified_outlined
                : Icons.flag_outlined,
        tone:
            readiness.competitionEligible
                ? GtexStatusTone.success
                : GtexStatusTone.neutral,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          ClipRRect(
            borderRadius: BorderRadius.circular(GtexSpacing.radiusPill),
            child: LinearProgressIndicator(
              minHeight: 10,
              value: readiness.readinessScore.clamp(0, 100) / 100,
              backgroundColor: GtexColors.line,
              color:
                  readiness.competitionEligible
                      ? GtexColors.pitch
                      : GtexColors.cyan,
            ),
          ),
          const SizedBox(height: GtexSpacing.sm),
          Wrap(
            spacing: GtexSpacing.sm,
            runSpacing: GtexSpacing.sm,
            children: <Widget>[
              GtexStatusChip(
                label: '${readiness.readinessScore}% ready',
                icon: Icons.speed_outlined,
                tone: GtexStatusTone.premium,
              ),
              GtexStatusChip(
                label: '${current.registeredPlayerCount} registered players',
                icon: Icons.groups_2_outlined,
                tone: GtexStatusTone.neutral,
              ),
              if (current.squadRegistration != null)
                GtexStatusChip(
                  label: gtexSquadRegistrationStatusLabel(
                    current.squadRegistration!.status,
                  ),
                  icon: Icons.assignment_turned_in_outlined,
                  tone:
                      current.squadRegistration!.isLocked
                          ? GtexStatusTone.success
                          : GtexStatusTone.warning,
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _GrowthOverviewPanel extends StatelessWidget {
  const _GrowthOverviewPanel({
    required this.dashboard,
    required this.loading,
    required this.error,
    required this.onRefresh,
  });

  final GtexClubGrowthDashboard? dashboard;
  final bool loading;
  final String? error;
  final VoidCallback? onRefresh;

  @override
  Widget build(BuildContext context) {
    final GtexClubGrowthDashboard? current = dashboard;
    if (current == null) {
      return GtexPanel(
        title: 'Growth loops',
        subtitle:
            loading ? 'Syncing staff, academy and sponsors' : 'Growth sync',
        accent: GtexColors.gold,
        trailing:
            loading
                ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
                : IconButton(
                  tooltip: 'Refresh growth',
                  onPressed: onRefresh,
                  icon: const Icon(Icons.refresh_outlined),
                  color: GtexColors.text,
                ),
        child: Text(
          error ??
              'Staff contracts, academy prospects, and sponsorship revenue will appear when the live club growth API returns.',
          style: const TextStyle(color: GtexColors.textMuted),
        ),
      );
    }

    return GtexPanel(
      title: 'Growth loops',
      subtitle: 'Staff, academy, and sponsor signals connected to this club',
      accent: GtexColors.gold,
      trailing: IconButton(
        tooltip: 'Refresh growth',
        onPressed: loading ? null : onRefresh,
        icon: const Icon(Icons.refresh_outlined),
        color: GtexColors.text,
      ),
      child: Wrap(
        spacing: GtexSpacing.sm,
        runSpacing: GtexSpacing.sm,
        children: <Widget>[
          SizedBox(
            width: 210,
            child: GtexMetricTile(
              label: 'Active staff',
              value: current.activeStaffCount.toString(),
              icon: Icons.badge_outlined,
              accent: GtexColors.pitch,
            ),
          ),
          SizedBox(
            width: 210,
            child: GtexMetricTile(
              label: 'Prospects',
              value: current.academyProspects.length.toString(),
              icon: Icons.school_outlined,
              accent: GtexColors.cyan,
            ),
          ),
          SizedBox(
            width: 210,
            child: GtexMetricTile(
              label: 'Sponsor value',
              value: gtexFormatCredits(
                current.sponsorship.outstandingPayoutMinor,
              ),
              icon: Icons.handshake_outlined,
              accent: GtexColors.gold,
            ),
          ),
        ],
      ),
    );
  }
}

class _StaffMarketplacePanel extends StatelessWidget {
  const _StaffMarketplacePanel({
    required this.dashboard,
    required this.loading,
    required this.error,
    required this.onRefresh,
    required this.onHireStaff,
  });

  final GtexClubGrowthDashboard? dashboard;
  final bool loading;
  final String? error;
  final VoidCallback? onRefresh;
  final ValueChanged<String>? onHireStaff;

  @override
  Widget build(BuildContext context) {
    final GtexClubGrowthDashboard? current = dashboard;
    if (current == null) {
      return _GrowthUnavailablePanel(
        title: 'Staff marketplace',
        subtitle: 'Managers, agents, scouts, coaches, and contracts.',
        icon: Icons.badge_outlined,
        loading: loading,
        error: error,
        onRefresh: onRefresh,
      );
    }
    final List<GtexStaffContract> activeContracts = current.staffContracts
        .where((GtexStaffContract item) => item.active)
        .toList(growable: false);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        _SectionHeader(
          title: 'Staff marketplace',
          subtitle:
              'Hire managers, agents, scouts, and coaches into Fan Coin payroll contracts.',
          icon: Icons.badge_outlined,
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Staff effects',
          subtitle:
              'Employment contracts settle in Fan Coin; manager card trades stay in the GTEX Coin market.',
          accent: GtexColors.pitch,
          trailing: IconButton(
            tooltip: 'Refresh staff',
            onPressed: loading ? null : onRefresh,
            icon: const Icon(Icons.refresh_outlined),
            color: GtexColors.text,
          ),
          child: Wrap(
            spacing: GtexSpacing.sm,
            runSpacing: GtexSpacing.sm,
            children: current.staffEffects.entries
                .map(
                  (MapEntry<String, int> entry) => GtexStatusChip(
                    label: '${_growthLabel(entry.key)} ${entry.value}',
                    icon: Icons.trending_up_outlined,
                    tone: GtexStatusTone.neutral,
                  ),
                )
                .toList(growable: false),
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Active contracts',
          subtitle:
              activeContracts.isEmpty
                  ? 'No active staff yet'
                  : '${activeContracts.length} active staff member(s)',
          accent: GtexColors.cyan,
          child:
              activeContracts.isEmpty
                  ? const Text(
                    'Hire from the marketplace below to attach staff effects to this club.',
                    style: TextStyle(color: GtexColors.textMuted),
                  )
                  : Column(
                    children: activeContracts
                        .map(_StaffContractRow.new)
                        .toList(growable: false),
                  ),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Available staff',
          subtitle:
              'Salary and commission are staff-contract terms, not manager card prices.',
          accent: GtexColors.gold,
          child: Column(
            children: current.staffMarket
                .map(
                  (GtexStaffProfile item) => _StaffProfileRow(
                    profile: item,
                    loading: loading,
                    onHireStaff: onHireStaff,
                  ),
                )
                .toList(growable: false),
          ),
        ),
        if (error != null) ...<Widget>[
          const SizedBox(height: GtexSpacing.md),
          Text(error!, style: const TextStyle(color: GtexColors.red)),
        ],
      ],
    );
  }
}

class _AcademyPipelinePanel extends StatelessWidget {
  const _AcademyPipelinePanel({
    required this.dashboard,
    required this.loading,
    required this.error,
    required this.onRefresh,
    required this.onGenerateProspects,
    required this.onOfferContract,
    required this.onPromoteProspect,
  });

  final GtexClubGrowthDashboard? dashboard;
  final bool loading;
  final String? error;
  final VoidCallback? onRefresh;
  final VoidCallback? onGenerateProspects;
  final ValueChanged<String>? onOfferContract;
  final ValueChanged<String>? onPromoteProspect;

  @override
  Widget build(BuildContext context) {
    final GtexClubGrowthDashboard? current = dashboard;
    if (current == null) {
      return _GrowthUnavailablePanel(
        title: 'Academy pipeline',
        subtitle: 'Generate prospects, offer contracts, and promote regens.',
        icon: Icons.school_outlined,
        loading: loading,
        error: error,
        onRefresh: onRefresh,
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        _SectionHeader(
          title: 'Academy pipeline',
          subtitle:
              'Prospect generation, youth contracts, and senior promotion.',
          icon: Icons.school_outlined,
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Academy profile',
          subtitle:
              'Level ${current.academyProfile.level} - ${gtexFormatCredits(current.academyProfile.investmentMinor)} invested',
          accent: GtexColors.cyan,
          trailing: GtexActionButton(
            label: 'Generate',
            icon: Icons.auto_awesome_outlined,
            compact: true,
            accent: GtexColors.cyan,
            onPressed: loading ? null : onGenerateProspects,
          ),
          child: Wrap(
            spacing: GtexSpacing.sm,
            runSpacing: GtexSpacing.sm,
            children: <Widget>[
              GtexStatusChip(
                label: '${current.academyProspects.length} prospects',
                icon: Icons.groups_2_outlined,
                tone: GtexStatusTone.neutral,
              ),
              GtexStatusChip(
                label:
                    '${current.academyProspects.where((GtexAcademyProspect item) => item.promotable).length} signed',
                icon: Icons.assignment_turned_in_outlined,
                tone: GtexStatusTone.success,
              ),
              GtexStatusChip(
                label: 'newgen bank only',
                icon: Icons.portrait_outlined,
                tone: GtexStatusTone.premium,
              ),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Prospects',
          subtitle: 'No procedural portrait fallback is used in this flow.',
          accent: GtexColors.pitch,
          child:
              current.academyProspects.isEmpty
                  ? const Text(
                    'Generate prospects to start the academy-to-regen pipeline for this club.',
                    style: TextStyle(color: GtexColors.textMuted),
                  )
                  : Column(
                    children: current.academyProspects
                        .map(
                          (GtexAcademyProspect prospect) => _AcademyProspectRow(
                            prospect: prospect,
                            loading: loading,
                            onOfferContract: onOfferContract,
                            onPromoteProspect: onPromoteProspect,
                          ),
                        )
                        .toList(growable: false),
                  ),
        ),
        if (error != null) ...<Widget>[
          const SizedBox(height: GtexSpacing.md),
          Text(error!, style: const TextStyle(color: GtexColors.red)),
        ],
      ],
    );
  }
}

class _SponsorshipGrowthPanel extends StatelessWidget {
  const _SponsorshipGrowthPanel({
    required this.dashboard,
    required this.loading,
    required this.error,
    required this.onRefresh,
  });

  final GtexClubGrowthDashboard? dashboard;
  final bool loading;
  final String? error;
  final VoidCallback? onRefresh;

  @override
  Widget build(BuildContext context) {
    final GtexClubGrowthDashboard? current = dashboard;
    if (current == null) {
      return _GrowthUnavailablePanel(
        title: 'Sponsorships',
        subtitle: 'Contracts, leads, payouts and commercial readiness.',
        icon: Icons.handshake_outlined,
        loading: loading,
        error: error,
        onRefresh: onRefresh,
      );
    }
    final GtexSponsorshipClubSummary sponsorship = current.sponsorship;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        _SectionHeader(
          title: 'Sponsorships',
          subtitle: 'Existing sponsorship engine data inside club command.',
          icon: Icons.handshake_outlined,
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Commercial dashboard',
          subtitle: 'Contracts, leads, and payout state.',
          accent: GtexColors.gold,
          trailing: IconButton(
            tooltip: 'Refresh sponsorships',
            onPressed: loading ? null : onRefresh,
            icon: const Icon(Icons.refresh_outlined),
            color: GtexColors.text,
          ),
          child: Wrap(
            spacing: GtexSpacing.sm,
            runSpacing: GtexSpacing.sm,
            children: <Widget>[
              SizedBox(
                width: 210,
                child: GtexMetricTile(
                  label: 'Active',
                  value: sponsorship.activeContracts.toString(),
                  icon: Icons.verified_outlined,
                  accent: GtexColors.pitch,
                ),
              ),
              SizedBox(
                width: 210,
                child: GtexMetricTile(
                  label: 'Pending',
                  value: sponsorship.pendingContracts.toString(),
                  icon: Icons.pending_actions_outlined,
                  accent: GtexColors.cyan,
                ),
              ),
              SizedBox(
                width: 210,
                child: GtexMetricTile(
                  label: 'Open leads',
                  value: sponsorship.openLeads.toString(),
                  icon: Icons.inbox_outlined,
                  accent: GtexColors.gold,
                ),
              ),
              SizedBox(
                width: 210,
                child: GtexMetricTile(
                  label: 'Outstanding',
                  value: gtexFormatCredits(sponsorship.outstandingPayoutMinor),
                  icon: Icons.payments_outlined,
                  accent: GtexColors.gold,
                ),
              ),
            ],
          ),
        ),
        if (error != null) ...<Widget>[
          const SizedBox(height: GtexSpacing.md),
          Text(error!, style: const TextStyle(color: GtexColors.red)),
        ],
      ],
    );
  }
}

class _GrowthUnavailablePanel extends StatelessWidget {
  const _GrowthUnavailablePanel({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.loading,
    required this.error,
    required this.onRefresh,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final bool loading;
  final String? error;
  final VoidCallback? onRefresh;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: <Widget>[
        _SectionHeader(title: title, subtitle: subtitle, icon: icon),
        const SizedBox(height: GtexSpacing.md),
        GtexEmptyState(
          title: loading ? 'Syncing growth data' : 'Growth data unavailable',
          message:
              error ??
              'The club command dashboard is waiting for the live club growth API.',
          icon: loading ? Icons.sync_outlined : Icons.cloud_off_outlined,
          actionLabel: loading ? null : 'Retry growth',
          onAction: loading ? null : onRefresh,
        ),
      ],
    );
  }
}

class _StaffContractRow extends StatelessWidget {
  const _StaffContractRow(this.contract);

  final GtexStaffContract contract;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      contentPadding: EdgeInsets.zero,
      leading: const Icon(Icons.badge_outlined, color: GtexColors.pitch),
      title: Text(
        contract.staffProfile.displayName,
        style: const TextStyle(
          color: GtexColors.text,
          fontWeight: FontWeight.w900,
        ),
      ),
      subtitle: Text(
        '${contract.staffProfile.staffType} - ${contract.durationDays} days - ${_formatFanCoinMinor(contract.salaryMinor)} payroll',
        style: const TextStyle(color: GtexColors.textMuted),
      ),
      trailing: GtexStatusChip(
        label: contract.status,
        icon: Icons.assignment_turned_in_outlined,
        tone: GtexStatusTone.success,
      ),
    );
  }
}

class _StaffProfileRow extends StatelessWidget {
  const _StaffProfileRow({
    required this.profile,
    required this.loading,
    required this.onHireStaff,
  });

  final GtexStaffProfile profile;
  final bool loading;
  final ValueChanged<String>? onHireStaff;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      contentPadding: EdgeInsets.zero,
      leading: const Icon(Icons.person_search_outlined, color: GtexColors.gold),
      title: Text(
        profile.displayName,
        style: const TextStyle(
          color: GtexColors.text,
          fontWeight: FontWeight.w900,
        ),
      ),
      subtitle: Text(
        '${profile.staffType} - rating ${profile.rating} - ${_formatFanCoinMinor(profile.salaryMinor)} salary - ${profile.skills.join(', ')}',
        style: const TextStyle(color: GtexColors.textMuted),
      ),
      trailing: GtexActionButton(
        label: 'Hire',
        icon: Icons.add_circle_outline,
        compact: true,
        accent: GtexColors.gold,
        onPressed:
            loading || onHireStaff == null
                ? null
                : () => onHireStaff!(profile.id),
      ),
    );
  }
}

class _AcademyProspectRow extends StatelessWidget {
  const _AcademyProspectRow({
    required this.prospect,
    required this.loading,
    required this.onOfferContract,
    required this.onPromoteProspect,
  });

  final GtexAcademyProspect prospect;
  final bool loading;
  final ValueChanged<String>? onOfferContract;
  final ValueChanged<String>? onPromoteProspect;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      contentPadding: EdgeInsets.zero,
      leading: const Icon(Icons.school_outlined, color: GtexColors.cyan),
      title: Text(
        prospect.displayName,
        style: const TextStyle(
          color: GtexColors.text,
          fontWeight: FontWeight.w900,
        ),
      ),
      subtitle: Text(
        '${prospect.position} - age ${prospect.age} - CA ${prospect.currentAbility} / PA ${prospect.potential} - portrait ${prospect.hasApprovedPortrait ? 'assigned' : 'missing'}',
        style: const TextStyle(color: GtexColors.textMuted),
      ),
      trailing: Wrap(
        spacing: GtexSpacing.xs,
        children: <Widget>[
          GtexStatusChip(
            label: _growthLabel(prospect.status),
            icon: Icons.flag_outlined,
            tone:
                prospect.promotable
                    ? GtexStatusTone.success
                    : GtexStatusTone.neutral,
          ),
          GtexStatusChip(
            label:
                prospect.hasApprovedPortrait ? 'portrait bank' : 'no portrait',
            icon: Icons.portrait_outlined,
            tone:
                prospect.hasApprovedPortrait
                    ? GtexStatusTone.premium
                    : GtexStatusTone.warning,
          ),
          if (prospect.seniorPlayerId?.trim().isNotEmpty == true)
            GtexStatusChip(
              label: 'senior linked',
              icon: Icons.link_outlined,
              tone: GtexStatusTone.success,
            ),
          if (prospect.contractEligible)
            GtexActionButton(
              label: 'Contract',
              icon: Icons.assignment_outlined,
              compact: true,
              accent: GtexColors.cyan,
              onPressed:
                  loading || onOfferContract == null
                      ? null
                      : () => onOfferContract!(prospect.id),
            ),
          if (prospect.promotable)
            GtexActionButton(
              label: 'Promote',
              icon: Icons.trending_up_outlined,
              compact: true,
              accent: GtexColors.pitch,
              onPressed:
                  loading || onPromoteProspect == null
                      ? null
                      : () => onPromoteProspect!(prospect.id),
            ),
        ],
      ),
    );
  }
}

String _growthLabel(String value) {
  final String normalized = value.replaceAll('_', ' ').trim();
  if (normalized.isEmpty) {
    return value;
  }
  return normalized[0].toUpperCase() + normalized.substring(1);
}

String _formatFanCoinMinor(int value) {
  final double amount = value / 100;
  final bool whole = amount == amount.roundToDouble();
  return '${amount.toStringAsFixed(whole ? 0 : 2)} Fan Coin';
}

class _LifecycleReadinessPanel extends StatelessWidget {
  const _LifecycleReadinessPanel({
    required this.dashboard,
    required this.loading,
    required this.error,
    required this.onRefresh,
    required this.onSyncSquadRegistration,
    required this.onSubmitSquadRegistration,
    required this.onLockSquadRegistration,
    required this.onAdvanceLifecycle,
  });

  final GtexClubOperatingDashboard? dashboard;
  final bool loading;
  final String? error;
  final VoidCallback? onRefresh;
  final VoidCallback? onSyncSquadRegistration;
  final VoidCallback? onSubmitSquadRegistration;
  final VoidCallback? onLockSquadRegistration;
  final VoidCallback? onAdvanceLifecycle;

  @override
  Widget build(BuildContext context) {
    final GtexClubOperatingDashboard? current = dashboard;
    if (current == null) {
      return Column(
        children: <Widget>[
          _SectionHeader(
            title: 'Club launch checklist',
            subtitle: 'Readiness, squad registration, and competition gate.',
            icon: Icons.fact_check_outlined,
          ),
          const SizedBox(height: GtexSpacing.md),
          GtexEmptyState(
            title: loading ? 'Syncing lifecycle' : 'Lifecycle unavailable',
            message:
                error ??
                'The owner dashboard uses the live Batch 24 lifecycle API and does not infer readiness locally.',
            icon: loading ? Icons.sync_outlined : Icons.cloud_off_outlined,
            actionLabel: loading ? null : 'Retry lifecycle',
            onAction: loading ? null : onRefresh,
          ),
        ],
      );
    }

    final GtexClubReadiness readiness = current.readiness;
    final GtexClubSquadRegistration? registration = current.squadRegistration;
    final bool actionsDisabled = loading;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        _SectionHeader(
          title: 'Club launch checklist',
          subtitle:
              'One owner journey from identity and wallet to squad lock and competition entry.',
          icon: Icons.fact_check_outlined,
        ),
        const SizedBox(height: GtexSpacing.md),
        _LifecycleOverviewPanel(
          dashboard: current,
          loading: loading,
          error: error,
          onRefresh: onRefresh,
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Launch controls',
          subtitle: 'These actions call the live Batch 24 endpoints.',
          accent: GtexColors.gold,
          child: Wrap(
            spacing: GtexSpacing.sm,
            runSpacing: GtexSpacing.sm,
            children: <Widget>[
              GtexActionButton(
                label: 'Sync squad',
                icon: Icons.sync_outlined,
                compact: true,
                secondary: true,
                accent: GtexColors.cyan,
                onPressed: actionsDisabled ? null : onSyncSquadRegistration,
              ),
              GtexActionButton(
                label: 'Submit',
                icon: Icons.outbox_outlined,
                compact: true,
                accent: GtexColors.gold,
                onPressed:
                    actionsDisabled || registration?.isLocked == true
                        ? null
                        : onSubmitSquadRegistration,
              ),
              GtexActionButton(
                label: 'Lock',
                icon: Icons.lock_outline,
                compact: true,
                accent: GtexColors.pitch,
                onPressed:
                    actionsDisabled || registration?.isLocked == true
                        ? null
                        : onLockSquadRegistration,
              ),
              GtexActionButton(
                label: 'Advance',
                icon: Icons.trending_flat_outlined,
                compact: true,
                secondary: true,
                accent: GtexColors.pitch,
                onPressed:
                    actionsDisabled || !readiness.competitionEligible
                        ? null
                        : onAdvanceLifecycle,
              ),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Readiness checks',
          subtitle:
              '${readiness.completedCount} complete, ${readiness.blockers.length} blocking',
          accent:
              readiness.competitionEligible
                  ? GtexColors.pitch
                  : GtexColors.cyan,
          child: Column(
            children: readiness.checklist
                .map((GtexClubReadinessItem item) => _ReadinessRow(item: item))
                .toList(growable: false),
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Squad registration',
          subtitle:
              registration == null
                  ? 'No launch squad synced yet'
                  : '${registration.players.length} players, ${gtexSquadRegistrationStatusLabel(registration.status).toLowerCase()}',
          accent: GtexColors.pitch,
          child:
              registration == null
                  ? const Text(
                    'Use Sync squad to create a launch registration from the club players currently attached to this owner account.',
                    style: TextStyle(color: GtexColors.textMuted),
                  )
                  : _PositionSummary(registration: registration),
        ),
        if (error != null) ...<Widget>[
          const SizedBox(height: GtexSpacing.md),
          GtexPanel(
            accent: GtexColors.red,
            child: Text(error!, style: const TextStyle(color: GtexColors.red)),
          ),
        ],
      ],
    );
  }
}

class _ReadinessRow extends StatelessWidget {
  const _ReadinessRow({required this.item});

  final GtexClubReadinessItem item;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: GtexSpacing.sm),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(
            item.complete
                ? Icons.check_circle_outline
                : Icons.radio_button_unchecked,
            color: item.complete ? GtexColors.pitch : GtexColors.textMuted,
          ),
          const SizedBox(width: GtexSpacing.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  item.label,
                  style: const TextStyle(
                    color: GtexColors.text,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: GtexSpacing.xxs),
                Text(
                  item.detail,
                  style: const TextStyle(color: GtexColors.textMuted),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _PositionSummary extends StatelessWidget {
  const _PositionSummary({required this.registration});

  final GtexClubSquadRegistration registration;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: GtexSpacing.sm,
      runSpacing: GtexSpacing.sm,
      children: <String>[
            'goalkeeper',
            'defender',
            'midfielder',
            'forward',
            'other',
          ]
          .map(
            (String group) => GtexStatusChip(
              label: '$group ${registration.positionSummary[group] ?? 0}',
              icon: Icons.person_outline,
              tone: GtexStatusTone.neutral,
            ),
          )
          .toList(growable: false),
    );
  }
}

class _OwnerMetrics extends StatelessWidget {
  const _OwnerMetrics({required this.snapshot});

  final GtexClubWorkspaceSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: GtexSpacing.sm,
      runSpacing: GtexSpacing.sm,
      children: <Widget>[
        SizedBox(
          width: 240,
          child: GtexMetricTile(
            label: 'Wallet',
            value: gtexFormatCredits(snapshot.finances.walletCredits),
            icon: Icons.account_balance_wallet_outlined,
            accent: GtexColors.pitch,
          ),
        ),
        SizedBox(
          width: 240,
          child: GtexMetricTile(
            label: 'Squad value',
            value: gtexFormatCredits(snapshot.finances.squadValueCredits),
            icon: Icons.groups_2_outlined,
            accent: GtexColors.pitch,
          ),
        ),
        SizedBox(
          width: 240,
          child: GtexMetricTile(
            label: 'Open orders',
            value: gtexFormatCredits(snapshot.finances.openOrdersCredits),
            icon: Icons.receipt_long_outlined,
            accent: GtexColors.gold,
          ),
        ),
        SizedBox(
          width: 240,
          child: GtexMetricTile(
            label: 'Monthly revenue',
            value: gtexFormatCredits(snapshot.finances.monthlyRevenueCredits),
            icon: Icons.trending_up_outlined,
            accent: GtexColors.pitch,
          ),
        ),
      ],
    );
  }
}

class _OrdersList extends StatelessWidget {
  const _OrdersList({required this.snapshot});

  final GtexClubWorkspaceSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: snapshot.orders
          .map(
            (GtexClubOrderItem order) => Padding(
              padding: const EdgeInsets.only(bottom: GtexSpacing.sm),
              child: GtexPanel(
                accent: GtexColors.gold,
                child: Row(
                  children: <Widget>[
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(
                            order.title,
                            style: const TextStyle(
                              color: GtexColors.text,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                          Text(
                            '${order.status} - ${order.timestampLabel}',
                            style: const TextStyle(color: GtexColors.textMuted),
                          ),
                        ],
                      ),
                    ),
                    Text(
                      gtexFormatCredits(order.amountCredits),
                      style: const TextStyle(
                        color: GtexColors.gold,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          )
          .toList(growable: false),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({
    required this.title,
    required this.subtitle,
    required this.icon,
  });

  final String title;
  final String subtitle;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return GtexPanel(
      accent: GtexColors.pitch,
      child: Row(
        children: <Widget>[
          Icon(icon, color: GtexColors.pitch, size: 32),
          const SizedBox(width: GtexSpacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  title,
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    color: GtexColors.text,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                Text(
                  subtitle,
                  style: Theme.of(
                    context,
                  ).textTheme.bodyMedium?.copyWith(color: GtexColors.textMuted),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _CompetitionOpsPanel extends StatelessWidget {
  const _CompetitionOpsPanel({required this.snapshot});

  final GtexClubWorkspaceSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final List<GtexClubOrderItem> competitionOrders = snapshot.orders
        .where(
          (GtexClubOrderItem item) =>
              item.title.toLowerCase().contains('rental') ||
              item.title.toLowerCase().contains('cup') ||
              item.title.toLowerCase().contains('competition'),
        )
        .toList(growable: false);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        const _SectionHeader(
          title: 'Competitions',
          subtitle:
              'Tournament readiness, fixture-linked orders, and club progress signals.',
          icon: Icons.emoji_events_outlined,
        ),
        const SizedBox(height: GtexSpacing.md),
        Wrap(
          spacing: GtexSpacing.md,
          runSpacing: GtexSpacing.md,
          children: <Widget>[
            SizedBox(
              width: 240,
              child: GtexMetricTile(
                label: 'Squad value',
                value: gtexFormatCredits(snapshot.squadValueCredits),
                icon: Icons.groups_outlined,
                accent: GtexColors.pitch,
              ),
            ),
            SizedBox(
              width: 240,
              child: GtexMetricTile(
                label: 'Open orders',
                value: gtexFormatCredits(snapshot.finances.openOrdersCredits),
                icon: Icons.receipt_long_outlined,
                accent: GtexColors.gold,
              ),
            ),
            SizedBox(
              width: 240,
              child: GtexMetricTile(
                label: 'Honors',
                value: '${snapshot.trophies.length}',
                icon: Icons.workspace_premium_outlined,
                accent: GtexColors.cyan,
              ),
            ),
          ],
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Competition signals',
          subtitle:
              competitionOrders.isEmpty
                  ? 'No competition-specific club orders are open right now.'
                  : 'Orders connected to rental pools, cups, and competition preparation.',
          accent: GtexColors.gold,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              if (competitionOrders.isEmpty)
                const Text(
                  'Use Competition OS to create, enter, and monitor fixtures. Club readiness signals update here from live club orders and activity.',
                  style: TextStyle(color: GtexColors.textSecondary),
                )
              else
                for (final GtexClubOrderItem order in competitionOrders)
                  Padding(
                    padding: const EdgeInsets.only(bottom: GtexSpacing.sm),
                    child: _MiniLine(
                      label: order.title,
                      value:
                          '${order.status} - ${gtexFormatCredits(order.amountCredits)}',
                    ),
                  ),
            ],
          ),
        ),
      ],
    );
  }
}

class _ClubSettingsPanel extends StatelessWidget {
  const _ClubSettingsPanel({required this.snapshot});

  final GtexClubWorkspaceSnapshot snapshot;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: <Widget>[
      const _SectionHeader(
        title: 'Club settings',
        subtitle:
            'Current identity, ownership, and visibility signals from the club workspace.',
        icon: Icons.settings_outlined,
      ),
      const SizedBox(height: GtexSpacing.md),
      GtexPanel(
        title: 'Workspace identity',
        subtitle: '${snapshot.shortCode} - ${snapshot.country}',
        accent: GtexColors.cyan,
        child: Wrap(
          spacing: GtexSpacing.xs,
          runSpacing: GtexSpacing.xs,
          children: <Widget>[
            GtexStatusChip(label: snapshot.division, color: GtexColors.pitch),
            GtexStatusChip(
              label: '${snapshot.followers} followers',
              color: GtexColors.cyan,
            ),
            GtexStatusChip(
              label: '${snapshot.shareholders} shareholders',
              color: GtexColors.gold,
            ),
            for (final String tag in snapshot.identityTags.take(5))
              GtexStatusChip(label: tag, color: GtexColors.purple),
          ],
        ),
      ),
      const SizedBox(height: GtexSpacing.md),
      GtexPanel(
        title: 'Operational policy',
        subtitle:
            'Settings are derived from the live club profile until write endpoints expose per-club preferences.',
        accent: GtexColors.pitch,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            _MiniLine(label: 'Owner', value: snapshot.ownerName),
            _MiniLine(label: 'Visibility', value: 'Public club profile'),
            _MiniLine(label: 'Market posture', value: 'Transfer-ready'),
            _MiniLine(
              label: 'Newsroom',
              value: '${snapshot.news.length} items',
            ),
          ],
        ),
      ),
    ],
  );
}

class _MiniLine extends StatelessWidget {
  const _MiniLine({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: GtexSpacing.sm),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Expanded(
            child: Text(
              label,
              style: const TextStyle(color: GtexColors.textMuted),
            ),
          ),
          const SizedBox(width: GtexSpacing.sm),
          Flexible(
            child: Text(
              value,
              textAlign: TextAlign.right,
              style: const TextStyle(
                color: GtexColors.text,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
