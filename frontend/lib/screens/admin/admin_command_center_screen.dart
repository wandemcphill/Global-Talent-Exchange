import 'package:flutter/material.dart';

import '../../data/gte_api_repository.dart';
import '../../features/app_routes/gte_navigation_helpers.dart';
import '../../features/app_routes/gte_route_data.dart';
import '../../features/navigation_guards/gte_navigation_guards.dart';
import '../../widgets/gte_shell_theme.dart';
import '../../widgets/gte_surface_panel.dart';

class AdminCommandCenterScreen extends StatelessWidget {
  const AdminCommandCenterScreen({
    super.key,
    required this.baseUrl,
    required this.accessToken,
    required this.backendMode,
  });

  final String baseUrl;
  final String accessToken;
  final GteBackendMode backendMode;

  GteNavigationDependencies get _dependencies => GteNavigationDependencies(
    apiBaseUrl: baseUrl,
    backendMode: backendMode,
    accessToken: accessToken,
    isAuthenticated: accessToken.trim().isNotEmpty,
    currentUserRole: 'admin',
  );

  Future<void> _openRoute(BuildContext context, GteAppRouteData route) {
    return GteNavigationHelpers.pushRoute<void>(
      context,
      route: route,
      dependencies: _dependencies,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(title: const Text('Admin command center')),
        body: ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
          children: <Widget>[
            GteSurfacePanel(
              emphasized: true,
              accentColor: GteShellTheme.accentAdmin,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    'Command routes',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Admin-only engines stay grouped here so finance, creator, and stabilizer controls can launch through the canonical route registry.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 16),
                  FilledButton.icon(
                    onPressed:
                        () => _openRoute(
                          context,
                          const GiftStabilizerRouteData(),
                        ),
                    icon: const Icon(Icons.card_giftcard_outlined),
                    label: const Text('Gift stabilizer'),
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
