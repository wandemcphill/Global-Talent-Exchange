import 'package:flutter/material.dart';

import '../broadcast_package_models.dart';
import 'match_header_widget.dart';

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
          colors: <Color>[Color(0xFF101C29), Color(0xFF081019)],
        ),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(22),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              'Official Roster Card',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                color: Colors.white,
                fontWeight: FontWeight.w900,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              package.matchLabel,
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: const Color(0xFFB3C2D5)),
            ),
            if (package.context.refereeName != null) ...<Widget>[
              const SizedBox(height: 12),
              _InfoPill(label: 'Referee', value: package.context.refereeName!),
            ],
            const SizedBox(height: 18),
            LayoutBuilder(
              builder: (BuildContext context, BoxConstraints constraints) {
                final bool compact = constraints.maxWidth < 860;
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
        border: Border.all(color: Colors.white.withValues(alpha: 0.07)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Row(
              children: <Widget>[
                TeamCrestWidget(team: team, size: 48),
                const SizedBox(width: 12),
                Expanded(
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
                      Wrap(
                        spacing: 10,
                        runSpacing: 6,
                        children: <Widget>[
                          _MiniMeta(label: team.displayCode),
                          _MiniMeta(label: team.formation),
                          if (team.coachName != null)
                            _MiniMeta(label: 'Mgr ${team.coachName!}'),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 18),
            const _SectionLabel(label: 'Starting XI'),
            const SizedBox(height: 10),
            for (final MatchPresentationPlayer player in team.starters.take(11))
              _RosterLine(player: player),
            if (team.hasBench) ...<Widget>[
              const SizedBox(height: 16),
              const _SectionLabel(label: 'Substitutes'),
              const SizedBox(height: 10),
              for (final MatchPresentationPlayer player in team.bench.take(12))
                _RosterLine(player: player, compact: true),
            ],
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
    final String roleLabel =
        (player.role ?? player.line ?? '').replaceAll('_', ' ').toUpperCase();
    return Padding(
      padding: EdgeInsets.symmetric(vertical: compact ? 4 : 5),
      child: Row(
        children: <Widget>[
          Container(
            width: 30,
            height: 30,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
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
          if (roleLabel.isNotEmpty)
            Text(
              roleLabel,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: const Color(0xFF8EA8C3),
                fontWeight: FontWeight.w700,
              ),
            ),
        ],
      ),
    );
  }
}

class _InfoPill extends StatelessWidget {
  const _InfoPill({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: Colors.white.withValues(alpha: 0.05),
        border: Border.all(color: Colors.white.withValues(alpha: 0.07)),
      ),
      child: Text(
        '$label: $value',
        style: Theme.of(context).textTheme.labelLarge?.copyWith(
          color: Colors.white,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

class _MiniMeta extends StatelessWidget {
  const _MiniMeta({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Text(
      label,
      style: Theme.of(context).textTheme.bodySmall?.copyWith(
        color: const Color(0xFF9FB3C8),
        fontWeight: FontWeight.w700,
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
