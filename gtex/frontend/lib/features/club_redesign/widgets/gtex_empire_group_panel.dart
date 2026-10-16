import 'package:flutter/material.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

/// Thin empire / ownership-group surface: shared budgets + sister-club count.
class GtexEmpireGroupPanel extends StatelessWidget {
  const GtexEmpireGroupPanel({
    super.key,
    required this.groups,
    this.isLoading = false,
    this.errorMessage,
    this.onRetry,
  });

  final List<GtexEmpireGroupSummary> groups;
  final bool isLoading;
  final String? errorMessage;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return GtexPanel(
      title: 'Ownership groups',
      subtitle:
          'Sister clubs share budget pools. Competitions flag same-group fixtures.',
      accent: GtexColors.gold,
      child: _body(context),
    );
  }

  Widget _body(BuildContext context) {
    if (errorMessage != null && groups.isEmpty) {
      return GtexBlockedState(
        compact: true,
        title: 'Empire groups unavailable',
        reason: errorMessage!,
        severity: GtexBlockedSeverity.error,
        ctaLabel: onRetry == null ? null : 'Retry',
        ctaAction: onRetry,
      );
    }
    if (isLoading && groups.isEmpty) {
      return const LinearProgressIndicator();
    }
    if (groups.isEmpty) {
      return const GtexEmptyState(
        title: 'No ownership group yet',
        message:
            'Own two or three clubs, then form a group to pool budgets across the empire.',
        icon: Icons.account_tree_outlined,
        accent: GtexColors.gold,
      );
    }
    return Column(
      children:
          groups
              .map(
                (GtexEmpireGroupSummary group) => Padding(
                  padding: const EdgeInsets.only(bottom: GtexSpacing.sm),
                  child: ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(
                      Icons.account_tree_outlined,
                      color: GtexColors.gold,
                    ),
                    title: Text(
                      group.name,
                      style: const TextStyle(fontWeight: FontWeight.w800),
                    ),
                    subtitle: Text(
                      '${group.clubCount} clubs · pool FC ${group.budgetPool.toStringAsFixed(0)}'
                      '${group.sharedBudgetEnabled ? '' : ' · shared budget off'}',
                    ),
                    trailing: Text(
                      'rep ${group.reputation.toStringAsFixed(0)}',
                      style: const TextStyle(
                        color: GtexColors.textMuted,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ),
              )
              .toList(growable: false),
    );
  }
}

class GtexEmpireGroupSummary {
  const GtexEmpireGroupSummary({
    required this.id,
    required this.name,
    required this.clubCount,
    required this.budgetPool,
    required this.reputation,
    required this.sharedBudgetEnabled,
  });

  final String id;
  final String name;
  final int clubCount;
  final double budgetPool;
  final double reputation;
  final bool sharedBudgetEnabled;

  factory GtexEmpireGroupSummary.fromJson(Object? value) {
    final Map<String, Object?> json =
        value is Map<String, Object?>
            ? value
            : value is Map
            ? Map<String, Object?>.from(value)
            : const <String, Object?>{};
    final Object? clubs = json['clubs'];
    final int clubCount =
        clubs is List
            ? clubs.length
            : int.tryParse('${json['club_count'] ?? json['clubCount'] ?? 0}') ??
                0;
    return GtexEmpireGroupSummary(
      id: (json['id'] ?? '').toString(),
      name: (json['name'] ?? 'Empire').toString(),
      clubCount: clubCount,
      budgetPool:
          double.tryParse(
            '${json['budget_pool'] ?? json['budgetPool'] ?? 0}',
          ) ??
          0,
      reputation:
          double.tryParse(
            '${json['reputation'] ?? json['reputation_score'] ?? 0}',
          ) ??
          0,
      sharedBudgetEnabled:
          json['shared_budget_enabled'] == true ||
          json['sharedBudgetEnabled'] == true,
    );
  }
}
