import 'package:flutter/material.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

class ClubLegacyMarketData {
  const ClubLegacyMarketData({
    required this.feeRate,
    required this.jetCap,
    required this.coachCap,
    required this.listings,
    required this.gifts,
    required this.provenance,
  });

  final String feeRate;
  final int jetCap;
  final int coachCap;
  final List<Map<String, dynamic>> listings;
  final List<Map<String, dynamic>> gifts;
  final List<Map<String, dynamic>> provenance;
}

class ClubLegacyMarketPanel extends StatelessWidget {
  const ClubLegacyMarketPanel({super.key, required this.data, required this.onAction});

  final ClubLegacyMarketData data;
  final void Function(String action) onAction;

  @override
  Widget build(BuildContext context) {
    return ListView(
      key: const Key('club-legacy-market-panel'),
      padding: const EdgeInsets.all(GtexSpacing.md),
      children: <Widget>[
        GtexPanel(
          title: 'Supply',
          subtitle: 'Fixed editions and club caps',
          accent: GtexColors.gold,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('Transfer fee ${data.feeRate}', key: const Key('club-market-fee')),
              Text('Jet cap ${data.jetCap}', key: const Key('club-market-jet-cap')),
              Text('Coach cap ${data.coachCap}', key: const Key('club-market-coach-cap')),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Listings',
          subtitle: 'A failed resale stays open',
          accent: GtexColors.cyan,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              if (data.listings.isEmpty) const Text('Nothing listed', style: TextStyle(color: GtexColors.textSecondary)),
              for (final Map<String, dynamic> row in data.listings)
                Text('${row['name']} · ${row['status']} · ${row['price']}', key: Key('club-market-listing-${row['id']}')),
              const SizedBox(height: GtexSpacing.sm),
              Wrap(
                spacing: GtexSpacing.xs,
                children: <Widget>[
                  GtexActionButton(
                    key: const Key('club-market-buy'),
                    label: 'Buy',
                    icon: Icons.shopping_bag_outlined,
                    compact: true,
                    onPressed: () => onAction('buy'),
                  ),
                  GtexActionButton(
                    key: const Key('club-market-transfer'),
                    label: 'Transfer',
                    icon: Icons.swap_horiz,
                    compact: true,
                    secondary: true,
                    onPressed: () => onAction('transfer'),
                  ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Gifts',
          subtitle: 'Ownership waits for acceptance',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              if (data.gifts.isEmpty) const Text('No gifts offered', style: TextStyle(color: GtexColors.textSecondary)),
              for (final Map<String, dynamic> row in data.gifts)
                Text('${row['recipient_ref']} · ${row['status']}', key: Key('club-market-gift-${row['id']}')),
              const SizedBox(height: GtexSpacing.sm),
              GtexActionButton(
                key: const Key('club-market-gift'),
                label: 'Offer gift',
                icon: Icons.card_giftcard,
                compact: true,
                onPressed: () => onAction('gift'),
              ),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Provenance',
          subtitle: 'From, to, price, actor',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              if (data.provenance.isEmpty)
                const Text('No transfers yet', style: TextStyle(color: GtexColors.textSecondary)),
              for (final Map<String, dynamic> row in data.provenance)
                Text(
                  '${row['from_owner_class']} → ${row['to_owner_class']} · ${row['price']} · ${row['actor_user_id']}',
                  key: Key('club-market-provenance-${row['id']}'),
                ),
            ],
          ),
        ),
      ],
    );
  }
}
