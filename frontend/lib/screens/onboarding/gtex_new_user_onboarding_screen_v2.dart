import 'package:flutter/material.dart';

import '../../features/onboarding_redesign/gtex_onboarding_flow_screen_v2.dart';

class GtexNewUserOnboardingScreenV2 extends StatelessWidget {
  const GtexNewUserOnboardingScreenV2({
    super.key,
    this.onOpenMarket,
    this.onCreateClub,
    this.onJoinClub,
    this.onStartKyc,
    this.onOpenCompetitions,
  });

  final VoidCallback? onOpenMarket;
  final VoidCallback? onCreateClub;
  final VoidCallback? onJoinClub;
  final VoidCallback? onStartKyc;
  final VoidCallback? onOpenCompetitions;

  @override
  Widget build(BuildContext context) {
    return GtexOnboardingFlowScreenV2(
      onOpenMarket: onOpenMarket,
      onCreateClub: onCreateClub,
      onJoinClub: onJoinClub,
      onStartKyc: onStartKyc,
      onOpenCompetitions: onOpenCompetitions,
    );
  }
}
