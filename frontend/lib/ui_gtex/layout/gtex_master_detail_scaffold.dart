import 'package:flutter/material.dart';

import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';

class GtexMasterDetailScaffold extends StatelessWidget {
  const GtexMasterDetailScaffold({
    super.key,
    required this.title,
    required this.leftPanel,
    required this.detail,
    this.subtitle,
    this.actions = const <Widget>[],
    this.rightPanel,
    this.leftPanelWidth = 310,
    this.rightPanelWidth = 340,
    this.detailMinWidth = 420,
    this.accent = GtexColors.pitch,
    this.mobileLeftTitle = 'Browse',
  });

  final String title;
  final String? subtitle;
  final Widget leftPanel;
  final Widget detail;
  final Widget? rightPanel;
  final List<Widget> actions;
  final double leftPanelWidth;
  final double rightPanelWidth;

  /// The narrowest the primary detail pane is ever allowed to become. The
  /// secondary panels drop to sheets rather than squeezing past it: the
  /// detail pane holds the actual content of the screen, so it is the last
  /// thing to give up width, not the first.
  final double detailMinWidth;
  final Color accent;
  final String mobileLeftTitle;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        // Layout is decided from the box this scaffold was actually handed,
        // not from the window. Inside the app shell the two differ by the
        // nav rail plus the world-pulse rail, and reading the window made
        // the scaffold reserve inline panels it had no room for - which is
        // what starved the detail pane down to a few dozen pixels at common
        // laptop widths. MediaQuery is only a fallback for an unbounded
        // parent, where there is no box to measure.
        final double outerWidth =
            constraints.hasBoundedWidth
                ? constraints.maxWidth
                : MediaQuery.sizeOf(context).width;

        if (outerWidth < GtexBreakpoints.mobile) {
          return _MobileMasterDetail(
            title: title,
            subtitle: subtitle,
            leftPanel: leftPanel,
            detail: detail,
            rightPanel: rightPanel,
            actions: actions,
            accent: accent,
            mobileLeftTitle: mobileLeftTitle,
          );
        }

        final double contentWidth =
            outerWidth - GtexSpacing.screenPadding.horizontal;

        double detailWidthFor({required bool left, required bool right}) {
          double remaining = contentWidth;
          if (left) {
            remaining -= leftPanelWidth + GtexSpacing.md;
          }
          if (right) {
            remaining -= rightPanelWidth + GtexSpacing.md;
          }
          return remaining;
        }

        // Progressive collapse in priority order: the summary panel yields
        // first, then the browse panel. Each keeps its affordance as a
        // sheet, so nothing becomes unreachable - it only stops competing
        // for horizontal space the screen cannot afford.
        bool showRight = rightPanel != null;
        if (showRight &&
            detailWidthFor(left: true, right: true) < detailMinWidth) {
          showRight = false;
        }
        bool showLeft = true;
        if (detailWidthFor(left: true, right: showRight) < detailMinWidth) {
          showLeft = false;
        }

        final bool offerLeftPanelSheet = !showLeft;
        final bool offerRightPanelSheet = rightPanel != null && !showRight;

