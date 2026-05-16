import 'package:flutter/material.dart';

import '../backgrounds/living_football_os_background.dart';
import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';

class GtexShellDestination {
  const GtexShellDestination({
    required this.label,
    required this.icon,
    required this.selectedIcon,
    required this.isSelected,
    required this.onTap,
    this.badgeLabel,
    this.accent = GtexColors.pitch,
  });

  final String label;
  final IconData icon;
  final IconData selectedIcon;
  final bool isSelected;
  final VoidCallback onTap;
  final String? badgeLabel;
  final Color accent;
}

class GtexAppShell extends StatelessWidget {
  const GtexAppShell({
    super.key,
    required this.destinations,
    required this.child,
    this.title = 'GTEX',
    this.subtitle = 'Global Talent Exchange',
    this.actions = const <Widget>[],
    this.status,
  });

  final List<GtexShellDestination> destinations;
  final Widget child;
  final String title;
  final String subtitle;
  final List<Widget> actions;
  final Widget? status;

  @override
  Widget build(BuildContext context) {
    final bool compact = GtexBreakpoints.isCompact(context);
    return LivingFootballOSBackground(
      child: Scaffold(
        backgroundColor: Colors.transparent,
        body: SafeArea(
          child:
              compact
                  ? Column(
                    children: <Widget>[
                      _TopBar(
                        title: title,
                        subtitle: subtitle,
                        actions: actions,
                      ),
                      if (status != null) status!,
                      Expanded(child: child),
                    ],
                  )
                  : Row(
                    children: <Widget>[
                      _NavRail(destinations: destinations),
                      Expanded(
                        child: Column(
                          children: <Widget>[
                            _TopBar(
                              title: title,
                              subtitle: subtitle,
                              actions: actions,
                            ),
                            if (status != null) status!,
                            Expanded(child: child),
                          ],
                        ),
                      ),
                    ],
                  ),
        ),
        bottomNavigationBar:
            compact
                ? _BottomNav(destinations: destinations.take(5).toList())
                : null,
      ),
    );
  }
}

class _TopBar extends StatelessWidget {
  const _TopBar({
    required this.title,
    required this.subtitle,
    required this.actions,
  });

  final String title;
  final String subtitle;
  final List<Widget> actions;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 72,
      padding: const EdgeInsets.symmetric(horizontal: GtexSpacing.lg),
      decoration: BoxDecoration(
        color: GtexColors.stadiumBlack.withValues(alpha: 0.56),
        border: Border(
          bottom: BorderSide(color: GtexColors.line.withValues(alpha: 0.48)),
        ),
      ),
      child: Row(
        children: <Widget>[
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: GtexColors.pitch,
              borderRadius: BorderRadius.circular(14),
              boxShadow: <BoxShadow>[
                GtexColors.glow(GtexColors.pitch, opacity: 0.28),
              ],
            ),
            child: const Center(
              child: Text(
                'G',
                style: TextStyle(
                  color: Colors.black,
                  fontWeight: FontWeight.w900,
                  fontSize: 22,
                ),
              ),
            ),
          ),
          const SizedBox(width: GtexSpacing.sm),
          Expanded(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: GtexColors.text,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                Text(
                  subtitle,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    color: GtexColors.textMuted,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          ),
          Wrap(spacing: GtexSpacing.xs, children: actions),
        ],
      ),
    );
  }
}

class _NavRail extends StatelessWidget {
  const _NavRail({required this.destinations});

  final List<GtexShellDestination> destinations;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 94,
      padding: const EdgeInsets.symmetric(vertical: GtexSpacing.md),
      decoration: BoxDecoration(
        color: GtexColors.stadiumBlack.withValues(alpha: 0.72),
        border: Border(
          right: BorderSide(color: GtexColors.line.withValues(alpha: 0.5)),
        ),
      ),
      child: Column(
        children: <Widget>[
          const SizedBox(height: GtexSpacing.xs),
          Expanded(
            child: ListView.separated(
              itemCount: destinations.length,
              separatorBuilder:
                  (_, __) => const SizedBox(height: GtexSpacing.xs),
              itemBuilder: (BuildContext context, int index) {
                final GtexShellDestination item = destinations[index];
                return _RailItem(item: item);
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _RailItem extends StatelessWidget {
  const _RailItem({required this.item});

  final GtexShellDestination item;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: GtexSpacing.xs),
      child: Tooltip(
        message: item.label,
        child: InkWell(
          borderRadius: BorderRadius.circular(GtexSpacing.radiusLg),
          onTap: item.onTap,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 160),
            padding: const EdgeInsets.symmetric(vertical: GtexSpacing.sm),
            decoration: BoxDecoration(
              color:
                  item.isSelected
                      ? item.accent.withValues(alpha: 0.13)
                      : Colors.transparent,
              borderRadius: BorderRadius.circular(GtexSpacing.radiusLg),
              border: Border.all(
                color:
                    item.isSelected
                        ? item.accent.withValues(alpha: 0.38)
                        : Colors.transparent,
              ),
            ),
            child: Column(
              children: <Widget>[
                Icon(
                  item.isSelected ? item.selectedIcon : item.icon,
                  color: item.isSelected ? item.accent : GtexColors.textMuted,
                ),
                const SizedBox(height: 6),
                Text(
                  item.label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: item.isSelected ? item.accent : GtexColors.textMuted,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _BottomNav extends StatelessWidget {
  const _BottomNav({required this.destinations});

  final List<GtexShellDestination> destinations;

  @override
  Widget build(BuildContext context) {
    final int rawIndex = destinations.indexWhere(
      (GtexShellDestination item) => item.isSelected,
    );
    final int selectedIndex =
        rawIndex < 0 ? 0 : rawIndex.clamp(0, destinations.length - 1).toInt();
    return NavigationBar(
      selectedIndex: selectedIndex,
      onDestinationSelected: (int index) => destinations[index].onTap(),
      destinations: destinations
          .map(
            (GtexShellDestination item) => NavigationDestination(
              icon: Icon(item.icon),
              selectedIcon: Icon(item.selectedIcon),
              label: item.label,
            ),
          )
          .toList(growable: false),
    );
  }
}
