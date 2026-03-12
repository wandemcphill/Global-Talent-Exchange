import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../controllers/creator_controller.dart';
import '../../models/creator_models.dart';
import '../../models/referral_models.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/gte_surface_panel.dart';
import '../../widgets/referrals/invite_channel_sheet.dart';
import '../../widgets/referrals/share_code_card.dart';

class CreatorCompetitionShareScreen extends StatefulWidget {
  const CreatorCompetitionShareScreen({
    super.key,
    required this.creatorController,
    this.competitionId,
  });

  final CreatorController creatorController;
  final String? competitionId;

  @override
  State<CreatorCompetitionShareScreen> createState() =>
      _CreatorCompetitionShareScreenState();
}

class _CreatorCompetitionShareScreenState
    extends State<CreatorCompetitionShareScreen> {
  @override
  void initState() {
    super.initState();
    widget.creatorController.load().then((_) {
      final String? competitionId = widget.competitionId;
      if (competitionId != null) {
        widget.creatorController.selectCompetition(competitionId);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Creator competition share')),
      body: AnimatedBuilder(
        animation: widget.creatorController,
        builder: (BuildContext context, _) {
          if ((widget.creatorController.isLoading &&
                  !widget.creatorController.hasData) ||
              widget.creatorController.isLoadingCompetitionShare ||
              widget.creatorController.competitionShare == null) {
            return const Padding(
              padding: EdgeInsets.all(20),
              child: GteStatePanel(
                title: 'Loading creator competition share',
                message:
                    'Preparing share code, invite message, and participation summary.',
                icon: Icons.emoji_events_outlined,
              ),
            );
          }
          if (widget.creatorController.errorMessage != null &&
              !widget.creatorController.hasData) {
            return Padding(
              padding: const EdgeInsets.all(20),
              child: GteStatePanel(
                title: 'Creator competition share unavailable',
                message: widget.creatorController.errorMessage!,
                icon: Icons.error_outline,
              ),
            );
          }

          final CreatorCompetitionShareData share =
              widget.creatorController.competitionShare!;
          return SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                ShareCodeCard(
                  title: share.headline,
                  code: share.shareCode,
                  shareUrl: share.shareUrl,
                  supportingText: share.supportingText,
                  onCopyCode: () => _copyValue(
                    value: share.shareCode,
                    message: 'Competition share code copied.',
                  ),
                  onCopyLink: () => _copyValue(
                    value: share.shareUrl,
                    message: 'Competition invite link copied.',
                  ),
                  onOpenChannelSheet: () => _shareInvite(share),
                ),
                const SizedBox(height: 16),
                GteSurfacePanel(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        share.competition.title,
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        share.competition.seasonLabel,
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        share.competition.inviteWindow,
                        style: Theme.of(context).textTheme.bodyLarge,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        share.competition.inviteAttributionLabel,
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        share.competition.participationLabel,
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 12),
                      Text(
                        share.attributionNote,
                        style: Theme.of(context).textTheme.labelLarge,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  Future<void> _shareInvite(CreatorCompetitionShareData share) async {
    final InviteChannel? channel = await showModalBottomSheet<InviteChannel>(
      context: context,
      builder: (BuildContext context) => const InviteChannelSheet(
        title: 'Share creator competition',
        message:
            'Pick a channel for this creator competition invite. Each option copies a ready message until device sharing is connected.',
      ),
    );
    if (!mounted || channel == null) {
      return;
    }
    final String message =
        'Join creator competition "${share.competition.title}" with code ${share.shareCode}. Invite link: ${share.shareUrl}';
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
