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
    this.emptyTitle = 'No players shortlisted yet',
    this.emptyMessage =
        'Browse leagues, divisions, and clubs, then add players to your basket.',
  });

  final List<GtexBasketLineItem> items;
  final String totalLabel;
  final String title;
  final String checkoutLabel;
  final VoidCallback? onCheckout;
  final String emptyTitle;
  final String emptyMessage;

  @override
  Widget build(BuildContext context) {
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
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: GtexSpacing.sm),
              GtexActionButton(
                label: checkoutLabel,
                onPressed: onCheckout,
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
