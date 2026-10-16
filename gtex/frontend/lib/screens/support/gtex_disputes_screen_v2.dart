import 'package:flutter/material.dart';

import '../../data/gte_api_repository.dart';
import '../../features/trust_ops_redesign/trust_ops_redesign.dart';

/// Route-compatible V2 wrapper for user-facing support/disputes screens.
class GtexDisputesScreenV2 extends StatelessWidget {
  const GtexDisputesScreenV2({
    super.key,
    this.repository,
    this.backendMode = GteBackendMode.live,
    this.onCreateDispute,
  });

  final GtexTrustOpsRepository? repository;
  final GteBackendMode backendMode;
  final VoidCallback? onCreateDispute;

  @override
  Widget build(BuildContext context) {
    return GtexKycDisputesScreen(
      repository:
          repository ??
          (backendMode == GteBackendMode.fixture
              ? const GtexTrustOpsDemoRepository()
              : null),
      initialModule: GtexTrustModule.disputes,
      onCreateDispute: onCreateDispute,
    );
  }
}
