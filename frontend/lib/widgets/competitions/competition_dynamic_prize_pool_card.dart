import 'package:flutter/material.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/widgets/gte_metric_chip.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';
import 'package:gte_frontend/widgets/gte_formatters.dart';

class CompetitionDynamicPrizePoolCard extends StatelessWidget {
  const CompetitionDynamicPrizePoolCard({
    super.key,
    required this.dynamicPrizePool,
    required this.currency,
    this.title = 'Viral jackpot',
    this.subtitle,
    this.countdownLabel,
    this.accentColor = GteShellTheme.accentWarm,
  });

  final CompetitionDynamicPrizePool dynamicPrizePool;
  final String currency;
  final String title;
  final String? subtitle;
  final String? countdownLabel;
  final Color accentColor;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      accentColor: accentColor,
      emphasized: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Icon(Icons.local_fire_department_outlined, color: accentColor),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(title, style: Theme.of(context).textTheme.titleLarge),
                    const SizedBox(height: 6),
                    Text(
                      'Jackpot Pool: ${gteFormatCompetitionAmount(dynamicPrizePool.totalPool, currency)}',
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    if (subtitle != null) ...<Widget>[
                      const SizedBox(height: 8),
                      Text(
                        subtitle!,
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
          if (countdownLabel != null) ...<Widget>[
            const SizedBox(height: 14),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(18),
                color: accentColor.withValues(alpha: 0.12),
                border: Border.all(color: accentColor.withValues(alpha: 0.28)),
              ),
              child: Text(
                countdownLabel!,
                style: Theme.of(
                  context,
                ).textTheme.titleMedium?.copyWith(color: accentColor),
              ),
            ),
          ],
          const SizedBox(height: 14),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: <Widget>[
              GteMetricChip(
                label: 'Base',
                value: gteFormatCompetitionAmount(
                  dynamicPrizePool.baseFunding,
                  currency,
                ),
              ),
              GteMetricChip(
                label: 'Activity boost',
                value: gteFormatCompetitionAmount(
                  dynamicPrizePool.activityBoost,
                  currency,
                ),
              ),
              GteMetricChip(
                label: 'Rollover',
                value: gteFormatCompetitionAmount(
                  dynamicPrizePool.jackpotRollover,
                  currency,
                ),
              ),
              GteMetricChip(
                label: 'Active 5m',
                value: dynamicPrizePool.activeUsers5m.toString(),
              ),
              GteMetricChip(
                label: 'Trades 5m',
                value: dynamicPrizePool.tradeVolume5m.toStringAsFixed(1),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
