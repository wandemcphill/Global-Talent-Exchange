import 'package:flutter/material.dart';
import 'package:gte_frontend/features/club_navigation/models/club_navigation_tab.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

class ClubTopTabs extends StatelessWidget {
  const ClubTopTabs({
    super.key,
    required this.selectedTab,
    required this.onSelected,
    List<ClubNavigationTab>? tabs,
  }) : tabs = tabs ?? ClubNavigationTab.values;

  final ClubNavigationTab selectedTab;
  final ValueChanged<ClubNavigationTab> onSelected;
  final List<ClubNavigationTab> tabs;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 52,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: tabs.length,
        separatorBuilder: (_, __) => const SizedBox(width: 10),
        itemBuilder: (BuildContext context, int index) {
          final ClubNavigationTab tab = tabs[index];
          final bool selected = tab == selectedTab;
          return _ClubTopTabChip(
            tab: tab,
            selected: selected,
            onTap: () => onSelected(tab),
          );
        },
      ),
    );
  }
}

class _ClubTopTabChip extends StatelessWidget {
  const _ClubTopTabChip({
    required this.tab,
    required this.selected,
    required this.onTap,
  });

  final ClubNavigationTab tab;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final Color foregroundColor =
        selected ? GteShellTheme.background : GteShellTheme.textPrimary;
    final Color iconColor =
        selected ? GteShellTheme.background : GteShellTheme.accent;

    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(999),
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          curve: Curves.easeOut,
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(999),
            border: Border.all(
              color: selected
                  ? GteShellTheme.accent.withValues(alpha: 0.5)
                  : GteShellTheme.stroke,
            ),
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: selected
                  ? <Color>[
                      GteShellTheme.accent,
                      GteShellTheme.accentWarm,
                    ]
                  : <Color>[
                      GteShellTheme.panelStrong.withValues(alpha: 0.92),
                      GteShellTheme.panel.withValues(alpha: 0.9),
                    ],
            ),
            boxShadow: selected
                ? <BoxShadow>[
                    BoxShadow(
                      color: GteShellTheme.accent.withValues(alpha: 0.2),
                      blurRadius: 20,
                      offset: const Offset(0, 10),
                    ),
                  ]
                : const <BoxShadow>[],
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              Icon(
                selected ? tab.selectedIcon : tab.icon,
                size: 18,
                color: iconColor,
              ),
              const SizedBox(width: 8),
              Text(
                tab.label,
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                      color: foregroundColor,
                    ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
