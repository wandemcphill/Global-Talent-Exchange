import 'package:flutter/material.dart';

import '../components/gtex_action_button.dart';
import '../components/gtex_empty_state.dart';
import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';

class GtexBasketLineItem {
  const GtexBasketLineItem({
    required this.id,
    required this.title,
    required this.subtitle,
    required this.priceLabel,
    this.onRemove,
  });

  final String id;
  final String title;
  final String subtitle;
  final String priceLabel;
  final VoidCallback? onRemove;
}

class GtexShortlistBasket extends StatelessWidget {
  const GtexShortlistBasket({
    super.key,
    required this.items,
    required this.totalLabel,
    this.title = 'Shortlist Basket',
    this.checkoutLabel = 'Continue to payment',
    this.onCheckout,
    this.balanceLabel,
    this.remainingLabel,
    this.insufficientLabel,
    this.onTopUpWallet,
    this.emptyTitle = 'No players shortlisted yet',
    this.emptyMessage =
        'Browse leagues, divisions, and clubs, then add players to your basket.',
  });

  final List<GtexBasketLineItem> items;
  final String totalLabel;
  final String title;
  final String checkoutLabel;
  final VoidCallback? onCheckout;
  final String? balanceLabel;
  final String? remainingLabel;
  final String? insufficientLabel;
  final VoidCallback? onTopUpWallet;
  final String emptyTitle;
  final String emptyMessage;

