import 'package:flutter/material.dart';

import '../data/gte_models.dart';
import 'gte_formatters.dart';
import 'gte_metric_chip.dart';
import 'gte_surface_panel.dart';

class GteWalletSummaryCard extends StatelessWidget {
  const GteWalletSummaryCard({
    super.key,
    required this.summary,
  });

  final GteWalletSummary summary;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      emphasized: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Wallet summary',
              style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 8),
          Text(
            'Live balances from `/api/wallets/summary`.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 18),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              GteMetricChip(
                label: 'Available',
                value: gteFormatCredits(summary.availableBalance),
              ),
              GteMetricChip(
                label: 'Reserved',
                value: gteFormatCredits(summary.reservedBalance),
                positive: summary.reservedBalance <= summary.totalBalance,
              ),
              GteMetricChip(
                label: 'Total',
                value: gteFormatCredits(summary.totalBalance),
              ),
              GteMetricChip(
                label: 'Currency',
                value: summary.currency.name.toUpperCase(),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
