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
                    'Club extensions',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Quick links keep club-adjacent routes close to the canonical workspace instead of promoting them into separate shell tabs.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 16),
                  Wrap(
                    spacing: 12,
                    runSpacing: 12,
                    children: <Widget>[
                      FilledButton.tonalIcon(
                        onPressed:
                            () => _openRoute(
                              context,
                              WorldClubContextRouteData(
                                clubId: clubId,
                                clubName: _resolvedClubName,
                              ),
                            ),
                        icon: const Icon(Icons.public_outlined),
                        label: const Text('World context'),
                      ),
                      FilledButton.tonalIcon(
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
                        icon: const Icon(Icons.inbox_outlined),
                        label: const Text('Owner-only inbox'),
                      ),
                    ],
                  ),
                  const SizedBox(height: 14),
                  Text(
                    _ownsWorkspace
                        ? 'Owner inbox is armed for this club workspace.'
                        : 'Switch into this club owner workspace before opening the owner offer inbox.',
                    style: Theme.of(context).textTheme.bodyMedium,
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