        return Padding(
          padding: GtexSpacing.screenPadding,
          child: Column(
            children: <Widget>[
              _MasterDetailHeader(
                title: title,
                subtitle: subtitle,
                actions: <Widget>[
                  if (offerLeftPanelSheet)
                    IconButton.filledTonal(
                      key: const Key('gtex-master-detail-browse-action'),
                      tooltip: mobileLeftTitle,
                      onPressed:
                          () => showGtexMasterDetailPanelSheet(
                            context,
                            mobileLeftTitle,
                            leftPanel,
                          ),
                      icon: const Icon(Icons.view_sidebar_outlined),
                    ),
                  if (offerRightPanelSheet)
                    IconButton.filledTonal(
                      key: const Key('gtex-master-detail-summary-action'),
                      tooltip: 'Open summary',
                      onPressed:
                          () => showGtexMasterDetailPanelSheet(
                            context,
                            'Summary',
                            rightPanel!,
                          ),
                      icon: const Icon(Icons.receipt_long_outlined),
                    ),
                  ...actions,
                ],
                accent: accent,
              ),
              const SizedBox(height: GtexSpacing.md),
              Expanded(
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: <Widget>[
                    if (showLeft) ...<Widget>[
                      SizedBox(
                        width: leftPanelWidth,
                        child: _PanelFrame(accent: accent, child: leftPanel),
                      ),
                      const SizedBox(width: GtexSpacing.md),
                    ],
                    Expanded(child: _PanelFrame(accent: accent, child: detail)),
                    if (showRight) ...<Widget>[
                      const SizedBox(width: GtexSpacing.md),
                      SizedBox(
                        width: rightPanelWidth,
                        child: _PanelFrame(accent: accent, child: rightPanel!),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _MobileMasterDetail extends StatelessWidget {
  const _MobileMasterDetail({
    required this.title,
    required this.subtitle,
    required this.leftPanel,
    required this.detail,
    required this.rightPanel,
    required this.actions,
    required this.accent,
    required this.mobileLeftTitle,
  });

  final String title;
  final String? subtitle;
  final Widget leftPanel;
  final Widget detail;
  final Widget? rightPanel;
  final List<Widget> actions;
  final Color accent;
  final String mobileLeftTitle;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(GtexSpacing.md),
      child: Column(
        children: <Widget>[
          _MasterDetailHeader(
            title: title,
            subtitle: subtitle,
            actions: <Widget>[
              IconButton.filledTonal(
                key: const Key('gtex-master-detail-browse-action'),
                tooltip: mobileLeftTitle,
                onPressed:
                    () => showGtexMasterDetailPanelSheet(
                      context,
                      mobileLeftTitle,
                      leftPanel,
                    ),
                icon: const Icon(Icons.view_sidebar_outlined),
              ),
              ...actions,
            ],
            accent: accent,
          ),
          const SizedBox(height: GtexSpacing.md),
          Expanded(child: _PanelFrame(accent: accent, child: detail)),
          if (rightPanel != null) ...<Widget>[
            const SizedBox(height: GtexSpacing.sm),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                key: const Key('gtex-master-detail-summary-action'),
                onPressed:
                    () => showGtexMasterDetailPanelSheet(
                      context,
                      'Summary',
                      rightPanel!,
                    ),
                icon: const Icon(Icons.receipt_long_outlined),
                label: const Text('Open summary'),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// Opens a panel that cannot be shown inline at the current width.
void showGtexMasterDetailPanelSheet(
  BuildContext context,
  String title,
  Widget child,
) {
  showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    backgroundColor: GtexColors.panel,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(
        top: Radius.circular(GtexSpacing.radiusLg),
      ),
    ),
    builder: (BuildContext context) {
      return SafeArea(
        child: SizedBox(
          height: MediaQuery.sizeOf(context).height * 0.84,
          child: Padding(
            padding: const EdgeInsets.all(GtexSpacing.md),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Row(
                  children: <Widget>[
                    Expanded(
                      child: Text(
                        title,
                        style: Theme.of(context).textTheme.titleLarge?.copyWith(
                          color: GtexColors.text,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                    ),
                    IconButton(
                      onPressed: () => Navigator.of(context).pop(),
                      icon: const Icon(Icons.close),
                    ),
                  ],
                ),
                const SizedBox(height: GtexSpacing.md),
                Expanded(child: child),
              ],
            ),
          ),
        ),
      );
    },
  );
}

/// Share of the header the action cluster may occupy before it wraps. The
/// title keeps the remainder, so short action sets never squeeze it.
const double _actionsWidthFraction = 0.62;

class _MasterDetailHeader extends StatelessWidget {
  const _MasterDetailHeader({
    required this.title,
    required this.subtitle,
    required this.actions,
    required this.accent,
  });

  final String title;
  final String? subtitle;
  final List<Widget> actions;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final bool compact = constraints.maxWidth < 420;
        final Widget titleBlock = Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Container(
              width: 5,
              height: 44,
              decoration: BoxDecoration(
                color: accent,
                borderRadius: BorderRadius.circular(GtexSpacing.radiusPill),
                boxShadow: <BoxShadow>[GtexColors.glow(accent, opacity: 0.28)],
              ),
            ),
            const SizedBox(width: GtexSpacing.sm),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  Text(
                    title,
                    maxLines: compact ? 2 : 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      color: GtexColors.text,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  if (subtitle != null)
                    Text(
                      subtitle!,
                      maxLines: compact ? 3 : 2,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: GtexColors.textMuted,
                      ),
                    ),
                ],
              ),
            ),
          ],
        );
        final Widget actionRow = Wrap(
          spacing: GtexSpacing.xs,
          runSpacing: GtexSpacing.xs,
          children: actions,
        );
        if (compact) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              titleBlock,
              if (actions.isNotEmpty) ...<Widget>[
                const SizedBox(height: GtexSpacing.sm),
                Align(alignment: Alignment.centerLeft, child: actionRow),
              ],
            ],
          );
        }
        // The action `Wrap` must be laid out against a bounded width or it
        // measures itself on a single infinite line and overflows the header.
        // A `ConstrainedBox` (rather than `Flexible`) bounds it without
        // claiming a fixed share of the row: the actions take only the width
        // they actually need, wrap to further runs once they exceed the cap,
        // and every remaining pixel goes to the title.
        final double actionsMaxWidth =
            (constraints.maxWidth - GtexSpacing.sm) * _actionsWidthFraction;
        return Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: <Widget>[
            Expanded(child: titleBlock),
            const SizedBox(width: GtexSpacing.sm),
            ConstrainedBox(
              constraints: BoxConstraints(maxWidth: actionsMaxWidth),
              child: actionRow,
            ),
          ],
        );
      },
    );
  }
}

class _PanelFrame extends StatelessWidget {
  const _PanelFrame({required this.child, required this.accent});

  final Widget child;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: GtexColors.panel.withValues(alpha: 0.76),
        borderRadius: BorderRadius.circular(GtexSpacing.radiusLg),
        border: Border.all(color: GtexColors.line.withValues(alpha: 0.72)),
        boxShadow: <BoxShadow>[GtexColors.glow(Colors.black, opacity: 0.32)],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(GtexSpacing.radiusLg),
        child: Material(type: MaterialType.transparency, child: child),
      ),
    );
  }
}
