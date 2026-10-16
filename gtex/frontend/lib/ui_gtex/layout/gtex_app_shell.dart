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
    this.livePulseStrip,
    this.worldPulseRail,
  });

  final List<GtexShellDestination> destinations;
  final Widget child;
  final String title;
  final String subtitle;
  final List<Widget> actions;
  final Widget? status;
  final Widget? livePulseStrip;
  final Widget? worldPulseRail;

  @override
  Widget build(BuildContext context) {
    final bool compact = GtexBreakpoints.isCompact(context);
    final Widget pulseStrip =
        livePulseStrip ?? _LiveFootballPulseStrip(destinations: destinations);
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
                      pulseStrip,
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
                            pulseStrip,
                            Expanded(
                              child: Row(
                                crossAxisAlignment: CrossAxisAlignment.stretch,
                                children: <Widget>[
                                  Expanded(child: child),
                                  if (worldPulseRail != null) worldPulseRail!,
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
            compact ? _BottomNav(destinations: destinations) : null,
      ),
    );
  }
}

class _LiveFootballPulseStrip extends StatelessWidget {
  const _LiveFootballPulseStrip({required this.destinations});

  final List<GtexShellDestination> destinations;

  @override
  Widget build(BuildContext context) {
    final List<GtexShellDestination> selected = destinations
        .where((GtexShellDestination destination) => destination.isSelected)
        .toList(growable: false);
    final GtexShellDestination? active =
        selected.isEmpty ? null : selected.first;
    final List<String> liveModules = destinations
        .where(
          (GtexShellDestination destination) => destination.badgeLabel != null,
        )
        .map(
          (GtexShellDestination destination) =>
              '${destination.label} ${destination.badgeLabel}',
        )
        .take(3)
        .toList(growable: false);
    final String modulesLabel =
        liveModules.isEmpty ? 'Live modules armed' : liveModules.join('  |  ');
    return Container(
      height: 34,
      padding: const EdgeInsets.symmetric(horizontal: GtexSpacing.lg),
      decoration: BoxDecoration(
        color: GtexColors.stadiumBlack.withValues(alpha: 0.38),
        border: Border(
          bottom: BorderSide(color: GtexColors.line.withValues(alpha: 0.28)),
        ),
      ),
      child: Row(
        children: <Widget>[
          Icon(
            Icons.sensors_rounded,
            size: 15,
            color: active?.accent ?? GtexColors.pitch,
          ),
          const SizedBox(width: GtexSpacing.xs),
          Text(
            active == null ? 'GTEX world pulse' : '${active.label} live',
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: GtexColors.text,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(width: GtexSpacing.sm),
          Expanded(
            child: Text(
              modulesLabel,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: GtexColors.textSecondary,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          Text(
            'football OS',
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: GtexColors.textMuted,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
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

  /// Share of the bar the action cluster may claim before it starts to
  /// scroll. The title keeps the rest, so a short action set never squeezes
  /// it.
  static const double _actionsWidthFraction = 0.62;

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
      child: LayoutBuilder(
        builder: (BuildContext context, BoxConstraints constraints) {
          return Row(
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
              // The action cluster used to be laid out unbounded inside this
              // row, so a full desktop action set overflowed the bar by 217px
              // between the mobile and desktop breakpoints. Bounding it to a
              // share of the bar and scrolling the remainder keeps every action
              // reachable without ever clipping the title.
              ConstrainedBox(
                constraints: BoxConstraints(
                  maxWidth:
                      (constraints.maxWidth - 42 - GtexSpacing.sm) *
                      _actionsWidthFraction,
                ),
                child: SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  reverse: true,
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: <Widget>[
                      for (final Widget action in actions)
                        Padding(
                          padding: const EdgeInsets.only(left: GtexSpacing.xs),
                          child: action,
                        ),
                    ],
                  ),
                ),
              ),
            ],
          );
        },
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
    final _BottomNavLayout layout = _BottomNavLayout.from(destinations);
    final int rawIndex = layout.visibleDestinations.indexWhere(
      (GtexShellDestination item) => item.isSelected,
    );
    final bool overflowSelected = layout.overflowDestinations.any(
      (GtexShellDestination item) => item.isSelected,
    );
    final int selectedIndex =
        overflowSelected
            ? layout.visibleDestinations.length
            : rawIndex < 0
            ? 0
            : rawIndex.clamp(0, layout.visibleDestinations.length - 1).toInt();
    return NavigationBar(
      selectedIndex: selectedIndex,
      onDestinationSelected: (int index) {
        if (index < layout.visibleDestinations.length) {
          layout.visibleDestinations[index].onTap();
          return;
        }
        _showMoreDestinations(context, layout.overflowDestinations);
      },
      destinations: <NavigationDestination>[
        for (final GtexShellDestination item in layout.visibleDestinations)
          NavigationDestination(
            icon: Icon(item.icon),
            selectedIcon: Icon(item.selectedIcon),
            label: item.label,
          ),
        if (layout.overflowDestinations.isNotEmpty)
          const NavigationDestination(
            key: Key('gtex-shell-more-destination'),
            icon: Icon(Icons.more_horiz_rounded),
            selectedIcon: Icon(Icons.more_rounded),
            label: 'More',
          ),
      ],
    );
  }

  Future<void> _showMoreDestinations(
    BuildContext context,
    List<GtexShellDestination> overflowDestinations,
  ) {
    return showModalBottomSheet<void>(
      context: context,
      useSafeArea: true,
      backgroundColor: GtexColors.stadiumBlack,
      builder: (BuildContext sheetContext) {
        return ListView.separated(
          shrinkWrap: true,
          padding: const EdgeInsets.fromLTRB(
            GtexSpacing.md,
            GtexSpacing.md,
            GtexSpacing.md,
            GtexSpacing.xl,
          ),
          itemCount: overflowDestinations.length,
          separatorBuilder:
              (_, __) => Divider(color: GtexColors.line.withValues(alpha: 0.4)),
          itemBuilder: (BuildContext context, int index) {
            final GtexShellDestination item = overflowDestinations[index];
            return ListTile(
              key: Key('gtex-shell-more-${item.label}'),
              leading: Icon(
                item.isSelected ? item.selectedIcon : item.icon,
                color: item.isSelected ? item.accent : GtexColors.textMuted,
              ),
              title: Text(
                item.label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  color: item.isSelected ? item.accent : GtexColors.text,
                  fontWeight: FontWeight.w800,
                ),
              ),
              trailing:
                  item.badgeLabel == null
                      ? null
                      : Text(
                        item.badgeLabel!,
                        style: Theme.of(context).textTheme.labelSmall?.copyWith(
                          color: item.accent,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
              selected: item.isSelected,
              onTap: () {
                Navigator.of(sheetContext).pop();
                item.onTap();
              },
            );
          },
        );
      },
    );
  }
}

class _BottomNavLayout {
  const _BottomNavLayout({
    required this.visibleDestinations,
    required this.overflowDestinations,
  });

  final List<GtexShellDestination> visibleDestinations;
  final List<GtexShellDestination> overflowDestinations;

  static _BottomNavLayout from(List<GtexShellDestination> destinations) {
    if (destinations.length <= 5) {
      return _BottomNavLayout(
        visibleDestinations: destinations,
        overflowDestinations: const <GtexShellDestination>[],
      );
    }
    return _BottomNavLayout(
      visibleDestinations: destinations.take(4).toList(growable: false),
      overflowDestinations: destinations.skip(4).toList(growable: false),
    );
  }
}
