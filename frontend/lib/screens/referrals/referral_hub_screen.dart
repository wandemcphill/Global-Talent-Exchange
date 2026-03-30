import 'package:flutter/material.dart';

import '../../controllers/creator_controller.dart';
import '../../controllers/referral_controller.dart';
import '../../widgets/gte_route_integrity_screen.dart';

class ReferralHubScreen extends StatelessWidget {
  const ReferralHubScreen({
    super.key,
    required this.referralController,
    required this.creatorController,
    this.isAuthenticated = false,
    this.hasApprovedCreatorAccess = false,
    this.isReferralRuntimeAvailable = false,
    this.onOpenLogin,
    this.onOpenCreatorAccessRequest,
  });

  final ReferralController referralController;
  final CreatorController creatorController;
  final bool isAuthenticated;
  final bool hasApprovedCreatorAccess;
  final bool isReferralRuntimeAvailable;
  final VoidCallback? onOpenLogin;
  final VoidCallback? onOpenCreatorAccessRequest;

  @override
  Widget build(BuildContext context) {
    return GteRouteIntegrityScreen.preview(
      title: 'Creator referrals preview',
      message:
          'Creator referrals remain preview-only until creator profile, leaderboard, finance, and referral state all run against the real backend without fixture fallback.',
      icon: Icons.groups_2_outlined,
      actionLabel: !isAuthenticated && onOpenLogin != null ? 'Sign in' : null,
      onAction: !isAuthenticated ? onOpenLogin : null,
    );
  }
}
