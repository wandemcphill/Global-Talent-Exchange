import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/gte_app_config.dart';
import '../../core/constants/app_breakpoints.dart';
import '../../core/constants/app_spacing.dart';
import '../../data/gte_api_repository.dart';
import '../../navigation/app_destinations.dart';
import '../../widgets/gte_shell_theme.dart';
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
    final GteAppConfig appConfig = GteAppConfig.fromEnvironment();
    final tokens = GteShellTheme.tokensOf(context);
    final visuals = GteShellTheme.visualsOf(context);
    final theme = GteShellTheme.definitionOf(context);
    final StatefulNavigationShell navigationShell = widget.navigationShell;
    final AppDestination destination =
        appDestinations[navigationShell.currentIndex];
    final Size screenSize = MediaQuery.sizeOf(context);
    final bool useRail = screenSize.width >= AppBreakpoints.medium;

    return AppBackground(
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          toolbarHeight: 92,
          titleSpacing: spacingMD,
          title: _ShellTitle(destination: destination),
          actions: <Widget>[
            _SignalPill(
              icon: Icons.cloud_done_rounded,
              label: _runtimePillLabel(appConfig),
              tone: theme.primaryColor,
            ),
            const SizedBox(width: spacingSM),
            _SignalPill(
              icon: Icons.fiber_manual_record_rounded,
              label: theme.metadata.label,
              tone: visuals.heroAccent,
            ),
            const SizedBox(width: spacingSM),
            _NotificationChip(count: auth.notifications),
            const SizedBox(width: spacingSM),
            Container(
              margin: const EdgeInsets.only(right: spacingMD),
              padding: const EdgeInsets.symmetric(
                horizontal: spacingSM,
                vertical: spacingXS,
              ),
              decoration: BoxDecoration(
                color: Color.alphaBlend(
                  visuals.heroAccent.withValues(alpha: 0.08),
                  visuals.shellFill,
                ),
                borderRadius: BorderRadius.circular(tokens.radiusPill),
                border: Border.all(
                  color: visuals.shellBorder.withValues(alpha: 0.94),
                ),
                boxShadow: <BoxShadow>[
                  BoxShadow(
                    color: visuals.navGlow.withValues(alpha: 0.14),
                    blurRadius: 22,
                    offset: const Offset(0, 10),
                  ),
                ],
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
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: <Widget>[
                        Text(
                          auth.userName,
                          style: Theme.of(context).textTheme.labelLarge,
                        ),
                        Text(
                          'Operator',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ],
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
                : _MobileNavDock(
                  currentIndex: navigationShell.currentIndex,
                  onDestinationSelected: _goToBranch,
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
                child: Padding(
                  padding: EdgeInsets.fromLTRB(
                    useRail ? spacingMD : spacingSM,
                    spacingSM,
                    spacingMD,
                    useRail ? spacingMD : 0,
                  ),
                  child: _ShellBodyTransition(
                    currentIndex: navigationShell.currentIndex,
                    child: navigationShell,
                  ),
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

String _runtimePillLabel(GteAppConfig appConfig) {
  final String mode = switch (appConfig.backendMode) {
    GteBackendMode.live => 'LIVE',
    GteBackendMode.fixture => 'FIXTURE',
    GteBackendMode.liveThenFixture => 'HYBRID',
  };
  final Uri? uri = Uri.tryParse(appConfig.apiBaseUrl.trim());
  final String host =
      uri?.host.trim().isNotEmpty == true
          ? uri!.host.trim()
          : appConfig.apiBaseUrl.trim().replaceFirst(RegExp(r'^https?://'), '');
  return '$mode · $host';
}

class _ShellTitle extends StatelessWidget {
  const _ShellTitle({required this.destination});

  final AppDestination destination;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final visuals = GteShellTheme.visualsOf(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: <Widget>[
          Text(
            'GTEX',
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
              letterSpacing: 1.6,
              color: visuals.heroAccent,
            ),
          ),
          const SizedBox(height: 4),
          Row(
            children: <Widget>[
              Text(
                destination.label,
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(width: spacingSM),
              Container(
                width: 38,
                height: 2,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(tokens.radiusPill),
                  gradient: LinearGradient(
                    colors: <Color>[
                      visuals.heroAccent,
                      visuals.heroAccent.withValues(alpha: 0),
                    ],
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            destination.subtitle,
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }
}

class _MobileNavDock extends StatelessWidget {
  const _MobileNavDock({
    required this.currentIndex,
    required this.onDestinationSelected,
  });

  final int currentIndex;
  final ValueChanged<int> onDestinationSelected;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final visuals = GteShellTheme.visualsOf(context);
    return SafeArea(
      minimum: const EdgeInsets.fromLTRB(spacingMD, 0, spacingMD, spacingMD),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(tokens.radiusLarge),
        child: BackdropFilter(
          filter: gtePanelBlur(visuals.glass ? visuals.surfaceBlurSigma : 8),
          child: Container(
            decoration: BoxDecoration(
              color: Color.alphaBlend(
                visuals.heroAccent.withValues(alpha: 0.03),
                visuals.shellFill,
              ),
              borderRadius: BorderRadius.circular(tokens.radiusLarge),
              border: Border.all(
                color: visuals.shellBorder.withValues(alpha: 0.94),
              ),
              boxShadow: <BoxShadow>[
                BoxShadow(
                  color: visuals.navGlow.withValues(alpha: 0.18),
                  blurRadius: 30,
                  offset: const Offset(0, 14),
                ),
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.3),
                  blurRadius: 20,
                  offset: const Offset(0, 10),
                ),
              ],
            ),
            child: NavigationBar(
              selectedIndex: currentIndex,
              onDestinationSelected: onDestinationSelected,
              destinations: appDestinations
                  .map(
                    (AppDestination destination) => NavigationDestination(
                      icon: Icon(destination.icon),
                      selectedIcon: Icon(destination.selectedIcon),
                      label: destination.label,
                    ),
                  )
                  .toList(growable: false),
            ),
          ),
        ),
      ),
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
    final motion = GteShellTheme.motionOf(context);

    return TweenAnimationBuilder<double>(
      key: ValueKey<int>(widget.currentIndex),
      tween: Tween<double>(begin: 0, end: 1),
      duration: motion.slow,
      curve: motion.standardCurve,
      child: RepaintBoundary(child: widget.child),
      builder: (BuildContext context, double value, Widget? child) {
        final double horizontalOffset = (1 - value) * 30 * _direction;
        final double scale = 0.985 + (value * 0.015);
        return Opacity(
          opacity: 0.76 + (value * 0.24),
          child: Transform.translate(
            offset: Offset(horizontalOffset, 0),
            child: Transform.scale(scale: scale, child: child),
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
    final tokens = GteShellTheme.tokensOf(context);
    final visuals = GteShellTheme.visualsOf(context);
    return Container(
      width: extended ? 272 : 110,
      margin: const EdgeInsets.fromLTRB(spacingMD, spacingMD, 0, spacingMD),
      decoration: BoxDecoration(
        color: Color.alphaBlend(
          visuals.heroAccent.withValues(alpha: 0.04),
          visuals.shellFill,
        ),
        borderRadius: BorderRadius.circular(tokens.radiusLarge),
        border: Border.all(color: visuals.shellBorder.withValues(alpha: 0.96)),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.28),
            blurRadius: 24,
            offset: const Offset(0, 18),
          ),
          BoxShadow(
            color: visuals.navGlow.withValues(alpha: 0.12),
            blurRadius: 34,
            spreadRadius: 2,
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(tokens.radiusLarge),
        child: BackdropFilter(
          filter: gtePanelBlur(visuals.glass ? visuals.surfaceBlurSigma : 10),
          child: NavigationRail(
            selectedIndex: currentIndex,
            extended: extended,
            minExtendedWidth: 272,
            groupAlignment: -0.9,
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
                          const _BrandBadge(compact: false),
                          const SizedBox(width: spacingMD),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: <Widget>[
                                Text(
                                  'Global Talent Exchange',
                                  style:
                                      Theme.of(context).textTheme.titleMedium,
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  'Silicon Valley football-tech shell',
                                  style: Theme.of(context).textTheme.bodySmall,
                                ),
                              ],
                            ),
                          ),
                        ],
                      )
                      : const _BrandBadge(compact: true),
            ),
            destinations: appDestinations
                .map(
                  (AppDestination destination) => NavigationRailDestination(
                    icon: Icon(destination.icon),
                    selectedIcon: Icon(destination.selectedIcon),
                    label: Text(destination.label),
                  ),
                )
                .toList(growable: false),
          ),
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
    final theme = GteShellTheme.definitionOf(context);
    final tokens = GteShellTheme.tokensOf(context);
    final visuals = GteShellTheme.visualsOf(context);
    return Container(
      width: compact ? 46 : 56,
      height: compact ? 46 : 56,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(tokens.radiusMedium),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[visuals.heroAccent, theme.secondaryColor],
        ),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: visuals.heroAccent.withValues(alpha: 0.28),
            blurRadius: 22,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      alignment: Alignment.center,
      child: Text(
        'G',
        style: Theme.of(context).textTheme.titleLarge?.copyWith(
          color: theme.onPrimaryColor,
          fontWeight: FontWeight.w900,
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
    final motion = GteShellTheme.motionOf(context);
    final theme = GteShellTheme.definitionOf(context);
    return TweenAnimationBuilder<double>(
      key: ValueKey<int>(count),
      tween: Tween<double>(begin: 0, end: 1),
      duration: motion.medium,
      curve: motion.standardCurve,
      child: _SignalPill(
        icon: Icons.notifications_active_outlined,
        label: '$count',
        tone: theme.tokens.accentCapital,
      ),
      builder: (BuildContext context, double value, Widget? child) {
        return Opacity(
          opacity: value,
          child: Transform.translate(
            offset: Offset(0, -14 * (1 - value)),
            child: child,
          ),
        );
      },
    );
  }
}

class _SignalPill extends StatelessWidget {
  const _SignalPill({
    required this.icon,
    required this.label,
    required this.tone,
  });

  final IconData icon;
  final String label;
  final Color tone;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return Container(
      margin: const EdgeInsets.symmetric(vertical: spacingSM),
      padding: const EdgeInsets.symmetric(
        horizontal: spacingSM,
        vertical: spacingXS,
      ),
      decoration: BoxDecoration(
        color: tone.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(tokens.radiusPill),
        border: Border.all(color: tone.withValues(alpha: 0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Icon(icon, color: tone, size: 16),
          const SizedBox(width: spacingXS),
          Text(
            label,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
              color: tone,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }
}