  @override
  Widget build(BuildContext context) {
    final bool blockedByBalance =
        insufficientLabel != null && insufficientLabel!.trim().isNotEmpty;
    if (items.isEmpty) {
      return Padding(
        padding: const EdgeInsets.all(GtexSpacing.md),
        child: GtexEmptyState(
          title: emptyTitle,
          message: emptyMessage,
          icon: Icons.shopping_basket_outlined,
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        Padding(
          padding: const EdgeInsets.all(GtexSpacing.md),
          child: Row(
            children: <Widget>[
              Expanded(
                child: Text(
                  title,
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    color: GtexColors.text,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
              Text(
                '${items.length}',
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: GtexColors.pitch,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ],
          ),
        ),
        Expanded(
          child: ListView.separated(
            padding: const EdgeInsets.symmetric(horizontal: GtexSpacing.md),
            itemCount: items.length,
            separatorBuilder: (_, __) => const SizedBox(height: GtexSpacing.xs),
            itemBuilder: (BuildContext context, int index) {
              final GtexBasketLineItem item = items[index];
              return Container(
                padding: const EdgeInsets.all(GtexSpacing.sm),
                decoration: BoxDecoration(
                  color: GtexColors.panelStrong.withValues(alpha: 0.74),
                  borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
                  border: Border.all(
                    color: GtexColors.line.withValues(alpha: 0.68),
                  ),
                ),
                child: Row(
                  children: <Widget>[
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(
                            'PLAYER PURCHASE',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: Theme.of(
                              context,
                            ).textTheme.labelSmall?.copyWith(
                              color: GtexColors.gold,
                              fontWeight: FontWeight.w900,
                              letterSpacing: 0.7,
                            ),
                          ),
                          const SizedBox(height: 3),
                          Text(
                            item.title,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              color: GtexColors.text,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                          Text(
                            item.subtitle,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              color: GtexColors.textMuted,
                              fontWeight: FontWeight.w600,
                              fontSize: 12,
                            ),
                          ),
                        ],
                      ),
                    ),
                    Text(
                      item.priceLabel,
                      style: const TextStyle(
                        color: GtexColors.gold,
                        fontFamily: 'JetBrains Mono',
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    if (item.onRemove != null)
                      IconButton(
                        tooltip: 'Remove',
                        onPressed: item.onRemove,
                        icon: const Icon(Icons.close, size: 18),
                      ),
                  ],
                ),
              );
            },
          ),
        ),
        Container(
          padding: const EdgeInsets.all(GtexSpacing.md),
          decoration: BoxDecoration(
            color: GtexColors.stadiumBlack.withValues(alpha: 0.62),
            border: Border(
              top: BorderSide(color: GtexColors.line.withValues(alpha: 0.7)),
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              const _BasketRailHeader(),
              const SizedBox(height: GtexSpacing.sm),
              Row(
                children: <Widget>[
                  const Expanded(
                    child: Text(
                      'TOTAL COST',
                      style: TextStyle(
                        color: GtexColors.textMuted,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 0.8,
                      ),
                    ),
                  ),
                  Text(
                    totalLabel,
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      color: GtexColors.gold,
                      fontFamily: 'JetBrains Mono',
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ],
              ),
              if (balanceLabel != null || remainingLabel != null) ...<Widget>[
                const SizedBox(height: GtexSpacing.sm),
                Wrap(
                  spacing: GtexSpacing.xs,
                  runSpacing: GtexSpacing.xs,
                  children: <Widget>[
                    if (balanceLabel != null)
                      _BasketMoneyChip(
                        label: 'Wallet',
                        value: balanceLabel!,
                        color: GtexColors.pitch,
                      ),
                    if (remainingLabel != null)
                      _BasketMoneyChip(
                        label: 'After purchase',
                        value: remainingLabel!,
                        color:
                            blockedByBalance
                                ? GtexColors.danger
                                : GtexColors.cyan,
                      ),
                  ],
                ),
              ],
              if (blockedByBalance) ...<Widget>[
                const SizedBox(height: GtexSpacing.sm),
                _BasketWarning(
                  message: insufficientLabel!,
                  onTopUpWallet: onTopUpWallet,
                ),
              ],
              const SizedBox(height: GtexSpacing.sm),
              GtexActionButton(
                label: checkoutLabel,
                onPressed: blockedByBalance ? null : onCheckout,
                icon: Icons.lock_open_outlined,
                accent: GtexColors.gold,
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _BasketRailHeader extends StatelessWidget {
  const _BasketRailHeader();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: GtexSpacing.sm,
        vertical: GtexSpacing.xs,
      ),
      decoration: BoxDecoration(
        color: GtexColors.gold.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(GtexSpacing.radiusSm),
        border: Border.all(color: GtexColors.gold.withValues(alpha: 0.28)),
      ),
      child: const Row(
        children: <Widget>[
          Icon(Icons.account_balance_wallet_outlined, size: 16),
          SizedBox(width: GtexSpacing.xs),
          Expanded(
            child: Text(
              'Wallet GTC only - KoraPay/manual top-up if balance is short',
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                color: GtexColors.gold,
                fontSize: 12,
                fontWeight: FontWeight.w900,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _BasketMoneyChip extends StatelessWidget {
  const _BasketMoneyChip({
    required this.label,
    required this.value,
    required this.color,
  });

  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: GtexSpacing.sm,
        vertical: GtexSpacing.xs,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(GtexSpacing.radiusSm),
        border: Border.all(color: color.withValues(alpha: 0.28)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Text(
            '$label: ',
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: GtexColors.textMuted,
              fontWeight: FontWeight.w800,
            ),
          ),
          Text(
            value,
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: color,
              fontFamily: 'JetBrains Mono',
              fontWeight: FontWeight.w900,
            ),
          ),
        ],
      ),
    );
  }
}

class _BasketWarning extends StatelessWidget {
  const _BasketWarning({required this.message, this.onTopUpWallet});

  final String message;
  final VoidCallback? onTopUpWallet;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(GtexSpacing.sm),
      decoration: BoxDecoration(
        color: GtexColors.danger.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
        border: Border.all(color: GtexColors.danger.withValues(alpha: 0.26)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const Icon(
            Icons.warning_amber_rounded,
            color: GtexColors.danger,
            size: 18,
          ),
          const SizedBox(width: GtexSpacing.xs),
          Expanded(
            child: Text(
              message,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: GtexColors.text,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          if (onTopUpWallet != null) ...<Widget>[
            const SizedBox(width: GtexSpacing.xs),
            TextButton(onPressed: onTopUpWallet, child: const Text('Top up')),
          ],
        ],
      ),
    );
  }
}
