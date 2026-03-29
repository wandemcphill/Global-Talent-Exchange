import 'package:flutter/material.dart';

class AppRoutes {
  const AppRoutes._();

  static const String root = '/';
  static const String home = '/home';
  static const String matches = '/matches';
  static const String clips = '/clips';
  static const String market = '/market';
  static const String world = '/world';
  static const String tasks = '/tasks';
  static const String profile = '/profile';
  static const String profileLogin = '/profile/login';
  static const String profileSignup = '/profile/signup';
  static const String profileAdmin = '/profile/admin';
  static const String profileGodMode = '/profile/admin/god-mode';
  static const String competitions = '/competitions';
  static const String competitionsFamily = '/competitions/:family';
  static const String competitionsDetail = '/competitions/:family/:id';
  static const String streamerEngine = '/competitions/streamer/engine';
  static const String matchesViewer = '/matches/viewer/:matchKey';
  static const String matchesBroadcast = '/matches/broadcast/:matchKey';
  static const String matchesThreeD = '/matches/3d/:matchKey';
  static const String matchesNativeThreeD = '/matches/native-3d';
  static const String matchesSpectate = '/matches/spectate';
  static const String matchesSimulate = '/matches/simulate';

  static String matchesViewerLocation(String matchKey) =>
      '/matches/viewer/$matchKey';

  static String matchesBroadcastLocation(String matchKey) =>
      '/matches/broadcast/$matchKey';

  static String matchesThreeDLocation(String matchKey) =>
      '/matches/3d/$matchKey';
}

class AppDestination {
  const AppDestination({
    required this.label,
    required this.location,
    required this.icon,
    required this.selectedIcon,
    required this.subtitle,
  });

  final String label;
  final String location;
  final IconData icon;
  final IconData selectedIcon;
  final String subtitle;
}

const List<AppDestination> appDestinations = <AppDestination>[
  AppDestination(
    label: 'Home',
    location: AppRoutes.home,
    icon: Icons.home_outlined,
    selectedIcon: Icons.home_rounded,
    subtitle: 'Command Center',
  ),
  AppDestination(
    label: 'Matches',
    location: AppRoutes.matches,
    icon: Icons.sports_soccer_outlined,
    selectedIcon: Icons.sports_soccer_rounded,
    subtitle: 'Live Match Control',
  ),
  AppDestination(
    label: 'Market',
    location: AppRoutes.market,
    icon: Icons.storefront_outlined,
    selectedIcon: Icons.storefront_rounded,
    subtitle: 'Wallet & Trading Desk',
  ),
  AppDestination(
    label: 'World',
    location: AppRoutes.world,
    icon: Icons.public_outlined,
    selectedIcon: Icons.public_rounded,
    subtitle: 'World Signal Grid',
  ),
  AppDestination(
    label: 'Profile',
    location: AppRoutes.profile,
    icon: Icons.person_outline_rounded,
    selectedIcon: Icons.person_rounded,
    subtitle: 'Operator Profile',
  ),
];
