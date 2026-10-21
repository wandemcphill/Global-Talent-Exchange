import 'package:flutter/material.dart';
import 'package:gte_frontend/features/navigation/model/gtex_shell_navigation_model.dart';

import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';
import '../theme/gtex_typography.dart';

/// Canonical GTEX `More` bottom sheet (Master Plan Document E1, E6 & F8).
///
/// Displays secondary destinations from [ShellNavigationModel.moreDestinations]:
/// `Newsroom`, `World`, `Community`, `Boardroom` (when `clubLegacyEnabled`),
/// `Wallet`, `Rewards`, `You`, and `Admin` (when `isAdmin`).
class GtexMoreSheet extends StatelessWidget {
  const GtexMoreSheet({
    super.key,
    required this.destinations,
    required this.onSelectDestination,
    this.activeRoute,
    this.workspaceLabel,
  });

  final List<GtexSecondaryDestinationSpec> destinations;
  final ValueChanged<GtexSecondaryDestinationSpec> onSelectDestination;
  final String? activeRoute;
  final String? workspaceLabel;

  static Future<GtexSecondaryDestinationSpec?> show(
    BuildContext context, {
    required List<GtexSecondaryDestinationSpec> destinations,
    String? activeRoute,
    String? workspaceLabel,
  }) {
    return showModalBottomSheet<GtexSecondaryDestinationSpec>(
      context: context,
      useSafeArea: true,
      backgroundColor: GtexColors.navy.bgRaised,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(
          top: Radius.circular(GtexRadius.sheet),
        ),
      ),
      builder: (BuildContext sheetContext) {
        return GtexMoreSheet(
          destinations: destinations,
          activeRoute: activeRoute,
          workspaceLabel: workspaceLabel,
          onSelectDestination: (GtexSecondaryDestinationSpec selected) {
            Navigator.of(sheetContext).pop(selected);
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final GtexColorTokens navy = GtexColors.navy;
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          GtexSpacing.md,
          GtexSpacing.md,
          GtexSpacing.md,
          GtexSpacing.lg,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: <Widget>[
                Text(
                  workspaceLabel == null || workspaceLabel!.trim().isEmpty
                      ? 'MORE DESTINATIONS'
                      : '${workspaceLabel!.trim().toUpperCase()} · MORE',
                  style: GtexTypography.label(color: navy.gold300),
                ),
                IconButton(
                  key: const Key('gtex-more-sheet-close'),
                  tooltip: 'Close More menu',
                  onPressed: () {
                    if (Navigator.of(context).canPop()) {
                      Navigator.of(context).pop();
                    }
                  },
                  icon: Icon(Icons.close_rounded, color: navy.textSecondary),
                ),
              ],
            ),
            const SizedBox(height: GtexSpacing.xs),
            Flexible(
              child: ListView.separated(
                shrinkWrap: true,
                itemCount: destinations.length,
                separatorBuilder:
                    (_, __) => Divider(color: navy.lineSubtle, height: 1),
                itemBuilder: (BuildContext context, int index) {
                  final GtexSecondaryDestinationSpec item = destinations[index];
                  final bool isSelected =
                      activeRoute != null &&
                      activeRoute!.trim() == item.canonicalRoute;
                  return ListTile(
                    key: Key('gtex-more-destination-${item.id.name}'),
                    minVerticalPadding: GtexSpacing.sm,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(GtexRadius.card),
                    ),
                    tileColor: isSelected ? navy.bgOverlay : Colors.transparent,
                    leading: Icon(
                      item.icon,
                      color: isSelected ? navy.gold500 : navy.textSecondary,
                    ),
                    title: Text(
                      item.label,
                      style: GtexTypography.titleS(
                        color: isSelected ? navy.gold500 : navy.textPrimary,
                      ),
                    ),
                    trailing: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: <Widget>[
                        if (item.badgeCount > 0) ...<Widget>[
                          Container(
                            key: Key('gtex-more-badge-${item.id.name}'),
                            padding: const EdgeInsets.symmetric(
                              horizontal: 8,
                              vertical: 2,
                            ),
                            decoration: BoxDecoration(
                              color: navy.gold500,
                              borderRadius: BorderRadius.circular(
                                GtexRadius.pill,
                              ),
                            ),
                            child: Text(
                              item.badgeCount.toString(),
                              style: GtexTypography.numericS(
                                color: navy.bgBase,
                              ),
                            ),
                          ),
                          const SizedBox(width: GtexSpacing.xs),
                        ],
                        Icon(
                          Icons.chevron_right_rounded,
                          color: navy.textTertiary,
                          size: 18,
                        ),
                      ],
                    ),
                    onTap: () => onSelectDestination(item),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}
