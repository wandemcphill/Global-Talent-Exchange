import 'package:flutter/material.dart';

import '../../features/trust_ops_redesign/trust_ops_redesign.dart';

/// Route-compatible V2 wrapper for the existing user KYC route.
class GtexKycScreenV2 extends StatelessWidget {
  const GtexKycScreenV2({super.key});

  @override
  Widget build(BuildContext context) {
    return const GtexKycDisputesScreen(initialModule: GtexTrustModule.kyc);
  }
}
