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
  final Color accent;
  final String mobileLeftTitle;

  @override
  Widget build(BuildContext context) {
    final double width = MediaQuery.sizeOf(context).width;
    final bool compact = GtexBreakpoints.isCompact(context);
    final bool showRightPanel =
        rightPanel != null && width >= GtexBreakpoints.desktop;
    if (compact) {
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

    return Padding(
      padding: GtexSpacing.screenPadding,
      child: Column(
        children: <Widget>[
          _MasterDetailHeader(
            title: title,
            subtitle: subtitle,
            actions: actions,
            accent: accent,
          ),
          const SizedBox(height: GtexSpacing.md),
          Expanded(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                SizedBox(
                  width: leftPanelWidth,
                  child: _PanelFrame(accent: accent, child: leftPanel),
                ),
                const SizedBox(width: GtexSpacing.md),
                Expanded(child: _PanelFrame(accent: accent, child: detail)),
                if (showRightPanel) ...<Widget>[
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
                tooltip: mobileLeftTitle,
                onPressed:
                    () => _openPanel(context, mobileLeftTitle, leftPanel),
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
                onPressed: () => _openPanel(context, 'Summary', rightPanel!),
                icon: const Icon(Icons.receipt_long_outlined),
                label: const Text('Open summary'),
              ),
            ),
          ],
        ],
      ),
    );
  }

  void _openPanel(BuildContext context, String title, Widget child) {
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
                          style: Theme.of(
                            context,
                          ).textTheme.titleLarge?.copyWith(
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
}

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
        return Row(children: <Widget>[Expanded(child: titleBlock), actionRow]);
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
        child: Material(
          type: MaterialType.transparency,
          child: child,
        ),
      ),
    );
  }
}
