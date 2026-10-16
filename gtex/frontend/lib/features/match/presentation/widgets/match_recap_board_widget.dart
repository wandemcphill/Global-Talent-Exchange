import 'package:flutter/material.dart';

import '../../../../models/match_event.dart';
import '../../../../models/real_match_engine_presentation.dart';

class MatchRecapBoardWidget extends StatelessWidget {
  const MatchRecapBoardWidget({
    super.key,
    required this.summaryBoard,
    this.events = const <MatchEvent>[],
    this.activeEventId,
  });

  final MatchEngineSummaryBoard summaryBoard;
  final List<MatchEvent> events;
  final String? activeEventId;

  @override
  Widget build(BuildContext context) {
    final List<MatchEvent> storyEvents = events
        .where((MatchEvent event) => event.isMajor)
        .take(6)
        .toList(growable: false);
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
                    '- $bullet',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Colors.white70,
                      height: 1.35,
                    ),
                  ),
                ),
              ),
            ],
            if (storyEvents.isNotEmpty) ...<Widget>[
              const SizedBox(height: 14),
              Text(
                'MATCH STORY',
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: Colors.white70,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: storyEvents
                    .map(
                      (MatchEvent event) => _EventLedgerChip(
                        event: event,
                        isActive: event.id == activeEventId,
                      ),
                    )
                    .toList(growable: false),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _EventLedgerChip extends StatelessWidget {
  const _EventLedgerChip({required this.event, required this.isActive});

  final MatchEvent event;
  final bool isActive;

  @override
  Widget build(BuildContext context) {
    final Color accent =
        isActive
            ? const Color(0xFFFDB022)
            : Colors.white.withValues(alpha: 0.24);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(14),
        color:
            isActive
                ? const Color(0x24FDB022)
                : Colors.white.withValues(alpha: 0.04),
        border: Border.all(color: accent),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Icon(event.icon, size: 16, color: isActive ? accent : Colors.white70),
          const SizedBox(width: 8),
          Text(
            '${event.clockLabel} ${event.bannerText}',
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
              color: Colors.white,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}
