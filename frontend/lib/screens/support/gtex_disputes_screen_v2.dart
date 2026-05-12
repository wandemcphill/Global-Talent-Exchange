import 'package:flutter/material.dart';

import '../../features/trust_ops_redesign/trust_ops_redesign.dart';

/// Route-compatible V2 wrapper for user-facing support/disputes screens.
class GtexDisputesScreenV2 extends StatelessWidget {
  const GtexDisputesScreenV2({
    super.key,
    this.onCreateDispute,
  });

  final VoidCallback? onCreateDispute;

  @override
  Widget build(BuildContext context) {
    return GtexKycDisputesScreen(
      initialModule: GtexTrustModule.disputes,
      onCreateDispute: onCreateDispute,
    );
  }
}
