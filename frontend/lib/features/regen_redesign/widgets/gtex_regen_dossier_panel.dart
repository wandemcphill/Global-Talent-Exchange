import 'package:flutter/material.dart';
import 'package:gte_frontend/features/player_detail/gtex_player_navigator.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

import '../models/gtex_regen_dossier.dart';
import '../models/gtex_regen_living_star.dart';
import '../models/gtex_regen_wire_models.dart';

/// The regen's record: lineage, potential, development, personality, value.
///
/// This is the difference between a database row and a football prospect. It
/// renders only what the backend actually published: every section either has
/// real data or states its own absence, and no section invents a number to
/// fill a gap (Phase 4 contract §P5 / §P6).
class GtexRegenDossierPanel extends StatelessWidget {
  const GtexRegenDossierPanel({
    super.key,
    required this.result,
    this.onRetry,
    this.ownershipActionsBuilder,
  });

  final GtexRegenDossierResult result;
  final VoidCallback? onRetry;

  /// Optional write controls, rendered under the Ownership section. Supplied
  /// by the screen rather than built here so this panel stays a pure view of
  /// the dossier and remains testable without a repository.
  final Widget Function(BuildContext context, GtexRegenDossier dossier)?
  ownershipActionsBuilder;

  @override
  Widget build(BuildContext context) {
    final GtexRegenDossier? dossier = result.dossier;
    if (dossier == null) {
      return _absence(context);
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        _LivingStarSection(dossier: dossier),
        const SizedBox(height: GtexSpacing.md),
        _LineageSection(dossier: dossier),
        const SizedBox(height: GtexSpacing.md),
        _PotentialSection(dossier: dossier),
        const SizedBox(height: GtexSpacing.md),
        _DevelopmentSection(dossier: dossier),
        const SizedBox(height: GtexSpacing.md),
        _PersonalitySection(dossier: dossier),
        const SizedBox(height: GtexSpacing.md),
        _OwnershipSection(dossier: dossier),
        if (ownershipActionsBuilder != null) ...<Widget>[
          const SizedBox(height: GtexSpacing.md),
          ownershipActionsBuilder!(context, dossier),
        ],
        const SizedBox(height: GtexSpacing.md),
        _ValueSection(dossier: dossier),
      ],
    );
  }

  Widget _absence(BuildContext context) {
    final bool transient = result.absence == GtexRegenDossierAbsence.loadFailed;
    return GtexBlockedState(
      title: transient ? 'Dossier unavailable' : 'No published dossier',
      reason: result.message ?? 'This regen has no published dossier.',
      resolution:
          transient
              ? null
              : 'Lineage, personality and development appear once this regen '
                  'has a published profile. National-pool depth regens are '
                  'generated for squad cover and never get one.',
      severity:
          transient ? GtexBlockedSeverity.warning : GtexBlockedSeverity.info,
      icon: transient ? Icons.cloud_off_rounded : Icons.hourglass_empty_rounded,
      ctaLabel: transient ? 'Retry' : null,
      ctaAction: transient ? onRetry : null,
    );
  }
}

/// Living star: voice, mood, archetype, exit ladder, match temperament.
class _LivingStarSection extends StatelessWidget {
  const _LivingStarSection({required this.dossier});

  final GtexRegenDossier dossier;

