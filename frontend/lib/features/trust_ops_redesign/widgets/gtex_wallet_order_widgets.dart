import 'package:flutter/material.dart';

import '../../../ui_gtex/ui_gtex.dart';
import '../models/gtex_trust_ops_models.dart';

class GtexWalletOverviewPanel extends StatelessWidget {
  const GtexWalletOverviewPanel({
    super.key,
    required this.state,
    required this.onTopUp,
    required this.onWithdraw,
  });

  final GtexTrustOpsState state;
  final VoidCallback onTopUp;
  final VoidCallback onWithdraw;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(GtexSpacing.md),
      children: <Widget>[
        Wrap(
          spacing: GtexSpacing.md,
          runSpacing: GtexSpacing.md,
          children: <Widget>[
            SizedBox(
              width: 260,
              child: GtexMetricTile(
                label: 'Wallet balance',
                value: state.wallet.balanceLabel,
                delta: state.wallet.lastUpdatedLabel,
                icon: Icons.account_balance_wallet_outlined,
              ),
            ),
            SizedBox(
              width: 260,
              child: GtexMetricTile(
                label: 'Available',
                value: state.wallet.availableLabel,
                icon: Icons.check_circle_outline,
                accent: GtexColors.mint,
              ),
            ),
            SizedBox(
              width: 260,
              child: GtexMetricTile(
                label: 'Pending withdrawal',
                value: state.wallet.pendingWithdrawalLabel,
                icon: Icons.schedule_outlined,
                accent: GtexColors.gold,
              ),
            ),
          ],
        ),
        const SizedBox(height: GtexSpacing.lg),
        Row(
          children: <Widget>[
            GtexActionButton(
              label: 'Top up',
              icon: Icons.add_card_outlined,
              onPressed: onTopUp,
            ),
            const SizedBox(width: GtexSpacing.sm),
            GtexActionButton(
              label: 'Withdraw',
              icon: Icons.payments_outlined,
              onPressed: onWithdraw,
              secondary: true,
              accent: GtexColors.gold,
            ),
          ],
        ),
        const SizedBox(height: GtexSpacing.lg),
        GtexPanel(
          title: 'Recent transactions',
          subtitle:
              'Money movement, player orders, rental payments and withdrawals.',
          child: Column(
            children: <Widget>[
              for (final GtexTransactionRecord tx in state.transactions)
                _TransactionRow(tx: tx),
            ],
          ),
        ),
      ],
    );
  }
}

class GtexOrdersPanel extends StatelessWidget {
  const GtexOrdersPanel({
    super.key,
    required this.orders,
    required this.selectedOrderId,
    required this.onSelectOrder,
  });

  final List<GtexOrderRecord> orders;
  final String? selectedOrderId;
  final ValueChanged<String> onSelectOrder;

