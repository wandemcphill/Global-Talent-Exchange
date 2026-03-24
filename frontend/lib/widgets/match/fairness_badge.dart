import 'package:flutter/material.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/services/fairness_indicator_service.dart';

class FairnessBadge extends StatelessWidget {
  const FairnessBadge({
    super.key,
    required this.viewState,
  });

  final MatchViewState viewState;

  @override
  Widget build(BuildContext context) {
    final FairnessBadgeState badgeState =
        FairnessIndicatorService.build(viewState);
    final Color accent = switch (badgeState.status) {
      MatchVerificationStatus.verified => const Color(0xFF17B26A),
      MatchVerificationStatus.tampered => const Color(0xFFF04438),
      MatchVerificationStatus.unverified => const Color(0xFFF79009),
    };
    return Tooltip(
      message: badgeState.message,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(999),
          color: accent.withValues(alpha: 0.14),
          border: Border.all(color: accent.withValues(alpha: 0.36)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Icon(
              switch (badgeState.status) {
                MatchVerificationStatus.verified => Icons.verified_outlined,
                MatchVerificationStatus.tampered => Icons.gpp_bad_outlined,
                MatchVerificationStatus.unverified => Icons.shield_outlined,
              },
              size: 14,
              color: accent,
            ),
            const SizedBox(width: 6),
            Text(
              badgeState.label,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: accent,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.2,
                  ),
            ),
          ],
        ),
      ),
    );
  }
}
