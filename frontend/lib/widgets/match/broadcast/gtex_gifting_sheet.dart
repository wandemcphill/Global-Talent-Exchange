import 'package:flutter/material.dart';

class GtexGiftingSheet extends StatelessWidget {
  const GtexGiftingSheet({
    super.key,
    required this.onSelected,
  });

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
    const List<double> amounts = <double>[0.1, 0.2, 0.5];
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
              'Backend payments stay out of this v1 screen. These buttons are clean integration hooks.',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Colors.white70,
                  ),
            ),
            const SizedBox(height: 18),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: amounts.map((double amount) {
                return FilledButton(
                  onPressed: () {
                    Navigator.of(context).pop();
                    onSelected(amount);
                  },
                  child: Text('${amount.toStringAsFixed(1)} coin'),
                );
              }).toList(growable: false),
            ),
          ],
        ),
      ),
    );
  }
}
