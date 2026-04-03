import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_controller.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/app_routes/gte_navigation_helpers.dart';
import 'package:gte_frontend/features/app_routes/gte_route_data.dart';
import 'package:gte_frontend/features/club_navigation/club_navigation.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';
import 'package:gte_frontend/widgets/gtex_branding.dart';

class ClubHubScreen extends StatelessWidget {
  const ClubHubScreen({
    super.key,
    required this.clubId,
    this.clubName,
    this.controller,
    this.baseUrl = 'http://127.0.0.1:8000',
    this.backendMode = GteBackendMode.live,
    this.isAuthenticated = true,
    this.onOpenLogin,
    this.initialTab = ClubNavigationTab.squad,
    this.navigationDependencies,
  });

  final String clubId;
  final String? clubName;
  final ClubController? controller;
  final String baseUrl;
  final GteBackendMode backendMode;
  final bool isAuthenticated;
  final VoidCallback? onOpenLogin;
  final ClubNavigationTab initialTab;
  final GteNavigationDependencies? navigationDependencies;

  GteNavigationDependencies get _dependencies =>
      navigationDependencies ??
      GteNavigationDependencies(
        apiBaseUrl: baseUrl,
        backendMode: backendMode,
        currentClubId: clubId,
        currentClubName: clubName,
        isAuthenticated: isAuthenticated,
      );

  String get _resolvedClubName {
    final String? trimmed = clubName?.trim();
    if (trimmed != null && trimmed.isNotEmpty) {
      return trimmed;
    }
    return clubId
        .split('-')
        .where((String fragment) => fragment.isNotEmpty)
        .map(
          (String fragment) =>
              '${fragment[0].toUpperCase()}${fragment.substring(1)}',
        )
        .join(' ');
  }

  bool get _ownsWorkspace {
    final String? currentClubId = _dependencies.currentClubId?.trim();
    return currentClubId != null && currentClubId == clubId;
  }

  Future<void> _openRoute(BuildContext context, GteAppRouteData route) {
    return GteNavigationHelpers.pushRoute<void>(
      context,
      route: route,
      dependencies: _dependencies,
    );
  }

