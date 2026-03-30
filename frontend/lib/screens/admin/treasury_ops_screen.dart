import 'package:flutter/material.dart';

import '../../data/gte_api_repository.dart';
import '../../widgets/gte_route_integrity_screen.dart';

class GteTreasuryOpsScreen extends StatelessWidget {
  const GteTreasuryOpsScreen({
    super.key,
    required this.baseUrl,
    required this.accessToken,
    this.backendMode = GteBackendMode.live,
  });

  final String baseUrl;
  final String accessToken;
  final GteBackendMode backendMode;

  @override
  Widget build(BuildContext context) {
    return const GteRouteIntegrityScreen.blocked(
      title: 'Treasury operations unavailable',
      message:
          'Treasury routes are blocked until settings, queues, and disputes can load from the real backend without exchange fallback.',
      icon: Icons.account_balance_wallet_outlined,
    );
  }
}