  @override
  Widget build(BuildContext context) {
    if (orders.isEmpty) {
      return const GtexEmptyState(
        title: 'No orders yet',
        message:
            'Player purchases, national-team rentals, create-a-son requests and wallet orders will appear here.',
        icon: Icons.receipt_long_outlined,
      );
    }
    return ListView.separated(
      padding: const EdgeInsets.all(GtexSpacing.md),
      itemCount: orders.length,
      separatorBuilder: (_, __) => const SizedBox(height: GtexSpacing.sm),
      itemBuilder: (BuildContext context, int index) {
        final GtexOrderRecord order = orders[index];
        final Color color = GtexTrustFormatters.statusColor(order.status);
        return GtexPanel(
          isSelected: selectedOrderId == order.id,
          onTap: () => onSelectOrder(order.id),
          accent: color,
          child: Row(
            children: <Widget>[
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      order.title,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        color: GtexColors.text,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      order.subtitle,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: GtexColors.textSecondary,
                      ),
                    ),
                    const SizedBox(height: GtexSpacing.sm),
                    Wrap(
                      spacing: GtexSpacing.sm,
                      children: <Widget>[
                        GtexStatusChip(
                          label: GtexTrustFormatters.statusLabel(order.status),
                          color: color,
                          compact: true,
                        ),
                        GtexStatusChip(
                          label: '${order.itemCount} items',
                          color: GtexColors.cyan,
                          compact: true,
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: <Widget>[
                  Text(
                    order.totalLabel,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      color: GtexColors.gold,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    order.createdLabel,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: GtexColors.textMuted,
                    ),
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }
}

class GtexTrustRightSummaryPanel extends StatelessWidget {
  const GtexTrustRightSummaryPanel({
    super.key,
    required this.state,
    required this.onTopUp,
    required this.onWithdraw,
    this.selectedOrder,
    this.selectedDispute,
    this.selectedKycCase,
    this.adminMode = false,
  });

  final GtexTrustOpsState state;
  final VoidCallback onTopUp;
  final VoidCallback onWithdraw;
  final GtexOrderRecord? selectedOrder;
  final GtexDisputeRecord? selectedDispute;
  final GtexKycCaseRecord? selectedKycCase;
  final bool adminMode;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(GtexSpacing.md),
      children: <Widget>[
        GtexPanel(
          title: adminMode ? 'Operator actions' : 'Wallet actions',
          subtitle:
              adminMode
                  ? 'Review context is live; mutation controls unlock only after audited review endpoints are mounted.'
                  : state.wallet.kycStatus,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              if (!adminMode) ...<Widget>[
                GtexActionButton(
                  label: 'Top up wallet',
                  icon: Icons.add_card_outlined,
                  onPressed: onTopUp,
                ),
                const SizedBox(height: GtexSpacing.sm),
                GtexActionButton(
                  label: 'Withdraw',
                  icon: Icons.payments_outlined,
                  onPressed: onWithdraw,
                  secondary: true,
                  accent: GtexColors.gold,
                ),
              ] else ...<Widget>[
                Text(
                  _selectedReviewSummary(
                    order: selectedOrder,
                    dispute: selectedDispute,
                    kycCase: selectedKycCase,
                  ),
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: GtexColors.textSecondary,
                    height: 1.45,
                  ),
                ),
                const SizedBox(height: GtexSpacing.md),
                const Wrap(
                  spacing: GtexSpacing.xs,
                  runSpacing: GtexSpacing.xs,
                  children: <Widget>[
                    GtexStatusChip(label: 'READ ONLY', color: GtexColors.cyan),
                    GtexStatusChip(
                      label: 'AUDIT REQUIRED',
                      color: GtexColors.gold,
                    ),
                    GtexStatusChip(
                      label: 'NO MUTATION ENDPOINT',
                      color: GtexColors.red,
                    ),
                  ],
                ),
              ],
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        if (state.operationsReadiness != null) ...<Widget>[
          _OperationsReadinessCard(snapshot: state.operationsReadiness!),
          const SizedBox(height: GtexSpacing.md),
        ],
        if (selectedOrder != null) _SelectedOrderCard(order: selectedOrder!),
        if (selectedKycCase != null) _SelectedKycCard(item: selectedKycCase!),
        if (selectedDispute != null)
          _SelectedDisputeCard(item: selectedDispute!),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Risk snapshot',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              _MiniLine(
                label: 'Pending KYC',
                value: '${state.pendingKycCount}',
              ),
              _MiniLine(
                label: 'Open disputes',
                value: '${state.openDisputeCount}',
              ),
              _MiniLine(
                label: 'Pending orders',
                value: '${state.pendingOrderCount}',
              ),
            ],
          ),
        ),
      ],
    );
  }
}

String _selectedReviewSummary({
  required GtexOrderRecord? order,
  required GtexDisputeRecord? dispute,
  required GtexKycCaseRecord? kycCase,
}) {
  if (order != null) {
    return 'Selected order ${order.id} is available for inspection. Approve, info-request, and escalation mutations remain locked until the live review adapter is mounted.';
  }
  if (dispute != null) {
    return 'Selected dispute ${dispute.id} is available for inspection. Resolution mutations remain locked until the live review adapter is mounted.';
  }
  if (kycCase != null) {
    return 'Selected KYC case ${kycCase.id} is available for inspection. Approval mutations remain locked until the live review adapter is mounted.';
  }
  return 'Select an order, KYC case, or dispute to review its live context. This rail is intentionally read-only until audited admin mutation endpoints are mounted.';
}

class _OperationsReadinessCard extends StatelessWidget {
  const _OperationsReadinessCard({required this.snapshot});

