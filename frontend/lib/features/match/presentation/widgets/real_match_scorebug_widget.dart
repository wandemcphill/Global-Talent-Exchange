import 'package:flutter/material.dart';

class RealMatchScorebugWidget extends StatelessWidget {
  const RealMatchScorebugWidget({
    super.key,
    required this.homeName,
    required this.awayName,
    required this.homeScore,
    required this.awayScore,
    required this.clockLabel,
    required this.phaseLabel,
    required this.stateLabel,
    required this.cameraLabel,
    this.eventLabel,
  });

  final String homeName;
  final String awayName;
  final int homeScore;
  final int awayScore;
  final String clockLabel;
  final String phaseLabel;
  final String stateLabel;
  final String cameraLabel;
  final String? eventLabel;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      key: const Key('real-match-scorebug'),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        gradient: const LinearGradient(
          colors: <Color>[Color(0xF40A121C), Color(0xF4132232)],
        ),
        border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.18),
            blurRadius: 22,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(14, 12, 14, 10),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Row(
              children: <Widget>[
                _TeamBlock(name: homeName, score: homeScore),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: <Widget>[
                      Text(
                        clockLabel,
                        style: Theme.of(
                          context,
                        ).textTheme.headlineSmall?.copyWith(
                          color: Colors.white,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        phaseLabel,
                        style: Theme.of(context).textTheme.labelLarge?.copyWith(
                          color: const Color(0xFFFDB022),
                          fontWeight: FontWeight.w800,
                          letterSpacing: 0.8,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 12),
                _TeamBlock(name: awayName, score: awayScore, alignEnd: true),
              ],
            ),
            const SizedBox(height: 10),
            Row(
              children: <Widget>[
                Expanded(
                  child: _MetaChip(
                    label: stateLabel.toUpperCase(),
                    accent: const Color(0xFF17B26A),
                  ),
                ),
                const SizedBox(width: 8),
                _MetaChip(label: cameraLabel, accent: const Color(0xFF53B1FD)),
              ],
            ),
            if (eventLabel != null &&
                eventLabel!.trim().isNotEmpty) ...<Widget>[
              const SizedBox(height: 10),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 8,
                ),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(12),
                  color: Colors.white.withValues(alpha: 0.05),
                ),
                child: Text(
                  eventLabel!,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.w700,
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

class _TeamBlock extends StatelessWidget {
  const _TeamBlock({
    required this.name,
    required this.score,
    this.alignEnd = false,
  });

  final String name;
  final int score;
  final bool alignEnd;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 100,
      child: Column(
        crossAxisAlignment:
            alignEnd ? CrossAxisAlignment.end : CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            name.toUpperCase(),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: Colors.white70,
              fontWeight: FontWeight.w700,
            ),
          ),
          Text(
            '$score',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
              color: Colors.white,
              fontWeight: FontWeight.w900,
            ),
          ),
        ],
      ),
    );
  }
}

class _MetaChip extends StatelessWidget {
  const _MetaChip({required this.label, required this.accent});

  final String label;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: accent.withValues(alpha: 0.15),
        border: Border.all(color: accent.withValues(alpha: 0.4)),
      ),
      child: Text(
        label,
        textAlign: TextAlign.center,
        style: Theme.of(context).textTheme.labelMedium?.copyWith(
          color: Colors.white,
          fontWeight: FontWeight.w800,
          letterSpacing: 0.6,
        ),
      ),
    );
  }
}
