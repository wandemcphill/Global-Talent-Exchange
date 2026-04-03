import 'package:flutter/material.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class GteNoClubOnboardingView extends StatelessWidget {
  const GteNoClubOnboardingView({
    super.key,
    this.onCreateClub,
    this.onBrowseClubMarket,
    this.onExploreArena,
    this.padding = const EdgeInsets.fromLTRB(20, 12, 20, 120),
  });

  final VoidCallback? onCreateClub;
  final VoidCallback? onBrowseClubMarket;
  final VoidCallback? onExploreArena;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    final List<Widget> overviewChips = <Widget>[
      if (onCreateClub != null) const Chip(label: Text('1. Create your club')),
      if (onBrowseClubMarket != null)
        const Chip(label: Text('2. Own an existing club')),
      if (onExploreArena != null)
        const Chip(label: Text('3. Explore competitions')),
    ];
    final List<Widget> overviewActions = <Widget>[
      if (onCreateClub != null)
        FilledButton.icon(
          onPressed: onCreateClub,
          icon: const Icon(Icons.add_circle_outline),
          label: const Text('Create your club'),
        ),
      if (onBrowseClubMarket != null)
        FilledButton.tonalIcon(
          onPressed: onBrowseClubMarket,
          icon: const Icon(Icons.storefront_outlined),
          label: const Text('Browse club market'),
        ),
      if (onExploreArena != null)
        OutlinedButton.icon(
          onPressed: onExploreArena,
          icon: const Icon(Icons.stadium_outlined),
          label: const Text('Explore competitions'),
        ),
    ];
    final List<Widget> cards = <Widget>[
      if (onCreateClub != null)
        _NoClubActionCard(
          eyebrow: 'FIRST STEP',
          title: 'Create your club',
          detail:
              'Launch a live club workspace, set the badge and palette later, and unlock identity, trophy, scouting, and competition routes immediately.',
          icon: Icons.add_circle_outline,
          accent: GteShellTheme.accentClub,
          actionLabel: 'Create club',
          onTap: onCreateClub!,
        ),
      if (onBrowseClubMarket != null)
        _NoClubActionCard(
          eyebrow: 'ALTERNATIVE',
          title: 'Own an existing club',
          detail:
              'Browse clubs available for sale, compare value, and take ownership to unlock club management.',
          icon: Icons.storefront_outlined,
          accent: GteShellTheme.accentWarm,
          actionLabel: 'Open club market',
          onTap: onBrowseClubMarket!,
        ),
      if (onExploreArena != null)
        _NoClubActionCard(
          eyebrow: 'ALSO AVAILABLE',
          title: 'Explore competitions',
          detail:
              'Join competitions while you decide which club to own or back first.',
          icon: Icons.stadium_outlined,
          accent: GteShellTheme.accentArena,
          actionLabel: 'Open competitions',
          onTap: onExploreArena!,
        ),
    ];
    return SingleChildScrollView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: padding,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          GteSurfacePanel(
            emphasized: true,
            accentColor: GteShellTheme.accent,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  'CLUB SETUP',
                  style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    color: GteShellTheme.accent,
                    letterSpacing: 1.1,
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  'This account does not own a club yet',
                  style: Theme.of(context).textTheme.displaySmall,
                ),
                const SizedBox(height: 8),
                Text(
                  'Create a new club from scratch or take over one already on the market, then come back here to manage identity, trophies, scouting, and matchday operations.',
                  style: Theme.of(context).textTheme.bodyLarge,
                ),
                const SizedBox(height: 18),
                Wrap(spacing: 12, runSpacing: 12, children: overviewChips),
                const SizedBox(height: 20),
                Wrap(spacing: 12, runSpacing: 12, children: overviewActions),
              ],
            ),
          ),
          const SizedBox(height: 20),
          LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              if (constraints.maxWidth < 820) {
                return Column(
                  children: cards
                      .map(
                        (Widget child) => Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: child,
                        ),
                      )
                      .toList(growable: false),
                );
              }
              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: cards
                    .map(
                      (Widget child) => Expanded(
                        child: Padding(
                          padding: EdgeInsets.only(
                            right: identical(child, cards.last) ? 0 : 12,
                          ),
                          child: child,
                        ),
                      ),
                    )
                    .toList(growable: false),
              );
            },
          ),
        ],
      ),
    );
  }
}

class _NoClubActionCard extends StatelessWidget {
  const _NoClubActionCard({
    required this.eyebrow,
    required this.title,
    required this.detail,
    required this.icon,
    required this.accent,
    required this.actionLabel,
    required this.onTap,
  });

  final String eyebrow;
  final String title;
  final String detail;
  final IconData icon;
  final Color accent;
  final String actionLabel;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      accentColor: accent,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            eyebrow,
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: accent,
              letterSpacing: 1.05,
            ),
          ),
          const SizedBox(height: 12),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Icon(icon, color: accent),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(title, style: Theme.of(context).textTheme.titleLarge),
                    const SizedBox(height: 8),
                    Text(detail, style: Theme.of(context).textTheme.bodyMedium),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          OutlinedButton.icon(
            onPressed: onTap,
            icon: Icon(icon),
            label: Text(actionLabel),
          ),
        ],
      ),
    );
  }
}
