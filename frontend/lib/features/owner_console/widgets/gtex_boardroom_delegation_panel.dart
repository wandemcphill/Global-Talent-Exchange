import 'package:flutter/material.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

/// Boardroom Facilities & Flagged Delegation UI (Master Plan Document H3, H9 & Phase F1).
///
/// Renders:
/// - Truthful feature-flagged state when `club_legacy` (`clubLegacyEnabled`) is off.
/// - Executive delegation policies (`GtexPolicyChip`), `"Who acts next"` banner,
///   GM requirement status, preset controls, and staff recommendations with
///   over-cap blocked diagnostics when `clubLegacyEnabled` is on.
/// - Club facilities (`stadium`, `training`, `academy`, `medical`) with
///   consequential `GtexConfirmSheet` confirmation and global broadcast notice (`H9`).
class GtexBoardroomDelegationPanel extends StatefulWidget {
  const GtexBoardroomDelegationPanel({
    super.key,
    this.clubLegacyEnabled = false,
    this.gmHired = false,
    this.policies = const <Map<String, dynamic>>[],
    this.recommendations = const <Map<String, dynamic>>[],
    this.facilities = const <Map<String, dynamic>>[],
    this.onApplyPreset,
    this.onUpdateTaskPolicy,
    this.onExecuteRecommendation,
    this.onUpgradeFacility,
  });

  final bool clubLegacyEnabled;
  final bool gmHired;
  final List<Map<String, dynamic>> policies;
  final List<Map<String, dynamic>> recommendations;
  final List<Map<String, dynamic>> facilities;
  final Future<void> Function(String preset)? onApplyPreset;
  final Future<void> Function(String taskKey, String mode, {num? capAmount})?
  onUpdateTaskPolicy;
  final Future<void> Function(String recommendationId, {String? idempotencyKey})?
  onExecuteRecommendation;
  final Future<void> Function(String facilityKind, {String? idempotencyKey})?
  onUpgradeFacility;

  static const String facilityBroadcastNotice =
      'Facility upgrades debit the club ledger and publish a global infrastructure broadcast and newsroom article.';

  static const List<Map<String, dynamic>> defaultFacilities =
      <Map<String, dynamic>>[
        <String, dynamic>{
          'kind': 'stadium',
          'label': 'Stadium Infrastructure',
          'level': 1,
          'next_cost': 5000,
          'effect': 'Higher gate receipts and fan growth.',
        },
        <String, dynamic>{
          'kind': 'training',
          'label': 'Training Complex',
          'level': 1,
          'next_cost': 5000,
          'effect': 'Faster growth for every player and regen.',
        },
        <String, dynamic>{
          'kind': 'academy',
          'label': 'Youth Academy',
          'level': 1,
          'next_cost': 5000,
          'effect': 'Bigger and higher-potential academy intakes.',
        },
        <String, dynamic>{
          'kind': 'medical',
          'label': 'Medical Performance Center',
          'level': 1,
          'next_cost': 5000,
          'effect': 'Shorter injuries and matchday fitness boost.',
        },
      ];

  @override
  State<GtexBoardroomDelegationPanel> createState() =>
      _GtexBoardroomDelegationPanelState();
}

