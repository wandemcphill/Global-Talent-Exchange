import 'package:flutter/material.dart';

import '../data/gte_api_repository.dart';
import '../features/club_identity/jerseys/presentation/club_identity_screen.dart';
import '../features/club_identity/reputation/presentation/reputation_screen.dart';
import '../features/club_identity/trophies/presentation/trophy_cabinet_screen.dart';
import '../providers/gte_exchange_controller.dart';
import '../widgets/gte_surface_panel.dart';

class GteClubIdentityHubScreen extends StatelessWidget {
  const GteClubIdentityHubScreen({
    super.key,
    required this.controller,
    required this.apiBaseUrl,
    required this.backendMode,
    required this.onOpenLogin,
  });

  final GteExchangeController controller;
  final String apiBaseUrl;
  final GteBackendMode backendMode;
  final VoidCallback onOpenLogin;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (BuildContext context, _) {
        final _ClubIdentityTarget target = _resolveClubTarget(controller);
        return SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              GteSurfacePanel(
                emphasized: true,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      'Club identity',
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Manage your club presence across badges, kits, reputation, and trophies.',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                    const SizedBox(height: 16),
                    Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      children: <Widget>[
                        _MetaChip(
                          icon: Icons.shield_outlined,
                          label: target.clubName,
                        ),
                        _MetaChip(
                          icon: Icons.tag_outlined,
                          label: target.clubId,
                        ),
                        _MetaChip(
                          icon: controller.isAuthenticated
                              ? Icons.verified
                              : Icons.person_outline,
                          label: controller.isAuthenticated
                              ? 'Signed in'
                              : 'Guest preview',
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),
              if (!controller.isAuthenticated)
                GteSurfacePanel(
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      const Icon(Icons.lock_outline),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          'Sign in to sync club identity updates with live services. Demo data is still available while signed out.',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                      ),
                      const SizedBox(width: 12),
                      FilledButton.tonal(
                        onPressed: onOpenLogin,
                        child: const Text('Sign in'),
                      ),
                    ],
                  ),
                ),
              const SizedBox(height: 20),
              _IdentitySection(
                title: 'Identity & kits',
                subtitle:
                    'Edit badge, palette, and kit variants for match intros, standings, and replay cards.',
                buttonLabel: 'Open identity',
                icon: Icons.checkroom_outlined,
                onPressed: () => _openIdentity(context, target),
              ),
              const SizedBox(height: 16),
              _IdentitySection(
                title: 'Reputation',
                subtitle:
                    'Track prestige tiers, leaderboard position, and historical reputation swings.',
                buttonLabel: 'Open reputation',
                icon: Icons.stars_outlined,
                onPressed: () => _openReputation(context, target),
              ),
              const SizedBox(height: 16),
              _IdentitySection(
                title: 'Trophy cabinet',
                subtitle:
                    'Browse honors, timeline archives, and leaderboard standings for your club.',
                buttonLabel: 'Open trophies',
                icon: Icons.emoji_events_outlined,
                onPressed: () => _openTrophies(context, target),
              ),
            ],
          ),
        );
      },
    );
  }

  void _openIdentity(BuildContext context, _ClubIdentityTarget target) {
    Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => ClubIdentityScreen(
          clubId: target.clubId,
          initialClubName: target.clubName,
        ),
      ),
    );
  }

  void _openReputation(BuildContext context, _ClubIdentityTarget target) {
    Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => ClubReputationOverviewScreen(
          clubId: target.clubId,
          clubName: target.clubName,
          baseUrl: apiBaseUrl,
          mode: backendMode,
        ),
      ),
    );
  }

  void _openTrophies(BuildContext context, _ClubIdentityTarget target) {
    Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => TrophyCabinetScreen(
          clubId: target.clubId,
          clubName: target.clubName,
        ),
      ),
    );
  }
}

class _IdentitySection extends StatelessWidget {
  const _IdentitySection({
    required this.title,
    required this.subtitle,
    required this.buttonLabel,
    required this.icon,
    required this.onPressed,
  });

  final String title;
  final String subtitle;
  final String buttonLabel;
  final IconData icon;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Icon(icon),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  title,
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ),
              FilledButton.tonalIcon(
                onPressed: onPressed,
                icon: const Icon(Icons.open_in_new),
                label: Text(buttonLabel),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            subtitle,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
        ],
      ),
    );
  }
}

class _MetaChip extends StatelessWidget {
  const _MetaChip({
    required this.icon,
    required this.label,
  });

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Chip(
      avatar: Icon(icon, size: 18),
      label: Text(label),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
    );
  }
}

class _ClubIdentityTarget {
  const _ClubIdentityTarget({
    required this.clubId,
    required this.clubName,
  });

  final String clubId;
  final String clubName;
}

_ClubIdentityTarget _resolveClubTarget(GteExchangeController controller) {
  final user = controller.session?.user;
  final String? displayName = user?.displayName?.trim();
  final String? username = user?.username.trim();
  if (displayName != null && displayName.isNotEmpty) {
    return _ClubIdentityTarget(
      clubId: _slugify(displayName),
      clubName: displayName,
    );
  }
  if (username != null && username.isNotEmpty) {
    return _ClubIdentityTarget(
      clubId: _slugify(username),
      clubName: username,
    );
  }
  return const _ClubIdentityTarget(
    clubId: 'royal-lagos-fc',
    clubName: 'Royal Lagos FC',
  );
}

String _slugify(String raw) {
  final String slug = raw
      .toLowerCase()
      .replaceAll(RegExp(r'[^a-z0-9]+'), '-')
      .replaceAll(RegExp(r'^-+|-+$'), '');
  if (slug.isEmpty) {
    return 'royal-lagos-fc';
  }
  return slug;
}
