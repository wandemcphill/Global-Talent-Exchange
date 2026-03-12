import 'package:flutter/material.dart';
import 'package:gte_frontend/models/club_catalog_models.dart';
import 'package:gte_frontend/widgets/gte_formatters.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class PurchaseSummaryCard extends StatelessWidget {
  const PurchaseSummaryCard({
    super.key,
    required this.record,
  });

  final ClubPurchaseRecord record;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            record.itemTitle,
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          Text(
            '${record.category} • ${gteFormatCredits(record.priceCredits)}',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 10),
          Text(
            record.statusLabel,
            style: Theme.of(context).textTheme.bodyLarge,
          ),
          const SizedBox(height: 8),
          Text(
            '${gteFormatDateTime(record.purchasedAt)} • ${record.confirmationLabel}',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 10),
          Text(
            record.transparencyNote,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
        ],
      ),
    );
  }
}
