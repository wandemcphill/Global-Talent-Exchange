import 'package:flutter/material.dart';

import '../broadcast_package_models.dart';

class FormationBoardWidget extends StatelessWidget {
  const FormationBoardWidget({
    super.key,
    required this.team,
    required this.title,
    this.accentColor = const Color(0xFF7DD3FC),
  });

  final MatchPresentationTeam team;
  final String title;
  final Color accentColor;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      key: Key('formation-board-${team.teamId}'),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(28),
        gradient: const LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: <Color>[Color(0xFF0E1A22), Color(0xFF091117)],
        ),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              title,
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                color: Colors.white,
                fontWeight: FontWeight.w900,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              '${team.teamName} | ${team.formation}',
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: Colors.white70),
            ),
            const SizedBox(height: 16),
            LayoutBuilder(
              builder: (BuildContext context, BoxConstraints constraints) {
                final bool compact = constraints.maxWidth < 660;
                final Widget pitch = _FormationPitch(
                  team: team,
                  accentColor: accentColor,
                );
                final Widget rail = _FormationInfoRail(
                  team: team,
                  accentColor: accentColor,
                );
                if (compact) {
                  return Column(
                    children: <Widget>[pitch, const SizedBox(height: 16), rail],
                  );
                }
                return Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Expanded(flex: 5, child: pitch),
                    const SizedBox(width: 18),
                    Expanded(flex: 3, child: rail),
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

class _FormationPitch extends StatelessWidget {
  const _FormationPitch({required this.team, required this.accentColor});

  final MatchPresentationTeam team;
  final Color accentColor;

  @override
  Widget build(BuildContext context) {
    final List<MatchPresentationPlayer> positionedPlayers = team.starters
        .where(
          (MatchPresentationPlayer player) =>
              player.x != null && player.y != null,
        )
        .toList(growable: false);

    return AspectRatio(
      aspectRatio: 0.86,
      child: DecoratedBox(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(24),
          gradient: const LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: <Color>[Color(0xFF174B34), Color(0xFF0F3325)],
          ),
          border: Border.all(color: Colors.white.withValues(alpha: 0.16)),
        ),
        child: Stack(
          children: <Widget>[
            Positioned.fill(child: CustomPaint(painter: _PitchLinesPainter())),
            if (positionedPlayers.isEmpty)
              Center(
                child: Text(
                  'Formation coordinates unavailable on this payload.',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Colors.white70,
                    fontWeight: FontWeight.w700,
                  ),
                  textAlign: TextAlign.center,
                ),
              )
            else
              for (final MatchPresentationPlayer player in positionedPlayers)
                Align(
                  alignment: Alignment(
                    ((player.y! / 100) * 2) - 1,
                    ((player.x! / 100) * 2) - 1,
                  ),
                  child: _FormationPlayerChip(
                    player: player,
                    accentColor: accentColor,
                  ),
                ),
          ],
        ),
      ),
    );
  }
}

class _FormationInfoRail extends StatelessWidget {
  const _FormationInfoRail({required this.team, required this.accentColor});

  final MatchPresentationTeam team;
  final Color accentColor;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.04),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            _InfoValue(
              label: 'Recent form',
              value:
                  team.recentForm == null
                      ? 'Unavailable'
                      : '${team.recentForm} / 100',
              accentColor: accentColor,
            ),
            const SizedBox(height: 12),
            _InfoValue(
              label: 'Coach',
              value: team.coachName ?? 'Unavailable',
              accentColor: accentColor,
            ),
            const SizedBox(height: 12),
            _InfoValue(
              label: 'Mentality',
              value: team.mentality ?? 'Standard',
              accentColor: accentColor,
            ),
            if (team.instructionSummary.isNotEmpty) ...<Widget>[
              const SizedBox(height: 16),
              Text(
                'Instructions',
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 8),
              for (final String item in team.instructionSummary.take(4))
                Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Text(
                    item,
                    style: Theme.of(
                      context,
                    ).textTheme.bodySmall?.copyWith(color: Colors.white70),
                  ),
                ),
            ],
            const SizedBox(height: 16),
            Text(
              'Bench',
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                color: Colors.white,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 8),
            if (team.bench.isEmpty)
              Text(
                'Bench data unavailable on this feed.',
                style: Theme.of(
                  context,
                ).textTheme.bodySmall?.copyWith(color: Colors.white60),
              )
            else
              for (final MatchPresentationPlayer player in team.bench.take(7))
                Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Text(
                    player.displayLabel,
                    style: Theme.of(
                      context,
                    ).textTheme.bodySmall?.copyWith(color: Colors.white70),
                  ),
                ),
          ],
        ),
      ),
    );
  }
}

class _FormationPlayerChip extends StatelessWidget {
  const _FormationPlayerChip({required this.player, required this.accentColor});

  final MatchPresentationPlayer player;
  final Color accentColor;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(minWidth: 70),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(14),
        color: const Color(0xE8131F28),
        border: Border.all(color: accentColor.withValues(alpha: 0.7)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Text(
            player.shirtNumber?.toString() ?? '-',
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
              color: accentColor,
              fontWeight: FontWeight.w900,
            ),
          ),
          Text(
            player.playerName,
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
              color: Colors.white,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }
}

class _InfoValue extends StatelessWidget {
  const _InfoValue({
    required this.label,
    required this.value,
    required this.accentColor,
  });

  final String label;
  final String value;
  final Color accentColor;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          label.toUpperCase(),
          style: Theme.of(context).textTheme.labelSmall?.copyWith(
            color: accentColor,
            fontWeight: FontWeight.w800,
            letterSpacing: 0.8,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          value,
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
            color: Colors.white,
            fontWeight: FontWeight.w700,
          ),
        ),
      ],
    );
  }
}

class _PitchLinesPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final Paint paint =
        Paint()
          ..color = Colors.white.withValues(alpha: 0.18)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.4;
    final Rect inner = (Offset.zero & size).deflate(14);
    canvas.drawRRect(
      RRect.fromRectAndRadius(inner, const Radius.circular(18)),
      paint,
    );
    canvas.drawLine(
      Offset(inner.left, inner.center.dy),
      Offset(inner.right, inner.center.dy),
      paint,
    );
    canvas.drawCircle(inner.center, inner.width * 0.13, paint);
    canvas.drawRect(
      Rect.fromLTWH(
        inner.left + (inner.width * 0.18),
        inner.top,
        inner.width * 0.64,
        inner.height * 0.15,
      ),
      paint,
    );
    canvas.drawRect(
      Rect.fromLTWH(
        inner.left + (inner.width * 0.18),
        inner.bottom - (inner.height * 0.15),
        inner.width * 0.64,
        inner.height * 0.15,
      ),
      paint,
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
