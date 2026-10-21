import 'package:flutter/material.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

import 'club_growth_controller.dart';
import 'club_growth_models.dart';

/// Canonical Staff Hiring / Termination (H7) & Academy Regen Pathway (H6) panel
/// for Phase D1.
class GtexClubGrowthJourneyPanel extends StatefulWidget {
  const GtexClubGrowthJourneyPanel({
    super.key,
    required this.controller,
  });

  final GtexClubGrowthController controller;

  @override
  State<GtexClubGrowthJourneyPanel> createState() =>
      _GtexClubGrowthJourneyPanelState();
}

class _GtexClubGrowthJourneyPanelState
    extends State<GtexClubGrowthJourneyPanel> {
  @override
  void initState() {
    super.initState();
    if (widget.controller.dashboard == null && !widget.controller.loading) {
      widget.controller.load();
    }
  }

  Future<void> _confirmHireStaff(
    BuildContext context,
    GtexStaffProfile staff,
  ) async {
    final String idempotencyKey =
        'hire-staff-${staff.id}-${DateTime.now().microsecondsSinceEpoch}';
    final bool confirmed =
        (await GtexConfirmSheet.show(
          context,
          title: 'Hire ${staff.displayName}',
          summary:
              'Offer and activate a 120-day club staff contract for ${staff.displayName} (${staff.staffType.toUpperCase()}).',
          confirmLabel: 'Confirm Hire',
          variant: GtexConfirmVariant.financial,
          idempotencyKey: idempotencyKey,
          financialDetails: GtexConfirmFinancialDetails(
            amountLabel: '${staff.salaryMinor}',
            currencyCode: 'GTC',
            feeLabel: '${(staff.commissionBps / 100).toStringAsFixed(1)}% comm',
            idempotencyKey: idempotencyKey,
          ),
          onConfirm: (String _) async {
            await widget.controller.hireStaff(staff.id);
          },
        )) ??
        false;
    if (!confirmed || !mounted) {
      return;
    }
  }

  Future<void> _confirmFireStaff(
    BuildContext context,
    GtexStaffContract contract,
  ) async {
    final bool confirmed =
        (await GtexConfirmSheet.show(
          context,
          title: 'Terminate ${contract.staffProfile.displayName}?',
          summary:
              'Terminating an active staff contract immediately removes their club bonuses. This action is irreversible.',
          confirmLabel: 'Terminate Contract',
          variant: GtexConfirmVariant.destructive,
          requireReason: true,
          onConfirm: (String _) async {
            await widget.controller.fireStaff(contract.id);
          },
        )) ??
        false;
    if (!confirmed || !mounted) {
      return;
    }
  }

  @override
  Widget build(BuildContext context) {
    final GtexColorTokens navy = GtexColors.navy;
    return AnimatedBuilder(
      animation: widget.controller,
      builder: (BuildContext context, _) {
        final GtexClubGrowthDashboard? dash = widget.controller.dashboard;
        if (dash == null && widget.controller.loading) {
          return const Center(child: CircularProgressIndicator());
        }
        if (dash == null) {
          return GtexEmptyState(
            title: 'Club growth unavailable',
            message:
                widget.controller.error ??
                'Unable to load staff and academy growth dashboard.',
            icon: Icons.school_outlined,
            actionLabel: 'Retry',
            onAction: widget.controller.load,
          );
        }

        return Column(
          key: const Key('gtex-d1-growth-journey-panel'),
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            GtexPanel(
              key: const Key('gtex-d1-staff-panel'),
              title: 'Staff & Recruitment Desk (H7)',
              subtitle:
                  'Active staff: ${dash.activeStaffCount} · Scout quality +${dash.staffEffects['scout_quality'] ?? 0} · Negotiation +${dash.staffEffects['negotiation_bonus'] ?? 0}',
              accent: navy.gold500,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  for (final GtexStaffProfile staff in dash.staffMarket)
                    Container(
                      key: Key('gtex-d1-staff-card-${staff.id}'),
                      margin: const EdgeInsets.only(bottom: GtexSpacing.sm),
                      padding: const EdgeInsets.all(GtexSpacing.sm),
                      decoration: BoxDecoration(
                        color: navy.bgInset,
                        borderRadius: BorderRadius.circular(GtexRadius.card),
                        border: Border.all(color: navy.lineSubtle),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Row(
                            children: <Widget>[
                              Expanded(
                                child: Text(
                                  '${staff.displayName} · ${staff.staffType.toUpperCase()}',
                                  style: GtexTypography.titleM(
                                    color: navy.textPrimary,
                                  ),
                                ),
                              ),
                              GtexStatusChip(
                                label: 'Rating ${staff.rating}',
                                color: navy.gold500,
                                compact: true,
                              ),
                            ],
                          ),
                          const SizedBox(height: GtexSpacing.xxs),
                          Text(
                            'Skills: ${staff.skills.join(', ')} · Salary ${staff.salaryMinor} minor · Commission ${(staff.commissionBps / 100).toStringAsFixed(1)}%',
                            style: GtexTypography.bodyS(
                              color: navy.textSecondary,
                            ),
                          ),
                          if (staff.suitabilityLabel != null ||
                              staff.personalityLabel != null ||
                              staff.reputationLabel != null) ...<Widget>[
                            const SizedBox(height: GtexSpacing.xs),
                            Wrap(
                              spacing: GtexSpacing.xs,
                              runSpacing: GtexSpacing.xs,
                              children: <Widget>[
                                if (staff.suitabilityLabel != null)
                                  GtexStatusChip(
                                    key: Key(
                                      'gtex-d1-staff-suitability-${staff.id}',
                                    ),
                                    label:
                                        'Suitability: ${staff.suitabilityLabel}',
                                    color: navy.info,
                                    compact: true,
                                  ),
                                if (staff.personalityLabel != null)
                                  GtexStatusChip(
                                    key: Key(
                                      'gtex-d1-staff-personality-${staff.id}',
                                    ),
                                    label:
                                        'Personality: ${staff.personalityLabel}',
                                    color: navy.info,
                                    compact: true,
                                  ),
                                if (staff.reputationLabel != null)
                                  GtexStatusChip(
                                    key: Key(
                                      'gtex-d1-staff-reputation-${staff.id}',
                                    ),
                                    label:
                                        'Reputation: ${staff.reputationLabel}',
                                    color: navy.gold300,
                                    compact: true,
                                  ),
                              ],
                            ),
                          ],
                          const SizedBox(height: GtexSpacing.xs),
                          GtexActionButton(
                            key: Key('gtex-d1-hire-staff-${staff.id}'),
                            label: 'Hire ${staff.displayName}',
                            icon: Icons.person_add_alt_1_outlined,
                            compact: true,
                            accent: navy.gold500,
                            onPressed:
                                widget.controller.busy
                                    ? null
                                    : () => _confirmHireStaff(context, staff),
                          ),
                        ],
                      ),
                    ),
                  if (dash.staffContracts.isNotEmpty) ...<Widget>[
                    const SizedBox(height: GtexSpacing.sm),
                    Text(
                      'Staff Contracts',
                      style: GtexTypography.titleM(color: navy.textPrimary),
                    ),
                    const SizedBox(height: GtexSpacing.xs),
                    for (final GtexStaffContract contract
                        in dash.staffContracts)
                      Container(
                        key: Key('gtex-d1-contract-${contract.id}'),
                        margin: const EdgeInsets.only(bottom: GtexSpacing.xs),
                        padding: const EdgeInsets.all(GtexSpacing.sm),
                        decoration: BoxDecoration(
                          color: navy.bgRaised,
                          borderRadius: BorderRadius.circular(GtexRadius.card),
                          border: Border.all(color: navy.lineSubtle),
                        ),
                        child: Row(
                          children: <Widget>[
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: <Widget>[
                                  Text(
                                    contract.staffProfile.displayName,
                                    style: GtexTypography.body(
                                      color: navy.textPrimary,
                                    ),
                                  ),
                                  Text(
                                    '${contract.roleScope.toUpperCase()} · ${contract.durationDays}d',
                                    style: GtexTypography.bodyS(
                                      color: navy.textSecondary,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            GtexStatusChip.fromBackendStatus(
                              contract.status,
                              compact: true,
                            ),
                            if (contract.active) ...<Widget>[
                              const SizedBox(width: GtexSpacing.xs),
                              GtexActionButton(
                                key: Key('gtex-d1-fire-staff-${contract.id}'),
                                label: 'Fire',
                                icon: Icons.person_remove_outlined,
                                compact: true,
                                secondary: true,
                                accent: navy.danger,
                                onPressed:
                                    widget.controller.busy
                                        ? null
                                        : () => _confirmFireStaff(
                                          context,
                                          contract,
                                        ),
                              ),
                            ],
                          ],
                        ),
                      ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: GtexSpacing.md),
            GtexPanel(
              key: const Key('gtex-d1-academy-panel'),
              title: 'Academy Regen Pathway (H6)',
              subtitle:
                  'Academy Level ${dash.academyProfile.level} · ${dash.academyProspects.length} prospects · Server-verified regen portraits',
              accent: navy.info,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  GtexActionButton(
                    key: const Key('gtex-d1-generate-prospects-btn'),
                    label: 'Generate Intake Prospects',
                    icon: Icons.auto_awesome_outlined,
                    accent: navy.info,
                    onPressed:
                        widget.controller.busy
                            ? null
                            : widget.controller.generateProspects,
                  ),
                  const SizedBox(height: GtexSpacing.sm),
                  if (dash.academyProspects.isEmpty)
                    Text(
                      'No academy prospects generated yet. Trigger an intake to scout youth regens.',
                      style: GtexTypography.bodyS(color: navy.textSecondary),
                    ),
                  for (final GtexAcademyProspect prospect
                      in dash.academyProspects)
                    Container(
                      key: Key('gtex-d1-prospect-${prospect.id}'),
                      margin: const EdgeInsets.only(bottom: GtexSpacing.sm),
                      padding: const EdgeInsets.all(GtexSpacing.sm),
                      decoration: BoxDecoration(
                        color: navy.bgInset,
                        borderRadius: BorderRadius.circular(GtexRadius.card),
                        border: Border.all(color: navy.lineSubtle),
                      ),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          GtexPortrait(
                            key: Key('gtex-d1-prospect-portrait-${prospect.id}'),
                            portraitUrl: prospect.resolvedPortraitUrl,
                            seed: prospect.id,
                            position: prospect.position,
                            nationalityCode: prospect.nationality ?? 'NG',
                            playerName: prospect.displayName,
                            size: GtexPortraitSize.sm48,
                          ),
                          const SizedBox(width: GtexSpacing.sm),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: <Widget>[
                                Row(
                                  children: <Widget>[
                                    Expanded(
                                      child: Text(
                                        '${prospect.displayName} (${prospect.position})',
                                        style: GtexTypography.titleM(
                                          color: navy.textPrimary,
                                        ),
                                      ),
                                    ),
                                    GtexStatusChip.fromBackendStatus(
                                      prospect.status,
                                      compact: true,
                                    ),
                                  ],
                                ),
                                const SizedBox(height: GtexSpacing.xxs),
                                Text(
                                  'Age ${prospect.age} · OVR ${prospect.currentAbility} · POT ${prospect.potential} · Portrait: ${prospect.resolvedPortraitUrl ?? 'pending'}',
                                  key: Key(
                                    'gtex-d1-prospect-meta-${prospect.id}',
                                  ),
                                  style: GtexTypography.bodyS(
                                    color: navy.textSecondary,
                                  ),
                                ),
                                const SizedBox(height: GtexSpacing.xs),
                                Wrap(
                                  spacing: GtexSpacing.xs,
                                  runSpacing: GtexSpacing.xs,
                                  children: <Widget>[
                                    if (prospect.contractEligible)
                                      GtexActionButton(
                                        key: Key(
                                          'gtex-d1-offer-prospect-${prospect.id}',
                                        ),
                                        label: 'Offer Youth Contract',
                                        compact: true,
                                        accent: navy.gold500,
                                        onPressed:
                                            widget.controller.busy
                                                ? null
                                                : () => widget.controller
                                                    .offerAndAcceptProspectContract(
                                                      prospect.id,
                                                    ),
                                      ),
                                    if (prospect.promotable)
                                      GtexActionButton(
                                        key: Key(
                                          'gtex-d1-promote-prospect-${prospect.id}',
                                        ),
                                        label: 'Promote to Senior Squad',
                                        compact: true,
                                        accent: navy.success,
                                        onPressed:
                                            widget.controller.busy
                                                ? null
                                                : () => widget.controller
                                                    .promoteProspect(
                                                      prospect.id,
                                                    ),
                                      ),
                                    if (prospect.promoted)
                                      GtexStatusChip(
                                        key: Key(
                                          'gtex-d1-promoted-badge-${prospect.id}',
                                        ),
                                        label:
                                            'Senior Squad · ${prospect.seniorPlayerId ?? prospect.id}',
                                        color: navy.success,
                                        compact: true,
                                      ),
                                  ],
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                ],
              ),
            ),
          ],
        );
      },
    );
  }
}