  @override
  Widget build(BuildContext context) {
    final GtexRegenLivingStar? star = dossier.livingStar;
    if (star == null) {
      return const GtexPanel(
        title: 'Living star',
        accent: GtexColors.accentViolet,
        child: GtexBlockedState(
          compact: true,
          title: 'Voice not published yet',
          reason:
              'Archetype, monologue and exit pressure appear once this regen '
              'has a living-star agency profile.',
          severity: GtexBlockedSeverity.info,
          icon: Icons.record_voice_over_outlined,
        ),
      );
    }

    final Color moodColor = star.moodSeverity >= 3
        ? GtexColors.danger
        : star.moodSeverity == 2
        ? GtexColors.gold
        : star.moodSeverity == 1
        ? GtexColors.cyan
        : GtexColors.mint;

    return GtexPanel(
      title: 'Living star',
      subtitle: '${star.archetypeLabel} · 1 OF 1',
      accent: GtexColors.accentViolet,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            star.archetypeSummary,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: GtexColors.textSecondary,
              height: 1.4,
            ),
          ),
          const SizedBox(height: GtexSpacing.sm),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: <Widget>[
              GtexStatusChip(
                label: star.moodLabel,
                color: moodColor,
                compact: true,
              ),
              GtexStatusChip(
                label: star.exitLabel,
                color:
                    star.exitSeverity >= 2
                        ? GtexColors.danger
                        : GtexColors.gold,
                compact: true,
              ),
              if (star.isUniqueCollectible)
                const GtexStatusChip(
                  label: '1 OF 1',
                  color: GtexColors.gold,
                  compact: true,
                ),
            ],
          ),
          const SizedBox(height: GtexSpacing.md),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(GtexSpacing.sm),
            decoration: BoxDecoration(
              color: GtexColors.surfaceOverlay,
              borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
              border: Border.all(color: GtexColors.surfaceBorder),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  'INNER MONOLOGUE',
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: GtexColors.textTertiary,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.7,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  '"${star.voiceLine}"',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: GtexColors.textPrimary,
                    fontWeight: FontWeight.w700,
                    height: 1.35,
                    fontStyle: FontStyle.italic,
                  ),
                ),
              ],
            ),
          ),
          if (star.promises.isNotEmpty) ...<Widget>[
            const SizedBox(height: GtexSpacing.md),
            Text(
              'Promise memory',
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                color: GtexColors.textPrimary,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: GtexSpacing.xs),
            ...star.promises.take(4).map((GtexRegenPromiseMemory promise) {
              return Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Icon(
                      promise.broken
                          ? Icons.warning_amber_rounded
                          : Icons.handshake_outlined,
                      size: 16,
                      color:
                          promise.broken
                              ? GtexColors.danger
                              : GtexColors.mint,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        promise.statement,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: GtexColors.textSecondary,
                          height: 1.35,
                        ),
                      ),
                    ),
                  ],
                ),
              );
            }),
          ],
          if (star.ownerActions.isNotEmpty) ...<Widget>[
            const SizedBox(height: GtexSpacing.sm),
            Text(
              'Owner levers: ${star.ownerActions.join(' · ')}',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: GtexColors.textTertiary,
                height: 1.35,
              ),
            ),
          ],
          if (star.heirStatus != null &&
              star.heirStatus != 'inactive') ...<Widget>[
            const SizedBox(height: GtexSpacing.sm),
            GtexStatusChip(
              label: 'Heir spark: ${star.heirStatus}',
              color: GtexColors.gold,
              compact: true,
            ),
          ],
          if (star.behaviorBrief.notes.isNotEmpty) ...<Widget>[
            const SizedBox(height: GtexSpacing.sm),
            Text(
              'Match temperament: ${star.behaviorBrief.notes.join(' · ')}',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: GtexColors.textSecondary,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// UNDERSTAND LINEAGE - who this regen descends from, and is that navigable.
class _LineageSection extends StatelessWidget {
  const _LineageSection({required this.dossier});

  final GtexRegenDossier dossier;

  @override
  Widget build(BuildContext context) {
    final RegenLineageDescriptor? lineage = dossier.lineage;
    final List<RegenLineageChainNode> chain = dossier.lineageChain;

    if (lineage == null && chain.isEmpty) {
      return GtexPanel(
        title: 'Lineage',
        accent: GtexColors.gold,
        child: GtexBlockedState(
          compact: true,
          title: 'Starts their own line',
          reason:
              dossier.lineageChainUnavailable
                  ? 'The lineage chain could not be read for this regen.'
                  : 'GTEX has no recorded parent for this regen.',
          severity: GtexBlockedSeverity.info,
          icon: Icons.account_tree_outlined,
        ),
      );
    }

    final String? parentId = dossier.parentPlayerId;
    final VoidCallback? openParent = GtexPlayerNavigator.tapToOpen(
      context,
      parentId,
    );

    return GtexPanel(
      title: 'Lineage',
      subtitle: dossier.generationLabel,
      accent: GtexColors.gold,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          if (lineage != null) ...<Widget>[
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: <Widget>[
                GtexStatusChip(
                  label: dossier.lineageLabel ?? 'Recorded lineage',
                  color: GtexColors.gold,
                ),
                GtexStatusChip(
                  label: '${lineage.lineageTier} lineage',
                  color: GtexColors.purple,
                  compact: true,
                ),
                if (lineage.isOwnerSon)
                  const GtexStatusChip(
                    label: 'Owner son',
                    color: GtexColors.mint,
                    compact: true,
                  ),
                if (lineage.isRealLegendLineage)
                  const GtexStatusChip(
                    label: 'Legend bloodline',
                    color: GtexColors.cyan,
                    compact: true,
                  ),
              ],
            ),
            if ((lineage.narrativeText ?? '').isNotEmpty) ...<Widget>[
              const SizedBox(height: GtexSpacing.sm),
              Text(
                lineage.narrativeText!,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: GtexColors.textSecondary,
                  height: 1.45,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
            const SizedBox(height: GtexSpacing.sm),
            // The relationship is always stated. It is only tappable when the
            // parent is a real player row inside a shell that can open Player
            // Detail - otherwise this would be a control that does nothing.
            if (openParent != null)
              GtexActionButton(
                label: 'Open parent player',
                icon: Icons.open_in_new_rounded,
                accent: GtexColors.gold,
                secondary: true,
                onPressed: openParent,
              )
            else
              Text(
                parentId == null
                    ? 'The parent is recorded as a ${lineage.relatedLegendType} '
                        'reference, not a tradable player, so there is no '
                        'player page to open.'
                    : 'Parent player detail is not reachable from here.',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: GtexColors.textMuted,
                  fontWeight: FontWeight.w600,
                ),
              ),
          ],
          if (chain.isNotEmpty) ...<Widget>[
            const SizedBox(height: GtexSpacing.md),
            Text(
              'Bloodline',
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                color: GtexColors.textSecondary,
                fontWeight: FontWeight.w900,
              ),
            ),
            const SizedBox(height: GtexSpacing.xs),
            ...chain.asMap().entries.map(
              (MapEntry<int, RegenLineageChainNode> entry) =>
                  _LineageNodeRow(node: entry.value, generation: entry.key + 1),
            ),
          ] else if (dossier.lineageChainUnavailable) ...<Widget>[
            const SizedBox(height: GtexSpacing.sm),
            Text(
              'The full bloodline could not be read.',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: GtexColors.textMuted,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _LineageNodeRow extends StatelessWidget {
  const _LineageNodeRow({required this.node, required this.generation});

  final RegenLineageChainNode node;
  final int generation;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: GtexSpacing.xs),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: <Widget>[
          GtexStatusChip(label: 'G$generation', color: GtexColors.gold, compact: true),
          const SizedBox(width: GtexSpacing.sm),
          Expanded(
            child: Text(
              node.displayName,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: GtexColors.text,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
          if (node.legacyTier != null)
            GtexStatusChip(
              label: node.legacyTier!,
              color: GtexColors.purple,
              compact: true,
            ),
        ],
      ),
    );
  }
}

/// EVALUATE POTENTIAL - the scouted band, not a false point estimate.
class _PotentialSection extends StatelessWidget {
  const _PotentialSection({required this.dossier});

  final GtexRegenDossier dossier;

  @override
  Widget build(BuildContext context) {
    final String? potentialBand = dossier.potentialBandLabel;
    final String? currentBand = dossier.currentBandLabel;
    final int? headroom = dossier.growthHeadroom;

    if (potentialBand == null && currentBand == null) {
      return const GtexPanel(
        title: 'Potential',
        accent: GtexColors.purple,
        child: GtexBlockedState(
          compact: true,
          title: 'Not rated',
          reason: 'GTEX has no scouted ability or potential for this regen.',
          severity: GtexBlockedSeverity.info,
          icon: Icons.query_stats_rounded,
        ),
      );
    }

    return GtexPanel(
      title: 'Potential',
      subtitle: 'Scout confidence: ${dossier.scoutConfidenceLabel}',
      accent: GtexColors.purple,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: GtexMetricTile(
                  label: 'Current ability',
                  value: currentBand ?? 'Unknown',
                  accent: GtexColors.cyan,
                ),
              ),
              const SizedBox(width: GtexSpacing.sm),
              Expanded(
                child: GtexMetricTile(
                  label: 'Potential ceiling',
                  value: potentialBand ?? 'Unknown',
                  accent: GtexColors.purple,
                ),
              ),
            ],
          ),
          const SizedBox(height: GtexSpacing.sm),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: <Widget>[
              // A band is a range because scouting is uncertain. Saying so is
              // the point: a single number would imply a precision the
              // backend does not claim.
              if (headroom != null && headroom > 0)
                GtexStatusChip(
                  label: '+$headroom growth headroom',
                  color: GtexColors.mint,
                  compact: true,
                ),
              if (headroom != null && headroom <= 0)
                const GtexStatusChip(
                  label: 'At ceiling',
                  color: GtexColors.textMuted,
                  compact: true,
                ),
              GtexStatusChip(
                label:
                    'Growth curve '
                    '${dossier.profile.growthCurve.toStringAsFixed(2)}',
                color: GtexColors.cyan,
                compact: true,
              ),
              if (dossier.profile.uniquenessScore > 0)
                GtexStatusChip(
                  label:
                      'Uniqueness '
                      '${dossier.profile.uniquenessScore.toStringAsFixed(2)}',
                  color: GtexColors.gold,
                  compact: true,
                ),
            ],
          ),
        ],
      ),
    );
  }
}

