import 'package:flutter/material.dart';

import '../models/gtex_creator_social_models.dart';
import 'gtex_creator_social_visuals.dart';

class GtexCreatorCompetitionPanel extends StatelessWidget {
  const GtexCreatorCompetitionPanel({
    super.key,
    required this.competitions,
    required this.revenueItems,
  });

  final List<GtexCreatorCompetition> competitions;
  final List<GtexCreatorRevenueItem> revenueItems;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final competitionsPanel = GtexPanel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Hosted competitions',
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.w900,
                  color: Colors.white,
                ),
              ),
              const SizedBox(height: 12),
              ...competitions.map(
                (competition) => _CompetitionTile(competition: competition),
              ),
            ],
          ),
        );
        final monetizationPanel = GtexPanel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Monetization',
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.w900,
                  color: Colors.white,
                ),
              ),
              const SizedBox(height: 12),
              ...revenueItems.map(
                (item) => Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Row(
                    children: [
                      Expanded(
                        child: Text(
                          item.label,
                          style: const TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          Text(
                            item.amountLabel,
                            style: const TextStyle(
                              color: gtexCreatorGold,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                          Text(
                            item.status,
                            style: const TextStyle(
                              color: gtexCreatorTextSoft,
                              fontSize: 12,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        );

        if (constraints.maxWidth < 720) {
          return Column(
            children: [
              competitionsPanel,
              const SizedBox(height: 12),
              monetizationPanel,
            ],
          );
        }

        return Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(flex: 3, child: competitionsPanel),
            const SizedBox(width: 12),
            Expanded(flex: 2, child: monetizationPanel),
          ],
        );
      },
    );
  }
}

class _CompetitionTile extends StatelessWidget {
  const _CompetitionTile({required this.competition});

  final GtexCreatorCompetition competition;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFF101B2C),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: Colors.white.withOpacity(.06)),
      ),
      child: Row(
        children: [
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              color: gtexCreatorGreen.withOpacity(.12),
              borderRadius: BorderRadius.circular(16),
            ),
            child: const Icon(
              Icons.emoji_events_rounded,
              color: gtexCreatorGreen,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  competition.title,
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  '${competition.entriesLabel} · ${competition.poolLabel}',
                  style: const TextStyle(color: gtexCreatorTextSoft),
                ),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              GtexPill(
                label: competition.status,
                color:
                    competition.status == 'Live'
                        ? gtexCreatorGreen
                        : gtexCreatorGold,
              ),
              const SizedBox(height: 8),
              Text(
                competition.revenueLabel,
                style: const TextStyle(color: Colors.white70, fontSize: 12),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
