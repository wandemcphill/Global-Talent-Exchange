import 'package:flutter/material.dart';
import 'package:gte_frontend/features/navigation/model/gtex_shell_navigation_model.dart';

import '../theme/gtex_colors.dart';
import '../theme/gtex_motion.dart';
import '../theme/gtex_spacing.dart';
import '../theme/gtex_typography.dart';

/// Canonical GTEX Navy bottom navigation bar for compact (`<720 dp`) viewports
/// (Master Plan Document E1, F8).
class GtexNavBar extends StatelessWidget {
  const GtexNavBar({
    super.key,
    required this.slots,
    required this.selectedSlotId,
    required this.onSelectSlot,
    this.onOpenMoreSheet,
  });

  final List<GtexShellSlotSpec> slots;
  final GtexShellSlotId selectedSlotId;
  final ValueChanged<GtexShellSlotSpec> onSelectSlot;
  final VoidCallback? onOpenMoreSheet;

  @override
  Widget build(BuildContext context) {
    final GtexColorTokens navy = GtexColors.navy;
    final List<GtexShellSlotSpec> visibleSlots =
        slots.take(5).toList(growable: false);
    final int activeIndex = visibleSlots.indexWhere(
      (GtexShellSlotSpec item) => item.id == selectedSlotId,
    );
    final int selectedIndex = activeIndex < 0 ? 0 : activeIndex;

    return Container(
      key: const Key('gtex-nav-bar'),
      decoration: BoxDecoration(
        color: navy.bgBase,
        border: Border(top: BorderSide(color: navy.lineSubtle)),
      ),
      child: NavigationBar(
        backgroundColor: navy.bgBase,
        indicatorColor: navy.gold500.withValues(alpha: 0.16),
        selectedIndex: selectedIndex,
        onDestinationSelected: (int index) {
          final GtexShellSlotSpec selected = visibleSlots[index];
          if (selected.opensMoreSheet && onOpenMoreSheet != null) {
            onOpenMoreSheet!();
            return;
          }
          onSelectSlot(selected);
        },
        destinations: <NavigationDestination>[
          for (final GtexShellSlotSpec slot in visibleSlots)
            NavigationDestination(
              key: Key('gtex-nav-slot-${slot.id.name}'),
              icon: _SlotIconWithBadge(
                icon: slot.icon,
                color: navy.textSecondary,
                badgeCount: slot.badgeCount,
              ),
              selectedIcon: _SlotIconWithBadge(
                icon: slot.selectedIcon,
                color: navy.gold500,
                badgeCount: slot.badgeCount,
              ),
              label: slot.label,
            ),
        ],
      ),
    );
  }
}

/// Canonical GTEX Navy left navigation rail for medium (`720–1279 dp`) and
/// expanded (`>=1280 dp`) viewports (Master Plan Document E1, F8).
class GtexNavRail extends StatelessWidget {
  const GtexNavRail({
    super.key,
    required this.primarySlots,
    required this.selectedSlotId,
    required this.onSelectSlot,
    this.secondaryDestinations = const <GtexSecondaryDestinationSpec>[],
    this.selectedSecondaryId,
    this.onSelectSecondary,
    this.onOpenMoreSheet,
  });

  final List<GtexShellSlotSpec> primarySlots;
  final GtexShellSlotId? selectedSlotId;
  final ValueChanged<GtexShellSlotSpec> onSelectSlot;
  final List<GtexSecondaryDestinationSpec> secondaryDestinations;
  final GtexSecondaryDestinationId? selectedSecondaryId;
  final ValueChanged<GtexSecondaryDestinationSpec>? onSelectSecondary;
  final VoidCallback? onOpenMoreSheet;

