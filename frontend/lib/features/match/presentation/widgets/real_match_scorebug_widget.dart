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
    this.competitionLabel,
    this.detailLabel,
    this.homeAccent = const Color(0xFF53B1FD),
    this.awayAccent = const Color(0xFFF97316),
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
  final String? competitionLabel;
  final String? detailLabel;
  final Color homeAccent;
  final Color awayAccent;

  @override
  Widget build(BuildContext context) {
    final List<Widget> topChips = <Widget>[
      if (competitionLabel != null && competitionLabel!.trim().isNotEmpty)
        _HeaderChip(
          label: competitionLabel!,
          accent: const Color(0xFF53B1FD),
          filled: false,
        ),
      _HeaderChip(
        label: phaseLabel.toUpperCase(),
        accent: const Color(0xFFFDB022),
      ),
      if (detailLabel != null && detailLabel!.trim().isNotEmpty)
        _HeaderChip(label: detailLabel!, accent: Colors.white54, filled: false),
    ];

    return DecoratedBox(
      key: const Key('real-match-scorebug'),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(24),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[Color(0xF50A121A), Color(0xF2132231)],
        ),
        border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.22),
            blurRadius: 24,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            if (topChips.isNotEmpty) ...<Widget>[
              Align(
                alignment: Alignment.centerLeft,
                child: Wrap(spacing: 8, runSpacing: 8, children: topChips),
              ),
              const SizedBox(height: 12),
            ],
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Expanded(
                  child: _TeamBlock(
                    name: homeName,
                    score: homeScore,
                    accent: homeAccent,
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 10),
                  child: Column(
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
                      const SizedBox(height: 4),
                      Container(
                        width: 32,
                        height: 2,
                        color: Colors.white.withValues(alpha: 0.14),
                      ),
                    ],
                  ),
                ),
                Expanded(
                  child: _TeamBlock(
                    name: awayName,
                    score: awayScore,
                    accent: awayAccent,
                    alignEnd: true,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Wrap(
              alignment: WrapAlignment.center,
              spacing: 8,
              runSpacing: 8,
              children: <Widget>[
                _MetaChip(
                  label: stateLabel.toUpperCase(),
                  accent: const Color(0xFF17B26A),
                ),
                _MetaChip(label: cameraLabel, accent: const Color(0xFF53B1FD)),
              ],
            ),
            if (eventLabel != null &&
                eventLabel!.trim().isNotEmpty) ...<Widget>[
              const SizedBox(height: 10),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 9,
                ),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(14),
                  color: Colors.white.withValues(alpha: 0.05),
                  border: Border.all(
                    color: Colors.white.withValues(alpha: 0.08),
                  ),
                ),
                child: Text(
                  eventLabel!,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.w800,
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
    required this.accent,
    this.alignEnd = false,
  });

  final String name;
  final int score;
  final Color accent;
  final bool alignEnd;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment:
          alignEnd ? CrossAxisAlignment.end : CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          mainAxisAlignment:
              alignEnd ? MainAxisAlignment.end : MainAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            if (!alignEnd)
              Container(
                width: 8,
                height: 8,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: accent,
                ),
              ),
            if (!alignEnd) const SizedBox(width: 8),
            Flexible(
              child: Text(
                name.toUpperCase(),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                textAlign: alignEnd ? TextAlign.right : TextAlign.left,
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: Colors.white70,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 0.5,
                ),
              ),
            ),
            if (alignEnd) const SizedBox(width: 8),
            if (alignEnd)
              Container(
                width: 8,
                height: 8,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: accent,
                ),
              ),
          ],
        ),
        const SizedBox(height: 4),
        Text(
          '$score',
          style: Theme.of(context).textTheme.headlineMedium?.copyWith(
            color: Colors.white,
            fontWeight: FontWeight.w900,
          ),
        ),
      ],
    );
  }
}

class _HeaderChip extends StatelessWidget {
  const _HeaderChip({
    required this.label,
    required this.accent,
    this.filled = true,
  });

  final String label;
  final Color accent;
  final bool filled;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color:
            filled
                ? accent.withValues(alpha: 0.16)
                : Colors.white.withValues(alpha: 0.04),
        border: Border.all(
          color:
              filled
                  ? accent.withValues(alpha: 0.34)
                  : Colors.white.withValues(alpha: 0.10),
        ),
      ),
      child: Text(
        label,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: Theme.of(context).textTheme.labelMedium?.copyWith(
          color: filled ? Colors.white : Colors.white70,
          fontWeight: FontWeight.w800,
        ),
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
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        textAlign: TextAlign.center,
        style: Theme.of(context).textTheme.labelMedium?.copyWith(
          color: Colors.white,
          fontWeight: FontWeight.w800,
          letterSpacing: 0.5,
        ),
      ),
    );
  }
}