/// DEVELOP / TRACK - what has actually happened to this regen.
class _DevelopmentSection extends StatelessWidget {
  const _DevelopmentSection({required this.dossier});

  final GtexRegenDossier dossier;

  @override
  Widget build(BuildContext context) {
    final List<RegenStoryEvent> events = dossier.developmentTimeline;
    final RegenLegacySnapshot? legacy = dossier.legacy;

    return GtexPanel(
      title: 'Development',
      accent: GtexColors.mint,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          if (legacy != null && legacy.hasRecordedCareer)
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: <Widget>[
                GtexStatusChip(
                  label: '${legacy.totalMatches} matches',
                  color: GtexColors.mint,
                  compact: true,
                ),
                GtexStatusChip(
                  label: '${legacy.goals} goals',
                  color: GtexColors.mint,
                  compact: true,
                ),
                GtexStatusChip(
                  label: '${legacy.assists} assists',
                  color: GtexColors.mint,
                  compact: true,
                ),
                if (legacy.trophies > 0)
                  GtexStatusChip(
                    label: '${legacy.trophies} trophies',
                    color: GtexColors.gold,
                    compact: true,
                  ),
                GtexStatusChip(
                  label: legacy.legacyTier,
                  color: GtexColors.purple,
                  compact: true,
                ),
              ],
            )
          else
            // A regen who has not played yet has no record. Drawing zeroes
            // here would read as "played and did nothing", which is a
            // different and false claim.
            const GtexBlockedState(
              compact: true,
              title: 'No recorded matches',
              reason:
                  'This regen has not appeared in a completed GTEX match yet, '
                  'so there is no career record to show.',
              severity: GtexBlockedSeverity.info,
              icon: Icons.sports_soccer_outlined,
            ),
          const SizedBox(height: GtexSpacing.md),
          if (events.isEmpty)
            Text(
              'No development events have been recorded for this regen.',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: GtexColors.textMuted,
                fontWeight: FontWeight.w600,
              ),
            )
          else
            ...events
                .take(6)
                .map((RegenStoryEvent event) => _TimelineRow(event: event)),
        ],
      ),
    );
  }
}

