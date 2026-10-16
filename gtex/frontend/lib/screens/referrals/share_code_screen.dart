import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../controllers/referral_controller.dart';
import '../../models/referral_models.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/referrals/invite_channel_sheet.dart';
import '../../widgets/referrals/share_code_card.dart';

class ShareCodeScreen extends StatefulWidget {
  const ShareCodeScreen({
    super.key,
    required this.controller,
  });

  final ReferralController controller;

  @override
  State<ShareCodeScreen> createState() => _ShareCodeScreenState();
}

class _ShareCodeScreenState extends State<ShareCodeScreen> {
  @override
  void initState() {
    super.initState();
    widget.controller.load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Share code')),
      body: AnimatedBuilder(
        animation: widget.controller,
        builder: (BuildContext context, _) {
          if (widget.controller.isLoading && !widget.controller.hasData) {
            return const Padding(
              padding: EdgeInsets.all(20),
              child: GteStatePanel(
                title: 'Loading share code',
                message:
                    'Preparing your invite link and creator competition copy.',
                icon: Icons.qr_code_2_outlined,
              ),
            );
          }
          if (widget.controller.errorMessage != null &&
              !widget.controller.hasData) {
            return Padding(
              padding: const EdgeInsets.all(20),
              child: GteStatePanel(
                title: 'Share code unavailable',
                message: widget.controller.errorMessage!,
                icon: Icons.error_outline,
              ),
            );
          }

          final ReferralHubData hub = widget.controller.hub!;
          return SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                ShareCodeCard(
                  title: 'Share your code',
                  code: hub.shareCode,
                  shareUrl: hub.shareUrl,
                  supportingText:
                      'Invite friends into creator competitions with a simple share code. Qualified joins count toward milestone rewards and participation credits.',
                  onCopyCode: () => _copyValue(
                    value: hub.shareCode,
                    message: 'Share code copied.',
                  ),
                  onCopyLink: () => _copyValue(
                    value: hub.shareUrl,
                    message: 'Invite link copied.',
                  ),
                  onOpenChannelSheet: () => _openChannelSheet(
                    hub: hub,
                  ),
                ),
                const SizedBox(height: 16),
                Text(
                  'Invite friends',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 8),
                Text(
                  'Share your code in WhatsApp circles, Telegram groups, or any system share flow. Until a native share integration is connected, each option copies a ready invite message.',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  Future<void> _openChannelSheet({
    required ReferralHubData hub,
  }) async {
    final InviteChannel? channel = await showModalBottomSheet<InviteChannel>(
      context: context,
      builder: (BuildContext context) => const InviteChannelSheet(
        title: 'Share invite',
        message:
            'Pick a channel for your community invite. Each action prepares creator-friendly copy with your code.',
      ),
    );
    if (!mounted || channel == null) {
      return;
    }
    final String message =
        'Share your code ${hub.shareCode}. Creator competition invite: ${hub.shareUrl}';
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