  Widget _buildRouteButton({
    required VoidCallback? onPressed,
    required IconData icon,
    required String label,
    bool emphasized = false,
  }) {
    if (emphasized) {
      return FilledButton.icon(
        onPressed: onPressed,
        icon: Icon(icon),
        label: Text(label),
      );
    }
    return FilledButton.tonalIcon(
      onPressed: onPressed,
      icon: Icon(icon),
      label: Text(label),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (!isAuthenticated) {
      return Container(
        decoration: gteBackdropDecoration(),
        child: Scaffold(
          backgroundColor: Colors.transparent,
          appBar: AppBar(title: const Text('Club hub')),
          body: Padding(
            padding: const EdgeInsets.all(20),
            child: GteStatePanel(
              eyebrow: 'CLUB ACCESS',
              title: 'Sign in to open club routes',
              message:
                  'Club extensions need an authenticated session before world context, owner inbox, and club-scoped flows can open.',
              actionLabel: onOpenLogin == null ? null : 'Sign in',
              onAction: onOpenLogin,
              icon: Icons.login_outlined,
              accentColor: GteShellTheme.accentClub,
            ),
          ),
        ),
      );
    }

    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              const Text('Club hub'),
              Text(
                _resolvedClubName,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ],
          ),
        ),
        body: ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
          children: <Widget>[
            GteSurfacePanel(
              emphasized: true,
              accentColor: GteShellTheme.accentClub,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      const GtexLogoMark(size: 36, compact: true),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Text(
                              _resolvedClubName,
                              style: Theme.of(context).textTheme.headlineSmall,
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'Club routes stay focused on the canonical workspace so football-world, owner, and identity actions do not drift into fallback contexts.',
                              style: Theme.of(context).textTheme.bodyMedium,
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  Wrap(
                    spacing: 10,
                    runSpacing: 10,
                    children: const <Widget>[
                      Chip(label: Text('Club scope')),
                      Chip(label: Text('Owner actions')),
                      Chip(label: Text('World lane')),
                      Chip(label: Text('2D / 3D replays')),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),
            GteSurfacePanel(
              accentColor: GteShellTheme.accentClub,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    'Club operations',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Open the routes that shape how the club looks, competes, and gets remembered.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 16),
                  Wrap(
                    spacing: 12,
                    runSpacing: 12,
                    children: <Widget>[
                      _buildRouteButton(
                        onPressed:
                            () => _openRoute(
                              context,
                              const CompetitionCreateRouteData(),
                            ),
                        icon: Icons.add_circle_outline,
                        label: 'Create competition',
                        emphasized: true,
                      ),
                      _buildRouteButton(
                        onPressed:
                            () => _openRoute(
                              context,
                              ClubIdentityJerseysRouteData(
                                clubId: clubId,
                                clubName: _resolvedClubName,
                              ),
                            ),
                        icon: Icons.shield_outlined,
                        label: 'Club identity',
                      ),
                      _buildRouteButton(
                        onPressed:
                            () => _openRoute(
                              context,
                              ClubReputationOverviewRouteData(
                                clubId: clubId,
                                clubName: _resolvedClubName,
                              ),
                            ),
                        icon: Icons.workspace_premium_outlined,
                        label: 'Reputation',
                      ),
                      _buildRouteButton(
                        onPressed:
                            () => _openRoute(
                              context,
                              ClubTrophyCabinetRouteData(
                                clubId: clubId,
                                clubName: _resolvedClubName,
                              ),
                            ),
                        icon: Icons.emoji_events_outlined,
                        label: 'Trophy cabinet',
                      ),
                      _buildRouteButton(
                        onPressed:
                            () => _openRoute(
                              context,
                              ClubDynastyOverviewRouteData(
                                clubId: clubId,
                                clubName: _resolvedClubName,
                              ),
                            ),
                        icon: Icons.auto_graph_outlined,
                        label: 'Dynasty',
                      ),
                      _buildRouteButton(
                        onPressed:
                            () => _openRoute(
                              context,
                              ClubAiAssistantRouteData(
                                clubId: clubId,
                                clubName: _resolvedClubName,
                              ),
                            ),
                        icon: Icons.smart_toy_outlined,
                        label: 'AI assistant',
                      ),
                      _buildRouteButton(
                        onPressed:
                            () => _openRoute(
                              context,
                              ClubReplaysRouteData(
                                clubId: clubId,
                                clubName: _resolvedClubName,
                              ),
                            ),
                        icon: Icons.play_circle_outline,
                        label: '2D / 3D replays',
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),
            GteSurfacePanel(
              accentColor: GteShellTheme.accentCapital,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    'Commercial lanes',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Move from ownership into sale-market, creator-stadium, and creator-share-market flows without leaving the club workspace.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 16),
                  Wrap(
                    spacing: 12,
                    runSpacing: 12,
                    children: <Widget>[
                      _buildRouteButton(
                        onPressed:
                            () => _openRoute(
                              context,
                              CreatorShareMarketClubRouteData(
                                clubId: clubId,
                                clubName: _resolvedClubName,
                              ),
                            ),
                        icon: Icons.insights_outlined,
                        label: 'Creator share market',
                        emphasized: true,
                      ),
                      _buildRouteButton(
                        onPressed:
                            () => _openRoute(
                              context,
                              CreatorStadiumClubRouteData(
                                clubId: clubId,
                                clubName: _resolvedClubName,
                              ),
                            ),
                        icon: Icons.theaters_outlined,
                        label: 'Creator stadium',
                      ),
                      _buildRouteButton(
                        onPressed:
                            () => _openRoute(
                              context,
                              ClubSaleMarketDetailRouteData(
                                clubId: clubId,
                                clubName: _resolvedClubName,
                              ),
                            ),
                        icon: Icons.sell_outlined,
                        label: 'Sell this club',
                      ),
                      _buildRouteButton(
                        onPressed:
                            () => _openRoute(
                              context,
                              const ClubSaleMarketListingsRouteData(),
                            ),
                        icon: Icons.storefront_outlined,
                        label: 'Browse club market',
                      ),
                      _buildRouteButton(
                        onPressed:
                            _ownsWorkspace
                                ? () => _openRoute(
                                  context,
                                  ClubSaleMarketOwnerOffersRouteData(
                                    clubId: clubId,
                                    clubName: _resolvedClubName,
                                  ),
                                )
                                : null,
                        icon: Icons.inbox_outlined,
                        label: 'Owner offer inbox',
                      ),
                    ],
                  ),
                  const SizedBox(height: 14),
                  Text(
                    _ownsWorkspace
                        ? 'Owner offer review is armed for this club workspace.'
                        : 'Switch into this club owner workspace before opening owner offer review.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),
            GteSurfacePanel(
              accentColor: GteShellTheme.accentArena,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    'World and scouting',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Use the club as the anchor point for world context, club-generated regens, national pre-seeds, transfer planning, and streamer tournaments.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 16),
                  Wrap(
                    spacing: 12,
                    runSpacing: 12,
                    children: <Widget>[
                      _buildRouteButton(
                        onPressed:
                            () => _openRoute(
                              context,
                              WorldClubContextRouteData(
                                clubId: clubId,
                                clubName: _resolvedClubName,
                              ),
                            ),
                        icon: Icons.public_outlined,
                        label: 'World context',
                        emphasized: true,
                      ),
                      _buildRouteButton(
                        onPressed:
                            () => _openRoute(
                              context,
                              WorldClubContextRouteData(
                                clubId: clubId,
                                clubName: _resolvedClubName,
                              ),
                            ),
                        icon: Icons.auto_awesome_outlined,
                        label: 'Regen universe',
                      ),
                      _buildRouteButton(
                        onPressed:
                            () => _openRoute(
                              context,
                              const FootballTransferCenterRouteData(),
                            ),
                        icon: Icons.swap_horiz_outlined,
                        label: 'Transfer center',
                      ),
                      _buildRouteButton(
                        onPressed:
                            () => _openRoute(
                              context,
                              const PlayerCardsBrowseRouteData(),
                            ),
                        icon: Icons.style_outlined,
                        label: 'Player cards',
                      ),
                      _buildRouteButton(
                        onPressed:
                            () => _openRoute(
                              context,
                              const NationalTeamCompetitionsRouteData(),
                            ),
                        icon: Icons.flag_outlined,
                        label: 'National teams',
                      ),
                      _buildRouteButton(
                        onPressed:
                            () => _openRoute(
                              context,
                              const StreamerTournamentsListRouteData(),
                            ),
                        icon: Icons.live_tv_outlined,
                        label: 'Streamer tournaments',
                      ),
                      _buildRouteButton(
                        onPressed:
                            () => _openRoute(
                              context,
                              const BroadcastDeskRouteData(),
                            ),
                        icon: Icons.podcasts_outlined,
                        label: 'Broadcast desk',
                      ),
                      _buildRouteButton(
                        onPressed:
                            () => _openRoute(
                              context,
                              const GtexJackpotRouteData(),
                            ),
                        icon: Icons.celebration_outlined,
                        label: 'GTEX jackpot',
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
