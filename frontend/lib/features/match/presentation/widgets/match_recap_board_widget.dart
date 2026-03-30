import 'package:flutter/material.dart';

import '../../../../models/real_match_engine_presentation.dart';

class MatchRecapBoardWidget extends StatelessWidget {
  const MatchRecapBoardWidget({super.key, required this.summaryBoard});

  final MatchEngineSummaryBoard summaryBoard;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      key: const Key('match-recap-board'),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(28),
        gradient: const LinearGradient(
          colors: <Color>[Color(0xF00B141F), Color(0xED132133)],
        ),
        border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.28),
            blurRadius: 30,
            offset: const Offset(0, 18),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.all(22),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              summaryBoard.title.toUpperCase(),
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                color: const Color(0xFFFDB022),
                fontWeight: FontWeight.w900,
                letterSpacing: 1.1,
              ),
            ),
            const SizedBox(height: 10),
            Text(
              summaryBoard.subtitle,
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                color: Colors.white,
                fontWeight: FontWeight.w900,
              ),
            ),
            if (summaryBoard.bullets.isNotEmpty) ...<Widget>[
              const SizedBox(height: 14),
              ...summaryBoard.bullets.map(
                (String bullet) => Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Text(
                    '• $bullet',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Colors.white70,
                      height: 1.35,
                    ),
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
