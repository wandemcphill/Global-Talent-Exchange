import 'package:flutter/material.dart';

enum ClubNavigationTab {
  squad(
    id: 'squad',
    label: 'Squad',
    icon: Icons.groups_outlined,
    selectedIcon: Icons.groups,
  ),
  tactics(
    id: 'tactics',
    label: 'Tactics',
    icon: Icons.dashboard_customize_outlined,
    selectedIcon: Icons.dashboard_customize,
  ),
  identity(
    id: 'identity',
    label: 'Identity',
    icon: Icons.shield_outlined,
    selectedIcon: Icons.shield,
  ),
  reputation(
    id: 'reputation',
    label: 'Reputation',
    icon: Icons.stars_outlined,
    selectedIcon: Icons.stars,
  ),
  trophies(
    id: 'trophies',
    label: 'Trophies',
    icon: Icons.emoji_events_outlined,
    selectedIcon: Icons.emoji_events,
  ),
  dynasty(
    id: 'dynasty',
    label: 'Dynasty',
    icon: Icons.timeline_outlined,
    selectedIcon: Icons.timeline,
  ),
  history(
    id: 'history',
    label: 'History',
    icon: Icons.history_edu_outlined,
    selectedIcon: Icons.history_edu,
  );

  const ClubNavigationTab({
    required this.id,
    required this.label,
    required this.icon,
    required this.selectedIcon,
  });

  final String id;
  final String label;
  final IconData icon;
  final IconData selectedIcon;
}
