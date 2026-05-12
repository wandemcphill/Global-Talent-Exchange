import 'package:flutter/material.dart';

import '../../data/gte_api_repository.dart';
import '../../features/trust_ops_redesign/trust_ops_redesign.dart';

/// Route-compatible V2 wrapper for admin trust operations.
class GtexAdminTrustOpsScreenV2 extends StatelessWidget {
  const GtexAdminTrustOpsScreenV2({
    super.key,
    this.baseUrl = 'http://127.0.0.1:8000',
    this.accessToken,
    this.backendMode = GteBackendMode.live,
  });

  final String baseUrl;
  final String? accessToken;
  final GteBackendMode backendMode;

  @override
  Widget build(BuildContext context) {
    return GtexAdminTrustOpsScreen(
      baseUrl: baseUrl,
      accessToken: accessToken,
      backendMode: backendMode,
    );
  }
}
