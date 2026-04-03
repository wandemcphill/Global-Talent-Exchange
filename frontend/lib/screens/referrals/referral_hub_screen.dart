import 'package:flutter/material.dart';

import '../../controllers/creator_controller.dart';
import '../../controllers/referral_controller.dart';
import '../../models/creator_models.dart';
import '../../models/referral_models.dart';
import '../../widgets/gte_formatters.dart';
import '../../widgets/gte_shell_theme.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/gte_surface_panel.dart';

class ReferralHubScreen extends StatefulWidget {
  const ReferralHubScreen({
    super.key,
    required this.referralController,
    required this.creatorController,
    this.isAuthenticated = false,
    this.hasApprovedCreatorAccess = false,
    this.isReferralRuntimeAvailable = false,
    this.onOpenLogin,
    this.onOpenCreatorAccessRequest,
  });

  final ReferralController referralController;
  final CreatorController creatorController;
  final bool isAuthenticated;
  final bool hasApprovedCreatorAccess;
  final bool isReferralRuntimeAvailable;
  final VoidCallback? onOpenLogin;
  final VoidCallback? onOpenCreatorAccessRequest;

  @override
  State<ReferralHubScreen> createState() => _ReferralHubScreenState();
}

class _ReferralHubScreenState extends State<ReferralHubScreen> {
  @override
  void initState() {
    super.initState();
    widget.creatorController.attachStateSync();
    _prime();
  }

