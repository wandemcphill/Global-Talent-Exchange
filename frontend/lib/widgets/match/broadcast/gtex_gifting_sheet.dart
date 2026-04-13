import 'package:flutter/material.dart';

import '../../../data/match_gift_api.dart';

typedef MatchGiftSelectionHandler =
    Future<void> Function(MatchGiftCatalogItem gift);

class GtexGiftingSheet extends StatelessWidget {
  const GtexGiftingSheet({super.key, required this.onSelected});

  final MatchGiftSelectionHandler onSelected;

  static Future<void> show(
    BuildContext context, {
    required MatchGiftSelectionHandler onSelected,
  }) {
    return showModalBottomSheet<void>(
      context: context,
      backgroundColor: const Color(0xFF0B1622),
      builder: (BuildContext context) {
        return GtexGiftingSheet(onSelected: onSelected);
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              'Send a live gift',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                color: Colors.white,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Match support settles through the live gift engine. Pick a real catalog item and send it to the verified match host.',
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: Colors.white70),
            ),
            const SizedBox(height: 18),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: kMatchGiftCatalog
                  .map(
                    (MatchGiftCatalogItem option) => FilledButton(
                      onPressed: () async {
                        Navigator.of(context).pop();
                        await onSelected(option);
                      },
                      style: FilledButton.styleFrom(
                        backgroundColor: Colors.white,
                        foregroundColor: const Color(0xFF0B1622),
                        padding: const EdgeInsets.symmetric(
                          horizontal: 18,
                          vertical: 14,
                        ),
                      ),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: <Widget>[
                          Text(
                            option.label,
                            style: const TextStyle(fontWeight: FontWeight.w800),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            '${option.fanCoinAmount.toStringAsFixed(0)} Fan Coin',
                          ),
                        ],
                      ),
                    ),
                  )
                  .toList(growable: false),
            ),
          ],
        ),
      ),
    );
  }
}
