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