  final GtexOperationsReadinessSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final List<GtexOperationsReadinessQueue> queues = snapshot.queues
        .take(5)
        .toList(growable: false);
    return GtexPanel(
      title: 'Operations readiness',
      subtitle: '${snapshot.totals['alerts'] ?? 0} alert signals',
      accent: _statusColor(snapshot.status),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          for (final GtexOperationsReadinessQueue queue in queues) ...<Widget>[
            _MiniLine(label: queue.title, value: _statusLabel(queue.status)),
          ],
        ],
      ),
    );
  }

  Color _statusColor(String status) {
    switch (status) {
      case 'blocked':
        return GtexColors.red;
      case 'attention':
        return GtexColors.orange;
      default:
        return GtexColors.pitch;
    }
  }

  String _statusLabel(String status) {
    switch (status) {
      case 'blocked':
        return 'Blocked';
      case 'attention':
        return 'Attention';
      case 'gated':
        return 'Gated';
      default:
        return 'Healthy';
    }
  }
}

class _TransactionRow extends StatelessWidget {
  const _TransactionRow({required this.tx});

  final GtexTransactionRecord tx;

  @override
  Widget build(BuildContext context) {
    final Color color = GtexTrustFormatters.statusColor(tx.status);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: GtexSpacing.sm),
      child: Row(
        children: <Widget>[
          Container(
            width: 38,
            height: 38,
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.12),
              shape: BoxShape.circle,
            ),
            child: Icon(Icons.sync_alt_outlined, color: color, size: 19),
          ),
          const SizedBox(width: GtexSpacing.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  tx.title,
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    color: GtexColors.text,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                Text(
                  '${tx.subtitle} • ${tx.timestampLabel}',
                  style: Theme.of(
                    context,
                  ).textTheme.bodySmall?.copyWith(color: GtexColors.textMuted),
                ),
              ],
            ),
          ),
          Text(
            tx.amountLabel,
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
              color: color,
              fontWeight: FontWeight.w900,
            ),
          ),
        ],
      ),
    );
  }
}

class _SelectedOrderCard extends StatelessWidget {
  const _SelectedOrderCard({required this.order});
  final GtexOrderRecord order;

  @override
  Widget build(BuildContext context) => GtexPanel(
    title: order.title,
    subtitle: order.subtitle,
    accent: GtexTrustFormatters.statusColor(order.status),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        _MiniLine(label: 'Order ID', value: order.id),
        _MiniLine(label: 'Total', value: order.totalLabel),
        _MiniLine(
          label: 'Status',
          value: GtexTrustFormatters.statusLabel(order.status),
        ),
      ],
    ),
  );
}

class _SelectedKycCard extends StatelessWidget {
  const _SelectedKycCard({required this.item});
  final GtexKycCaseRecord item;

  @override
  Widget build(BuildContext context) => GtexPanel(
    title: item.userName,
    subtitle: item.notes,
    accent: GtexTrustFormatters.statusColor(item.status),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        _MiniLine(label: 'Country', value: item.country),
        _MiniLine(label: 'Level', value: item.level),
        _MiniLine(label: 'Risk', value: item.riskLabel),
      ],
    ),
  );
}

class _SelectedDisputeCard extends StatelessWidget {
  const _SelectedDisputeCard({required this.item});
  final GtexDisputeRecord item;

  @override
  Widget build(BuildContext context) => GtexPanel(
    title: item.title,
    subtitle: item.summary,
    accent: GtexTrustFormatters.statusColor(item.status),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        _MiniLine(label: 'Counterparty', value: item.counterparty),
        _MiniLine(label: 'Amount', value: item.amountLabel),
        _MiniLine(label: 'Opened', value: item.openedLabel),
      ],
    ),
  );
}

class _MiniLine extends StatelessWidget {
  const _MiniLine({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 5),
    child: Row(
      children: <Widget>[
        Expanded(
          child: Text(
            label,
            style: Theme.of(
              context,
            ).textTheme.bodySmall?.copyWith(color: GtexColors.textMuted),
          ),
        ),
        Text(
          value,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: GtexColors.text,
            fontWeight: FontWeight.w800,
          ),
        ),
      ],
    ),
  );
}
