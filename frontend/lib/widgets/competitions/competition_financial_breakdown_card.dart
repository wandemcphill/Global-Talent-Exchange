import 'package:flutter/material.dart';
import 'package:gte_frontend/widgets/gte_formatters.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class CompetitionFinancialBreakdownCard extends StatelessWidget {
  const CompetitionFinancialBreakdownCard({
    super.key,
    required this.title,
    required this.entryFee,
    required this.participantCount,
    required this.platformFeePct,
    required this.platformFeeAmount,
    required this.hostFeePct,
    required this.hostFeeAmount,
    required this.prizePool,
    required this.currency,
    this.projected = false,
    this.lockNotice,
  });

  final String title;
  final double entryFee;
  final int participantCount;
  final double platformFeePct;
  final double platformFeeAmount;
  final double hostFeePct;
  final double hostFeeAmount;
  final double prizePool;
  final String currency;
  final bool projected;
  final String? lockNotice;

  @override
  Widget build(BuildContext context) {
    final double grossPool = entryFee * participantCount;
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(title, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          Text(
            projected
                ? 'Projected fees at full capacity with transparent payout and secure escrow wording.'
                : 'Live fee summary for this creator competition.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 18),
          _MoneyRow(
            label: 'Entry fee',
            value: '${_formatAmount(entryFee, currency)} per player',
          ),
          _MoneyRow(
            label: projected
                ? 'Projected gross pool'
                : 'Gross pool',
            value: _formatAmount(grossPool, currency),
          ),
          _MoneyRow(
            label:
                'Platform service fee (${(platformFeePct * 100).toStringAsFixed(0)}%)',
            value: _formatAmount(platformFeeAmount, currency),
          ),
          if (hostFeePct > 0 || hostFeeAmount > 0)
            _MoneyRow(
              label: 'Host fee (${(hostFeePct * 100).toStringAsFixed(0)}%)',
              value: _formatAmount(hostFeeAmount, currency),
            ),
          const Divider(height: 28),
          _MoneyRow(
            label: 'Prize pool',
            value: _formatAmount(prizePool, currency),
            emphasize: true,
          ),
          const SizedBox(height: 14),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              const Icon(Icons.shield_outlined, color: GteShellTheme.accent),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  'Entry fees are held in secure escrow until the published rules settle the transparent payout.',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ),
            ],
          ),
          if (lockNotice != null) ...<Widget>[
            const SizedBox(height: 14),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                const Icon(
                  Icons.lock_outline,
                  color: GteShellTheme.accentWarm,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    lockNotice!,
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

class _MoneyRow extends StatelessWidget {
  const _MoneyRow({
    required this.label,
    required this.value,
    this.emphasize = false,
  });

  final String label;
  final String value;
  final bool emphasize;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        children: <Widget>[
          Expanded(
            child: Text(
              label,
              style: emphasize
                  ? Theme.of(context).textTheme.titleMedium
                  : Theme.of(context).textTheme.bodyMedium,
            ),
          ),
          Text(
            value,
            style: emphasize
                ? Theme.of(context).textTheme.titleLarge?.copyWith(
                      color: GteShellTheme.accent,
                    )
                : Theme.of(context).textTheme.titleMedium,
          ),
        ],
      ),
    );
  }
}

String _formatAmount(double value, String currency) {
  if (currency.toLowerCase() == 'credit') {
    return gteFormatCredits(value);
  }
  if (currency.toLowerCase() == 'coin') {
    return gteFormatFanCoins(value);
  }
  final bool whole = value == value.roundToDouble();
  final String number = value.toStringAsFixed(whole ? 0 : 2);
  return '$number ${currency.toUpperCase()}';
}
