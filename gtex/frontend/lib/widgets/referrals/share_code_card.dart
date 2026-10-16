import 'package:flutter/material.dart';

import '../gte_surface_panel.dart';

class ShareCodeCard extends StatelessWidget {
  const ShareCodeCard({
    super.key,
    required this.title,
    required this.code,
    required this.shareUrl,
    required this.supportingText,
    required this.onCopyCode,
    required this.onCopyLink,
    required this.onOpenChannelSheet,
  });

  final String title;
  final String code;
  final String shareUrl;
  final String supportingText;
  final VoidCallback onCopyCode;
  final VoidCallback onCopyLink;
  final VoidCallback onOpenChannelSheet;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      emphasized: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            title,
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          Text(
            supportingText,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 16),
          SelectableText(
            code,
            style: Theme.of(context).textTheme.displaySmall?.copyWith(
                  fontSize: 28,
                ),
          ),
          const SizedBox(height: 8),
          SelectableText(
            shareUrl,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 18),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: <Widget>[
              FilledButton.icon(
                onPressed: onCopyCode,
                icon: const Icon(Icons.copy_all_outlined),
                label: const Text('Copy code'),
              ),
              FilledButton.tonalIcon(
                onPressed: onCopyLink,
                icon: const Icon(Icons.link_outlined),
                label: const Text('Copy link'),
              ),
              OutlinedButton.icon(
                onPressed: onOpenChannelSheet,
                icon: const Icon(Icons.share_outlined),
                label: const Text('Share invite'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
