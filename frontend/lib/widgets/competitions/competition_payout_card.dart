import 'package:flutter/material.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class CompetitionPayoutCard extends StatelessWidget {
  const CompetitionPayoutCard({
    super.key,
    required this.title,
    required this.currency,
    required this.payouts,
  });

  final String title;
  final String currency;
  final List<CompetitionPayoutBreakdown> payouts;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(title, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          Text(
            'Transparent payout is fixed to the published rules once paid entries begin.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 16),
          if (payouts.isEmpty)
            Text(
              'No payout structure is configured yet.',
              style: Theme.of(context).textTheme.bodyMedium,
            )
          else
            ...payouts.map(
              (CompetitionPayoutBreakdown payout) => Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: GteShellTheme.panelStrong.withValues(alpha: 0.48),
                    borderRadius: BorderRadius.circular(18),
                    border: Border.all(color: GteShellTheme.stroke),
                  ),
                  child: Row(
                    children: <Widget>[
                      Container(
                        width: 42,
                        height: 42,
                        decoration: BoxDecoration(
                          color: const Color(0x147DE2D1),
                          borderRadius: BorderRadius.circular(14),
                        ),
                        alignment: Alignment.center,
                        child: Text(
                          '#${payout.place}',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          '${(payout.percent * 100).toStringAsFixed(0)}% of the prize pool',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                      ),
                      Text(
                        _formatAmount(payout.amount, currency),
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(
                              color: GteShellTheme.accent,
                            ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

String _formatAmount(double value, String currency) {
  final bool whole = value == value.roundToDouble();
  final String number = value.toStringAsFixed(whole ? 0 : 2);
  if (currency.toLowerCase() == 'credit') {
    return '$number cr';
  }
  return '$number ${currency.toUpperCase()}';
}