class _TimelineRow extends StatelessWidget {
  const _TimelineRow({required this.event});

  final RegenStoryEvent event;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: GtexSpacing.sm),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const Padding(
            padding: EdgeInsets.only(top: 4),
            child: Icon(
              Icons.circle,
              size: 8,
              color: GtexColors.mint,
            ),
          ),
          const SizedBox(width: GtexSpacing.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  event.title,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: GtexColors.text,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                if (event.summary.isNotEmpty)
                  Text(
                    event.summary,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: GtexColors.textSecondary,
                      height: 1.35,
                    ),
                  ),
                Text(
                  _dateLabel(event.occurredAt),
                  style: theme.textTheme.labelSmall?.copyWith(
                    color: GtexColors.textMuted,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  static String _dateLabel(DateTime value) {
    final DateTime local = value.toLocal();
    final String month = local.month.toString().padLeft(2, '0');
    final String day = local.day.toString().padLeft(2, '0');
    return '${local.year}-$month-$day';
  }
}

/// The personality the backend generated - a prospect, not a stat block.
class _PersonalitySection extends StatelessWidget {
  const _PersonalitySection({required this.dossier});

  final GtexRegenDossier dossier;

  @override
  Widget build(BuildContext context) {
    final RegenPersonality? personality = dossier.personality;
    final RegenOrigin? origin = dossier.origin;

    if (personality == null) {
      return const GtexPanel(
        title: 'Personality',
        accent: GtexColors.cyan,
        child: GtexBlockedState(
          compact: true,
          title: 'Not generated',
          reason: 'GTEX has no personality profile for this regen.',
          severity: GtexBlockedSeverity.info,
          icon: Icons.psychology_outlined,
        ),
      );
    }

    return GtexPanel(
      title: 'Personality',
      subtitle: origin == null ? null : 'From ${origin.placeLabel}',
      accent: GtexColors.cyan,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          if (personality.tags.isNotEmpty) ...<Widget>[
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children:
                  personality.tags
                      .map(
                        (String tag) => GtexStatusChip(
                          label: tag,
                          color: GtexColors.cyan,
                          compact: true,
                        ),
                      )
                      .toList(growable: false),
            ),
            const SizedBox(height: GtexSpacing.md),
          ],
          // Strongest traits first: what makes this regen distinctive is more
          // useful than a fixed alphabetical grid of all fourteen.
          ...personality.rankedTraits
              .take(4)
              .map((MapEntry<String, int> trait) => _TraitBar(trait: trait)),
        ],
      ),
    );
  }
}

