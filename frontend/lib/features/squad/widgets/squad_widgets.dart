import 'package:flutter/material.dart';

import '../../../core/constants/app_breakpoints.dart';
import '../../../core/constants/app_spacing.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/widgets/gtex_surface_card.dart';
import '../../../shared/state/gtex_async_surface_state.dart';
import '../../../shared/widgets/async_state_widget.dart';
import '../domain/squad_models.dart';
import '../providers/squad_providers.dart';

class SquadStatusPanel extends StatelessWidget {
  const SquadStatusPanel({
    super.key,
    required this.title,
    required this.message,
    required this.icon,
    this.color = AppColors.primary,
  });

  final String title;
  final String message;
  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 680),
        child: GtexSurfaceCard(
          glowColor: color,
          padding: const EdgeInsets.all(spacingLG),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Icon(icon, color: color, size: 34),
              const SizedBox(height: spacingMD),
              Text(title, style: Theme.of(context).textTheme.headlineSmall),
              const SizedBox(height: spacingSM),
              Text(
                message,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class SquadOperationsView extends StatelessWidget {
  const SquadOperationsView({
    super.key,
    required this.snapshot,
    required this.request,
    required this.bottomPadding,
  });

  final SquadOperationsSnapshot snapshot;
  final SquadRequest request;
  final double bottomPadding;

  @override
  Widget build(BuildContext context) {
    final List<String> chemistryWarnings = squadChemistryWarnings(snapshot);
    final List<ContractStatusDTO> contractWarnings = squadContractWarnings(
      snapshot,
    );

    return ListView(
      key: const Key('squad-operations-view'),
      padding: EdgeInsets.only(bottom: bottomPadding),
      children: <Widget>[
        SquadSummaryBar(snapshot: snapshot),
        const SizedBox(height: spacingLG),
        SquadAvailabilityMatrixSection(matrix: snapshot.availabilityMatrix),
        const SizedBox(height: spacingLG),
        _ResponsivePair(
          left: SquadReadinessSection(snapshot: snapshot),
          right: SquadInjurySection(injuries: snapshot.injuries),
        ),
        const SizedBox(height: spacingLG),
        _ResponsivePair(
          left: SquadChemistrySection(warnings: chemistryWarnings),
          right: SquadContractSection(
            contracts:
                request.canViewContracts
                    ? contractWarnings
                    : const <ContractStatusDTO>[],
            blocked: !request.canViewContracts,
          ),
        ),
        const SizedBox(height: spacingLG),
        SquadRosterSection(players: snapshot.roster),
        const SizedBox(height: spacingLG),
        SquadScoutingNotesSection(notes: snapshot.scoutingNotes),
      ],
    );
  }
}

class SquadSummaryBar extends StatelessWidget {
  const SquadSummaryBar({super.key, required this.snapshot});

  final SquadOperationsSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    return GtexSurfaceCard(
      glowColor: AppColors.primary,
      padding: const EdgeInsets.all(spacingLG),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Squad', style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: spacingXS),
          Text(
            'Club Squad Operations',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: spacingMD),
          Wrap(
            spacing: spacingMD,
            runSpacing: spacingMD,
            children: <Widget>[
              _MetricPill(label: 'Players', value: '${snapshot.roster.length}'),
              _MetricPill(
                label: 'Available',
                value: '${snapshot.availableCount}',
                color: AppColors.success,
              ),
              _MetricPill(
                label: 'Injured',
                value: '${snapshot.injuredCount}',
                color: AppColors.danger,
              ),
              _MetricPill(
                label: 'Suspended',
                value: '${snapshot.suspendedCount}',
                color: AppColors.gold,
              ),
              _MetricPill(
                label: 'Selection Ready',
                value: '${snapshot.selectionReadyCount}',
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class SquadAvailabilityMatrixSection extends StatelessWidget {
  const SquadAvailabilityMatrixSection({super.key, required this.matrix});

  final AvailabilityMatrix matrix;

  @override
  Widget build(BuildContext context) {
    return _SectionCard(
      title: 'Availability Matrix',
      child: AsyncStateWidget<AvailabilityMatrix>(
        state: squadAvailabilityMatrixSurfaceState(matrix),
        onLoading: () => const _InlineState(message: 'Loading availability...'),
        onEmpty:
            (String? reason) => _InlineState(
              key: const Key('squad-empty-availability-matrix'),
              message: reason ?? 'Availability matrix is empty.',
            ),
        onBlocked:
            (String reason, String? ctaRoute) =>
                _InlineState(message: reason, color: AppColors.danger),
        onPending:
            (AvailabilityMatrix? stale) => const _InlineState(
              message: 'Availability update pending backend confirmation.',
            ),
        onSyncing: _AvailabilityGrid.new,
        onReconnecting:
            (AvailabilityMatrix? lastKnown, int attempt) =>
                lastKnown == null
                    ? _InlineState(
                      message: 'Reconnecting availability: $attempt',
                    )
                    : _AvailabilityGrid(lastKnown),
        onDegraded:
            (AvailabilityMatrix current, String warning) =>
                _AvailabilityGrid(current),
        onConfirmed:
            (AvailabilityMatrix data, String? auditRef) =>
                _AvailabilityGrid(data),
        onError:
            (String code, String message, VoidCallback retry) => _InlineState(
              message: '$code: $message',
              color: AppColors.danger,
            ),
        onData: _AvailabilityGrid.new,
      ),
    );
  }
}

class SquadRosterSection extends StatelessWidget {
  const SquadRosterSection({super.key, required this.players});

  final List<SquadPlayerDTO> players;

  @override
  Widget build(BuildContext context) {
    return _SectionCard(
      title: 'Roster',
      child:
          players.isEmpty
              ? const _InlineState(message: 'No players in squad.')
              : Column(
                children: players
                    .map(
                      (SquadPlayerDTO player) => SquadPlayerRow(player: player),
                    )
                    .toList(growable: false),
              ),
    );
  }
}

class SquadPlayerRow extends StatelessWidget {
  const SquadPlayerRow({super.key, required this.player});

  final SquadPlayerDTO player;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: spacingSM),
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: AppColors.surfaceMuted.withValues(alpha: 0.58),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.divider),
        ),
        child: Padding(
          padding: const EdgeInsets.all(spacingMD),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(
                children: <Widget>[
                  Expanded(
                    child: Text(
                      player.name,
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                  ),
                  const SizedBox(width: spacingSM),
                  _StatusBadge(
                    label: player.availability.label,
                    color: _availabilityColor(player.availability),
                  ),
                ],
              ),
              const SizedBox(height: spacingSM),
              Wrap(
                spacing: spacingSM,
                runSpacing: spacingSM,
                children: <Widget>[
                  _SmallBadge(label: player.position),
                  _SmallBadge(label: 'Morale ${player.morale.score}'),
                  _SmallBadge(
                    label: 'Chemistry ${player.chemistryFit.overallScore}',
                  ),
                  _SmallBadge(
                    label:
                        player.selectionReady ? 'Selection ready' : 'Not ready',
                    color:
                        player.selectionReady
                            ? AppColors.success
                            : AppColors.gold,
                  ),
                  if (player.contractStatus.isRenewalRisk)
                    _SmallBadge(
                      key: Key('contract-renewal-risk-${player.id}'),
                      label: 'Renewal risk <26 weeks',
                      color: AppColors.danger,
                    ),
                ],
              ),
              if (player.chemistryFit.warnings.isNotEmpty) ...<Widget>[
                const SizedBox(height: spacingSM),
                ...player.chemistryFit.warnings.map(
                  (String warning) => Text('Chemistry warning: $warning'),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class SquadReadinessSection extends StatelessWidget {
  const SquadReadinessSection({super.key, required this.snapshot});

  final SquadOperationsSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    return _SectionCard(
      title: 'Readiness',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          _InfoRow(
            label: 'Selection ready',
            value: '${snapshot.selectionReadyCount}',
          ),
          _InfoRow(label: 'Available', value: '${snapshot.availableCount}'),
          _InfoRow(label: 'Injured', value: '${snapshot.injuredCount}'),
          _InfoRow(label: 'Suspended', value: '${snapshot.suspendedCount}'),
        ],
      ),
    );
  }
}

class SquadInjurySection extends StatelessWidget {
  const SquadInjurySection({super.key, required this.injuries});

  final List<InjuryDTO> injuries;

  @override
  Widget build(BuildContext context) {
    return _SectionCard(
      title: 'Injuries',
      child:
          injuries.isEmpty
              ? const _InlineState(message: 'No backend injuries reported.')
              : Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: injuries
                    .map(
                      (InjuryDTO injury) => _ListTileLine(
                        title: injury.playerName ?? injury.playerId ?? 'Player',
                        subtitle: <String?>[
                          injury.type,
                          injury.severity,
                          dateLabel(injury.expectedReturn),
                        ].whereType<String>().join(' | '),
                      ),
                    )
                    .toList(growable: false),
              ),
    );
  }
}

class SquadChemistrySection extends StatelessWidget {
  const SquadChemistrySection({super.key, required this.warnings});

  final List<String> warnings;

  @override
  Widget build(BuildContext context) {
    return _SectionCard(
      title: 'Chemistry',
      child:
          warnings.isEmpty
              ? const _InlineState(
                message: 'No chemistry warnings from backend.',
              )
              : Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: warnings
                    .map(
                      (String warning) => _InlineState(
                        message: 'Chemistry warning: $warning',
                        color: AppColors.gold,
                      ),
                    )
                    .toList(growable: false),
              ),
    );
  }
}

class SquadContractSection extends StatelessWidget {
  const SquadContractSection({
    super.key,
    required this.contracts,
    required this.blocked,
  });

  final List<ContractStatusDTO> contracts;
  final bool blocked;

  @override
  Widget build(BuildContext context) {
    return _SectionCard(
      title: 'Contracts',
      child:
          blocked
              ? const _InlineState(
                message: 'Contract management is restricted to club owners.',
                color: AppColors.danger,
                icon: Icons.lock_rounded,
              )
              : contracts.isEmpty
              ? const _InlineState(message: 'No contract warnings.')
              : Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: contracts
                    .map(
                      (ContractStatusDTO contract) => _ListTileLine(
                        title:
                            contract.playerName ??
                            contract.playerId ??
                            'Contract',
                        subtitle: <String>[
                          'Renewal risk <26 weeks',
                          if (contract.weeksRemaining != null)
                            '${contract.weeksRemaining} weeks remaining',
                          if (contract.status != null) contract.status!,
                        ].join(' | '),
                      ),
                    )
                    .toList(growable: false),
              ),
    );
  }
}

class SquadScoutingNotesSection extends StatelessWidget {
  const SquadScoutingNotesSection({super.key, required this.notes});

  final List<ScoutingNoteDTO> notes;

  @override
  Widget build(BuildContext context) {
    return _SectionCard(
      title: 'Scouting Notes',
      child:
          notes.isEmpty
              ? const _InlineState(message: 'No backend scouting notes yet.')
              : Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: notes
                    .map(
                      (ScoutingNoteDTO note) => _ListTileLine(
                        title: note.content,
                        subtitle: <String?>[
                          note.authorId,
                          dateLabel(note.createdAt),
                          if (note.tags.isNotEmpty) note.tags.join(', '),
                        ].whereType<String>().join(' | '),
                      ),
                    )
                    .toList(growable: false),
              ),
    );
  }
}

class _AvailabilityGrid extends StatelessWidget {
  const _AvailabilityGrid(this.matrix);

  final AvailabilityMatrix matrix;

  @override
  Widget build(BuildContext context) {
    if (matrix.fixtures.isEmpty) {
      return const _InlineState(message: 'Fixture columns backend pending.');
    }

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              const SizedBox(width: 180, child: Text('Player')),
              ...matrix.fixtures.map(
                (AvailabilityFixture fixture) => SizedBox(
                  width: 130,
                  child: Text(fixture.label, overflow: TextOverflow.ellipsis),
                ),
              ),
            ],
          ),
          const SizedBox(height: spacingSM),
          ...matrix.players.map(
            (AvailabilityMatrixPlayer player) => Padding(
              padding: const EdgeInsets.only(bottom: spacingSM),
              child: Row(
                children: <Widget>[
                  SizedBox(
                    width: 180,
                    child: Text('${player.name} (${player.position})'),
                  ),
                  ...matrix.fixtures.map((AvailabilityFixture fixture) {
                    final SquadAvailabilityStatus status = _matrixStatusFor(
                      player,
                      fixture,
                    );
                    return SizedBox(
                      width: 130,
                      child: _StatusBadge(
                        label: status.label,
                        color: _availabilityColor(status),
                      ),
                    );
                  }),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  SquadAvailabilityStatus _matrixStatusFor(
    AvailabilityMatrixPlayer player,
    AvailabilityFixture fixture,
  ) {
    for (final AvailabilityCell cell in matrix.cells) {
      if (cell.playerId == player.playerId &&
          cell.fixtureId == fixture.fixtureId) {
        return cell.status;
      }
    }
    return SquadAvailabilityStatus.unknown;
  }
}

class _ResponsivePair extends StatelessWidget {
  const _ResponsivePair({required this.left, required this.right});

  final Widget left;
  final Widget right;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        if (constraints.maxWidth >= AppBreakpoints.medium) {
          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Expanded(child: left),
              const SizedBox(width: spacingMD),
              Expanded(child: right),
            ],
          );
        }
        return Column(
          children: <Widget>[left, const SizedBox(height: spacingMD), right],
        );
      },
    );
  }
}

