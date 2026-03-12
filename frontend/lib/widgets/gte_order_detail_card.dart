import 'package:flutter/material.dart';

import '../data/gte_models.dart';
import 'gte_formatters.dart';
import 'gte_metric_chip.dart';
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
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Text('Order status',
                    style: Theme.of(context).textTheme.headlineSmall),
              ),
              Chip(label: Text(gteFormatOrderStatus(order.status.name))),
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
              GteMetricChip(
                  label: 'Side', value: order.side.name.toUpperCase()),
              GteMetricChip(
                label: 'Quantity',
                value: order.quantity.toStringAsFixed(2),
              ),
              GteMetricChip(
                label: 'Filled',
                value: order.filledQuantity.toStringAsFixed(2),
              ),
              GteMetricChip(
                label: 'Remaining',
                value: order.remainingQuantity.toStringAsFixed(2),
              ),
              GteMetricChip(
                label: 'Limit',
                value: gteFormatNullableCredits(order.maxPrice),
              ),
              GteMetricChip(
                label: 'Reserved',
                value: gteFormatCredits(order.reservedAmount),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Text(
            'Order ID: ${order.id}',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 4),
          Text(
            'Created: $createdLabel',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 4),
          Text(
            'Updated: $updatedLabel',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 4),
          Text(
            'Execution count: ${order.executionSummary.executionCount}',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          if (order.executionSummary.executionCount == 0) ...<Widget>[
            const SizedBox(height: 4),
            Text(
              'No executions yet. Refresh to pull the latest status from the backend.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              FilledButton.tonalIcon(
                onPressed: isRefreshing ? null : onRefresh,
                icon: isRefreshing
                    ? const SizedBox(
                        width: 14,
                        height: 14,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
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
}
