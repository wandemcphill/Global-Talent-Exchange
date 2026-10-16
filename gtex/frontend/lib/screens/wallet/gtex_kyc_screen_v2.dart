import 'package:flutter/material.dart';

import '../../data/gte_api_repository.dart';
import '../../features/trust_ops_redesign/trust_ops_redesign.dart';

/// Route-compatible V2 wrapper for the existing user KYC route.
class GtexKycScreenV2 extends StatelessWidget {
  const GtexKycScreenV2({
    super.key,
    this.repository,
    this.backendMode = GteBackendMode.live,
  });

  final GtexTrustOpsRepository? repository;
  final GteBackendMode backendMode;

  @override
  Widget build(BuildContext context) {
    return GtexKycDisputesScreen(
      repository:
          repository ??
          (backendMode == GteBackendMode.fixture
              ? const GtexTrustOpsDemoRepository()
              : null),
      initialModule: GtexTrustModule.kyc,
    );
  }
}
