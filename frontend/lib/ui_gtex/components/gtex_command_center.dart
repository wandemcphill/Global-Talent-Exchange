import 'package:flutter/material.dart';

import '../theme/gtex_colors.dart';
import '../theme/gtex_command_center_tokens.dart';
import '../theme/gtex_spacing.dart';
import '../theme/gtex_typography.dart';
import 'gtex_action_button.dart';

/// Semantic state for the Command Center identity indicator.
///
/// The display label remains caller-owned, while this state controls its
/// visual treatment. That prevents a preview or unavailable surface from
/// accidentally inheriting live-football styling.
enum GtexCommandStatus {
  live(GtexCommandTokens.live),
  active(GtexCommandTokens.ownership),
  open(GtexCommandTokens.coin),
  preview(GtexCommandTokens.fan),
  unavailable(GtexCommandTokens.risk),
  offline(GtexCommandTokens.settled);

  const GtexCommandStatus(this.color);

  final Color color;
}

class GtexCommandMetric {
  const GtexCommandMetric({
    required this.label,
    required this.value,
    required this.detail,
    required this.accent,
    this.icon,
  });

  final String label;
  final String value;
  final String detail;
  final Color accent;
  final IconData? icon;
}

/// The shared GTEX Command Center masthead. It makes the current football
/// identity and next useful actions visible before secondary operational data.
class GtexCommandCenterMasthead extends StatelessWidget {
  const GtexCommandCenterMasthead({
    super.key,
    required this.eyebrow,
    required this.identity,
    required this.title,
    required this.summary,
    required this.statusLabel,
    required this.status,
    required this.metrics,
    this.identityDetail,
    this.primaryAction,
    this.secondaryAction,
  });

  final String eyebrow;
  final String identity;
  final String? identityDetail;
  final String title;
  final String summary;
  final String statusLabel;
  final GtexCommandStatus status;
  final List<GtexCommandMetric> metrics;
  final Widget? primaryAction;
  final Widget? secondaryAction;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[
            GtexColors.surfaceOverlay,
            GtexColors.surfaceRaised,
            GtexCommandTokens.pitch.withValues(alpha: 0.12),
          ],
        ),
        borderRadius: BorderRadius.circular(GtexCommandTokens.mastheadRadius),
        border: Border.all(color: GtexColors.surfaceBorderStrong),
      ),
      child: Padding(
        padding: const EdgeInsets.all(GtexSpacing.lg),
        child: LayoutBuilder(
          builder: (BuildContext context, BoxConstraints constraints) {
            final bool compact = constraints.maxWidth < 720;
            final Widget identityBlock = _IdentityBlock(
              identity: identity,
              detail: identityDetail,
              statusLabel: statusLabel,
              status: status,
            );
            final Widget copy = Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  eyebrow.toUpperCase(),
                  style: GtexText.labelSM.copyWith(
                    color: GtexCommandTokens.pitch,
                    letterSpacing: 1.3,
                  ),
                ),
                const SizedBox(height: GtexSpacing.xs),
                Text(
                  title,
                  style: GtexText.displayXL.copyWith(
                    color: GtexColors.textPrimary,
                    height: 0.95,
                  ),
                ),
                const SizedBox(height: GtexSpacing.sm),
                Text(
                  summary,
                  style: GtexText.bodyMD.copyWith(
                    color: GtexColors.textSecondary,
                  ),
                ),
                if (primaryAction != null ||
                    secondaryAction != null) ...<Widget>[
                  const SizedBox(height: GtexSpacing.md),
                  Wrap(
                    spacing: GtexSpacing.sm,
                    runSpacing: GtexSpacing.sm,
                    children: <Widget>[
                      if (primaryAction != null) primaryAction!,
                      if (secondaryAction != null) secondaryAction!,
                    ],
                  ),
                ],
              ],
            );
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                if (compact) ...<Widget>[
                  identityBlock,
                  const SizedBox(height: GtexSpacing.lg),
                ],
                if (!compact)
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Expanded(child: copy),
                      const SizedBox(width: GtexSpacing.lg),
                      SizedBox(width: 230, child: identityBlock),
                    ],
                  )
                else
                  copy,
                const SizedBox(height: GtexSpacing.lg),
                _MetricRail(metrics: metrics),
              ],
            );
          },
        ),
      ),
    );
  }
}

class GtexCommandAction extends StatelessWidget {
  const GtexCommandAction({
    super.key,
    required this.label,
    required this.icon,
    required this.onPressed,
    this.accent = GtexCommandTokens.pitch,
    this.secondary = false,
  });

  final String label;
  final IconData icon;
  final VoidCallback? onPressed;
  final Color accent;
  final bool secondary;

