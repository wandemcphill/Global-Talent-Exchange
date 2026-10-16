import 'package:flutter/material.dart';

import '../../controllers/creator_controller.dart';
import '../../models/creator_models.dart';
import '../../widgets/gte_shell_theme.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/gte_surface_panel.dart';

class CreatorProfileScreen extends StatefulWidget {
  const CreatorProfileScreen({super.key, required this.controller});

  final CreatorController controller;

  @override
  State<CreatorProfileScreen> createState() => _CreatorProfileScreenState();
}

class _CreatorProfileScreenState extends State<CreatorProfileScreen> {
  @override
  void initState() {
    super.initState();
    widget.controller.load();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: widget.controller,
      builder: (BuildContext context, Widget? child) {
        final CreatorProfile? profile = widget.controller.profile;
        if (profile == null && widget.controller.isLoading) {
          return const Center(child: CircularProgressIndicator());
        }
        if (profile == null) {
          return Padding(
            padding: const EdgeInsets.all(20),
            child: GteStatePanel(
              title: 'Creator profile unavailable',
              message:
                  widget.controller.errorMessage ??
                  'Creator profile data is still syncing.',
              actionLabel: 'Retry',
              onAction: () => widget.controller.load(force: true),
              icon: Icons.person_pin_circle_outlined,
              accentColor: GteShellTheme.accentCommunity,
            ),
          );
        }
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
          children: <Widget>[
            GteSurfacePanel(
              emphasized: true,
              accentColor: GteShellTheme.accentCommunity,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    profile.displayName,
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 8),
                  Text(profile.handleLabel),
                  const SizedBox(height: 8),
                  Text(profile.bio),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 12,
                    runSpacing: 12,
                    children: <Widget>[
                      Chip(label: Text('Tier: ${profile.tier}')),
                      Chip(label: Text('Status: ${profile.status}')),
                      Chip(label: Text('Share code: ${profile.shareCode}')),
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
                    'Community footprint',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 8),
                  Text('Invites: ${profile.stats.communityInvites}'),
                  Text('Qualified joins: ${profile.stats.qualifiedReferrals}'),
                  Text('Competitions: ${profile.stats.creatorCompetitions}'),
                  Text('Participants: ${profile.stats.contestParticipants}'),
                ],
              ),
            ),
          ],
        );
      },
    );
  }
}
