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
    this.adminBuybackPreview,
    this.isLoadingAdminBuybackPreview = false,
    this.isExecutingAdminBuyback = false,
    this.adminBuybackError,
    this.onLoadAdminBuybackPreview,
    this.onExecuteAdminBuyback,
  });

  final GteOrderRecord order;
  final String playerLabel;
  final bool isRefreshing;
  final bool isCancelling;
  final VoidCallback onRefresh;
  final VoidCallback onCancel;
  final bool showPlayerLabel;
  final GteAdminBuybackPreview? adminBuybackPreview;
  final bool isLoadingAdminBuybackPreview;
  final bool isExecutingAdminBuyback;
  final String? adminBuybackError;
  final VoidCallback? onLoadAdminBuybackPreview;
  final VoidCallback? onExecuteAdminBuyback;

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
          if (order.side == GteOrderSide.sell &&
              (order.status == GteOrderStatus.open ||
                  order.status == GteOrderStatus.partiallyFilled)) ...<Widget>[
            _AdminBuybackPanel(
              preview: adminBuybackPreview,
              isLoading: isLoadingAdminBuybackPreview,
              isExecuting: isExecutingAdminBuyback,
              errorMessage: adminBuybackError,
              onRefreshPreview: onLoadAdminBuybackPreview,
              onExecute: onExecuteAdminBuyback,
            ),
            const SizedBox(height: 16),
          ],
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

class _AdminBuybackPanel extends StatelessWidget {
  const _AdminBuybackPanel({
    required this.preview,
    required this.isLoading,
    required this.isExecuting,
    required this.errorMessage,
    required this.onRefreshPreview,
    required this.onExecute,
  });

  final GteAdminBuybackPreview? preview;
  final bool isLoading;
  final bool isExecuting;
  final String? errorMessage;
  final VoidCallback? onRefreshPreview;
  final VoidCallback? onExecute;

  @override
  Widget build(BuildContext context) {
    return Container(
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
          Text('Sell flow', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          Text(
            preview?.message ??
                'P2P stays first. Admin quick exit only appears as a lower fallback after the priority window.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 12),
          if (preview != null)
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: <Widget>[
                GteMetricChip(
                  label: 'Fair value',
                  value: gteFormatCredits(preview!.fairValue),
                ),
                GteMetricChip(
                  label: 'Expected P2P',
                  value: gteFormatCredits(preview!.estimatedP2pTotal),
                  positive: true,
                ),
                GteMetricChip(
                  label: 'Admin quick exit',
                  value: gteFormatCredits(preview!.adminTotal),
                ),
                GteMetricChip(
                  label: 'Payout band',
                  value: preview!.payoutBand,
                ),
                GteMetricChip(
                  label: 'Country',
                  value: preview!.country ?? 'Unavailable',
                  positive: preview!.country != null,
                ),
              ],
            )
          else if (isLoading)
            const LinearProgressIndicator()
          else
            Text(
              'Check the fallback quote to compare P2P value against the lower admin exit.',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          if (preview != null && preview!.reasons.isNotEmpty) ...<Widget>[
            const SizedBox(height: 12),
            Text(
              preview!.reasons.first,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: GteShellTheme.accentWarm,
                  ),
            ),
          ],
          if (errorMessage != null) ...<Widget>[
            const SizedBox(height: 12),
            Text(
              errorMessage!,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Theme.of(context).colorScheme.error,
                  ),
            ),
          ],
          const SizedBox(height: 12),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              FilledButton.tonalIcon(
                onPressed: isLoading ? null : onRefreshPreview,
                icon: isLoading
                    ? const SizedBox(
                        width: 14,
                        height: 14,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.compare_arrows),
                label: const Text('Check fallback'),
              ),
              if (preview != null)
                FilledButton(
                  onPressed: preview!.eligible && !isExecuting
                      ? onExecute
                      : null,
                  child: Text(
                    isExecuting ? 'Selling...' : 'Sell to admin',
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }
}
