import 'package:flutter/material.dart';

import '../../data/gte_api_repository.dart';
import '../../widgets/gte_route_integrity_screen.dart';

class AdminFinancialDashboardScreen extends StatelessWidget {
  const AdminFinancialDashboardScreen({
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
    return const GteRouteIntegrityScreen.blocked(
      title: 'Admin finance unavailable',
      message:
          'Admin finance routes are blocked until the economy control tower and simulations can run against the real backend only.',
      icon: Icons.account_balance_outlined,
    );
  }
}
