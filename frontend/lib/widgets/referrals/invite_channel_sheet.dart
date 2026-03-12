import 'package:flutter/material.dart';

import '../../models/referral_models.dart';

class InviteChannelSheet extends StatelessWidget {
  const InviteChannelSheet({
    super.key,
    required this.title,
    required this.message,
  });

  final String title;
  final String message;

  @override
  Widget build(BuildContext context) {
    final List<InviteChannel> channels = <InviteChannel>[
      InviteChannel.whatsApp,
      InviteChannel.telegram,
      InviteChannel.systemShare,
      InviteChannel.copyLink,
      InviteChannel.copyCode,
    ];

    return SafeArea(
      child: ConstrainedBox(
        constraints: BoxConstraints(
          maxHeight: MediaQuery.of(context).size.height * 0.8,
        ),
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                title,
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 8),
              Text(
                message,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 18),
              for (final InviteChannel channel in channels)
                ListTile(
                  leading: Icon(_iconFor(channel)),
                  title: Text(channel.label),
                  subtitle: Text(channel.helperText),
                  onTap: () =>
                      Navigator.of(context).pop<InviteChannel>(channel),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

IconData _iconFor(InviteChannel channel) {
  switch (channel) {
    case InviteChannel.copyCode:
      return Icons.copy_outlined;
    case InviteChannel.copyLink:
      return Icons.link_outlined;
    case InviteChannel.whatsApp:
      return Icons.forum_outlined;
    case InviteChannel.telegram:
      return Icons.send_outlined;
    case InviteChannel.systemShare:
      return Icons.ios_share_outlined;
  }
}
