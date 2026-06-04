import 'package:flutter/material.dart';

import '../domain/competition_bracket_models.dart';

enum CompeteBracketEmptyStateKind { blocked, degraded }

class CompetitionBracketSurface extends StatelessWidget {
  const CompetitionBracketSurface({
    super.key,
    required this.payload,
    this.padding = const EdgeInsets.all(16),
    this.roundWidth = 280,
    this.onOpenLiveMatch,
  });

  final CompetitionBracketPayload? payload;
  final EdgeInsetsGeometry padding;
  final double roundWidth;
  final ValueChanged<String>? onOpenLiveMatch;

  @override
  Widget build(BuildContext context) {
    final CompetitionBracketPayload? bracket = payload;
    if (bracket == null) {
      return const CompeteBracketEmptyState.blocked(
        title: 'Bracket blocked',
        message: 'Backend bracket payload is missing.',
      );
    }
    if (bracket.rounds.isEmpty) {
      return CompeteBracketEmptyState.degraded(
        title: 'Bracket pending backend payload',
        message:
            'No backend rounds were supplied, so this surface is not generating a placeholder bracket.',
        details: bracket.backendWarnings,
      );
    }

    return Padding(
      padding: padding,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          CompetitionLifecycleBanner(
            lifecycle: bracket.lifecycle,
            title: bracket.title,
            competitionId: bracket.competitionId,
            revision: bracket.revision,
            warnings: bracket.backendWarnings,
          ),
          const SizedBox(height: 16),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: bracket.rounds
                  .map(
                    (CompetitionBracketRound round) => Padding(
                      padding: const EdgeInsets.only(right: 12),
                      child: CompetitionBracketRoundColumn(
                        round: round,
                        width: roundWidth,
                        onOpenLiveMatch: onOpenLiveMatch,
                      ),
                    ),
                  )
                  .toList(growable: false),
            ),
          ),
        ],
      ),
    );
  }
}

class CompetitionLifecycleBanner extends StatelessWidget {
  const CompetitionLifecycleBanner({
    super.key,
    required this.lifecycle,
    this.title,
    this.competitionId,
    this.revision,
    this.warnings = const <String>[],
  });

