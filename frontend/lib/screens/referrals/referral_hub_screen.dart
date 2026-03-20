import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../controllers/creator_controller.dart';
import '../../controllers/referral_controller.dart';
import '../../models/referral_models.dart';
import '../../widgets/creators/creator_header_card.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/referrals/invite_channel_sheet.dart';
import '../../widgets/referrals/milestone_progress_card.dart';
import '../../widgets/referrals/referral_summary_card.dart';
import '../../widgets/referrals/reward_history_list.dart';
import '../../widgets/referrals/share_code_card.dart';
import '../competitions/creator_competition_share_screen.dart';
import '../creators/creator_dashboard_screen.dart';
import 'referral_invites_screen.dart';
import 'referral_rewards_screen.dart';
import 'share_code_screen.dart';

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
    _maybeLoadRuntimeData();
  }

  @override
  void didUpdateWidget(covariant ReferralHubScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.isAuthenticated != widget.isAuthenticated ||
        oldWidget.hasApprovedCreatorAccess != widget.hasApprovedCreatorAccess ||
        oldWidget.isReferralRuntimeAvailable !=
            widget.isReferralRuntimeAvailable ||
        oldWidget.referralController != widget.referralController ||
        oldWidget.creatorController != widget.creatorController) {
      _maybeLoadRuntimeData();
    }
  }

  bool get _shouldLoadRuntimeData =>
      widget.isAuthenticated &&
      widget.hasApprovedCreatorAccess &&
      widget.isReferralRuntimeAvailable;

  void _maybeLoadRuntimeData() {
    if (!_shouldLoadRuntimeData) {
      return;
    }
    widget.referralController.load();
    widget.creatorController.load();
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.isAuthenticated) {
      return SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
        child: GteStatePanel(
          eyebrow: 'CREATOR REFERRALS',
          title: 'Sign in to open creator referrals',
          message:
              'Referral tools are only available from a real signed-in creator session.',
          actionLabel: widget.onOpenLogin == null ? null : 'Sign in',
          onAction: widget.onOpenLogin,
          icon: Icons.login_outlined,
        ),
      );
    }
    if (!widget.hasApprovedCreatorAccess) {
      return SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
        child: GteStatePanel(
          eyebrow: 'CREATOR REFERRALS',
          title: 'Creator access required',
          message:
              'Referral and creator-community tools unlock only after creator access is approved.',
          actionLabel: widget.onOpenCreatorAccessRequest == null
              ? null
              : 'Request creator access',
          onAction: widget.onOpenCreatorAccessRequest,
          icon: Icons.how_to_reg_outlined,
        ),
      );
    }
    if (!widget.isReferralRuntimeAvailable) {
      return const SingleChildScrollView(
        padding: EdgeInsets.fromLTRB(20, 12, 20, 120),
        child: GteStatePanel(
          eyebrow: 'CREATOR REFERRALS',
          title: 'Referral runtime unavailable',
          message:
              'Live creator referral data is not connected in this runtime yet, so invite codes and milestones are hidden instead of showing fixture identities.',
          icon: Icons.info_outline,
        ),
      );
    }

    return AnimatedBuilder(
      animation: Listenable.merge(
        <Listenable>[
          widget.referralController,
          widget.creatorController,
        ],
      ),
      builder: (BuildContext context, _) {
        final bool loadingReferral = widget.referralController.isLoading &&
            !widget.referralController.hasData;
        final bool loadingCreator = widget.creatorController.isLoading &&
            !widget.creatorController.hasData;
        if (loadingReferral || loadingCreator) {
          return const SingleChildScrollView(
            padding: EdgeInsets.fromLTRB(20, 12, 20, 120),
            child: GteStatePanel(
              title: 'Loading referral hub',
              message:
                  'Preparing share code, invite attribution, and milestone reward tracking.',
              icon: Icons.groups_2_outlined,
            ),
          );
        }
        if (widget.referralController.errorMessage != null &&
            !widget.referralController.hasData) {
          return SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
            child: GteStatePanel(
              title: 'Referral hub unavailable',
              message: widget.referralController.errorMessage!,
              icon: Icons.error_outline,
            ),
          );
        }
        if (widget.creatorController.errorMessage != null &&
            !widget.creatorController.hasData) {
          return SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
            child: GteStatePanel(
              title: 'Creator profile unavailable',
              message: widget.creatorController.errorMessage!,
              icon: Icons.error_outline,
            ),
          );
        }

        final ReferralHubData hub = widget.referralController.hub!;
        final bool hasCreatorProfile = widget.creatorController.profile != null;
        return SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Community invites',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 8),
              Text(
                hub.welcomeDetail,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 16),
              if (hasCreatorProfile) ...<Widget>[
                CreatorHeaderCard(
                  profile: widget.creatorController.profile!,
                  onShareCodeTap: () => _openShareCode(context),
                ),
                const SizedBox(height: 16),
              ],
              ShareCodeCard(
                title: 'Share your code',
                code: hub.shareCode,
                shareUrl: hub.shareUrl,
                supportingText:
                    'Invite friends with a creator-friendly share code and keep every qualified join tied to community growth milestones.',
                onCopyCode: () => _copyValue(
                  value: hub.shareCode,
                  message: 'Share code copied.',
                ),
                onCopyLink: () => _copyValue(
                  value: hub.shareUrl,
                  message: 'Invite link copied.',
                ),
                onOpenChannelSheet: () => _shareInvite(
                  code: hub.shareCode,
                  url: hub.shareUrl,
                ),
              ),
              const SizedBox(height: 16),
              ReferralSummaryCard(
                summary: hub.summary,
                creatorHandle: hub.creatorHandle,
              ),
              const SizedBox(height: 16),
              MilestoneProgressCard(milestones: hub.milestones),
              const SizedBox(height: 16),
              RewardHistoryList(
                title: 'Recent reward history',
                entries: hub.rewardHistory.take(3).toList(growable: false),
              ),
              const SizedBox(height: 16),
              Wrap(
                spacing: 12,
                runSpacing: 12,
                children: <Widget>[
                  FilledButton.icon(
                    onPressed: () => _openShareCode(context),
                    icon: const Icon(Icons.qr_code_2_outlined),
                    label: const Text('Open share code'),
                  ),
                  FilledButton.tonalIcon(
                    onPressed: () => _openRewards(context),
                    icon: const Icon(Icons.workspace_premium_outlined),
                    label: const Text('Reward history'),
                  ),
                  FilledButton.tonalIcon(
                    onPressed: () => _openInvites(context),
                    icon: const Icon(Icons.mark_email_read_outlined),
                    label: const Text('Invite attribution'),
                  ),
                  if (hasCreatorProfile)
                    OutlinedButton.icon(
                      onPressed: () => _openCreatorDashboard(context),
                      icon: const Icon(Icons.person_outline),
                      label: const Text('Creator dashboard'),
                    ),
                  if (hasCreatorProfile)
                    OutlinedButton.icon(
                      onPressed: () => _openCompetitionShare(context),
                      icon: const Icon(Icons.emoji_events_outlined),
                      label: const Text('Share creator competition'),
                    ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }

  Future<void> _openShareCode(BuildContext context) async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => ShareCodeScreen(
          controller: widget.referralController,
        ),
      ),
    );
  }

  Future<void> _openRewards(BuildContext context) async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => ReferralRewardsScreen(
          controller: widget.referralController,
        ),
      ),
    );
  }

  Future<void> _openInvites(BuildContext context) async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => ReferralInvitesScreen(
          controller: widget.referralController,
        ),
      ),
    );
  }

  Future<void> _openCreatorDashboard(BuildContext context) async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => CreatorDashboardScreen(
          controller: widget.creatorController,
        ),
      ),
    );
  }

  Future<void> _openCompetitionShare(BuildContext context) async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => CreatorCompetitionShareScreen(
          creatorController: widget.creatorController,
        ),
      ),
    );
  }

  Future<void> _shareInvite({
    required String code,
    required String url,
  }) async {
    final InviteChannel? channel = await showModalBottomSheet<InviteChannel>(
      context: context,
      builder: (BuildContext context) => const InviteChannelSheet(
        title: 'Choose a share channel',
        message:
            'Pick how you want to send your creator competition invite. Placeholder channels copy a ready message until device-level sharing is connected.',
      ),
    );
    if (!mounted || channel == null) {
      return;
    }
    final String message =
        'Share creator competition invite with code $code. Community link: $url';
    await Clipboard.setData(ClipboardData(text: message));
    if (!mounted) {
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('${channel.label} invite copied.')),
    );
  }

  Future<void> _copyValue({
    required String value,
    required String message,
  }) async {
    await Clipboard.setData(ClipboardData(text: value));
    if (!mounted) {
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }
}
