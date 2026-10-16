import 'package:flutter/material.dart';

import '../../models/creator_models.dart';
import '../gte_shell_theme.dart';
import '../gte_surface_panel.dart';

class CreatorHeaderCard extends StatelessWidget {
  const CreatorHeaderCard({
    super.key,
    required this.profile,
    this.onShareCodeTap,
  });

  final CreatorProfile profile;
  final VoidCallback? onShareCodeTap;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      emphasized: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Container(
                width: 64,
                height: 64,
                decoration: BoxDecoration(
                  color: GteShellTheme.accent.withValues(alpha: 0.14),
                  borderRadius: BorderRadius.circular(22),
                ),
                alignment: Alignment.center,
                child: Text(
                  profile.displayName.characters.first.toUpperCase(),
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      profile.displayName,
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      profile.handleLabel,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            color: GteShellTheme.accent,
                          ),
                    ),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: <Widget>[
                        Chip(
                          label: Text(profile.communityTag),
                          avatar: const Icon(Icons.campaign_outlined, size: 18),
                        ),
                        ActionChip(
                          label: Text('Share code ${profile.shareCode}'),
                          avatar:
                              const Icon(Icons.qr_code_2_outlined, size: 18),
                          onPressed: onShareCodeTap,
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Text(
            profile.headline,
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          Text(
            profile.bio,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
        ],
      ),
    );
  }
}
