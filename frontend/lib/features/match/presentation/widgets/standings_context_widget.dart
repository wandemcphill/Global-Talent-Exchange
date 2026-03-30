import 'package:flutter/material.dart';

import '../broadcast_package_models.dart';

class StandingsContextWidget extends StatelessWidget {
  const StandingsContextWidget({super.key, required this.contextBoard});

  final MatchContextBoard contextBoard;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      key: const Key('standings-context-board'),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(28),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[Color(0xFF111B29), Color(0xFF0A1118)],
        ),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              'Standings and Context',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                color: Colors.white,
                fontWeight: FontWeight.w900,
              ),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: <Widget>[
                if (contextBoard.competitionName != null)
                  _MetaChip(label: contextBoard.competitionName!),
                if (contextBoard.competitionStage != null)
                  _MetaChip(label: contextBoard.competitionStage!),
                if (contextBoard.dateLabel != null)
                  _MetaChip(label: contextBoard.dateLabel!),
                if (contextBoard.kickoffLabel != null)
                  _MetaChip(label: contextBoard.kickoffLabel!),
                if (contextBoard.venueName != null)
                  _MetaChip(label: contextBoard.venueName!),
                if (contextBoard.refereeName != null)
                  _MetaChip(label: 'Ref ${contextBoard.refereeName!}'),
              ],
            ),
            if (contextBoard.matchSignificance != null) ...<Widget>[
              const SizedBox(height: 14),
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(18),
                  color: const Color(0xFF102B3D),
                  border: Border.all(
                    color: const Color(0xFF7DD3FC).withValues(alpha: 0.32),
                  ),
                ),
                child: Text(
                  contextBoard.matchSignificance!,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
            const SizedBox(height: 16),
            if (contextBoard.standings.isEmpty)
              Text(
                'League table context is not available on this live match payload.',
                style: Theme.of(
                  context,
                ).textTheme.bodyMedium?.copyWith(color: Colors.white70),
              )
            else
              Column(
                children: contextBoard.standings
                    .map(
                      (MatchStandingsEntry entry) => _StandingRow(entry: entry),
                    )
                    .toList(growable: false),
              ),
            if (contextBoard.storylines.isNotEmpty) ...<Widget>[
              const SizedBox(height: 16),
              Text(
                'Storylines',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 8),
              for (final String storyline in contextBoard.storylines.take(4))
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Text(
                    '- $storyline',
                    style: Theme.of(
                      context,
                    ).textTheme.bodySmall?.copyWith(color: Colors.white70),
                  ),
                ),
            ],
          ],
        ),
      ),
    );
  }
}

class _MetaChip extends StatelessWidget {
  const _MetaChip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelMedium?.copyWith(
          color: Colors.white,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

class _StandingRow extends StatelessWidget {
  const _StandingRow({required this.entry});

  final MatchStandingsEntry entry;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        color: Colors.white.withValues(alpha: 0.04),
      ),
      child: Row(
        children: <Widget>[
          SizedBox(
            width: 30,
            child: Text(
              entry.position?.toString() ?? '-',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                color: Colors.white,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
          Expanded(
            child: Text(
              entry.teamName,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: Colors.white,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          if (entry.form != null)
            Padding(
              padding: const EdgeInsets.only(right: 12),
              child: Text(
                entry.form!,
                style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  color: const Color(0xFF7DD3FC),
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
          Text(
            entry.points == null ? 'PTS --' : 'PTS ${entry.points}',
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: Colors.white70,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}
