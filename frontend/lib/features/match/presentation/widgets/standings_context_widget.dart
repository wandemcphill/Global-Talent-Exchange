import 'package:flutter/material.dart';

import '../broadcast_package_models.dart';

class StandingsContextWidget extends StatelessWidget {
  const StandingsContextWidget({
    super.key,
    required this.contextBoard,
    this.homeTeam,
    this.awayTeam,
  });

  final MatchContextBoard contextBoard;
  final MatchPresentationTeam? homeTeam;
  final MatchPresentationTeam? awayTeam;

  @override
  Widget build(BuildContext context) {
    final String? standingsSummary = _standingsSummary();
    final List<_FormPill> formPills = _formPills();
    return DecoratedBox(
      key: const Key('standings-context-board'),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(28),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[Color(0xFF0F1826), Color(0xFF081018)],
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
                if (contextBoard.competitionContext != null)
                  _MetaChip(label: contextBoard.competitionContext!),
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
            if (standingsSummary != null) ...<Widget>[
              const SizedBox(height: 14),
              _HighlightStrip(text: standingsSummary),
            ],
            if (contextBoard.matchSignificance != null) ...<Widget>[
              const SizedBox(height: 12),
              _HighlightStrip(
                text: contextBoard.matchSignificance!,
                accent: const Color(0xFFF59E0B),
              ),
            ],
            if (formPills.isNotEmpty) ...<Widget>[
              const SizedBox(height: 16),
              Text(
                'Recent form',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 8),
              Wrap(spacing: 8, runSpacing: 8, children: formPills),
            ],
            if (contextBoard.standings.isNotEmpty) ...<Widget>[
              const SizedBox(height: 16),
              Text(
                'Standings snapshot',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 10),
              Column(
                children: contextBoard.standings
                    .take(8)
                    .map(
                      (MatchStandingsEntry entry) => _StandingRow(entry: entry),
                    )
                    .toList(growable: false),
              ),
            ],
          ],
        ),
      ),
    );
  }

  String? _standingsSummary() {
    if (contextBoard.standings.isEmpty ||
        homeTeam == null ||
        awayTeam == null) {
      return null;
    }
    final MatchStandingsEntry? homeStanding = _entryForTeam(homeTeam!);
    final MatchStandingsEntry? awayStanding = _entryForTeam(awayTeam!);
    if (homeStanding == null || awayStanding == null) {
      return null;
    }
    final String homeRank = _ordinal(homeStanding.position);
    final String awayRank = _ordinal(awayStanding.position);
    if (homeRank.isEmpty || awayRank.isEmpty) {
      return null;
    }
    return '$homeRank versus $awayRank with ${homeStanding.points ?? '-'} and ${awayStanding.points ?? '-'} points on the board.';
  }

  MatchStandingsEntry? _entryForTeam(MatchPresentationTeam team) {
    for (final MatchStandingsEntry entry in contextBoard.standings) {
      if (entry.teamId != null && entry.teamId == team.teamId) {
        return entry;
      }
      if (entry.teamName.trim().toLowerCase() ==
          team.teamName.trim().toLowerCase()) {
        return entry;
      }
    }
    return null;
  }

  List<_FormPill> _formPills() {
    return <_FormPill>[
      if (homeTeam != null &&
          (homeTeam!.recentForm != null ||
              _entryForTeam(homeTeam!)?.form != null))
        _FormPill(
          teamName: homeTeam!.teamName,
          numericForm: homeTeam!.recentForm,
          formGuide: _entryForTeam(homeTeam!)?.form,
        ),
      if (awayTeam != null &&
          (awayTeam!.recentForm != null ||
              _entryForTeam(awayTeam!)?.form != null))
        _FormPill(
          teamName: awayTeam!.teamName,
          numericForm: awayTeam!.recentForm,
          formGuide: _entryForTeam(awayTeam!)?.form,
        ),
    ];
  }

  String _ordinal(int? value) {
    if (value == null) {
      return '';
    }
    final int mod100 = value % 100;
    if (mod100 >= 11 && mod100 <= 13) {
      return '${value}th';
    }
    switch (value % 10) {
      case 1:
        return '${value}st';
      case 2:
        return '${value}nd';
      case 3:
        return '${value}rd';
      default:
        return '${value}th';
    }
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

class _HighlightStrip extends StatelessWidget {
  const _HighlightStrip({
    required this.text,
    this.accent = const Color(0xFF7DD3FC),
  });

  final String text;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: accent.withValues(alpha: 0.12),
        border: Border.all(color: accent.withValues(alpha: 0.28)),
      ),
      child: Text(
        text,
        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
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
    final String pointsLabel =
        entry.points == null ? '-- pts' : '${entry.points} pts';
    final String playedLabel =
        entry.played == null ? '' : ' | P ${entry.played}';
    final String goalDifferenceLabel =
        entry.goalDifference == null
            ? ''
            : ' | GD ${entry.goalDifference! >= 0 ? '+' : ''}${entry.goalDifference}';
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
            width: 34,
            child: Text(
              entry.position?.toString() ?? '-',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                color: Colors.white,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  entry.teamName,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                Text(
                  '$pointsLabel$playedLabel$goalDifferenceLabel',
                  style: Theme.of(
                    context,
                  ).textTheme.bodySmall?.copyWith(color: Colors.white60),
                ),
              ],
            ),
          ),
          if (entry.form != null)
            Text(
              entry.form!,
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                color: const Color(0xFF7DD3FC),
                fontWeight: FontWeight.w800,
              ),
            ),
        ],
      ),
    );
  }
}

class _FormPill extends StatelessWidget {
  const _FormPill({
    required this.teamName,
    required this.numericForm,
    required this.formGuide,
  });

  final String teamName;
  final int? numericForm;
  final String? formGuide;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: Colors.white.withValues(alpha: 0.07)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            teamName,
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: Colors.white,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            [
              if (numericForm != null) '${numericForm} / 100',
              if (formGuide != null && formGuide!.trim().isNotEmpty) formGuide!,
            ].join(' | '),
            style: Theme.of(
              context,
            ).textTheme.bodySmall?.copyWith(color: const Color(0xFFB9C7D7)),
          ),
        ],
      ),
    );
  }
}