  @override
  void didUpdateWidget(covariant ReferralHubScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.creatorController != widget.creatorController) {
      oldWidget.creatorController.detachStateSync();
      widget.creatorController.attachStateSync();
    }
    if (oldWidget.creatorController != widget.creatorController ||
        oldWidget.referralController != widget.referralController ||
        oldWidget.isAuthenticated != widget.isAuthenticated ||
        oldWidget.hasApprovedCreatorAccess != widget.hasApprovedCreatorAccess) {
      _prime();
    }
  }

  @override
  void dispose() {
    widget.creatorController.detachStateSync();
    super.dispose();
  }

  void _prime() {
    if (!widget.isAuthenticated || !widget.hasApprovedCreatorAccess) {
      return;
    }
    widget.creatorController.load();
    widget.referralController.load();
  }

  Future<void> _refresh() {
    return Future.wait<void>(<Future<void>>[
      widget.creatorController.load(force: true),
      widget.referralController.load(force: true),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.isAuthenticated) {
      return Padding(
        padding: const EdgeInsets.all(20),
        child: GteStatePanel(
          eyebrow: 'COMMUNITY ACCESS',
          title: 'Sign in to open community tools',
          message:
              'Community growth, creator competitions, and referral rewards only load for signed-in accounts.',
          icon: Icons.login_outlined,
          accentColor: GteShellTheme.accentCommunity,
          actionLabel: widget.onOpenLogin == null ? null : 'Sign in',
          onAction: widget.onOpenLogin,
        ),
      );
    }
    if (!widget.hasApprovedCreatorAccess) {
      return Padding(
        padding: const EdgeInsets.all(20),
        child: GteStatePanel(
          eyebrow: 'CREATOR ACCESS',
          title: 'Apply for creator access',
          message:
              'This lane unlocks creator competitions, share codes, referral rewards, and creator performance tooling after creator access is approved.',
          icon: Icons.how_to_reg_outlined,
          accentColor: GteShellTheme.accentCommunity,
          actionLabel:
              widget.onOpenCreatorAccessRequest == null
                  ? null
                  : 'Request access',
          onAction: widget.onOpenCreatorAccessRequest,
        ),
      );
    }

    return AnimatedBuilder(
      animation: Listenable.merge(<Listenable>[
        widget.creatorController,
        widget.referralController,
      ]),
      builder: (BuildContext context, Widget? child) {
        final CreatorProfile? profile = widget.creatorController.profile;
        final CreatorFinanceSummary? finance =
            widget.creatorController.financeSummary ?? profile?.financeSummary;
        final CreatorCompetitionShareData? share =
            widget.creatorController.competitionShare;
        final CreatorCopilotAnalysis? copilot =
            widget.creatorController.copilotAnalysis;
        final ReferralHubData? referralHub = widget.referralController.hub;

        if (profile == null && widget.creatorController.isLoading) {
          return const Center(child: CircularProgressIndicator());
        }
        if (profile == null) {
          return Padding(
            padding: const EdgeInsets.all(20),
            child: GteStatePanel(
              eyebrow: 'COMMUNITY DATA',
              title: 'Community tools are unavailable',
              message:
                  widget.creatorController.errorMessage ??
                  'Creator data is still syncing.',
              icon: Icons.groups_outlined,
              accentColor: GteShellTheme.accentCommunity,
              actionLabel: 'Retry',
              onAction: _refresh,
            ),
          );
        }

        return RefreshIndicator(
          onRefresh: _refresh,
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
            children: <Widget>[
              GteSurfacePanel(
                emphasized: true,
                accentColor: GteShellTheme.accentCommunity,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      'CREATOR COMMUNITY',
                      style: Theme.of(context).textTheme.labelLarge?.copyWith(
                        color: GteShellTheme.accentCommunity,
                        letterSpacing: 1.1,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      '${profile.displayName} community desk',
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      profile.headline,
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      profile.bio,
                      style: Theme.of(context).textTheme.bodyLarge,
                    ),
                    const SizedBox(height: 16),
                    Wrap(
                      spacing: 10,
                      runSpacing: 10,
                      children: <Widget>[
                        Chip(label: Text(profile.handleLabel)),
                        Chip(label: Text('Tier: ${profile.tier}')),
                        Chip(label: Text('Status: ${profile.status}')),
                        Chip(label: Text('Share code: ${profile.shareCode}')),
                        if (profile.revenueSharePercent != null)
                          Chip(
                            label: Text(
                              'Revenue share: ${profile.revenueSharePercent!.toStringAsFixed(1)}%',
                            ),
                          ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 18),
              GteSurfacePanel(
                accentColor: GteShellTheme.accentCommunity,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      'Performance snapshot',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Track creator growth, live competitions, and community conversion from one surface.',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                    const SizedBox(height: 16),
                    Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      children: <Widget>[
                        _CommunityStatTile(
                          label: 'Invites',
                          value: profile.stats.communityInvites.toString(),
                        ),
                        _CommunityStatTile(
                          label: 'Qualified joins',
                          value: profile.stats.qualifiedReferrals.toString(),
                        ),
                        _CommunityStatTile(
                          label: 'Competitions',
                          value: profile.stats.creatorCompetitions.toString(),
                        ),
                        _CommunityStatTile(
                          label: 'Participants',
                          value: profile.stats.contestParticipants.toString(),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    Text(
                      profile.growthSummary.growthDetail,
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      children: <Widget>[
                        Chip(
                          label: Text(profile.growthSummary.weeklyInviteLift),
                        ),
                        Chip(label: Text(profile.growthSummary.topChannel)),
                        Chip(
                          label: Text(
                            profile.growthSummary.inviteAttributionRate,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 18),
              GteSurfacePanel(
                accentColor: GteShellTheme.accentArena,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      'Competition share tools',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      share?.supportingText ??
                          'Choose a creator competition to surface the active share code and invite lane.',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                    if (profile.competitions.isNotEmpty) ...<Widget>[
                      const SizedBox(height: 16),
                      Wrap(
                        spacing: 10,
                        runSpacing: 10,
                        children: profile.competitions
                            .map(
                              (CreatorCompetition competition) => FilterChip(
                                label: Text(competition.title),
                                selected:
                                    share?.competition.competitionId ==
                                    competition.competitionId,
                                onSelected:
                                    widget
                                            .creatorController
                                            .isLoadingCompetitionShare
                                        ? null
                                        : (bool _) {
                                          widget.creatorController
                                              .selectCompetition(
                                                competition.competitionId,
                                              );
                                        },
                              ),
                            )
                            .toList(growable: false),
                      ),
                    ],
                    if (widget
                        .creatorController
                        .isLoadingCompetitionShare) ...<Widget>[
                      const SizedBox(height: 16),
                      const LinearProgressIndicator(),
                    ],
                    if (share != null) ...<Widget>[
                      const SizedBox(height: 16),
                      Text(
                        share.competition.title,
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 8),
                      Text(share.competition.seasonLabel),
                      Text(share.competition.inviteWindow),
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 12,
                        runSpacing: 12,
                        children: <Widget>[
                          Chip(label: Text('Share code: ${share.shareCode}')),
                          Chip(
                            label: Text(
                              share.competition.inviteAttributionLabel,
                            ),
                          ),
                          Chip(
                            label: Text(share.competition.participationLabel),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      SelectableText(
                        share.shareUrl,
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        share.attributionNote,
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ],
                ),
              ),
              if (finance != null) ...<Widget>[
                const SizedBox(height: 18),
                GteSurfacePanel(
                  accentColor: GteShellTheme.accentCapital,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        'Creator finance',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Review live creator revenue, wallet balances, and settlement posture.',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 16),
                      Wrap(
                        spacing: 12,
                        runSpacing: 12,
                        children: <Widget>[
                          _CommunityStatTile(
                            label: 'Wallet available',
                            value: gteFormatCompetitionAmount(
                              finance.walletAvailableBalance,
                              finance.walletCurrency,
                            ),
                          ),
                          _CommunityStatTile(
                            label: 'Gift income',
                            value: gteFormatCompetitionAmount(
                              finance.totalGiftIncome,
                              finance.currency,
                            ),
                          ),
                          _CommunityStatTile(
                            label: 'Reward income',
                            value: gteFormatCompetitionAmount(
                              finance.totalRewardIncome,
                              finance.currency,
                            ),
                          ),
                          _CommunityStatTile(
                            label: 'Clip income',
                            value: gteFormatCompetitionAmount(
                              finance.totalClipIncome,
                              finance.currency,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      Wrap(
                        spacing: 12,
                        runSpacing: 12,
                        children: <Widget>[
                          Chip(
                            label: Text(
                              '${finance.totalClipViews} total clip views',
                            ),
                          ),
                          Chip(
                            label: Text(
                              '${finance.monetizedClips} monetized clips',
                            ),
                          ),
                          Chip(
                            label: Text(
                              '${finance.viralClipCount} viral clips',
                            ),
                          ),
                          Chip(
                            label: Text(
                              'Pending: ${gteFormatCompetitionAmount(finance.pendingWithdrawals, finance.currency)}',
                            ),
                          ),
                        ],
                      ),
                      if (finance.insights.isNotEmpty) ...<Widget>[
                        const SizedBox(height: 16),
                        ...finance.insights.map(
                          (String insight) => Padding(
                            padding: const EdgeInsets.only(bottom: 8),
                            child: Text(
                              insight,
                              style: Theme.of(context).textTheme.bodyMedium,
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ],
              if (copilot != null) ...<Widget>[
                const SizedBox(height: 18),
                GteSurfacePanel(
                  accentColor: GteShellTheme.accentWarm,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        'Creator copilot',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Backend copilot analysis is exposed here so creators can act on the current draft without leaving the app shell.',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 16),
                      Wrap(
                        spacing: 12,
                        runSpacing: 12,
                        children: <Widget>[
                          _CommunityStatTile(
                            label: 'Viral score',
                            value: '${copilot.prediction.viralScorePercent}%',
                          ),
                          _CommunityStatTile(
                            label: 'Expected views',
                            value: copilot.prediction.expectedViews.toString(),
                          ),
                          _CommunityStatTile(
                            label: 'Best format',
                            value: copilot.prediction.bestFormat,
                          ),
                          _CommunityStatTile(
                            label: 'Hook strength',
                            value: '${copilot.hookAnalysis.hookScorePercent}%',
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      Text(
                        copilot.liveCoaching.headline,
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 8),
                      Text(copilot.liveCoaching.message),
                      const SizedBox(height: 8),
                      Text(
                        copilot.liveCoaching.recommendedAction,
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      if (copilot.actionPlan.isNotEmpty) ...<Widget>[
                        const SizedBox(height: 12),
                        ...copilot.actionPlan.map(
                          (String step) => Padding(
                            padding: const EdgeInsets.only(bottom: 6),
                            child: Text('- $step'),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ],
              const SizedBox(height: 18),
              GteSurfacePanel(
                accentColor: GteShellTheme.accentCommunity,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      'Referral rewards',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      referralHub?.welcomeDetail ??
                          'Referral rewards and invite attribution will appear here when the referral runtime is enabled for this environment.',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                    if (referralHub == null) ...<Widget>[
                      const SizedBox(height: 16),
                      GteStatePanel(
                        eyebrow: 'REFERRAL STATUS',
                        title:
                            widget.isReferralRuntimeAvailable
                                ? 'Referral data is still syncing'
                                : 'Referral runtime is not enabled yet',
                        message:
                            widget.referralController.errorMessage ??
                            (widget.isReferralRuntimeAvailable
                                ? 'Pull to refresh once invite attribution data is ready.'
                                : 'Creator tools are live, but referral rewards still need the live referral runtime to be switched on.'),
                        icon: Icons.campaign_outlined,
                        accentColor: GteShellTheme.accentCommunity,
                        actionLabel: 'Refresh',
                        onAction: _refresh,
                      ),
                    ] else ...<Widget>[
                      const SizedBox(height: 16),
                      Wrap(
                        spacing: 12,
                        runSpacing: 12,
                        children: <Widget>[
                          _CommunityStatTile(
                            label: 'Invites sent',
                            value: referralHub.summary.invitesSent.toString(),
                          ),
                          _CommunityStatTile(
                            label: 'Qualified',
                            value:
                                referralHub.summary.qualifiedReferrals
                                    .toString(),
                          ),
                          _CommunityStatTile(
                            label: 'Attributed',
                            value:
                                referralHub.summary.inviteAttributions
                                    .toString(),
                          ),
                          _CommunityStatTile(
                            label: 'Reward balance',
                            value: referralHub.summary.rewardBalanceLabel,
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      Text(
                        referralHub.summary.rewardDetail,
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      if (referralHub.milestones.isNotEmpty) ...<Widget>[
                        const SizedBox(height: 16),
                        Text(
                          'Milestones',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 12),
                        ...referralHub.milestones.map(
                          (MilestoneProgress milestone) => Padding(
                            padding: const EdgeInsets.only(bottom: 12),
                            child: GteSurfacePanel(
                              padding: const EdgeInsets.all(16),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: <Widget>[
                                  Row(
                                    children: <Widget>[
                                      Expanded(
                                        child: Text(
                                          milestone.title,
                                          style:
                                              Theme.of(
                                                context,
                                              ).textTheme.titleMedium,
                                        ),
                                      ),
                                      Chip(
                                        label: Text(
                                          milestone.unlocked
                                              ? 'Unlocked'
                                              : '${milestone.currentValue}/${milestone.targetValue}',
                                        ),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 8),
                                  Text(milestone.detail),
                                  const SizedBox(height: 8),
                                  LinearProgressIndicator(
                                    value: milestone.progress,
                                    minHeight: 8,
                                  ),
                                  const SizedBox(height: 8),
                                  Text(milestone.rewardLabel),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ],
                      if (referralHub.rewardHistory.isNotEmpty) ...<Widget>[
                        const SizedBox(height: 8),
                        Text(
                          'Recent rewards',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 12),
                        ...referralHub.rewardHistory
                            .take(3)
                            .map(
                              (RewardHistoryEntry reward) => Padding(
                                padding: const EdgeInsets.only(bottom: 12),
                                child: GteSurfacePanel(
                                  padding: const EdgeInsets.all(16),
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: <Widget>[
                                      Row(
                                        children: <Widget>[
                                          Expanded(
                                            child: Text(
                                              reward.title,
                                              style:
                                                  Theme.of(
                                                    context,
                                                  ).textTheme.titleMedium,
                                            ),
                                          ),
                                          Chip(
                                            label: Text(reward.category.label),
                                          ),
                                        ],
                                      ),
                                      const SizedBox(height: 8),
                                      Text(reward.detail),
                                      const SizedBox(height: 8),
                                      Text(reward.rewardLabel),
                                      Text(
                                        '${gteFormatDateTime(reward.issuedAt)} - ${reward.ledgerNote}',
                                        style:
                                            Theme.of(
                                              context,
                                            ).textTheme.bodySmall,
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ),
                      ],
                      if (referralHub.invites.isNotEmpty) ...<Widget>[
                        const SizedBox(height: 8),
                        Text(
                          'Recent invites',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 12),
                        ...referralHub.invites
                            .take(3)
                            .map(
                              (ReferralInviteEntry invite) => Padding(
                                padding: const EdgeInsets.only(bottom: 12),
                                child: GteSurfacePanel(
                                  padding: const EdgeInsets.all(16),
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: <Widget>[
                                      Row(
                                        children: <Widget>[
                                          Expanded(
                                            child: Text(
                                              invite.inviteeLabel,
                                              style:
                                                  Theme.of(
                                                    context,
                                                  ).textTheme.titleMedium,
                                            ),
                                          ),
                                          Chip(
                                            label: Text(invite.channel.label),
                                          ),
                                        ],
                                      ),
                                      const SizedBox(height: 8),
                                      Text(invite.competitionLabel),
                                      Text(invite.statusLabel),
                                      Text(invite.inviteAttributionLabel),
                                      const SizedBox(height: 8),
                                      Text(
                                        gteFormatDateTime(invite.sentAt),
                                        style:
                                            Theme.of(
                                              context,
                                            ).textTheme.bodySmall,
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ),
                      ],
                    ],
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _CommunityStatTile extends StatelessWidget {
  const _CommunityStatTile({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(minWidth: 140),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0xFF2A3A56)),
        color: Colors.white.withValues(alpha: 0.03),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(label, style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: 4),
          Text(value, style: Theme.of(context).textTheme.titleMedium),
        ],
      ),
    );
  }
}
