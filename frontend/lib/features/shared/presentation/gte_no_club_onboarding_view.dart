import 'package:flutter/material.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class GteNoClubOnboardingView extends StatelessWidget {
  const GteNoClubOnboardingView({
    super.key,
    this.isAuthenticated = true,
    this.onCreateClub,
    this.onBrowseClubMarket,
    this.onExploreArena,
    this.onOpenMatchday,
    this.onOpenPlayerUniverse,
    this.onOpenWorld,
    this.onOpenWallet,
    this.padding = const EdgeInsets.fromLTRB(20, 12, 20, 120),
  });

  final bool isAuthenticated;
  final VoidCallback? onCreateClub;
  final VoidCallback? onBrowseClubMarket;
  final VoidCallback? onExploreArena;
  final VoidCallback? onOpenMatchday;
  final VoidCallback? onOpenPlayerUniverse;
  final VoidCallback? onOpenWorld;
  final VoidCallback? onOpenWallet;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    final List<_NoClubActionSpec> actions = <_NoClubActionSpec>[
      if (onCreateClub != null)
        _NoClubActionSpec(
          eyebrow: isAuthenticated ? 'FOUNDATION' : 'START HERE',
          chipLabel: isAuthenticated ? 'Create your club' : 'Create account',
          title:
              isAuthenticated ? 'Create your club' : 'Create your GTEX account',
          detail:
              isAuthenticated
                  ? 'Launch a live club workspace, set the badge and palette later, and unlock identity, trophy, scouting, and competition routes immediately.'
                  : 'Register or sign in first, then create a club from scratch when you are ready to own a full football workspace.',
          icon: Icons.add_circle_outline,
          accent: GteShellTheme.accentClub,
          actionLabel: isAuthenticated ? 'Create club' : 'Sign in or register',
          onTap: onCreateClub!,
          prominence: _NoClubActionProminence.primary,
        ),
      if (onBrowseClubMarket != null)
        _NoClubActionSpec(
          eyebrow: 'ALTERNATIVE',
          chipLabel: 'Own an existing club',
          title: 'Own an existing club',
          detail:
              'Browse clubs available for sale, compare value, and take ownership to unlock club management.',
          icon: Icons.storefront_outlined,
          accent: GteShellTheme.accentWarm,
          actionLabel: 'Open club market',
          onTap: onBrowseClubMarket!,
          prominence: _NoClubActionProminence.tonal,
        ),
      if (onExploreArena != null)
        _NoClubActionSpec(
          eyebrow: 'PLAY NOW',
          chipLabel: 'Explore competitions',
          title: 'Explore competitions',
          detail:
              'Open live cups, standings, and football storylines while you decide which club to own or back first.',
          icon: Icons.stadium_outlined,
          accent: GteShellTheme.accentArena,
          actionLabel: 'Open competitions',
          onTap: onExploreArena!,
          prominence: _NoClubActionProminence.outlined,
        ),
      if (onOpenMatchday != null)
        _NoClubActionSpec(
          eyebrow: 'MATCHDAY',
          chipLabel: 'Open matchday hub',
          title: 'Play matchday lanes',
          detail:
              'Enter the routed 2D viewer, broadcast desk, and Flutter 3D lane from the live matchday hub even before you own a club.',
          icon: Icons.sports_soccer_outlined,
          accent: GteShellTheme.accentArena,
          actionLabel: 'Open matchday',
          onTap: onOpenMatchday!,
          prominence: _NoClubActionProminence.tonal,
        ),
      if (onOpenPlayerUniverse != null)
        _NoClubActionSpec(
          eyebrow: 'PLAYER UNIVERSE',
          chipLabel: 'Scout players',
          title: 'Scout players and digital assets',
          detail:
              'Jump into the broader player-card marketplace so real players, listings, and card inventory stay reachable from day one.',
          icon: Icons.person_search_outlined,
          accent: GteShellTheme.accent,
          actionLabel: 'Open player universe',
          onTap: onOpenPlayerUniverse!,
          prominence: _NoClubActionProminence.tonal,
        ),
      if (onOpenWorld != null)
        _NoClubActionSpec(
          eyebrow: 'WORLD ENGINE',
          chipLabel: 'Open regen universe',
          title: 'Open the regen universe',
          detail:
              'Follow rising stars, national regens, scouting feed, and world-building context before you commit to a club.',
          icon: Icons.public_outlined,
          accent: GteShellTheme.accentCommunity,
          actionLabel: 'Open world',
          onTap: onOpenWorld!,
          prominence: _NoClubActionProminence.tonal,
        ),
      if (onOpenWallet != null)
        _NoClubActionSpec(
          eyebrow: 'TREASURY',
          chipLabel: 'Open GTEX coin wallet',
          title: 'Open the GTEX coin wallet',
          detail:
              'Top-up and wallet posture live in the GTEX coin lane, so funding remains visible before you start buying players.',
          icon: Icons.account_balance_wallet_outlined,
          accent: GteShellTheme.accentCapital,
          actionLabel: 'Open wallet',
          onTap: onOpenWallet!,
          prominence: _NoClubActionProminence.outlined,
        ),
    ];
    final List<Widget> overviewChips = <Widget>[
      for (int index = 0; index < actions.length; index++)
        Chip(label: Text('${index + 1}. ${actions[index].chipLabel}')),
    ];
    final List<Widget> overviewActions = actions
        .map(
          (_NoClubActionSpec action) => _OverviewActionButton(action: action),
        )
        .toList(growable: false);
    final List<Widget> cards = actions
        .map(
          (_NoClubActionSpec action) => _NoClubActionCard(
            eyebrow: action.eyebrow,
            title: action.title,
            detail: action.detail,
            icon: action.icon,
            accent: action.accent,
            actionLabel: action.actionLabel,
            onTap: action.onTap,
          ),
        )
        .toList(growable: false);
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
                  isAuthenticated
                      ? 'This account does not own a club yet'
                      : 'Start with account access, then claim a club',
                  style: Theme.of(context).textTheme.displaySmall,
                ),
                const SizedBox(height: 8),
                Text(
                  isAuthenticated
                      ? 'Create a new club from scratch or take over one already on the market, then come back here to manage identity, trophies, scouting, and matchday operations. You can still enter matchday, the player universe, world/regens, and the GTEX coin wallet right now.'
                      : 'Register or sign in to create a club, but you can already scout the player universe, follow the regen world, open the matchday hub, and inspect the GTEX coin lane before choosing your first club.',
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

class _OverviewActionButton extends StatelessWidget {
  const _OverviewActionButton({required this.action});

  final _NoClubActionSpec action;

  @override
  Widget build(BuildContext context) {
    switch (action.prominence) {
      case _NoClubActionProminence.primary:
        return FilledButton.icon(
          onPressed: action.onTap,
          icon: Icon(action.icon),
          label: Text(action.actionLabel),
        );
      case _NoClubActionProminence.tonal:
        return FilledButton.tonalIcon(
          onPressed: action.onTap,
          icon: Icon(action.icon),
          label: Text(action.actionLabel),
        );
      case _NoClubActionProminence.outlined:
        return OutlinedButton.icon(
          onPressed: action.onTap,
          icon: Icon(action.icon),
          label: Text(action.actionLabel),
        );
    }
  }
}

enum _NoClubActionProminence { primary, tonal, outlined }

class _NoClubActionSpec {
  const _NoClubActionSpec({
    required this.eyebrow,
    required this.chipLabel,
    required this.title,
    required this.detail,
    required this.icon,
    required this.accent,
    required this.actionLabel,
    required this.onTap,
    required this.prominence,
  });

  final String eyebrow;
  final String chipLabel;
  final String title;
  final String detail;
  final IconData icon;
  final Color accent;
  final String actionLabel;
  final VoidCallback onTap;
  final _NoClubActionProminence prominence;
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
