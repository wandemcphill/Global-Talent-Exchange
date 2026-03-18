import 'package:flutter/material.dart';

import '../../data/gte_api_repository.dart';
import '../../widgets/gte_route_integrity_screen.dart';

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

  @override
  Widget build(BuildContext context) {
    return const GteRouteIntegrityScreen.hidden(
      title: 'Admin command center removed from active shell',
      message:
          'Admin command center routes stay hidden until policy, finance, and admin engine surfaces are backed by the real backend only.',
      icon: Icons.dashboard_customize_outlined,
    );
  }

  Future<void> _openRoute(GteAppRouteData route) {
    return GteNavigationHelpers.pushRoute<void>(
      context,
      route: route,
      dependencies: _routeDependencies(),
    );
  }

  GteNavigationDependencies _routeDependencies() {
    final String accessToken = widget.accessToken.trim();
    final bool hasAdminSession = accessToken.isNotEmpty;
    return GteNavigationDependencies(
      apiBaseUrl: widget.baseUrl,
      backendMode: widget.backendMode,
      currentUserId: hasAdminSession ? 'admin-user' : 'guest-user',
      currentUserName: hasAdminSession ? 'Admin' : null,
      currentUserRole: hasAdminSession ? 'admin' : null,
      accessToken: hasAdminSession ? accessToken : null,
      isAuthenticated: hasAdminSession,
    );
  }
}
