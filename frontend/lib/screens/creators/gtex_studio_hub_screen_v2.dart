import 'package:flutter/material.dart';

import '../../controllers/creator_controller.dart';
import '../../controllers/referral_controller.dart';
import '../../models/creator_models.dart';
import '../../models/referral_models.dart';
import '../../ui_gtex/ui_gtex.dart';

enum _StudioModule { overview, creator, referrals, competitions, earnings }

class GtexStudioHubScreenV2 extends StatefulWidget {
  const GtexStudioHubScreenV2({
    super.key,
    required this.creatorController,
    required this.referralController,
    required this.isAuthenticated,
    required this.hasApprovedCreatorAccess,
    required this.isReferralRuntimeAvailable,
    this.onOpenLogin,
    this.onOpenCreatorAccessRequest,
  });

  final CreatorController creatorController;
  final ReferralController referralController;
  final bool isAuthenticated;
  final bool hasApprovedCreatorAccess;
  final bool isReferralRuntimeAvailable;
  final VoidCallback? onOpenLogin;
  final VoidCallback? onOpenCreatorAccessRequest;

  @override
  State<GtexStudioHubScreenV2> createState() => _GtexStudioHubScreenV2State();
}

class _GtexStudioHubScreenV2State extends State<GtexStudioHubScreenV2> {
  _StudioModule _module = _StudioModule.overview;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _sync());
  }

  Future<void> _sync() async {
    if (!mounted || !widget.isAuthenticated) {
      return;
    }
    await Future.wait<void>(<Future<void>>[
      widget.referralController.load(),
      widget.creatorController.load(),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.isAuthenticated) {
      return GtexFocusFlowScaffold(
        title: 'Studio locked',
        subtitle:
            'Sign in to open creator tools, referral milestones, audience growth, and GTEX world signals.',
        accent: GtexColors.mint,
        leading: const Icon(
          Icons.dashboard_outlined,
          color: GtexColors.mint,
          size: 56,
        ),
        footer: Align(
          alignment: Alignment.center,
          child: GtexActionButton(
            label: 'Sign in',
            icon: Icons.login,
            accent: GtexColors.mint,
            onPressed: widget.onOpenLogin,
          ),
        ),
        child: const Text(
          'GTEX Studio connects creator competitions, referrals, audience signals and football-world activity to a signed-in club account.',
          textAlign: TextAlign.center,
          style: TextStyle(color: GtexColors.textSecondary, height: 1.45),
        ),
      );
    }

    return AnimatedBuilder(
      animation: Listenable.merge(<Listenable>[
        widget.creatorController,
        widget.referralController,
      ]),
      builder: (BuildContext context, Widget? child) {
        return GtexMasterDetailScaffold(
          title: 'Creator & World Hub',
          subtitle:
              'Live creator profile, referral rewards, hosted competitions, and audience growth in one GTEX studio.',
          accent: GtexColors.mint,
          mobileLeftTitle: 'Studio',
          leftPanelWidth: 310,
          rightPanelWidth: 340,
          actions: <Widget>[
            IconButton.filledTonal(
              tooltip: 'Refresh studio',
              onPressed: _sync,
              icon: const Icon(Icons.sync),
            ),
            if (!widget.hasApprovedCreatorAccess)
              GtexActionButton(
                label: 'Creator access',
                icon: Icons.verified_outlined,
                accent: GtexColors.gold,
                onPressed: widget.onOpenCreatorAccessRequest,
              ),
          ],
          leftPanel: _buildLeftPanel(context),
          detail: _buildDetail(context),
          rightPanel: _buildRightPanel(context),
        );
      },
    );
  }

  Widget _buildLeftPanel(BuildContext context) {
    final CreatorProfile? profile = widget.creatorController.profile;
    final ReferralHubData? hub = widget.referralController.hub;
    return ListView(
      children: <Widget>[
        _ModuleTile(
          title: 'Overview',
          subtitle: 'Creator, referral and world pulse',
          icon: Icons.dashboard_outlined,
          selected: _module == _StudioModule.overview,
          onTap: () => setState(() => _module = _StudioModule.overview),
        ),
        _ModuleTile(
          title: 'Creator profile',
          subtitle: profile?.handleLabel ?? 'Access and profile status',
          icon: Icons.workspace_premium_outlined,
          selected: _module == _StudioModule.creator,
          onTap: () => setState(() => _module = _StudioModule.creator),
        ),
        _ModuleTile(
          title: 'Referrals',
          subtitle: hub?.shareCode ?? 'Invite rewards and milestones',
          icon: Icons.ios_share_outlined,
          selected: _module == _StudioModule.referrals,
          onTap: () => setState(() => _module = _StudioModule.referrals),
        ),
        _ModuleTile(
          title: 'Hosted competitions',
          subtitle: '${profile?.competitions.length ?? 0} synced competitions',
          icon: Icons.emoji_events_outlined,
          selected: _module == _StudioModule.competitions,
          onTap: () => setState(() => _module = _StudioModule.competitions),
        ),
        _ModuleTile(
          title: 'Earnings',
          subtitle: profile?.financeSummary.walletCurrency ?? 'Wallet signals',
          icon: Icons.payments_outlined,
          selected: _module == _StudioModule.earnings,
          onTap: () => setState(() => _module = _StudioModule.earnings),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Runtime',
          accent: GtexColors.mint,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              GtexStatusChip(
                label:
                    widget.creatorController.isLoading ||
                            widget.referralController.isLoading
                        ? 'Syncing'
                        : 'Ready',
                color: GtexColors.mint,
              ),
              const SizedBox(height: GtexSpacing.sm),
              Text(
                widget.isReferralRuntimeAvailable
                    ? 'Referral runtime is available.'
                    : 'Referral runtime will appear when backend support is enabled.',
                style: const TextStyle(color: GtexColors.textMuted),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildDetail(BuildContext context) {
    switch (_module) {
      case _StudioModule.creator:
        return _CreatorProfilePanel(
          profile: widget.creatorController.profile,
          hasApprovedCreatorAccess: widget.hasApprovedCreatorAccess,
          isLoading: widget.creatorController.isLoading,
          errorMessage: widget.creatorController.errorMessage,
          onOpenCreatorAccessRequest: widget.onOpenCreatorAccessRequest,
          onRefresh: () => widget.creatorController.load(force: true),
        );
      case _StudioModule.referrals:
        return _ReferralPanel(
          hub: widget.referralController.hub,
          isLoading: widget.referralController.isLoading,
          errorMessage: widget.referralController.errorMessage,
          onRefresh: () => widget.referralController.load(force: true),
        );
      case _StudioModule.competitions:
        return _CreatorCompetitionsPanel(
          competitions:
              widget.creatorController.profile?.competitions ??
              const <CreatorCompetition>[],
        );
      case _StudioModule.earnings:
        return _EarningsPanel(
          finance:
              widget.creatorController.financeSummary ??
              widget.creatorController.profile?.financeSummary,
        );
      case _StudioModule.overview:
        return _OverviewPanel(
          profile: widget.creatorController.profile,
          hub: widget.referralController.hub,
          creatorLoading: widget.creatorController.isLoading,
          referralLoading: widget.referralController.isLoading,
          hasApprovedCreatorAccess: widget.hasApprovedCreatorAccess,
          onOpenCreatorAccessRequest: widget.onOpenCreatorAccessRequest,
        );
    }
  }

  Widget _buildRightPanel(BuildContext context) {
    final CreatorProfile? profile = widget.creatorController.profile;
    final ReferralHubData? hub = widget.referralController.hub;
    return ListView(
      children: <Widget>[
        GtexPanel(
          title: 'Studio actions',
          subtitle: 'Keep creator growth and referrals moving.',
          accent: GtexColors.mint,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              GtexActionButton(
                label: 'Refresh live data',
                icon: Icons.sync,
                accent: GtexColors.mint,
                onPressed: _sync,
              ),
              const SizedBox(height: GtexSpacing.sm),
              GtexActionButton(
                label:
                    widget.hasApprovedCreatorAccess
                        ? 'Creator verified'
                        : 'Request creator access',
                icon: Icons.workspace_premium_outlined,
                secondary: widget.hasApprovedCreatorAccess,
                accent: GtexColors.gold,
                onPressed:
                    widget.hasApprovedCreatorAccess
                        ? null
                        : widget.onOpenCreatorAccessRequest,
              ),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Share signal',
          accent: GtexColors.gold,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                hub?.shareCode ?? profile?.shareCode ?? 'No share code yet',
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  color: GtexColors.gold,
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: GtexSpacing.xs),
              Text(
                hub?.shareUrl ??
                    profile?.profileLink ??
                    'Share links appear here once the studio runtime syncs.',
                style: const TextStyle(color: GtexColors.textMuted),
              ),
            ],
          ),
        ),
        if (profile?.financeSummary.insights.isNotEmpty == true) ...<Widget>[
          const SizedBox(height: GtexSpacing.md),
          GtexPanel(
            title: 'Creator insights',
            accent: GtexColors.cyan,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: profile!.financeSummary.insights
                  .take(4)
                  .map(
                    (String item) => Padding(
                      padding: const EdgeInsets.only(bottom: GtexSpacing.sm),
                      child: Text(
                        item,
                        style: const TextStyle(color: GtexColors.textSecondary),
                      ),
                    ),
                  )
                  .toList(growable: false),
            ),
          ),
        ],
      ],
    );
  }
}

class _ModuleTile extends StatelessWidget {
  const _ModuleTile({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.selected,
    required this.onTap,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GtexPanel(
      margin: const EdgeInsets.only(bottom: GtexSpacing.sm),
      padding: const EdgeInsets.all(GtexSpacing.sm),
      isSelected: selected,
      accent: GtexColors.mint,
      onTap: onTap,
      child: Row(
        children: <Widget>[
          Icon(icon, color: selected ? GtexColors.mint : GtexColors.textMuted),
          const SizedBox(width: GtexSpacing.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: GtexColors.text,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                Text(
                  subtitle,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
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

class _OverviewPanel extends StatelessWidget {
  const _OverviewPanel({
    required this.profile,
    required this.hub,
    required this.creatorLoading,
    required this.referralLoading,
    required this.hasApprovedCreatorAccess,
    this.onOpenCreatorAccessRequest,
  });

  final CreatorProfile? profile;
  final ReferralHubData? hub;
  final bool creatorLoading;
  final bool referralLoading;
  final bool hasApprovedCreatorAccess;
  final VoidCallback? onOpenCreatorAccessRequest;

  @override
  Widget build(BuildContext context) {
    final CreatorFinanceSummary? finance = profile?.financeSummary;
    return ListView(
      children: <Widget>[
        GtexPanel(
          title: profile?.displayName ?? 'GTEX Studio',
          subtitle:
              profile?.headline ??
              'Creator profile, referral activity and football-world signals sync here.',
          accent: GtexColors.mint,
          child: Wrap(
            spacing: GtexSpacing.md,
            runSpacing: GtexSpacing.md,
            children: <Widget>[
              SizedBox(
                width: 190,
                child: GtexMetricTile(
                  label: 'Creator access',
                  value: hasApprovedCreatorAccess ? 'Approved' : 'Pending',
                  icon: Icons.verified_outlined,
                  accent: GtexColors.gold,
                ),
              ),
              SizedBox(
                width: 190,
                child: GtexMetricTile(
                  label: 'Qualified referrals',
                  value:
                      '${hub?.summary.qualifiedReferrals ?? profile?.stats.qualifiedReferrals ?? 0}',
                  icon: Icons.group_add_outlined,
                  accent: GtexColors.mint,
                ),
              ),
              SizedBox(
                width: 190,
                child: GtexMetricTile(
                  label: 'Competitions',
                  value: '${profile?.stats.creatorCompetitions ?? 0}',
                  icon: Icons.emoji_events_outlined,
                  accent: GtexColors.cyan,
                ),
              ),
              SizedBox(
                width: 190,
                child: GtexMetricTile(
                  label: 'Wallet',
                  value:
                      finance == null
                          ? 'Pending'
                          : '${finance.walletAvailableBalance.toStringAsFixed(0)} ${finance.walletCurrency}',
                  icon: Icons.account_balance_wallet_outlined,
                  accent: GtexColors.gold,
                ),
              ),
            ],
          ),
        ),
        if (!hasApprovedCreatorAccess) ...<Widget>[
          const SizedBox(height: GtexSpacing.md),
          GtexEmptyState(
            title: 'Creator access pending',
            message:
                'Request creator access to unlock hosted competitions, monetization, creator profile controls and audience analytics.',
            icon: Icons.workspace_premium_outlined,
            accent: GtexColors.gold,
            actionLabel: 'Request access',
            onAction: onOpenCreatorAccessRequest,
          ),
        ],
        if (creatorLoading || referralLoading) ...<Widget>[
          const SizedBox(height: GtexSpacing.md),
          const LinearProgressIndicator(color: GtexColors.mint),
        ],
      ],
    );
  }
}

class _CreatorProfilePanel extends StatelessWidget {
  const _CreatorProfilePanel({
    required this.profile,
    required this.hasApprovedCreatorAccess,
    required this.isLoading,
    this.errorMessage,
    this.onOpenCreatorAccessRequest,
    this.onRefresh,
  });

  final CreatorProfile? profile;
  final bool hasApprovedCreatorAccess;
  final bool isLoading;
  final String? errorMessage;
  final VoidCallback? onOpenCreatorAccessRequest;
  final VoidCallback? onRefresh;

  @override
  Widget build(BuildContext context) {
    final CreatorProfile? currentProfile = profile;
    if (currentProfile == null) {
      return GtexEmptyState(
        title:
            hasApprovedCreatorAccess
                ? 'Creator profile syncing'
                : 'No creator profile yet',
        message:
            errorMessage ??
            (hasApprovedCreatorAccess
                ? 'GTEX is loading the live creator profile for this account.'
                : 'Creator profile controls unlock after access approval.'),
        icon: Icons.workspace_premium_outlined,
        accent: GtexColors.gold,
        actionLabel: hasApprovedCreatorAccess ? 'Retry' : 'Request access',
        onAction:
            hasApprovedCreatorAccess ? onRefresh : onOpenCreatorAccessRequest,
      );
    }
    return ListView(
      children: <Widget>[
        GtexPanel(
          title: currentProfile.displayName,
          subtitle: currentProfile.bio,
          accent: GtexColors.mint,
          child: Wrap(
            spacing: GtexSpacing.sm,
            runSpacing: GtexSpacing.sm,
            children: <Widget>[
              GtexStatusChip(
                label: currentProfile.handleLabel,
                color: GtexColors.mint,
              ),
              GtexStatusChip(
                label: currentProfile.tier,
                color: GtexColors.gold,
              ),
              GtexStatusChip(
                label: currentProfile.status,
                color: GtexColors.cyan,
              ),
              if (currentProfile.revenueSharePercent != null)
                GtexStatusChip(
                  label:
                      '${currentProfile.revenueSharePercent!.toStringAsFixed(1)}% share',
                  color: GtexColors.gold,
                ),
            ],
          ),
        ),
        if (isLoading) const LinearProgressIndicator(color: GtexColors.mint),
      ],
    );
  }
}

class _ReferralPanel extends StatelessWidget {
  const _ReferralPanel({
    required this.hub,
    required this.isLoading,
    this.errorMessage,
    this.onRefresh,
  });

  final ReferralHubData? hub;
  final bool isLoading;
  final String? errorMessage;
  final VoidCallback? onRefresh;

  @override
  Widget build(BuildContext context) {
    final ReferralHubData? currentHub = hub;
    if (currentHub == null) {
      return GtexEmptyState(
        title: 'Referral hub syncing',
        message:
            errorMessage ??
            'Referral codes, milestones and invite history appear here when the live runtime responds.',
        icon: Icons.ios_share_outlined,
        accent: GtexColors.mint,
        actionLabel: 'Retry referrals',
        onAction: onRefresh,
      );
    }
    return ListView(
      children: <Widget>[
        GtexPanel(
          title: currentHub.welcomeTitle,
          subtitle: currentHub.welcomeDetail,
          accent: GtexColors.mint,
          child: Wrap(
            spacing: GtexSpacing.md,
            runSpacing: GtexSpacing.md,
            children: <Widget>[
              SizedBox(
                width: 190,
                child: GtexMetricTile(
                  label: 'Invites sent',
                  value: '${currentHub.summary.invitesSent}',
                  accent: GtexColors.mint,
                ),
              ),
              SizedBox(
                width: 190,
                child: GtexMetricTile(
                  label: 'Qualified',
                  value: '${currentHub.summary.qualifiedReferrals}',
                  accent: GtexColors.gold,
                ),
              ),
              SizedBox(
                width: 190,
                child: GtexMetricTile(
                  label: 'Rewards',
                  value: currentHub.summary.rewardBalanceLabel,
                  accent: GtexColors.cyan,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        for (final MilestoneProgress milestone in currentHub.milestones.take(6))
          Padding(
            padding: const EdgeInsets.only(bottom: GtexSpacing.sm),
            child: GtexPanel(
              title: milestone.title,
              subtitle: milestone.detail,
              accent: milestone.unlocked ? GtexColors.gold : GtexColors.mint,
              child: LinearProgressIndicator(
                value: milestone.progress,
                color: milestone.unlocked ? GtexColors.gold : GtexColors.mint,
                backgroundColor: GtexColors.line,
              ),
            ),
          ),
        if (isLoading) const LinearProgressIndicator(color: GtexColors.mint),
      ],
    );
  }
}

class _CreatorCompetitionsPanel extends StatelessWidget {
  const _CreatorCompetitionsPanel({required this.competitions});

  final List<CreatorCompetition> competitions;

  @override
  Widget build(BuildContext context) {
    if (competitions.isEmpty) {
      return const GtexEmptyState(
        title: 'No hosted competitions yet',
        message:
            'Creator-hosted competitions will appear here once the live creator profile reports them.',
        icon: Icons.emoji_events_outlined,
        accent: GtexColors.gold,
      );
    }
    return ListView.separated(
      itemCount: competitions.length,
      separatorBuilder: (_, __) => const SizedBox(height: GtexSpacing.sm),
      itemBuilder: (BuildContext context, int index) {
        final CreatorCompetition item = competitions[index];
        return GtexPanel(
          title: item.title,
          subtitle: '${item.seasonLabel} - ${item.inviteWindow}',
          accent: item.isLive ? GtexColors.red : GtexColors.gold,
          child: Wrap(
            spacing: GtexSpacing.sm,
            runSpacing: GtexSpacing.sm,
            children: <Widget>[
              GtexStatusChip(
                label: item.isLive ? 'LIVE' : 'Scheduled',
                color: item.isLive ? GtexColors.red : GtexColors.gold,
              ),
              GtexStatusChip(
                label: item.participationLabel,
                color: GtexColors.mint,
              ),
              GtexStatusChip(label: item.rewardLabel, color: GtexColors.cyan),
            ],
          ),
        );
      },
    );
  }
}

class _EarningsPanel extends StatelessWidget {
  const _EarningsPanel({required this.finance});

  final CreatorFinanceSummary? finance;

  @override
  Widget build(BuildContext context) {
    final CreatorFinanceSummary? currentFinance = finance;
    if (currentFinance == null) {
      return const GtexEmptyState(
        title: 'Earnings unavailable',
        message:
            'Creator wallet, clip income, referrals and withdrawals appear here after the live creator finance sync.',
        icon: Icons.payments_outlined,
        accent: GtexColors.gold,
      );
    }
    return ListView(
      children: <Widget>[
        Wrap(
          spacing: GtexSpacing.md,
          runSpacing: GtexSpacing.md,
          children: <Widget>[
            SizedBox(
              width: 210,
              child: GtexMetricTile(
                label: 'Wallet balance',
                value:
                    '${currentFinance.walletBalance.toStringAsFixed(0)} ${currentFinance.walletCurrency}',
                accent: GtexColors.gold,
              ),
            ),
            SizedBox(
              width: 210,
              child: GtexMetricTile(
                label: 'Available',
                value:
                    '${currentFinance.walletAvailableBalance.toStringAsFixed(0)} ${currentFinance.walletCurrency}',
                accent: GtexColors.mint,
              ),
            ),
            SizedBox(
              width: 210,
              child: GtexMetricTile(
                label: 'Referral bonus',
                value: currentFinance.totalReferralBonus.toStringAsFixed(0),
                accent: GtexColors.cyan,
              ),
            ),
            SizedBox(
              width: 210,
              child: GtexMetricTile(
                label: 'Pending withdrawals',
                value: currentFinance.pendingWithdrawals.toStringAsFixed(0),
                accent: GtexColors.red,
              ),
            ),
          ],
        ),
      ],
    );
  }
}
