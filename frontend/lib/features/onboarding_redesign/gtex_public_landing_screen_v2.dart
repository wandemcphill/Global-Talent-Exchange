import 'package:flutter/material.dart';

import 'gtex_22_home_screen.dart';

/// The canonical GTEX 2027 Public Homepage and Landing experience.
///
/// Replaces the legacy pre-2027 landing page with the full cinematic football
/// universe: verified club ownership (up to 3 clubs), Phase 5 television revenue,
/// regen economy and talent dossiers, active competitions with 4 scheduled daily
/// jackpot drops (00:00, 06:00, 12:00, 18:00 UTC), luxury showroom, and
/// dual-ledger (GTC vs GTX) regulatory disclosures.
class GtexPublicLandingScreenV2 extends StatelessWidget {
  const GtexPublicLandingScreenV2({
    super.key,
    this.onSignup,
    this.onLogin,
    this.onCreatorSignup,
    this.onTraderSignup,
    this.onExploreMarket,
  });

  final VoidCallback? onSignup;
  final VoidCallback? onLogin;
  final VoidCallback? onCreatorSignup;
  final VoidCallback? onTraderSignup;
  final VoidCallback? onExploreMarket;

  @override
  Widget build(BuildContext context) {
    return Gtex22HomeScreen(
      onSignup: onSignup,
      onLogin: onLogin,
      onCreatorSignup: onCreatorSignup,
      onTraderSignup: onTraderSignup,
      onExploreMarket: onExploreMarket,
    );
  }
}
