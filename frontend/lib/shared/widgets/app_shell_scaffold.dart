import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/constants/app_breakpoints.dart';
import '../../core/constants/app_spacing.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_motion.dart';
import '../../navigation/app_destinations.dart';
import '../providers/auth_provider.dart';
import 'app_background.dart';

class AppShellScaffold extends ConsumerStatefulWidget {
  const AppShellScaffold({super.key, required this.navigationShell});

  final StatefulNavigationShell navigationShell;

  @override
  ConsumerState<AppShellScaffold> createState() => _AppShellScaffoldState();
}

class _AppShellScaffoldState extends ConsumerState<AppShellScaffold> {
  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authPresentationProvider);
    final StatefulNavigationShell navigationShell = widget.navigationShell;
    final AppDestination destination =
        appDestinations[navigationShell.currentIndex];
    final Size screenSize = MediaQuery.sizeOf(context);
    final bool useRail = screenSize.width >= AppBreakpoints.medium;

    return AppBackground(
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          toolbarHeight: 78,
          titleSpacing: spacingMD,
          title: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.center,
            children: <Widget>[
              Text(
                'GTEX',
                style: Theme.of(
                  context,
                ).textTheme.titleLarge?.copyWith(letterSpacing: 1.4),
              ),
              const SizedBox(height: spacingXS),
              Text(
                destination.subtitle,
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ),
          actions: <Widget>[
            _NotificationChip(count: auth.notifications),
            const SizedBox(width: spacingSM),
            Container(
              margin: const EdgeInsets.only(right: spacingMD),
              padding: const EdgeInsets.symmetric(
                horizontal: spacingSM,
                vertical: spacingXS,
              ),
              decoration: BoxDecoration(
                color: AppColors.card.withValues(alpha: 0.84),
                borderRadius: BorderRadius.circular(999),
                border: Border.all(color: AppColors.divider),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  CircleAvatar(
                    radius: 14,
                    backgroundImage: AssetImage(auth.avatarAsset),
                  ),
                  if (screenSize.width >= AppBreakpoints.compact) ...<Widget>[
                    const SizedBox(width: spacingSM),
                    Text(
                      auth.userName,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: AppColors.textPrimary,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
        bottomNavigationBar:
            useRail
                ? null
                : NavigationBar(
                  selectedIndex: navigationShell.currentIndex,
                  onDestinationSelected: _goToBranch,
                  destinations:
                      appDestinations
                          .map(
                            (AppDestination destination) =>
                                NavigationDestination(
                                  icon: Icon(destination.icon),
                                  selectedIcon: Icon(destination.selectedIcon),
                                  label: destination.label,
                                ),
                          )
                          .toList(),
                ),
        body: SafeArea(
          top: false,
          child: Row(
            children: <Widget>[
              if (useRail)
                _DesktopRail(
                  currentIndex: navigationShell.currentIndex,
                  onDestinationSelected: _goToBranch,
                  extended: screenSize.width >= AppBreakpoints.expanded,
                ),
              Expanded(
                child: _ShellBodyTransition(
                  currentIndex: navigationShell.currentIndex,
                  child: navigationShell,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _goToBranch(int index) {
    widget.navigationShell.goBranch(
      index,
      initialLocation: index == widget.navigationShell.currentIndex,
    );
  }
}

class _ShellBodyTransition extends StatefulWidget {
  const _ShellBodyTransition({required this.currentIndex, required this.child});

  final int currentIndex;
  final Widget child;

  @override
  State<_ShellBodyTransition> createState() => _ShellBodyTransitionState();
}

class _ShellBodyTransitionState extends State<_ShellBodyTransition> {
  int _previousIndex = 0;
  int _direction = 1;

  @override
  void didUpdateWidget(covariant _ShellBodyTransition oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.currentIndex == widget.currentIndex) {
      return;
    }

    _direction = widget.currentIndex >= oldWidget.currentIndex ? 1 : -1;
    _previousIndex = oldWidget.currentIndex;
  }

  @override
  Widget build(BuildContext context) {
    if (_previousIndex == widget.currentIndex) {
      _previousIndex = widget.currentIndex;
    }

    return TweenAnimationBuilder<double>(
      key: ValueKey<int>(widget.currentIndex),
      tween: Tween<double>(begin: 0, end: 1),
      duration: AppMotion.slow,
      curve: AppMotion.easeInOut,
      child: RepaintBoundary(child: widget.child),
      builder: (BuildContext context, double value, Widget? child) {
        final double horizontalOffset = (1 - value) * 42 * _direction;
        return Opacity(
          opacity: 0.7 + (value * 0.3),
          child: Transform.translate(
            offset: Offset(horizontalOffset, 0),
            child: child,
          ),
        );
      },
    );
  }
}

class _DesktopRail extends StatelessWidget {
  const _DesktopRail({
    required this.currentIndex,
    required this.onDestinationSelected,
    required this.extended,
  });

  final int currentIndex;
  final ValueChanged<int> onDestinationSelected;
  final bool extended;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: extended ? 248 : 104,
      margin: const EdgeInsets.fromLTRB(spacingMD, spacingMD, 0, spacingMD),
      decoration: BoxDecoration(
        color: AppColors.card.withValues(alpha: 0.84),
        borderRadius: BorderRadius.circular(28),
        border: Border.all(color: AppColors.divider),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.22),
            blurRadius: 24,
            offset: const Offset(0, 18),
          ),
          BoxShadow(
            color: AppColors.primary.withValues(alpha: 0.08),
            blurRadius: 28,
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(28),
        child: NavigationRail(
          selectedIndex: currentIndex,
          extended: extended,
          minExtendedWidth: 248,
          groupAlignment: -0.85,
          onDestinationSelected: onDestinationSelected,
          leading: Padding(
            padding: const EdgeInsets.fromLTRB(
              spacingMD,
              spacingLG,
              spacingMD,
              spacingMD,
            ),
            child:
                extended
                    ? Row(
                      children: <Widget>[
                        _BrandBadge(compact: false),
                        const SizedBox(width: spacingMD),
                        Expanded(
                          child: Text(
                            'Global Talent Exchange',
                            style: Theme.of(context).textTheme.bodyMedium
                                ?.copyWith(fontWeight: FontWeight.w700),
                          ),
                        ),
                      ],
                    )
                    : const _BrandBadge(compact: true),
          ),
          destinations:
              appDestinations
                  .map(
                    (AppDestination destination) => NavigationRailDestination(
                      icon: Icon(destination.icon),
                      selectedIcon: Icon(destination.selectedIcon),
                      label: Text(destination.label),
                    ),
                  )
                  .toList(),
        ),
      ),
    );
  }
}

class _BrandBadge extends StatelessWidget {
  const _BrandBadge({required this.compact});

  final bool compact;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: compact ? 44 : 52,
      height: compact ? 44 : 52,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[AppColors.primary, AppColors.gold],
        ),
      ),
      alignment: Alignment.center,
      child: Text(
        'G',
        style: Theme.of(context).textTheme.titleLarge?.copyWith(
          color: AppColors.background,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }
}

class _NotificationChip extends StatelessWidget {
  const _NotificationChip({required this.count});

  final int count;

  @override
  Widget build(BuildContext context) {
    return TweenAnimationBuilder<double>(
      key: ValueKey<int>(count),
      tween: Tween<double>(begin: 0, end: 1),
      duration: AppMotion.medium,
      curve: AppMotion.easeOut,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: spacingSM),
        padding: const EdgeInsets.symmetric(
          horizontal: spacingSM,
          vertical: spacingXS,
        ),
        decoration: BoxDecoration(
          color: AppColors.card.withValues(alpha: 0.84),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: AppColors.divider),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            const Icon(
              Icons.notifications_active_outlined,
              color: AppColors.gold,
              size: 18,
            ),
            const SizedBox(width: spacingXS),
            Text(
              '$count',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: AppColors.textPrimary,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
      ),
      builder: (BuildContext context, double value, Widget? child) {
        return Opacity(
          opacity: value,
          child: Transform.translate(
            offset: Offset(0, -18 * (1 - value)),
            child: child,
          ),
        );
      },
    );
  }
}