class _SectionCard extends StatelessWidget {
  const _SectionCard({required this.title, required this.child});

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return GtexSurfaceCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(title, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: spacingMD),
          child,
        ],
      ),
    );
  }
}

class _MetricPill extends StatelessWidget {
  const _MetricPill({
    required this.label,
    required this.value,
    this.color = AppColors.primary,
  });

  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: spacingMD,
        vertical: spacingSM,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.28)),
      ),
      child: Text('$label: $value'),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: spacingSM,
        vertical: spacingXS,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.11),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.28)),
      ),
      child: Text(label),
    );
  }
}

class _SmallBadge extends StatelessWidget {
  const _SmallBadge({
    super.key,
    required this.label,
    this.color = AppColors.primary,
  });

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return _StatusBadge(label: label, color: color);
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: spacingSM),
      child: Row(
        children: <Widget>[
          Expanded(
            child: Text(
              label,
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
            ),
          ),
          const SizedBox(width: spacingMD),
          Text(value),
        ],
      ),
    );
  }
}

class _ListTileLine extends StatelessWidget {
  const _ListTileLine({required this.title, required this.subtitle});

  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: spacingSM),
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: AppColors.surfaceMuted.withValues(alpha: 0.58),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.divider),
        ),
        child: Padding(
          padding: const EdgeInsets.all(spacingMD),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(title, style: Theme.of(context).textTheme.titleMedium),
              if (subtitle.isNotEmpty) ...<Widget>[
                const SizedBox(height: spacingXS),
                Text(
                  subtitle,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _InlineState extends StatelessWidget {
  const _InlineState({
    super.key,
    required this.message,
    this.color = AppColors.gold,
    this.icon = Icons.info_rounded,
  });

  final String message;
  final Color color;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.09),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.28)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(spacingMD),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Icon(icon, color: color, size: 20),
            const SizedBox(width: spacingSM),
            Expanded(child: Text(message)),
          ],
        ),
      ),
    );
  }
}

Color _availabilityColor(SquadAvailabilityStatus status) {
  return switch (status) {
    SquadAvailabilityStatus.available => AppColors.success,
    SquadAvailabilityStatus.injured => AppColors.danger,
    SquadAvailabilityStatus.suspended => AppColors.gold,
    SquadAvailabilityStatus.away => AppColors.primary,
    SquadAvailabilityStatus.unfit => AppColors.gold,
    SquadAvailabilityStatus.unknown => AppColors.textSecondary,
  };
}

String? dateLabel(DateTime? value) {
  if (value == null) {
    return null;
  }
  final String month = value.month.toString().padLeft(2, '0');
  final String day = value.day.toString().padLeft(2, '0');
  return '${value.year}-$month-$day';
}
