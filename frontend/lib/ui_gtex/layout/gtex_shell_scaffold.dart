import 'package:flutter/material.dart';
import 'package:gte_frontend/features/navigation/model/gtex_shell_navigation_model.dart';

import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';
import '../theme/gtex_typography.dart';
import 'gtex_more_sheet.dart';
import 'gtex_nav_bar.dart';
import 'gtex_top_bar.dart';

/// Canonical GTEX Navy shell scaffold (Master Plan Document F7, F8 & K1).
///
/// Responsive breakpoints:
/// - `compact < 720`: [GtexTopBar] + content + 5-slot [GtexNavBar] (with `More` sheet).
/// - `medium 720–1279`: [GtexNavRail] + [GtexTopBar] + content.
/// - `expanded >= 1280`: [GtexNavRail] + [GtexTopBar] + content + optional `worldPulseRail`.
class GtexShellScaffold extends StatelessWidget {
  const GtexShellScaffold({
    super.key,
    required this.navigationModel,
    required this.topBar,
    required this.child,
    required this.selectedSlotId,
    required this.onSelectSlot,
    this.selectedSecondaryId,
    this.onSelectSecondary,
    this.activeRoute,
    this.livePulseStrip,
    this.worldPulseRail,
    this.offlineBannerMessage,
  });

  final ShellNavigationModel navigationModel;
  final GtexTopBar topBar;
  final Widget child;
  final GtexShellSlotId selectedSlotId;
  final ValueChanged<GtexShellSlotSpec> onSelectSlot;
  final GtexSecondaryDestinationId? selectedSecondaryId;
  final ValueChanged<GtexSecondaryDestinationSpec>? onSelectSecondary;
  final String? activeRoute;
  final Widget? livePulseStrip;
  final Widget? worldPulseRail;
  final String? offlineBannerMessage;

  Future<void> _openMoreSheet(BuildContext context) async {
    final GtexSecondaryDestinationSpec? selected = await GtexMoreSheet.show(
      context,
      destinations: navigationModel.moreDestinations,
      activeRoute: activeRoute,
      workspaceLabel: navigationModel.activeWorkspace.label,
    );
    if (selected != null && onSelectSecondary != null) {
      onSelectSecondary!(selected);
    }
  }

  @override
  Widget build(BuildContext context) {
    final GtexColorTokens navy = GtexColors.navy;
    final bool compact = GtexBreakpoints.isCompact(context);
    final bool expanded = GtexBreakpoints.isWide(context);
    final Widget? banner =
        (offlineBannerMessage ?? '').trim().isNotEmpty
            ? _OfflineMaintenanceBanner(message: offlineBannerMessage!.trim())
            : null;

    return Scaffold(
      key: const Key('gtex-shell-scaffold'),
      backgroundColor: navy.bgBase,
      body: SafeArea(
        child:
            compact
                ? Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: <Widget>[
                    topBar,
                    if (banner != null) banner,
                    if (livePulseStrip != null) livePulseStrip!,
                    Expanded(child: child),
                  ],
                )
                : Row(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: <Widget>[
                    GtexNavRail(
                      primarySlots: navigationModel.primarySlots,
                      selectedSlotId: selectedSlotId,
                      onSelectSlot: onSelectSlot,
                      secondaryDestinations: navigationModel.moreDestinations,
                      selectedSecondaryId: selectedSecondaryId,
                      onSelectSecondary: onSelectSecondary,
                      onOpenMoreSheet: () => _openMoreSheet(context),
                    ),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: <Widget>[
                          topBar,
                          if (banner != null) banner,
                          if (livePulseStrip != null) livePulseStrip!,
                          Expanded(
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: <Widget>[
                                Expanded(child: child),
                                if (expanded && worldPulseRail != null)
                                  worldPulseRail!,
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
      ),
      bottomNavigationBar:
          compact
              ? GtexNavBar(
                slots: navigationModel.primarySlots,
                selectedSlotId: selectedSlotId,
                onSelectSlot: onSelectSlot,
                onOpenMoreSheet: () => _openMoreSheet(context),
              )
              : null,
    );
  }
}

class _OfflineMaintenanceBanner extends StatelessWidget {
  const _OfflineMaintenanceBanner({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    final GtexColorTokens navy = GtexColors.navy;
    return Container(
      key: const Key('gtex-shell-offline-banner'),
      padding: const EdgeInsets.symmetric(
        horizontal: GtexSpacing.md,
        vertical: GtexSpacing.xs,
      ),
      decoration: BoxDecoration(
        color: navy.warning.withValues(alpha: 0.14),
        border: Border(bottom: BorderSide(color: navy.warning)),
      ),
      child: Row(
        children: <Widget>[
          Icon(Icons.cloud_off_rounded, size: 16, color: navy.warning),
          const SizedBox(width: GtexSpacing.xs),
          Expanded(
            child: Text(
              message,
              style: GtexTypography.bodyS(color: navy.warning),
            ),
          ),
        ],
      ),
    );
  }
}