class _TraitBar extends StatelessWidget {
  const _TraitBar({required this.trait});

  final MapEntry<String, int> trait;

  @override
  Widget build(BuildContext context) {
    final double fraction = (trait.value.clamp(0, 100)) / 100;
    return Padding(
      padding: const EdgeInsets.only(bottom: GtexSpacing.sm),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Text(
                  trait.key,
                  style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    color: GtexColors.textSecondary,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
              Text(
                '${trait.value}',
                style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  color: GtexColors.text,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: fraction,
              minHeight: 6,
              backgroundColor: GtexColors.panelStrong,
              valueColor: const AlwaysStoppedAnimation<Color>(
                GtexColors.cyan,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// OWN - what the regen is worth, and what is driving that.
class _ValueSection extends StatelessWidget {
  const _ValueSection({required this.dossier});

  final GtexRegenDossier dossier;

  @override
  Widget build(BuildContext context) {
    final RegenValueBreakdown? value = dossier.value;
    if (value == null) {
      return const GtexPanel(
        title: 'Value',
        accent: GtexColors.gold,
        child: GtexBlockedState(
          compact: true,
          title: 'Not valued',
          reason: 'No value snapshot has been calculated for this regen.',
          severity: GtexBlockedSeverity.info,
          icon: Icons.savings_outlined,
        ),
      );
    }

    final List<MapEntry<String, int>> components = value.rankedComponents;
    return GtexPanel(
      title: 'Value',
      subtitle:
          value.calculatedAt == null
              ? null
              : 'Snapshot ${_TimelineRow._dateLabel(value.calculatedAt!)}',
      accent: GtexColors.gold,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          GtexMetricTile(
            label: 'Current value',
            value: '${value.currentValueCoin} coin',
            accent: GtexColors.gold,
          ),
          if (components.isNotEmpty) ...<Widget>[
            const SizedBox(height: GtexSpacing.sm),
            Text(
              'What drives it',
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                color: GtexColors.textSecondary,
                fontWeight: FontWeight.w900,
              ),
            ),
            const SizedBox(height: GtexSpacing.xs),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children:
                  components
                      .map(
                        (MapEntry<String, int> entry) => GtexStatusChip(
                          label: '${entry.key} ${entry.value}',
                          color: GtexColors.gold,
                          compact: true,
                        ),
                      )
                      .toList(growable: false),
            ),
          ],
        ],
      ),
    );
  }
}

/// OWN - the contract situation, and what the regen is agitating for.
///
/// Reads `GET /api/players/{id}/regen`, which the client had never called.
/// The backend deliberately publishes a *count* of competing offers and the
/// floor terms while hiding what rivals actually bid, so that asymmetry is
/// shown as the product rule it is rather than smoothed into a fake number.
class _OwnershipSection extends StatelessWidget {
  const _OwnershipSection({required this.dossier});

  final GtexRegenDossier dossier;

  @override
  Widget build(BuildContext context) {
    final RegenLifecycleState? lifecycle = dossier.lifecycle;
    if (lifecycle == null) {
      return const GtexPanel(
        title: 'Ownership',
        accent: GtexColors.mint,
        child: GtexBlockedState(
          compact: true,
          title: 'No contract situation published',
          reason:
              'GTEX publishes no contract or offer state for this regen yet.',
          severity: GtexBlockedSeverity.info,
          icon: Icons.assignment_outlined,
        ),
      );
    }

    final RegenOfferMarket? market = lifecycle.offerMarket;
    final RegenPressureState? pressure = lifecycle.pressureState;

    return GtexPanel(
      title: 'Ownership',
      subtitle: 'Phase: ${lifecycle.lifecyclePhase}',
      accent: GtexColors.mint,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: <Widget>[
              if (lifecycle.retired)
                const GtexStatusChip(
                  label: 'Retired',
                  color: GtexColors.textMuted,
                  compact: true,
                ),
              if (lifecycle.freeAgent)
                const GtexStatusChip(
                  label: 'Free agent',
                  color: GtexColors.gold,
                  compact: true,
                ),
              if (lifecycle.transferListed)
                const GtexStatusChip(
                  label: 'Transfer listed',
                  color: GtexColors.cyan,
                  compact: true,
                ),
              if (lifecycle.retirementPressure)
                const GtexStatusChip(
                  label: 'Nearing retirement',
                  color: GtexColors.danger,
                  compact: true,
                ),
              if (pressure?.activeTransferRequest ?? false)
                const GtexStatusChip(
                  label: 'Transfer requested',
                  color: GtexColors.danger,
                  compact: true,
                ),
              if (pressure?.refusesNewContract ?? false)
                const GtexStatusChip(
                  label: 'Refusing new terms',
                  color: GtexColors.danger,
                  compact: true,
                ),
              if (pressure?.endOfContractPressure ?? false)
                const GtexStatusChip(
                  label: 'Contract running down',
                  color: GtexColors.gold,
                  compact: true,
                ),
            ],
          ),
          if ((lifecycle.agencyMessage ?? '').isNotEmpty) ...<Widget>[
            const SizedBox(height: GtexSpacing.sm),
            Text(
              lifecycle.agencyMessage!,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: GtexColors.textSecondary,
                height: 1.45,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
          const SizedBox(height: GtexSpacing.md),
          if (market == null)
            Text(
              'No offer market is published for this regen.',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: GtexColors.textMuted,
                fontWeight: FontWeight.w600,
              ),
            )
          else ...<Widget>[
            Row(
              children: <Widget>[
                Expanded(
                  child: GtexMetricTile(
                    label: 'Training fee',
                    value:
                        '${market.trainingFeeGtexCoin.toStringAsFixed(0)} '
                        '${market.feeCurrencyCode ?? 'GTEX'}',
                    accent: GtexColors.gold,
                  ),
                ),
                const SizedBox(width: GtexSpacing.sm),
                Expanded(
                  child: GtexMetricTile(
                    label: 'Minimum salary',
                    value:
                        '${market.minimumSalaryFancoinPerYear.toStringAsFixed(0)} '
                        '${market.salaryCurrencyCode ?? lifecycle.contractCurrency}'
                        '/yr',
                    accent: GtexColors.mint,
                  ),
                ),
              ],
            ),
            const SizedBox(height: GtexSpacing.sm),
            GtexStatusChip(
              label:
                  market.visibleOfferCount == 0
                      ? 'No competing offers'
                      : '${market.visibleOfferCount} competing offer'
                          '${market.visibleOfferCount == 1 ? '' : 's'}',
              color:
                  market.visibleOfferCount == 0
                      ? GtexColors.textMuted
                      : GtexColors.cyan,
              compact: true,
            ),
            if (market.hiddenCompetingSalaryAmounts) ...<Widget>[
              const SizedBox(height: GtexSpacing.xs),
              // Not a gap in the data - a deliberate rule. Saying so stops it
              // reading as missing information.
              Text(
                'Rival bid amounts are hidden by design. You see how many '
                'clubs are in, not what they offered.',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: GtexColors.textMuted,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ],
        ],
      ),
    );
  }
}
