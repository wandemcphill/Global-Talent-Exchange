import 'package:flutter/material.dart';

import '../broadcast_package_models.dart';

class MatchHeaderWidget extends StatelessWidget {
  const MatchHeaderWidget({
    super.key,
    required this.package,
    required this.competitionName,
    required this.phaseLabel,
    this.isSegmented = false,
  });

  final MatchPresentationPackage package;
  final String competitionName;
  final String phaseLabel;
  final bool isSegmented;

  @override
  Widget build(BuildContext context) {
    final MatchContextBoard contextBoard = package.context;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(32),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[Color(0xFF10304A), Color(0xFF07101A)],
        ),
        border: Border.all(color: Colors.white.withValues(alpha: 0.10)),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.22),
            blurRadius: 24,
            offset: const Offset(0, 14),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: <Widget>[
              _MetaPill(label: competitionName),
              if (contextBoard.competitionStage != null)
                _MetaPill(label: contextBoard.competitionStage!),
              if (contextBoard.venueName != null)
                _MetaPill(label: contextBoard.venueName!),
              if (contextBoard.kickoffLabel != null)
                _MetaPill(label: 'KO ${contextBoard.kickoffLabel!}'),
              _MetaPill(label: phaseLabel),
              if (isSegmented) const _MetaPill(label: 'LIVE SEGMENT'),
            ],
          ),
          const SizedBox(height: 20),
          LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              final bool compact = constraints.maxWidth < 780;
              if (compact) {
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    _TeamHeadline(team: package.home, alignEnd: false),
                    const Padding(
                      padding: EdgeInsets.symmetric(vertical: 16),
                      child: Center(child: _VersusPuck()),
                    ),
                    _TeamHeadline(team: package.away, alignEnd: false),
                  ],
                );
              }
              return Row(
                children: <Widget>[
                  Expanded(
                    child: _TeamHeadline(team: package.home, alignEnd: false),
                  ),
                  const Padding(
                    padding: EdgeInsets.symmetric(horizontal: 16),
                    child: _VersusPuck(),
                  ),
                  Expanded(
                    child: _TeamHeadline(team: package.away, alignEnd: true),
                  ),
                ],
              );
            },
          ),
          if (contextBoard.matchSignificance != null) ...<Widget>[
            const SizedBox(height: 18),
            Text(
              contextBoard.matchSignificance!,
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                color: Colors.white70,
                height: 1.35,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class TeamCrestWidget extends StatelessWidget {
  const TeamCrestWidget({super.key, required this.team, this.size = 72});

  final MatchPresentationTeam team;
  final double size;

  @override
  Widget build(BuildContext context) {
    final MatchPresentationCrest? crest = team.crest;
    final Color primary = _colorFromHex(
      crest?.primaryColorHex ?? team.primaryColorHex ?? '#0F172A',
      fallback: const Color(0xFF0F172A),
    );
    final Color secondary = _colorFromHex(
      crest?.secondaryColorHex ?? team.secondaryColorHex ?? '#E5EDF6',
      fallback: const Color(0xFFE5EDF6),
    );
    final Color accent = _colorFromHex(
      crest?.accentColorHex ?? team.accentColorHex ?? '#7DD3FC',
      fallback: const Color(0xFF7DD3FC),
    );
    return Container(
      width: size,
      height: size,
      padding: EdgeInsets.all(size * 0.10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(size * 0.24),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[primary, accent],
        ),
        border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
      ),
      child: DecoratedBox(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(size * 0.18),
          color: secondary.withValues(alpha: 0.18),
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(size * 0.18),
          child:
              crest?.hasArtwork == true
                  ? Image.network(
                    crest!.imageUrl!,
                    fit: BoxFit.cover,
                    errorBuilder:
                        (_, __, ___) => _CrestFallback(
                          label: crest.initials ?? team.displayCode,
                          primary: primary,
                          secondary: secondary,
                        ),
                  )
                  : _CrestFallback(
                    label: crest?.initials ?? team.displayCode,
                    primary: primary,
                    secondary: secondary,
                  ),
        ),
      ),
    );
  }
}

class _TeamHeadline extends StatelessWidget {
  const _TeamHeadline({required this.team, required this.alignEnd});

  final MatchPresentationTeam team;
  final bool alignEnd;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment:
          alignEnd ? MainAxisAlignment.end : MainAxisAlignment.start,
      children: <Widget>[
        if (alignEnd) ...<Widget>[
          Expanded(child: _TeamLabel(team: team, alignEnd: true)),
          const SizedBox(width: 14),
          TeamCrestWidget(team: team),
        ] else ...<Widget>[
          TeamCrestWidget(team: team),
          const SizedBox(width: 14),
          Expanded(child: _TeamLabel(team: team, alignEnd: false)),
        ],
      ],
    );
  }
}

class _TeamLabel extends StatelessWidget {
  const _TeamLabel({required this.team, required this.alignEnd});

  final MatchPresentationTeam team;
  final bool alignEnd;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment:
          alignEnd ? CrossAxisAlignment.end : CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          team.teamName,
          textAlign: alignEnd ? TextAlign.right : TextAlign.left,
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
            color: Colors.white,
            fontWeight: FontWeight.w900,
          ),
        ),
        const SizedBox(height: 6),
        Wrap(
          alignment: alignEnd ? WrapAlignment.end : WrapAlignment.start,
          spacing: 8,
          runSpacing: 6,
          children: <Widget>[
            _MetricTag(label: team.displayCode),
            _MetricTag(label: team.formation),
            if (team.coachName != null) _MetricTag(label: team.coachName!),
          ],
        ),
      ],
    );
  }
}

class _VersusPuck extends StatelessWidget {
  const _VersusPuck();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 70,
      height: 70,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: Colors.white.withValues(alpha: 0.08),
        border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
      ),
      child: Text(
        'VS',
        style: Theme.of(context).textTheme.titleLarge?.copyWith(
          color: Colors.white,
          fontWeight: FontWeight.w900,
        ),
      ),
    );
  }
}

class _MetricTag extends StatelessWidget {
  const _MetricTag({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Text(
      label,
      style: Theme.of(context).textTheme.bodySmall?.copyWith(
        color: const Color(0xFFC4D4E6),
        fontWeight: FontWeight.w700,
      ),
    );
  }
}

class _MetaPill extends StatelessWidget {
  const _MetaPill({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
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

class _CrestFallback extends StatelessWidget {
  const _CrestFallback({
    required this.label,
    required this.primary,
    required this.secondary,
  });

  final String label;
  final Color primary;
  final Color secondary;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[primary, primary.withValues(alpha: 0.76)],
        ),
      ),
      child: Center(
        child: Text(
          label.toUpperCase(),
          maxLines: 1,
          overflow: TextOverflow.fade,
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
            color: secondary,
            fontWeight: FontWeight.w900,
            letterSpacing: 1.0,
          ),
        ),
      ),
    );
  }
}

Color _colorFromHex(String value, {required Color fallback}) {
  final String normalized = value.trim().replaceAll('#', '');
  if (normalized.length != 6 && normalized.length != 8) {
    return fallback;
  }
  final int? parsed = int.tryParse(
    normalized.length == 6 ? 'FF$normalized' : normalized,
    radix: 16,
  );
  return parsed == null ? fallback : Color(parsed);
}
