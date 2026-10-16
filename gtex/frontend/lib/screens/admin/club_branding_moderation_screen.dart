import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_controller.dart';
import 'package:gte_frontend/widgets/admin/branding_review_card.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';

class ClubBrandingModerationScreen extends StatelessWidget {
  const ClubBrandingModerationScreen({
    super.key,
    required this.controller,
  });

  final ClubController controller;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (BuildContext context, _) {
        final queue = controller.moderationQueue;
        return Container(
          decoration: gteBackdropDecoration(),
          child: Scaffold(
            backgroundColor: Colors.transparent,
            appBar: AppBar(
              title: const Text('Branding moderation'),
            ),
            body: queue.isEmpty
                ? const Padding(
                    padding: EdgeInsets.all(20),
                    child: GteStatePanel(
                      title: 'No branding reviews waiting',
                      message:
                          'Open club admin first or refresh analytics to load the moderation queue.',
                      icon: Icons.fact_check_outlined,
                    ),
                  )
                : ListView.separated(
                    padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
                    itemBuilder: (BuildContext context, int index) {
                      final review = queue[index];
                      return BrandingReviewCard(
                        review: review,
                        onApprove: () => controller.moderateBranding(
                          reviewId: review.id,
                          approved: true,
                        ),
                        onRequestChanges: () => controller.moderateBranding(
                          reviewId: review.id,
                          approved: false,
                        ),
                      );
                    },
                    separatorBuilder: (_, __) => const SizedBox(height: 14),
                    itemCount: queue.length,
                  ),
          ),
        );
      },
    );
  }
}
