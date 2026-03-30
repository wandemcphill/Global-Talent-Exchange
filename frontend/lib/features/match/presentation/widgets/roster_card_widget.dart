import 'package:flutter/material.dart';

import '../broadcast_package_models.dart';

class RosterCardWidget extends StatelessWidget {
  const RosterCardWidget({super.key, required this.package});

  final MatchPresentationPackage package;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      key: const Key('roster-card'),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(28),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[Color(0xFF102130), Color(0xFF0B141D)],
        ),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(22),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              'Official Roster',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                color: Colors.white,
                fontWeight: FontWeight.w900,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              package.matchLabel,
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: const Color(0xFFAFBED2)),
            ),
            const SizedBox(height: 18),
            LayoutBuilder(
              builder: (BuildContext context, BoxConstraints constraints) {
                final bool compact = constraints.maxWidth < 780;
                final List<Widget> columns = <Widget>[
                  _RosterColumn(team: package.home),
                  _RosterColumn(team: package.away),
                ];
                if (compact) {
                  return Column(
                    children: <Widget>[
                      columns[0],
                      const SizedBox(height: 18),
                      columns[1],
                    ],
                  );
                }
                return Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Expanded(child: columns[0]),
                    const SizedBox(width: 18),
                    Expanded(child: columns[1]),
                  ],
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}

class _RosterColumn extends StatelessWidget {
  const _RosterColumn({required this.team});

  final MatchPresentationTeam team;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.04),
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              team.teamName,
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                color: Colors.white,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              '${team.shortName} | ${team.formation}'
              '${team.coachName == null ? '' : ' | Coach ${team.coachName}'}',
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: const Color(0xFFB7C6D9)),
            ),
            const SizedBox(height: 16),
            const _SectionLabel(label: 'Starting XI'),
            const SizedBox(height: 10),
            for (final MatchPresentationPlayer player in team.starters.take(11))
              _RosterLine(player: player),
            const SizedBox(height: 14),
            const _SectionLabel(label: 'Substitutes'),
            const SizedBox(height: 10),
            if (team.bench.isEmpty)
              Text(
                'Bench data unavailable on this match payload.',
                style: Theme.of(
                  context,
                ).textTheme.bodySmall?.copyWith(color: Colors.white60),
              )
            else
              for (final MatchPresentationPlayer player in team.bench.take(9))
                _RosterLine(player: player, compact: true),
          ],
        ),
      ),
    );
  }
}

class _RosterLine extends StatelessWidget {
  const _RosterLine({required this.player, this.compact = false});

  final MatchPresentationPlayer player;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.symmetric(vertical: compact ? 4 : 5),
      child: Row(
        children: <Widget>[
          Container(
            width: 28,
            height: 28,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(999),
              color: Colors.white.withValues(alpha: 0.08),
            ),
            child: Text(
              player.shirtNumber?.toString() ?? '-',
              style: Theme.of(context).textTheme.labelMedium?.copyWith(
                color: Colors.white,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              player.playerName,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: Colors.white,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          if (player.role != null)
            Text(
              player.role!.replaceAll('_', ' ').toUpperCase(),
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: const Color(0xFF8FA8C4),
                fontWeight: FontWeight.w700,
              ),
            ),
        ],
      ),
    );
  }
}

class _SectionLabel extends StatelessWidget {
  const _SectionLabel({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Text(
      label.toUpperCase(),
      style: Theme.of(context).textTheme.labelLarge?.copyWith(
        color: const Color(0xFF7DD3FC),
        fontWeight: FontWeight.w800,
        letterSpacing: 1.0,
      ),
    );
  }
}