  final CompetitionLifecycleState lifecycle;
  final String? title;
  final String? competitionId;
  final String? revision;
  final List<String> warnings;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final ColorScheme colors = theme.colorScheme;
    final List<String> detailLines = <String>[
      if (_notBlank(competitionId)) 'Competition $competitionId',
      if (_notBlank(revision)) 'Revision $revision',
      if (_notBlank(lifecycle.reason)) lifecycle.reason!,
      if (_notBlank(lifecycle.blockedReason)) lifecycle.blockedReason!,
      ...warnings,
    ];
    return DecoratedBox(
      decoration: BoxDecoration(
        border: Border.all(color: colors.outlineVariant),
        borderRadius: BorderRadius.circular(8),
        color: colors.surface,
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Expanded(
                  child: Text(
                    _notBlank(title) ? title! : 'Competition bracket',
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                    overflow: TextOverflow.ellipsis,
                    maxLines: 2,
                  ),
                ),
                const SizedBox(width: 12),
                _StatusChip(
                  label: competitionLifecycleStageLabel(lifecycle.stage),
                  isLive: lifecycle.isLive,
                  isBlocked: lifecycle.isBlocked,
                ),
              ],
            ),
            if (detailLines.isNotEmpty) ...<Widget>[
              const SizedBox(height: 8),
              Text(
                detailLines.join(' | '),
                style: theme.textTheme.bodySmall?.copyWith(
                  color: colors.onSurfaceVariant,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class CompetitionBracketRoundColumn extends StatelessWidget {
  const CompetitionBracketRoundColumn({
    super.key,
    required this.round,
    this.width = 280,
    this.onOpenLiveMatch,
  });

  final CompetitionBracketRound round;
  final double width;
  final ValueChanged<String>? onOpenLiveMatch;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final ColorScheme colors = theme.colorScheme;
    return SizedBox(
      width: width,
      child: DecoratedBox(
        decoration: BoxDecoration(
          border: Border.all(color: colors.outlineVariant),
          borderRadius: BorderRadius.circular(8),
          color: colors.surface,
        ),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(
                children: <Widget>[
                  Expanded(
                    child: Text(
                      round.displayName,
                      style: theme.textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  const SizedBox(width: 8),
                  _StatusChip(
                    label: competitionBracketNodeStatusLabel(round.status),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              if (round.matches.isEmpty)
                const _InlineDegradedState(
                  message: 'Backend has not supplied matches for this round.',
                )
              else
                Column(
                  children: round.matches
                      .map(
                        (CompetitionBracketMatch match) => Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: CompetitionBracketMatchTile(
                            match: match,
                            onOpenLiveMatch: onOpenLiveMatch,
                          ),
                        ),
                      )
                      .toList(growable: false),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class CompetitionBracketMatchTile extends StatelessWidget {
  const CompetitionBracketMatchTile({
    super.key,
    required this.match,
    this.onOpenLiveMatch,
  });

  final CompetitionBracketMatch match;
  final ValueChanged<String>? onOpenLiveMatch;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final ColorScheme colors = theme.colorScheme;
    return DecoratedBox(
      decoration: BoxDecoration(
        border: Border.all(color: colors.outlineVariant),
        borderRadius: BorderRadius.circular(8),
        color: colors.surfaceContainerHighest,
      ),
      child: Padding(
        padding: const EdgeInsets.all(10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Row(
              children: <Widget>[
                Expanded(
                  child: Text(
                    match.displayLabel,
                    style: theme.textTheme.labelLarge,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                const SizedBox(width: 8),
                _StatusChip(
                  label: competitionBracketNodeStatusLabel(match.status),
                  isLive: match.status == CompetitionBracketNodeStatus.live,
                ),
              ],
            ),
            const SizedBox(height: 8),
            _BracketSideRow(
              side: match.home,
              score: match.homeScore,
              winnerParticipantId: match.winnerParticipantId,
            ),
            Divider(color: colors.outlineVariant, height: 12),
            _BracketSideRow(
              side: match.away,
              score: match.awayScore,
              winnerParticipantId: match.winnerParticipantId,
            ),
            if (_notBlank(match.liveMatchId)) ...<Widget>[
              const SizedBox(height: 8),
              if (onOpenLiveMatch == null)
                Text(
                  'Live match ${match.liveMatchId}',
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: colors.onSurfaceVariant,
                  ),
                  overflow: TextOverflow.ellipsis,
                )
              else
                Align(
                  alignment: Alignment.centerLeft,
                  child: TextButton.icon(
                    onPressed: () => onOpenLiveMatch!(match.liveMatchId!),
                    icon: const Icon(Icons.live_tv_outlined, size: 18),
                    label: const Text('Open match center'),
                  ),
                ),
            ],
          ],
        ),
      ),
    );
  }
}

class CompeteBracketEmptyState extends StatelessWidget {
  const CompeteBracketEmptyState.blocked({
    super.key,
    required this.title,
    required this.message,
    this.details = const <String>[],
  }) : kind = CompeteBracketEmptyStateKind.blocked;

  const CompeteBracketEmptyState.degraded({
    super.key,
    required this.title,
    required this.message,
    this.details = const <String>[],
  }) : kind = CompeteBracketEmptyStateKind.degraded;

  final CompeteBracketEmptyStateKind kind;
  final String title;
  final String message;
  final List<String> details;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final ColorScheme colors = theme.colorScheme;
    final bool blocked = kind == CompeteBracketEmptyStateKind.blocked;
    return Padding(
      padding: const EdgeInsets.all(16),
      child: DecoratedBox(
        decoration: BoxDecoration(
          border: Border.all(
            color: blocked ? colors.error : colors.outlineVariant,
          ),
          borderRadius: BorderRadius.circular(8),
          color:
              blocked
                  ? colors.errorContainer.withValues(alpha: 0.24)
                  : colors.surfaceContainerHighest,
        ),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Icon(
                blocked ? Icons.lock_outline : Icons.warning_amber_outlined,
                color: blocked ? colors.error : colors.secondary,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      title,
                      style: theme.textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(message, style: theme.textTheme.bodyMedium),
                    if (details.isNotEmpty) ...<Widget>[
                      const SizedBox(height: 8),
                      Text(
                        details.join(' | '),
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: colors.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _BracketSideRow extends StatelessWidget {
  const _BracketSideRow({
    required this.side,
    required this.score,
    required this.winnerParticipantId,
  });

  final CompetitionBracketSide side;
  final int? score;
  final String? winnerParticipantId;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final ColorScheme colors = theme.colorScheme;
    final bool winner =
        winnerParticipantId != null &&
        (side.participantId == winnerParticipantId ||
            side.clubId == winnerParticipantId);
    return Row(
      children: <Widget>[
        if (side.seed != null)
          Padding(
            padding: const EdgeInsets.only(right: 8),
            child: Text(
              '#${side.seed}',
              style: theme.textTheme.bodySmall?.copyWith(
                color: colors.onSurfaceVariant,
              ),
            ),
          ),
        Expanded(
          child: Text(
            side.displayName,
            style: theme.textTheme.bodyMedium?.copyWith(
              fontWeight: winner ? FontWeight.w700 : FontWeight.w500,
              color: side.hasPayload ? null : colors.onSurfaceVariant,
              fontStyle: side.hasPayload ? null : FontStyle.italic,
            ),
            overflow: TextOverflow.ellipsis,
          ),
        ),
        const SizedBox(width: 8),
        Text(
          score?.toString() ?? '-',
          style: theme.textTheme.titleSmall?.copyWith(
            fontWeight: FontWeight.w700,
          ),
        ),
      ],
    );
  }
}

class _InlineDegradedState extends StatelessWidget {
  const _InlineDegradedState({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final ColorScheme colors = theme.colorScheme;
    return DecoratedBox(
      decoration: BoxDecoration(
        border: Border.all(color: colors.outlineVariant),
        borderRadius: BorderRadius.circular(8),
        color: colors.surfaceContainerHighest,
      ),
      child: Padding(
        padding: const EdgeInsets.all(10),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Icon(
              Icons.warning_amber_outlined,
              size: 18,
              color: colors.secondary,
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                message,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: colors.onSurfaceVariant,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({
    required this.label,
    this.isLive = false,
    this.isBlocked = false,
  });

  final String label;
  final bool isLive;
  final bool isBlocked;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final ColorScheme colors = theme.colorScheme;
    final Color background =
        isBlocked
            ? colors.errorContainer
            : isLive
            ? colors.primaryContainer
            : colors.secondaryContainer;
    final Color foreground =
        isBlocked
            ? colors.onErrorContainer
            : isLive
            ? colors.onPrimaryContainer
            : colors.onSecondaryContainer;
    return DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: background,
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        child: Text(
          label,
          style: theme.textTheme.labelSmall?.copyWith(
            color: foreground,
            fontWeight: FontWeight.w700,
          ),
          overflow: TextOverflow.ellipsis,
        ),
      ),
    );
  }
}

bool _notBlank(String? value) => value != null && value.trim().isNotEmpty;
