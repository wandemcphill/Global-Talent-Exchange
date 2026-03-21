import 'package:flutter/material.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class GteNoClubOnboardingView extends StatelessWidget {
  const GteNoClubOnboardingView({
    super.key,
    this.onBrowseClubMarket,
    this.onExploreArena,
    this.padding = const EdgeInsets.fromLTRB(20, 12, 20, 120),
  });

  final VoidCallback? onBrowseClubMarket;
  final VoidCallback? onExploreArena;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    final List<Widget> overviewChips = <Widget>[
      if (onBrowseClubMarket != null)
        const Chip(label: Text('1. Browse Club Market')),
      if (onExploreArena != null) const Chip(label: Text('2. Explore Arena')),
    ];
    final List<Widget> overviewActions = <Widget>[
      if (onBrowseClubMarket != null)
        FilledButton.icon(
          onPressed: onBrowseClubMarket,
          icon: const Icon(Icons.storefront_outlined),
          label: const Text('Browse Club Market'),
        ),
      if (onExploreArena != null)
        FilledButton.tonalIcon(
          onPressed: onExploreArena,
          icon: const Icon(Icons.stadium_outlined),
          label: const Text('Explore Arena'),
        ),
    ];
    final List<Widget> cards = <Widget>[
      if (onBrowseClubMarket != null)
        _NoClubActionCard(
          eyebrow: 'PLAY NOW',
          title: 'Browse Club Market',
          detail:
              'Scout live club prices and sale notes even before you own a club.',
          icon: Icons.storefront_outlined,
          accent: GteShellTheme.accentWarm,
          actionLabel: 'Browse Club Market',
          onTap: onBrowseClubMarket!,
        ),
      if (onExploreArena != null)
        _NoClubActionCard(
          eyebrow: 'PLAY NOW',
          title: 'Explore Arena',
          detail:
              'Jump into cups and live match nights while club linking is still pending.',
          icon: Icons.stadium_outlined,
          accent: GteShellTheme.accentArena,
          actionLabel: 'Explore Arena',
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
                  'NO CLUB ONBOARDING',
                  style: Theme.of(context).textTheme.labelLarge?.copyWith(
                        color: GteShellTheme.accent,
                        letterSpacing: 1.1,
                      ),
                ),
                const SizedBox(height: 12),
                Text(
                  'Your club spot is still open',
                  style: Theme.of(context).textTheme.displaySmall,
                ),
                const SizedBox(height: 8),
                Text(
                  'Club-only actions stay locked until this account is linked to a club. Until then, jump into the live routes below.',
                  style: Theme.of(context).textTheme.bodyLarge,
                ),
                const SizedBox(height: 18),
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: overviewChips,
                ),
                const SizedBox(height: 20),
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: overviewActions,
                ),
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
          FilledButton.tonalIcon(
            onPressed: onTap,
            icon: Icon(icon),
            label: Text(actionLabel),
          ),
        ],
      ),
    );
  }
}