  @override
  Widget build(BuildContext context) => SizedBox(
    height: GtexCommandTokens.actionHeight,
    child: GtexActionButton(
      label: label,
      icon: icon,
      onPressed: onPressed,
      accent: accent,
      secondary: secondary,
    ),
  );
}

class GtexCommandFocusTile extends StatelessWidget {
  const GtexCommandFocusTile({
    super.key,
    required this.kicker,
    required this.title,
    required this.detail,
    required this.icon,
    required this.accent,
    this.onTap,
  });

  final String kicker;
  final String title;
  final String detail;
  final IconData icon;
  final Color accent;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(GtexCommandTokens.panelRadius),
        onTap: onTap,
        child: Ink(
          padding: const EdgeInsets.all(GtexSpacing.md),
          decoration: BoxDecoration(
            color: GtexColors.surfaceRaised,
            borderRadius: BorderRadius.circular(GtexCommandTokens.panelRadius),
            border: Border.all(color: accent.withValues(alpha: 0.38)),
          ),
          child: Row(
            children: <Widget>[
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: accent.withValues(alpha: 0.14),
                ),
                child: Icon(
                  icon,
                  color: accent,
                  size: GtexCommandTokens.iconMd,
                ),
              ),
              const SizedBox(width: GtexSpacing.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      kicker.toUpperCase(),
                      style: GtexText.labelSM.copyWith(color: accent),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      title,
                      style: GtexText.labelLG.copyWith(
                        color: GtexColors.textPrimary,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      detail,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: GtexText.bodySM.copyWith(
                        color: GtexColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
              Icon(
                Icons.arrow_forward_rounded,
                color: GtexColors.textMuted,
                size: GtexCommandTokens.iconSm,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _IdentityBlock extends StatelessWidget {
  const _IdentityBlock({
    required this.identity,
    required this.detail,
    required this.statusLabel,
    required this.status,
  });
  final String identity;
  final String? detail;
  final String statusLabel;
  final GtexCommandStatus status;
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(GtexSpacing.md),
    decoration: BoxDecoration(
      color: Colors.black.withValues(alpha: 0.18),
      borderRadius: BorderRadius.circular(GtexCommandTokens.panelRadius),
      border: Border.all(color: GtexColors.surfaceBorder),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          children: <Widget>[
            Container(
              width: 10,
              height: 10,
              decoration: BoxDecoration(
                color: status.color,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: GtexSpacing.xs),
            Text(
              statusLabel.toUpperCase(),
              style: GtexText.labelSM.copyWith(color: status.color),
            ),
          ],
        ),
        const SizedBox(height: GtexSpacing.md),
        Text(
          identity,
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
          style: GtexText.displayMD.copyWith(color: GtexColors.textPrimary),
        ),
        if (detail != null) ...<Widget>[
          const SizedBox(height: 4),
          Text(
            detail!,
            style: GtexText.bodySM.copyWith(color: GtexColors.textSecondary),
          ),
        ],
      ],
    ),
  );
}

class _MetricRail extends StatelessWidget {
  const _MetricRail({required this.metrics});
  final List<GtexCommandMetric> metrics;
  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (BuildContext context, BoxConstraints constraints) {
      final int columns =
          constraints.maxWidth >= 960
              ? 4
              : constraints.maxWidth >= 540
              ? 2
              : 1;
      final double gap = GtexSpacing.sm;
      final double width =
          (constraints.maxWidth - gap * (columns - 1)) / columns;
      return Wrap(
        spacing: gap,
        runSpacing: gap,
        children: metrics
            .map(
              (GtexCommandMetric metric) =>
                  SizedBox(width: width, child: _MetricCell(metric: metric)),
            )
            .toList(growable: false),
      );
    },
  );
}

class _MetricCell extends StatelessWidget {
  const _MetricCell({required this.metric});
  final GtexCommandMetric metric;
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(GtexSpacing.sm),
    decoration: BoxDecoration(
      color: GtexColors.surfaceBase.withValues(alpha: 0.72),
      borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
      border: Border.all(color: metric.accent.withValues(alpha: 0.24)),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          children: <Widget>[
            if (metric.icon != null) ...<Widget>[
              Icon(
                metric.icon,
                color: metric.accent,
                size: GtexCommandTokens.iconSm,
              ),
              const SizedBox(width: 5),
            ],
            Expanded(
              child: Text(
                metric.label.toUpperCase(),
                overflow: TextOverflow.ellipsis,
                style: GtexText.labelSM.copyWith(color: metric.accent),
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        Text(
          metric.value,
          overflow: TextOverflow.ellipsis,
          style: GtexText.monoLG.copyWith(color: GtexColors.textPrimary),
        ),
        const SizedBox(height: 2),
        Text(
          metric.detail,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: GtexText.bodySM.copyWith(color: GtexColors.textSecondary),
        ),
      ],
    ),
  );
}
