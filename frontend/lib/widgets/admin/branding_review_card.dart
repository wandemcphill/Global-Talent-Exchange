import 'package:flutter/material.dart';
import 'package:gte_frontend/models/club_branding_models.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class BrandingReviewCard extends StatelessWidget {
  const BrandingReviewCard({
    super.key,
    required this.review,
    this.onApprove,
    this.onRequestChanges,
  });

  final BrandingReviewCase review;
  final VoidCallback? onApprove;
  final VoidCallback? onRequestChanges;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            review.clubName,
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          Text(
            '${review.themeName} • ${review.backdropName}',
            style: Theme.of(context).textTheme.bodyLarge,
          ),
          const SizedBox(height: 6),
          Text(
            review.motto,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 10),
          Text(
            '${review.statusLabel} • ${review.submittedAtLabel}',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 10),
          Text(
            review.reviewNote,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          if (onApprove != null || onRequestChanges != null) ...<Widget>[
            const SizedBox(height: 16),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: <Widget>[
                if (onApprove != null)
                  FilledButton.tonal(
                    onPressed: onApprove,
                    child: const Text('Approve'),
                  ),
                if (onRequestChanges != null)
                  OutlinedButton(
                    onPressed: onRequestChanges,
                    child: const Text('Request changes'),
                  ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}
