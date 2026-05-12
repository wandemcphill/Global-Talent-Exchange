import 'package:flutter/material.dart';

import '../../../ui_gtex/ui_gtex.dart';
import '../models/gtex_trust_ops_models.dart';

class GtexTrustContextPanel extends StatelessWidget {
  const GtexTrustContextPanel({
    super.key,
    required this.selectedModule,
    required this.onModuleSelected,
    required this.state,
    this.adminMode = false,
  });

  final GtexTrustModule selectedModule;
  final ValueChanged<GtexTrustModule> onModuleSelected;
  final GtexTrustOpsState state;
  final bool adminMode;

  @override
  Widget build(BuildContext context) {
    final List<_ModuleItem> items =
        adminMode
            ? <_ModuleItem>[
              _ModuleItem(
                GtexTrustModule.kyc,
                'KYC Queue',
                '${state.pendingKycCount} pending',
                Icons.verified_user_outlined,
              ),
              _ModuleItem(
                GtexTrustModule.disputes,
                'Disputes',
                '${state.openDisputeCount} open',
                Icons.gavel_outlined,
              ),
              _ModuleItem(
                GtexTrustModule.orders,
                'Orders',
                '${state.pendingOrderCount} pending',
                Icons.receipt_long_outlined,
              ),
              _ModuleItem(
                GtexTrustModule.wallet,
                'Coin / Wallet',
                state.wallet.balanceLabel,
                Icons.account_balance_wallet_outlined,
              ),
            ]
            : <_ModuleItem>[
              _ModuleItem(
                GtexTrustModule.wallet,
                'Wallet',
                state.wallet.balanceLabel,
                Icons.account_balance_wallet_outlined,
              ),
              _ModuleItem(
                GtexTrustModule.orders,
                'Orders',
                '${state.orders.length} records',
                Icons.receipt_long_outlined,
              ),
              _ModuleItem(
                GtexTrustModule.kyc,
                'KYC',
                state.wallet.kycStatus,
                Icons.verified_user_outlined,
              ),
              _ModuleItem(
                GtexTrustModule.disputes,
                'Disputes',
                '${state.disputes.length} cases',
                Icons.support_agent_outlined,
              ),
            ];

    return ListView(
      children: <Widget>[
        Text(
          adminMode ? 'Trust operations' : 'Wallet & support',
          style: Theme.of(context).textTheme.titleLarge?.copyWith(
            color: GtexColors.text,
            fontWeight: FontWeight.w900,
          ),
        ),
        const SizedBox(height: GtexSpacing.xs),
        Text(
          adminMode
              ? 'Review KYC, orders, withdrawals, disputes and wallet risk.'
              : 'Manage money movement, orders, verification and support from one calm workspace.',
          style: Theme.of(
            context,
          ).textTheme.bodySmall?.copyWith(color: GtexColors.textSecondary),
        ),
        const SizedBox(height: GtexSpacing.md),
        for (final _ModuleItem item in items) ...<Widget>[
          GtexPanel(
            isSelected: selectedModule == item.module,
            onTap: () => onModuleSelected(item.module),
            padding: const EdgeInsets.all(GtexSpacing.sm),
            child: Row(
              children: <Widget>[
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: GtexColors.pitch.withValues(alpha: 0.10),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(item.icon, color: GtexColors.pitch, size: 20),
                ),
                const SizedBox(width: GtexSpacing.sm),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        item.title,
                        style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          color: GtexColors.text,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        item.subtitle,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: GtexColors.textMuted,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: GtexSpacing.sm),
        ],
      ],
    );
  }
}

class _ModuleItem {
  const _ModuleItem(this.module, this.title, this.subtitle, this.icon);

  final GtexTrustModule module;
  final String title;
  final String subtitle;
  final IconData icon;
}