class _GtexBoardroomDelegationPanelState
    extends State<GtexBoardroomDelegationPanel> {
  final Set<String> _busyKeys = <String>{};

  List<Map<String, dynamic>> get _effectiveFacilities =>
      widget.facilities.isEmpty
          ? GtexBoardroomDelegationPanel.defaultFacilities
          : widget.facilities;

  String _resolveWhoActsNextSummary() {
    final int blockedCount =
        widget.recommendations
            .where(
              (Map<String, dynamic> r) =>
                  '${r['status'] ?? ''}'.trim().toLowerCase() == 'blocked',
            )
            .length;
    final int recommendedCount =
        widget.recommendations
            .where((Map<String, dynamic> r) {
              final String s = '${r['status'] ?? ''}'.trim().toLowerCase();
              return s == 'recommended' || s == 'open';
            })
            .length;

    if (blockedCount > 0) {
      return 'Who acts next: Owner approval required ($blockedCount over-cap recommendation${blockedCount == 1 ? '' : 's'} blocked)';
    }
    if (recommendedCount > 0) {
      return 'Who acts next: Owner review ready ($recommendedCount staff recommendation${recommendedCount == 1 ? '' : 's'} awaiting execution)';
    }
    final bool anyAutomatic = widget.policies.any((Map<String, dynamic> p) {
      final String mode = '${p['mode'] ?? ''}'.trim().toLowerCase();
      return mode == 'automatic' || mode == 'auto' || mode == 'executive_led';
    });
    if (anyAutomatic) {
      return 'Who acts next: Executive staff operating within automatic delegation caps';
    }
    return 'Who acts next: Owner retains direct boardroom authority';
  }

  Future<void> _applyPreset(String preset) async {
    final String lockKey = 'preset:$preset';
    if (_busyKeys.contains(lockKey) || widget.onApplyPreset == null) {
      return;
    }
    setState(() => _busyKeys.add(lockKey));
    try {
      await widget.onApplyPreset!(preset);
    } finally {
      if (mounted) {
        setState(() => _busyKeys.remove(lockKey));
      } else {
        _busyKeys.remove(lockKey);
      }
    }
  }

  Future<void> _executeRecommendation(Map<String, dynamic> rec) async {
    final String recId = '${rec['id'] ?? ''}';
    final String lockKey = 'rec:$recId';
    if (recId.isEmpty ||
        _busyKeys.contains(lockKey) ||
        widget.onExecuteRecommendation == null) {
      return;
    }
    setState(() => _busyKeys.add(lockKey));
    try {
      await widget.onExecuteRecommendation!(
        recId,
        idempotencyKey: 'rec-exec-$recId',
      );
    } finally {
      if (mounted) {
        setState(() => _busyKeys.remove(lockKey));
      } else {
        _busyKeys.remove(lockKey);
      }
    }
  }

  Future<void> _promptUpgradeFacility(Map<String, dynamic> facility) async {
    final String kind = '${facility['kind'] ?? 'stadium'}';
    final String label = '${facility['label'] ?? kind.toUpperCase()}';
    final int level =
        facility['level'] is num
            ? (facility['level'] as num).toInt()
            : int.tryParse('${facility['level'] ?? 1}') ?? 1;
    final Object? rawNextCost = facility['next_cost'] ?? facility['cost'];
    final num nextCost =
        rawNextCost is num
            ? rawNextCost
            : num.tryParse('${rawNextCost ?? 5000}') ?? 5000;
    final String costLabel = nextCost.toStringAsFixed(
      nextCost % 1 == 0 ? 0 : 2,
    );
    final String idempotencyKey = 'facility:$kind:lv${level + 1}';

    await GtexConfirmSheet.show(
      context,
      title: 'Upgrade $label to Level ${level + 1}',
      summary:
          '${facility['effect'] ?? 'Enhances club infrastructure and long-term performance.'}',
      confirmLabel: 'Approve Upgrade ($costLabel GTX)',
      variant: GtexConfirmVariant.financial,
      idempotencyKey: idempotencyKey,
      publicAnnouncementNotice:
          GtexBoardroomDelegationPanel.facilityBroadcastNotice,
      financialDetails: GtexConfirmFinancialDetails(
        amountLabel: costLabel,
        currencyCode: 'GTX',
        idempotencyKey: idempotencyKey,
      ),
      onConfirm: (String resolvedKey) async {
        if (widget.onUpgradeFacility != null) {
          await widget.onUpgradeFacility!(kind, idempotencyKey: resolvedKey);
        }
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final GtexColorTokens navy = GtexColors.navy;

    return Container(
      key: const Key('gtex-f1-boardroom-delegation-panel'),
      padding: const EdgeInsets.all(GtexSpacing.md),
      decoration: BoxDecoration(
        color: navy.bgBase,
        borderRadius: BorderRadius.circular(GtexRadius.card),
        border: Border.all(color: navy.lineSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          if (!widget.clubLegacyEnabled)
            const GtexBlockedState(
              key: Key('gtex-f1-delegation-flag-off'),
              title: 'Executive Delegation (Club Legacy)',
              reason:
                  'NPC executive delegation is currently behind the club_legacy launch flag.',
              severity: GtexBlockedSeverity.info,
              icon: Icons.flag_outlined,
            )
          else
            _buildActiveDelegationSection(navy),
          const SizedBox(height: GtexSpacing.md),
          _buildFacilitiesSection(navy),
        ],
      ),
    );
  }

  Widget _buildActiveDelegationSection(GtexColorTokens navy) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        Wrap(
          alignment: WrapAlignment.spaceBetween,
          crossAxisAlignment: WrapCrossAlignment.center,
          spacing: GtexSpacing.sm,
          runSpacing: GtexSpacing.xs,
          children: <Widget>[
            Text(
              'Executive Delegation & Staff Authority',
              style: GtexTypography.titleM(color: navy.textPrimary),
            ),
            Wrap(
              spacing: GtexSpacing.xs,
              runSpacing: GtexSpacing.xs,
              children: <Widget>[
                OutlinedButton(
                  key: const Key('gtex-f1-preset-owner_hands_on'),
                  onPressed:
                      widget.onApplyPreset == null
                          ? null
                          : () => _applyPreset('owner_hands_on'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: navy.textSecondary,
                    side: BorderSide(color: navy.lineSubtle),
                  ),
                  child: const Text('Hands-on'),
                ),
                ElevatedButton(
                  key: const Key('gtex-f1-preset-balanced'),
                  onPressed:
                      widget.onApplyPreset == null
                          ? null
                          : () => _applyPreset('balanced'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: navy.gold500,
                    foregroundColor: navy.textInverse,
                  ),
                  child: const Text('Balanced preset'),
                ),
                OutlinedButton(
                  key: const Key('gtex-f1-preset-executive_led'),
                  onPressed:
                      widget.onApplyPreset == null
                          ? null
                          : () => _applyPreset('executive_led'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: navy.info,
                    side: BorderSide(color: navy.info),
                  ),
                  child: const Text('Executive-led'),
                ),
              ],
            ),
          ],
        ),
        const SizedBox(height: GtexSpacing.sm),
        Container(
          key: const Key('gtex-f1-who-acts-next'),
          padding: const EdgeInsets.all(GtexSpacing.sm),
          decoration: BoxDecoration(
            color: navy.bgRaised,
            borderRadius: BorderRadius.circular(GtexRadius.chip),
            border: Border.all(color: navy.gold500.withValues(alpha: 0.5)),
          ),
          child: Row(
            children: <Widget>[
              Icon(Icons.assignment_ind_rounded, size: 18, color: navy.gold300),
              const SizedBox(width: GtexSpacing.xs),
              Expanded(
                child: Text(
                  _resolveWhoActsNextSummary(),
                  style: GtexTypography.bodyS(color: navy.gold300),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.xs),
        Container(
          key: const Key('gtex-f1-gm-status'),
          padding: const EdgeInsets.all(GtexSpacing.sm),
          decoration: BoxDecoration(
            color: navy.bgInset,
            borderRadius: BorderRadius.circular(GtexRadius.chip),
            border: Border.all(
              color: widget.gmHired ? navy.success : navy.warning,
            ),
          ),
          child: Row(
            children: <Widget>[
              Icon(
                widget.gmHired
                    ? Icons.verified_rounded
                    : Icons.warning_amber_rounded,
                size: 18,
                color: widget.gmHired ? navy.success : navy.warning,
              ),
              const SizedBox(width: GtexSpacing.xs),
              Expanded(
                child: Text(
                  widget.gmHired
                      ? 'General Manager active — pre-season delegation unlocked.'
                      : 'Pre-season delegation tasks require hiring a General Manager (GM).',
                  style: GtexTypography.bodyS(
                    color: widget.gmHired ? navy.textPrimary : navy.warning,
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.sm),
        for (final Map<String, dynamic> policy in widget.policies) ...<Widget>[
          _buildPolicyRow(policy, navy),
          const SizedBox(height: GtexSpacing.xs),
        ],
        if (widget.recommendations.isNotEmpty) ...<Widget>[
          const SizedBox(height: GtexSpacing.sm),
          Text(
            'Staff Recommendations',
            style: GtexTypography.titleS(color: navy.textPrimary),
          ),
          const SizedBox(height: GtexSpacing.xs),
          for (final Map<String, dynamic> rec
              in widget.recommendations) ...<Widget>[
            _buildRecommendationRow(rec, navy),
            const SizedBox(height: GtexSpacing.xs),
          ],
        ],
      ],
    );
  }

  Widget _buildPolicyRow(Map<String, dynamic> policy, GtexColorTokens navy) {
    final String taskKey = '${policy['task_key'] ?? 'task'}';
    final String label = '${policy['label'] ?? taskKey.replaceAll('_', ' ')}';
    final String mode = '${policy['mode'] ?? 'owner_only'}';
    final Object? rawCap = policy['cap_amount'] ?? policy['cap'];
    final String? capLabel =
        rawCap != null && '$rawCap'.trim().isNotEmpty
            ? '$rawCap GTX'
            : null;

    return Container(
      key: Key('gtex-f1-policy-row-$taskKey'),
      padding: const EdgeInsets.all(GtexSpacing.sm),
      decoration: BoxDecoration(
        color: navy.bgRaised,
        borderRadius: BorderRadius.circular(GtexRadius.card),
        border: Border.all(color: navy.lineSubtle),
      ),
      child: Wrap(
        alignment: WrapAlignment.spaceBetween,
        crossAxisAlignment: WrapCrossAlignment.center,
        spacing: GtexSpacing.sm,
        runSpacing: GtexSpacing.xs,
        children: <Widget>[
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                label,
                style: GtexTypography.titleS(color: navy.textPrimary),
              ),
              if (capLabel != null)
                Text(
                  'Delegation cap: $capLabel',
                  style: GtexTypography.bodyS(color: navy.textSecondary),
                ),
            ],
          ),
          GtexPolicyChip.fromBackendMode(
            mode,
            key: Key('gtex-f1-policy-$taskKey'),
            capLabel: capLabel,
          ),
        ],
      ),
    );
  }

  Widget _buildRecommendationRow(
    Map<String, dynamic> rec,
    GtexColorTokens navy,
  ) {
    final String id = '${rec['id'] ?? ''}';
    final String title =
        '${rec['title'] ?? rec['summary'] ?? rec['task_key'] ?? 'Recommendation'}';
    final String status = '${rec['status'] ?? 'recommended'}'.trim();
    final String normalizedStatus = status.toLowerCase();
    final bool isBlocked = normalizedStatus == 'blocked';
    final bool canExecute =
        normalizedStatus == 'recommended' || normalizedStatus == 'open';
    final Object? amount = rec['amount'] ?? rec['cost'] ?? '0';
    final Object? cap = rec['cap'] ?? rec['cap_amount'] ?? '0';

    return Container(
      key: Key('gtex-f1-rec-$id'),
      padding: const EdgeInsets.all(GtexSpacing.sm),
      decoration: BoxDecoration(
        color: navy.bgRaised,
        borderRadius: BorderRadius.circular(GtexRadius.card),
        border: Border.all(
          color: isBlocked ? navy.danger : navy.lineSubtle,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          Wrap(
            alignment: WrapAlignment.spaceBetween,
            crossAxisAlignment: WrapCrossAlignment.center,
            spacing: GtexSpacing.xs,
            runSpacing: GtexSpacing.xs,
            children: <Widget>[
              Text(
                title,
                style: GtexTypography.titleS(color: navy.textPrimary),
              ),
              GtexStatusChip.fromBackendStatus(
                status,
                key: Key('gtex-f1-rec-status-$id'),
                compact: true,
              ),
            ],
          ),
          if (isBlocked) ...<Widget>[
            const SizedBox(height: GtexSpacing.xs),
            Container(
              key: Key('gtex-f1-rec-blocked-$id'),
              padding: const EdgeInsets.all(GtexSpacing.xs),
              decoration: BoxDecoration(
                color: navy.danger.withValues(alpha: 0.14),
                borderRadius: BorderRadius.circular(GtexRadius.chip),
                border: Border.all(color: navy.danger),
              ),
              child: Text(
                'Blocked over policy cap: $amount GTX exceeds cap of $cap GTX — Owner action required.',
                style: GtexTypography.bodyS(color: navy.danger),
              ),
            ),
          ],
          if (canExecute && widget.onExecuteRecommendation != null) ...<Widget>[
            const SizedBox(height: GtexSpacing.xs),
            Align(
              alignment: Alignment.centerRight,
              child: ElevatedButton(
                key: Key('gtex-f1-rec-exec-$id'),
                onPressed:
                    _busyKeys.contains('rec:$id')
                        ? null
                        : () => _executeRecommendation(rec),
                style: ElevatedButton.styleFrom(
                  backgroundColor: navy.gold500,
                  foregroundColor: navy.textInverse,
                ),
                child: const Text('Execute recommendation'),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildFacilitiesSection(GtexColorTokens navy) {
    return Container(
      key: const Key('gtex-f1-facilities-section'),
      padding: const EdgeInsets.all(GtexSpacing.sm),
      decoration: BoxDecoration(
        color: navy.bgRaised,
        borderRadius: BorderRadius.circular(GtexRadius.card),
        border: Border.all(color: navy.lineSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          Row(
            children: <Widget>[
              Icon(Icons.domain_rounded, size: 18, color: navy.gold500),
              const SizedBox(width: GtexSpacing.xs),
              Expanded(
                child: Text(
                  'Club Facilities & Infrastructure (H9)',
                  style: GtexTypography.titleS(color: navy.textPrimary),
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            'Upgrading stadium, training, academy, or medical facilities debits the club ledger and publishes a global broadcast.',
            style: GtexTypography.bodyS(color: navy.textSecondary),
          ),
          const SizedBox(height: GtexSpacing.sm),
          for (final Map<String, dynamic> facility
              in _effectiveFacilities) ...<Widget>[
            _buildFacilityRow(facility, navy),
            const SizedBox(height: GtexSpacing.xs),
          ],
        ],
      ),
    );
  }

  Widget _buildFacilityRow(
    Map<String, dynamic> facility,
    GtexColorTokens navy,
  ) {
    final String kind = '${facility['kind'] ?? 'stadium'}';
    final String label = '${facility['label'] ?? kind.toUpperCase()}';
    final int level =
        facility['level'] is num
            ? (facility['level'] as num).toInt()
            : int.tryParse('${facility['level'] ?? 1}') ?? 1;
    final Object? nextCost = facility['next_cost'] ?? facility['cost'];
    final bool canUpgrade = level < 5 && nextCost != null;

    return Container(
      key: Key('gtex-f1-facility-$kind'),
      padding: const EdgeInsets.all(GtexSpacing.sm),
      decoration: BoxDecoration(
        color: navy.bgInset,
        borderRadius: BorderRadius.circular(GtexRadius.chip),
        border: Border.all(color: navy.lineSubtle),
      ),
      child: Wrap(
        alignment: WrapAlignment.spaceBetween,
        crossAxisAlignment: WrapCrossAlignment.center,
        spacing: GtexSpacing.sm,
        runSpacing: GtexSpacing.xs,
        children: <Widget>[
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                '$label · Level $level',
                style: GtexTypography.titleS(color: navy.textPrimary),
              ),
              if (facility['effect'] != null)
                Text(
                  '${facility['effect']}',
                  style: GtexTypography.bodyS(color: navy.textSecondary),
                ),
            ],
          ),
          if (canUpgrade)
            ElevatedButton.icon(
              key: Key('gtex-f1-facility-upgrade-$kind'),
              onPressed: () => _promptUpgradeFacility(facility),
              style: ElevatedButton.styleFrom(
                backgroundColor: navy.gold500,
                foregroundColor: navy.textInverse,
              ),
              icon: const Icon(Icons.upgrade_rounded, size: 16),
              label: Text('Upgrade ($nextCost GTX)'),
            )
          else
            GtexStatusChip.fromBackendStatus('completed', compact: true),
        ],
      ),
    );
  }
}
