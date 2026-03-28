import 'package:flutter/material.dart';

class GtexGiftingSheet extends StatelessWidget {
  const GtexGiftingSheet({super.key, required this.onSelected});

  final ValueChanged<double> onSelected;

  static Future<void> show(
    BuildContext context, {
    required ValueChanged<double> onSelected,
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
    const List<_GiftOption> options = <_GiftOption>[
      _GiftOption(label: 'Fire', amount: 2),
      _GiftOption(label: 'Applause', amount: 5),
      _GiftOption(label: 'Crown', amount: 20),
    ];
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
              'Match gifting runs on Fan Coin. These controls stay wired as clean integration hooks for live settlement.',
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: Colors.white70),
            ),
            const SizedBox(height: 18),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: options
                  .map((_GiftOption option) {
                    return FilledButton(
                      onPressed: () {
                        Navigator.of(context).pop();
                        onSelected(option.amount);
                      },
                      child: Text(
                        '${option.label} - ${option.amount.toStringAsFixed(0)} Fan Coin',
                      ),
                    );
                  })
                  .toList(growable: false),
            ),
          ],
        ),
      ),
    );
  }
}

class _GiftOption {
  const _GiftOption({required this.label, required this.amount});

  final String label;
  final double amount;
}
