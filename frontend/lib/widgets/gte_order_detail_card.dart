import 'package:flutter/material.dart';

import '../data/gte_models.dart';
import 'gte_formatters.dart';
import 'gte_metric_chip.dart';
import 'gte_shell_theme.dart';
import 'gte_surface_panel.dart';

class GteOrderDetailCard extends StatelessWidget {
  const GteOrderDetailCard({
    super.key,
    required this.order,
    required this.playerLabel,
    required this.isRefreshing,
    required this.isCancelling,
    required this.onRefresh,
    required this.onCancel,
    this.showPlayerLabel = false,
  });

  final GteOrderRecord order;
  final String playerLabel;
  final bool isRefreshing;
  final bool isCancelling;
  final VoidCallback onRefresh;
  final VoidCallback onCancel;
  final bool showPlayerLabel;

  @override
  Widget build(BuildContext context) {
    final String updatedLabel = gteFormatDateTime(order.updatedAt);
    final String createdLabel = gteFormatDateTime(order.createdAt);
    final Color statusTone = _statusColor(order.status);
    return GteSurfacePanel(
      accentColor: statusTone,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(child: Text('Order status', style: Theme.of(context).textTheme.headlineSmall)),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(999),
                  color: statusTone.withValues(alpha: 0.12),
                ),
                child: Text(
                  gteFormatOrderStatus(order.status.name),
                  style: Theme.of(context).textTheme.labelLarge?.copyWith(color: statusTone),
                ),
              ),
            ],
          ),
          if (showPlayerLabel) ...<Widget>[
            const SizedBox(height: 6),
            Text(playerLabel, style: Theme.of(context).textTheme.bodyMedium),
          ],
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              GteMetricChip(label: 'Side', value: order.side.name.toUpperCase(), positive: order.side == GteOrderSide.buy),
              GteMetricChip(label: 'Quantity', value: order.quantity.toStringAsFixed(2)),
              GteMetricChip(label: 'Filled', value: order.filledQuantity.toStringAsFixed(2), positive: order.filledQuantity > 0),
              GteMetricChip(label: 'Remaining', value: order.remainingQuantity.toStringAsFixed(2)),
              GteMetricChip(label: 'Limit', value: gteFormatNullableCredits(order.maxPrice)),
              GteMetricChip(label: 'Reserved', value: gteFormatCredits(order.reservedAmount)),
            ],
          ),
          const SizedBox(height: 16),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(20),
              color: Colors.white.withValues(alpha: 0.03),
              border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text('Ledger notes', style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 8),
                Text('Order ID: ${order.id}', style: Theme.of(context).textTheme.bodySmall),
                const SizedBox(height: 4),
                Text('Created: $createdLabel', style: Theme.of(context).textTheme.bodySmall),
                const SizedBox(height: 4),
                Text('Updated: $updatedLabel', style: Theme.of(context).textTheme.bodySmall),
                const SizedBox(height: 4),
                Text('Execution count: ${order.executionSummary.executionCount}', style: Theme.of(context).textTheme.bodySmall),
                if (order.executionSummary.executionCount == 0) ...<Widget>[
                  const SizedBox(height: 8),
                  Text('No executions yet. Refresh to pull the latest backend state.', style: Theme.of(context).textTheme.bodySmall),
                ],
              ],
            ),
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              FilledButton.tonalIcon(
                onPressed: isRefreshing ? null : onRefresh,
                icon: isRefreshing
                    ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2))
                    : const Icon(Icons.refresh),
                label: const Text('Refresh'),
              ),
              if (order.canCancel)
                FilledButton(
                  onPressed: isCancelling ? null : onCancel,
                  child: Text(isCancelling ? 'Cancelling...' : 'Cancel order'),
                ),
            ],
          ),
        ],
      ),
    );
  }

  Color _statusColor(GteOrderStatus status) {
    switch (status) {
      case GteOrderStatus.filled:
        return GteShellTheme.positive;
      case GteOrderStatus.cancelled:
      case GteOrderStatus.rejected:
        return GteShellTheme.negative;
      case GteOrderStatus.partiallyFilled:
        return GteShellTheme.accentWarm;
      case GteOrderStatus.open:
      case GteOrderStatus.unknown:
        return GteShellTheme.accent;
    }
  }
}
