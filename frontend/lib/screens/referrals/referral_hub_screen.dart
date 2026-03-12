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
  });

  final ReferralController referralController;
  final CreatorController creatorController;

  @override
  State<ReferralHubScreen> createState() => _ReferralHubScreenState();
}

class _ReferralHubScreenState extends State<ReferralHubScreen> {
  @override
  void initState() {
    super.initState();
    widget.referralController.load();
    widget.creatorController.load();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: Listenable.merge(
        <Listenable>[
          widget.referralController,
          widget.creatorController,
        ],
      ),
      builder: (BuildContext context, _) {
        final bool loading = widget.referralController.isLoading &&
            !widget.referralController.hasData;
        if (loading) {
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

        final ReferralHubData hub = widget.referralController.hub!;
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
              if (widget.creatorController.profile != null) ...<Widget>[
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
                  OutlinedButton.icon(
                    onPressed: () => _openCreatorDashboard(context),
                    icon: const Icon(Icons.person_outline),
                    label: const Text('Creator dashboard'),
                  ),
                  OutlinedButton.icon(
                    onPressed: () => _openCompetitionShare(context),
                    icon: const Icon(Icons.emoji_events_outlined),
                    label: const Text('Join creator competition'),
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
        'Join creator competition with code $code. Community invite: $url';
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