  @override
  Widget build(BuildContext context) {
    final GtexColorTokens navy = GtexColors.navy;
    final List<GtexShellSlotSpec> directPrimary = primarySlots
        .where((GtexShellSlotSpec slot) => !slot.opensMoreSheet)
        .toList(growable: false);

    return Container(
      key: const Key('gtex-nav-rail'),
      width: 104,
      padding: const EdgeInsets.symmetric(vertical: GtexSpacing.sm),
      decoration: BoxDecoration(
        color: navy.bgBase,
        border: Border(right: BorderSide(color: navy.lineSubtle)),
      ),
      child: ListView(
        padding: const EdgeInsets.symmetric(horizontal: GtexSpacing.xs),
        children: <Widget>[
          for (final GtexShellSlotSpec slot in directPrimary) ...<Widget>[
            _RailButton(
              key: Key('gtex-rail-slot-${slot.id.name}'),
              label: slot.label,
              icon:
                  slot.id == selectedSlotId ? slot.selectedIcon : slot.icon,
              isSelected: slot.id == selectedSlotId,
              badgeCount: slot.badgeCount,
              onTap: () => onSelectSlot(slot),
            ),
            const SizedBox(height: GtexSpacing.xxs),
          ],
          if (secondaryDestinations.isNotEmpty &&
              onSelectSecondary != null) ...<Widget>[
            Padding(
              padding: const EdgeInsets.symmetric(vertical: GtexSpacing.xs),
              child: Divider(color: navy.lineSubtle, height: 1),
            ),
            for (final GtexSecondaryDestinationSpec item
                in secondaryDestinations) ...<Widget>[
              _RailButton(
                key: Key('gtex-rail-secondary-${item.id.name}'),
                label: item.label,
                icon: item.icon,
                isSelected: item.id == selectedSecondaryId,
                badgeCount: item.badgeCount,
                onTap: () => onSelectSecondary!(item),
              ),
              const SizedBox(height: GtexSpacing.xxs),
            ],
          ] else if (onOpenMoreSheet != null) ...<Widget>[
            _RailButton(
              key: const Key('gtex-rail-more-button'),
              label: 'More',
              icon: Icons.more_horiz_rounded,
              isSelected: false,
              badgeCount: 0,
              onTap: onOpenMoreSheet!,
            ),
          ],
        ],
      ),
    );
  }
}

class _RailButton extends StatelessWidget {
  const _RailButton({
    super.key,
    required this.label,
    required this.icon,
    required this.isSelected,
    required this.badgeCount,
    required this.onTap,
  });

  final String label;
  final IconData icon;
  final bool isSelected;
  final int badgeCount;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final GtexColorTokens navy = GtexColors.navy;
    final Color foreground = isSelected ? navy.gold500 : navy.textSecondary;

    return Tooltip(
      message: label,
      child: InkWell(
        borderRadius: BorderRadius.circular(GtexRadius.card),
        onTap: onTap,
        child: AnimatedContainer(
          duration: GtexMotion.effectiveDuration(
            context,
            GtexMotion.stateDuration,
          ),
          curve: GtexMotion.curve,
          constraints: const BoxConstraints(
            minHeight: GtexSpacing.minTouchTarget,
          ),
          padding: const EdgeInsets.symmetric(
            vertical: GtexSpacing.xs,
            horizontal: GtexSpacing.xxs,
          ),
          decoration: BoxDecoration(
            color:
                isSelected
                    ? navy.gold500.withValues(alpha: 0.14)
                    : Colors.transparent,
            borderRadius: BorderRadius.circular(GtexRadius.card),
            border: Border.all(
              color:
                  isSelected
                      ? navy.gold500.withValues(alpha: 0.45)
                      : Colors.transparent,
            ),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              _SlotIconWithBadge(
                icon: icon,
                color: foreground,
                badgeCount: badgeCount,
              ),
              const SizedBox(height: 4),
              Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: GtexTypography.numericS(color: foreground),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SlotIconWithBadge extends StatelessWidget {
  const _SlotIconWithBadge({
    required this.icon,
    required this.color,
    required this.badgeCount,
  });

  final IconData icon;
  final Color color;
  final int badgeCount;

  @override
  Widget build(BuildContext context) {
    final GtexColorTokens navy = GtexColors.navy;
    if (badgeCount <= 0) {
      return Icon(icon, color: color, size: 22);
    }
    final String badgeText = badgeCount > 99 ? '99+' : badgeCount.toString();
    return Stack(
      clipBehavior: Clip.none,
      children: <Widget>[
        Icon(icon, color: color, size: 22),
        Positioned(
          right: -8,
          top: -6,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
            decoration: BoxDecoration(
              color: navy.gold500,
              borderRadius: BorderRadius.circular(GtexRadius.pill),
            ),
            child: Text(
              badgeText,
              style: GtexTypography.numericS(color: navy.bgBase),
            ),
          ),
        ),
      ],
    );
  }
}
