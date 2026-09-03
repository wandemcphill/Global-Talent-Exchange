import 'package:flutter/material.dart';
import 'package:gte_frontend/features/player_detail/gtex_player_navigator.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

import '../models/gtex_regen_wire_models.dart';

/// Shared async board: one loading, empty and error idiom for the three
/// world-level regen surfaces, so none of them invents a different one.
class GtexRegenAsyncBoard<T> extends StatelessWidget {
  const GtexRegenAsyncBoard({
    super.key,
    required this.future,
    required this.emptyTitle,
    required this.emptyMessage,
    required this.builder,
    required this.accent,
    this.onRetry,
  });

  final Future<List<T>> future;
  final String emptyTitle;
  final String emptyMessage;
  final Widget Function(BuildContext context, List<T> items) builder;
  final Color accent;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<T>>(
      future: future,
      builder: (BuildContext context, AsyncSnapshot<List<T>> snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return Padding(
            padding: const EdgeInsets.all(GtexSpacing.md),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: const <Widget>[
                GtexSkeleton.box(height: 84),
                SizedBox(height: GtexSpacing.sm),
                GtexSkeleton.box(height: 84),
                SizedBox(height: GtexSpacing.sm),
                GtexSkeleton.box(height: 84),
              ],
            ),
          );
        }
        if (snapshot.hasError) {
          return Padding(
            padding: const EdgeInsets.all(GtexSpacing.md),
            child: GtexBlockedState(
              title: 'Could not load',
              reason: '${snapshot.error}',
              severity: GtexBlockedSeverity.warning,
              icon: Icons.cloud_off_rounded,
              ctaLabel: onRetry == null ? null : 'Retry',
              ctaAction: onRetry,
            ),
          );
        }
        final List<T> items = snapshot.data ?? <T>[];
        if (items.isEmpty) {
          return GtexEmptyState(
            title: emptyTitle,
            message: emptyMessage,
            icon: Icons.auto_awesome,
            accent: accent,
          );
        }
        return builder(context, items);
      },
    );
  }
}

/// UNDERSTAND LINEAGE at world scale: origins and their descendants.
class GtexRegenBloodlinesBoard extends StatelessWidget {
  const GtexRegenBloodlinesBoard({super.key, required this.chains});

  final List<RegenBloodlineChain> chains;

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      padding: const EdgeInsets.all(GtexSpacing.md),
      itemCount: chains.length,
      separatorBuilder:
          (BuildContext _, int __) => const SizedBox(height: GtexSpacing.md),
      itemBuilder: (BuildContext context, int index) {
        final RegenBloodlineChain chain = chains[index];
        return GtexPanel(
          title: chain.originLabel,
          subtitle:
              '${chain.entries.length} descendant'
              '${chain.entries.length == 1 ? '' : 's'} - '
              'drift ${chain.driftScore.toStringAsFixed(2)}',
          accent: GtexColors.gold,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children:
                chain.entries
                    .map(
                      (RegenBloodlineMember member) =>
                          _BloodlineMemberRow(member: member),
                    )
                    .toList(growable: false),
          ),
        );
      },
    );
  }
}

class _BloodlineMemberRow extends StatelessWidget {
  const _BloodlineMemberRow({required this.member});

  final RegenBloodlineMember member;

  @override
  Widget build(BuildContext context) {
    final VoidCallback? open = GtexPlayerNavigator.tapToOpen(
      context,
      member.playerId,
    );
    return Padding(
      padding: const EdgeInsets.only(bottom: GtexSpacing.sm),
      child: GtexPanel(
        padding: const EdgeInsets.all(GtexSpacing.sm),
        accent: GtexColors.gold,
        onTap: open,
        child: Row(
          children: <Widget>[
            GtexStatusChip(
              label: 'G${member.generationIndex}',
              color: GtexColors.gold,
              compact: true,
            ),
            const SizedBox(width: GtexSpacing.sm),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    member.displayName,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: GtexColors.text,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  Text(
                    '${member.primaryPosition} - '
                    '${member.currentRating}/${member.potential}',
                    style: const TextStyle(
                      color: GtexColors.textSecondary,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
            if (open != null)
              const Icon(
                Icons.chevron_right_rounded,
                color: GtexColors.textMuted,
              ),
          ],
        ),
      ),
    );
  }
}

/// The live regen leaderboard, straight from `/regen-universe/rankings`.
class GtexRegenRankingsBoard extends StatelessWidget {
  const GtexRegenRankingsBoard({super.key, required this.entries});

  final List<RegenRankingEntry> entries;

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      padding: const EdgeInsets.all(GtexSpacing.md),
      itemCount: entries.length,
      separatorBuilder:
          (BuildContext _, int __) => const SizedBox(height: GtexSpacing.sm),
      itemBuilder: (BuildContext context, int index) {
        final RegenRankingEntry entry = entries[index];
        final VoidCallback? open = GtexPlayerNavigator.tapToOpen(
          context,
          entry.playerId,
        );
        return GtexPanel(
          padding: const EdgeInsets.all(GtexSpacing.sm),
          accent: GtexColors.purple,
          onTap: open,
          child: Row(
            children: <Widget>[
              SizedBox(
                width: 40,
                child: Text(
                  '#${entry.rank}',
                  style: const TextStyle(
                    color: GtexColors.purple,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
              Expanded(
                child: Text(
                  entry.playerName,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: GtexColors.text,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
              GtexStatusChip(
                label: entry.score.toStringAsFixed(1),
                color: GtexColors.purple,
                compact: true,
              ),
              if (open != null)
                const Icon(
                  Icons.chevron_right_rounded,
                  color: GtexColors.textMuted,
                ),
            ],
          ),
        );
      },
    );
  }
}

/// TRACK, at the end of a career: `/regen-universe/hall-of-fame`.
class GtexRegenHallOfFameBoard extends StatelessWidget {
  const GtexRegenHallOfFameBoard({super.key, required this.entries});

  final List<RegenHallOfFameEntry> entries;

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      padding: const EdgeInsets.all(GtexSpacing.md),
      itemCount: entries.length,
      separatorBuilder:
          (BuildContext _, int __) => const SizedBox(height: GtexSpacing.sm),
      itemBuilder: (BuildContext context, int index) {
        final RegenHallOfFameEntry entry = entries[index];
        final VoidCallback? open = GtexPlayerNavigator.tapToOpen(
          context,
          entry.playerId,
        );
        return GtexPanel(
          title: entry.playerName,
          subtitle:
              entry.peakRank == null
                  ? '${entry.seasonsActive} seasons'
                  : '${entry.seasonsActive} seasons - peak #${entry.peakRank}',
          accent: GtexColors.gold,
          onTap: open,
          child: Wrap(
            spacing: 8,
            runSpacing: 8,
            children: <Widget>[
              GtexStatusChip(
                label: '${entry.totalAwards} awards',
                color: GtexColors.gold,
                compact: true,
              ),
              GtexStatusChip(
                label: 'Legacy ${entry.legacyScore.toStringAsFixed(1)}',
                color: GtexColors.purple,
                compact: true,
              ),
            ],
          ),
        );
      },
    );
  }
}
