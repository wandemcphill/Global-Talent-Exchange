import 'package:flutter/material.dart';

import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';
import '../theme/gtex_typography.dart';

/// Variants for [GtexAttentionCard] (Document F8).
enum GtexAttentionVariant {
  decision,
  approval,
  deadline,
  alert,
  info,
}

/// Lifecycle states for [GtexAttentionCard] (Document F8).
enum GtexAttentionState {
  unread,
  dueSoon,
  overdue,
  resolved,
}

/// Canonical task / decision / deadline attention card (Master Plan Document F8).
class GtexAttentionCard extends StatelessWidget {
  const GtexAttentionCard({
    super.key,
    required this.title,
    required this.subtitle,
    this.variant = GtexAttentionVariant.decision,
    this.state = GtexAttentionState.unread,
    this.dueLabel,
    this.whoActsNextLabel,
    this.primaryActionLabel = 'Review',
    this.onPrimaryAction,
    this.onTap,
  });

  final String title;
  final String subtitle;
  final GtexAttentionVariant variant;
  final GtexAttentionState state;
  final String? dueLabel;
  final String? whoActsNextLabel;
  final String primaryActionLabel;
  final VoidCallback? onPrimaryAction;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final GtexColorTokens navy = GtexColors.navy;
    final bool isResolved = state == GtexAttentionState.resolved;
    final Color accentColor = _resolveAccentColor(navy);
    final IconData icon = _resolveIcon();
    final String stateBadgeLabel = _resolveStateLabel();

    return Semantics(
      container: true,
      label: '$title, $stateBadgeLabel',
      child: Material(
        color: navy.bgRaised,
        borderRadius: BorderRadius.circular(GtexRadius.card),
        child: InkWell(
          onTap: onTap ?? onPrimaryAction,
          borderRadius: BorderRadius.circular(GtexRadius.card),
          child: Container(
            constraints: const BoxConstraints(
              minHeight: GtexSpacing.listRowMinHeight,
            ),
            padding: GtexSpacing.cardPadding,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(GtexRadius.card),
              border: Border.all(
                color:
                    state == GtexAttentionState.overdue
                        ? navy.danger.withValues(alpha: 0.65)
                        : navy.lineSubtle,
              ),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: accentColor.withValues(alpha: 0.14),
                    borderRadius: BorderRadius.circular(GtexRadius.chip),
                    border: Border.all(
                      color: accentColor.withValues(alpha: 0.45),
                    ),
                  ),
                  alignment: Alignment.center,
                  child: Icon(icon, size: 18, color: accentColor),
                ),
                const SizedBox(width: GtexSpacing.sm),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Row(
                        children: <Widget>[
                          if (state == GtexAttentionState.unread) ...<Widget>[
                            Container(
                              key: const Key('gtex-attention-unread-dot'),
                              width: 8,
                              height: 8,
                              decoration: BoxDecoration(
                                color: navy.gold500,
                                shape: BoxShape.circle,
                              ),
                            ),
                            const SizedBox(width: 6),
                          ],
                          Expanded(
                            child: Text(
                              title,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: GtexTypography.titleS(
                                color:
                                    isResolved
                                        ? navy.textSecondary
                                        : navy.textPrimary,
                              ),
                            ),
                          ),
                          const SizedBox(width: GtexSpacing.xs),
                          _AttentionStateChip(
                            label: dueLabel ?? stateBadgeLabel,
                            color: accentColor,
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        subtitle,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: GtexTypography.bodyS(color: navy.textSecondary),
                      ),
                      if ((whoActsNextLabel ?? '')
                          .trim()
                          .isNotEmpty) ...<Widget>[
                        const SizedBox(height: 6),
                        Text(
                          whoActsNextLabel!.trim(),
                          style: GtexTypography.label(color: navy.gold300),
                        ),
                      ],
                    ],
                  ),
                ),
                if (!isResolved && onPrimaryAction != null) ...<Widget>[
                  const SizedBox(width: GtexSpacing.sm),
                  SizedBox(
                    height: GtexSpacing.minTouchTarget,
                    child: TextButton(
                      onPressed: onPrimaryAction,
                      style: TextButton.styleFrom(
                        foregroundColor: navy.gold500,
                        padding: const EdgeInsets.symmetric(
                          horizontal: GtexSpacing.sm,
                        ),
                      ),
                      child: Text(primaryActionLabel),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  Color _resolveAccentColor(GtexColorTokens navy) {
    return switch (state) {
      GtexAttentionState.overdue => navy.danger,
      GtexAttentionState.dueSoon => navy.warning,
      GtexAttentionState.resolved => navy.success,
      GtexAttentionState.unread => switch (variant) {
        GtexAttentionVariant.decision ||
        GtexAttentionVariant.approval => navy.gold500,
        GtexAttentionVariant.deadline => navy.warning,
        GtexAttentionVariant.alert => navy.danger,
        GtexAttentionVariant.info => navy.info,
      },
    };
  }

  IconData _resolveIcon() {
    if (state == GtexAttentionState.resolved) {
      return Icons.check_circle_outline_rounded;
    }
    return switch (variant) {
      GtexAttentionVariant.decision => Icons.gavel_rounded,
      GtexAttentionVariant.approval => Icons.fact_check_outlined,
      GtexAttentionVariant.deadline => Icons.timer_outlined,
      GtexAttentionVariant.alert => Icons.warning_amber_rounded,
      GtexAttentionVariant.info => Icons.mail_outline_rounded,
    };
  }

  String _resolveStateLabel() {
    return switch (state) {
      GtexAttentionState.unread => 'Unread',
      GtexAttentionState.dueSoon => 'Due soon',
      GtexAttentionState.overdue => 'Overdue',
      GtexAttentionState.resolved => 'Resolved',
    };
  }
}

class _AttentionStateChip extends StatelessWidget {
  const _AttentionStateChip({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(GtexRadius.pill),
        border: Border.all(color: color.withValues(alpha: 0.45)),
      ),
      child: Text(
        label,
        style: GtexTypography.numericS(color: color),
      ),
    );
  }
}
