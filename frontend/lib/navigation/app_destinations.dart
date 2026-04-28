import 'package:flutter/material.dart';

class AppRoutes {
  const AppRoutes._();

  static const String root = '/';
  static const String home = '/home';
  static const String matches = '/matches';
  static const String clips = '/clips';
  static const String market = '/market';
  static const String transferCenter = '/market/transfers';
  static const String transferCenterDetail = '/market/transfers/:listingId';
  static const String world = '/world';
  static const String regens = '/world/regens';
  static const String federations = '/world/federations';
  static const String federationDetail = '/world/federations/:federationId';
  static const String nationalTeams = '/national-teams';
  static const String nationalTeamDetail = '/national-teams/:competitionId';
  static const String tasks = '/tasks';
  static const String profile = '/profile';
  static const String profileLogin = '/profile/login';
  static const String profileSignup = '/profile/signup';
  static const String profileAdmin = '/profile/admin';
  static const String competitions = '/competitions';
  static const String competitionsCreate = '/competitions/create';
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

  static String transferCenterDetailLocation(String listingId) =>
      '/market/transfers/$listingId';

  static String federationDetailLocation(String federationId) =>
      '/world/federations/$federationId';

  static String nationalTeamDetailLocation(String competitionId) =>
      '/national-teams/$competitionId';
}

enum AppRouteSurfaceState { live, partiallyWired, placeholder, hidden }

extension AppRouteSurfaceStateX on AppRouteSurfaceState {
  String get inventoryLabel {
    return switch (this) {
      AppRouteSurfaceState.live => 'live',
      AppRouteSurfaceState.partiallyWired => 'partially wired',
      AppRouteSurfaceState.placeholder => 'placeholder',
      AppRouteSurfaceState.hidden => 'hidden',
    };
  }

  String? get disclosureLabel {
    return switch (this) {
      AppRouteSurfaceState.live => null,
      AppRouteSurfaceState.partiallyWired => 'Preview',
      AppRouteSurfaceState.placeholder => 'Coming soon',
      AppRouteSurfaceState.hidden => null,
    };
  }
}

class AppRouteSurface {
  const AppRouteSurface({
    required this.label,
    required this.location,
    required this.state,
    required this.summary,
    this.primaryNav = false,
    this.quickAction = false,
  });

  final String label;
  final String location;
  final AppRouteSurfaceState state;
  final String summary;
  final bool primaryNav;
  final bool quickAction;

  bool get showInPrimaryNav =>
      primaryNav && state != AppRouteSurfaceState.placeholder;

  bool get showInQuickActions =>
      quickAction &&
      state != AppRouteSurfaceState.hidden &&
      state != AppRouteSurfaceState.placeholder;
}

class AppDestination {
  const AppDestination({
    required this.label,
    required this.location,
    required this.icon,
    required this.selectedIcon,
    required this.subtitle,
    required this.surfaceState,
  });

  final String label;
  final String location;
  final IconData icon;
  final IconData selectedIcon;
  final String subtitle;
  final AppRouteSurfaceState surfaceState;
}

const List<AppRouteSurface> appRouteInventory = <AppRouteSurface>[
  AppRouteSurface(
    label: 'Root',
    location: AppRoutes.root,
    state: AppRouteSurfaceState.hidden,
    summary: 'Redirect-only route.',
  ),
  AppRouteSurface(
    label: 'Home',
    location: AppRoutes.home,
    state: AppRouteSurfaceState.live,
    summary:
        'Club HQ with squad, fixtures, transfer, and competition entry points.',
    primaryNav: true,
  ),
  AppRouteSurface(
    label: 'Fixtures',
    location: AppRoutes.matches,
    state: AppRouteSurfaceState.live,
    summary: 'Fixtures, live 2D match viewing, and results.',
    primaryNav: true,
    quickAction: true,
  ),
  AppRouteSurface(
    label: 'Clips',
    location: AppRoutes.clips,
    state: AppRouteSurfaceState.live,
    summary: 'Live feed with explicit guest-session auth gating.',
    quickAction: true,
  ),
  AppRouteSurface(
    label: 'Transfer Market',
    location: AppRoutes.market,
    state: AppRouteSurfaceState.live,
    summary: 'Buy, bid, sign, and list players from the live transfer market.',
    primaryNav: true,
    quickAction: true,
  ),
  AppRouteSurface(
    label: 'World',
    location: AppRoutes.world,
    state: AppRouteSurfaceState.live,
    summary:
        'Live world discovery with routed federation, national team, and competition-family entry points. Deeper world programs stay gated to explicit routes as they ship.',
    quickAction: true,
  ),
  AppRouteSurface(
    label: 'Regen Prospects',
    location: AppRoutes.regens,
    state: AppRouteSurfaceState.hidden,
    summary:
        'Dedicated live route for regen prospects, awards, and national-pool players.',
  ),
  AppRouteSurface(
    label: 'Transfer Listings',
    location: AppRoutes.transferCenter,
    state: AppRouteSurfaceState.live,
    summary: 'Dedicated transfer-listing route with player views and bids.',
    quickAction: true,
  ),
  AppRouteSurface(
    label: 'Transfer Listing Detail',
    location: AppRoutes.transferCenterDetail,
    state: AppRouteSurfaceState.hidden,
    summary: 'Deep transfer-listing route.',
  ),
  AppRouteSurface(
    label: 'Federations',
    location: AppRoutes.federations,
    state: AppRouteSurfaceState.live,
    summary:
        'Live federation list, ranking, regional tournament, and governance entry point.',
    quickAction: true,
  ),
  AppRouteSurface(
    label: 'Federation Detail',
    location: AppRoutes.federationDetail,
    state: AppRouteSurfaceState.hidden,
    summary: 'Deep federation detail route.',
  ),
  AppRouteSurface(
    label: 'National Teams',
    location: AppRoutes.nationalTeams,
    state: AppRouteSurfaceState.live,
    summary:
        'Live national-team competitions, rankings, and draft squad route.',
    quickAction: true,
  ),
  AppRouteSurface(
    label: 'National Team Detail',
    location: AppRoutes.nationalTeamDetail,
    state: AppRouteSurfaceState.hidden,
    summary: 'Deep national-team competition route.',
  ),
  AppRouteSurface(
    label: 'Tasks',
    location: AppRoutes.tasks,
    state: AppRouteSurfaceState.live,
    summary: 'Live daily-challenge and streak workflow.',
    quickAction: true,
  ),
  AppRouteSurface(
    label: 'Manager',
    location: AppRoutes.profile,
    state: AppRouteSurfaceState.live,
    summary: 'Manager account, club wallet, and admin access.',
    primaryNav: true,
  ),
  AppRouteSurface(
    label: 'Sign In',
    location: AppRoutes.profileLogin,
    state: AppRouteSurfaceState.hidden,
    summary: 'Deep auth route.',
  ),
  AppRouteSurface(
    label: 'Create Account',
    location: AppRoutes.profileSignup,
    state: AppRouteSurfaceState.hidden,
    summary: 'Deep auth route.',
  ),
  AppRouteSurface(
    label: 'Profile Admin',
    location: AppRoutes.profileAdmin,
    state: AppRouteSurfaceState.hidden,
    summary: 'Permission-gated admin tooling.',
  ),
  AppRouteSurface(
    label: 'Competitions',
    location: AppRoutes.competitions,
    state: AppRouteSurfaceState.live,
    summary: 'Create, join, manage, and review football competitions.',
    primaryNav: true,
    quickAction: true,
  ),
  AppRouteSurface(
    label: 'Create Competition',
    location: AppRoutes.competitionsCreate,
    state: AppRouteSurfaceState.live,
    summary:
        'Authenticated managers can create user-hosted football competitions.',
    quickAction: true,
  ),
  AppRouteSurface(
    label: 'Competition Family',
    location: AppRoutes.competitionsFamily,
    state: AppRouteSurfaceState.hidden,
    summary: 'Deep family route.',
  ),
  AppRouteSurface(
    label: 'Competition Detail',
    location: AppRoutes.competitionsDetail,
    state: AppRouteSurfaceState.hidden,
    summary: 'Deep competition-detail route.',
  ),
  AppRouteSurface(
    label: 'Coming soon',
    location: AppRoutes.streamerEngine,
    state: AppRouteSurfaceState.placeholder,
    summary:
        'Coming soon for launch. Extra competition tools are not in the 2D manager shell.',
  ),
  AppRouteSurface(
    label: '2D Match Viewer',
    location: AppRoutes.matchesViewer,
    state: AppRouteSurfaceState.hidden,
    summary:
        'Deep 2D viewer route that opens the qualified live viewer session or a truthful fallback when the session feed is unavailable.',
  ),
  AppRouteSurface(
    label: 'Coming soon',
    location: AppRoutes.matchesBroadcast,
    state: AppRouteSurfaceState.placeholder,
    summary:
        'Coming soon for launch. 2D match viewing is the active matchday route.',
  ),
  AppRouteSurface(
    label: 'Coming soon',
    location: AppRoutes.matchesThreeD,
    state: AppRouteSurfaceState.placeholder,
    summary:
        'Coming soon for launch. 3D match viewing is blocked in the active shell.',
  ),
  AppRouteSurface(
    label: 'Coming soon',
    location: AppRoutes.matchesNativeThreeD,
    state: AppRouteSurfaceState.placeholder,
    summary:
        'Coming soon for launch. Advanced match viewing is blocked in the active shell.',
  ),
  AppRouteSurface(
    label: 'Spectate',
    location: AppRoutes.matchesSpectate,
    state: AppRouteSurfaceState.placeholder,
    summary: 'Coming soon for launch. Use fixtures and the 2D viewer instead.',
  ),
  AppRouteSurface(
    label: 'Simulation',
    location: AppRoutes.matchesSimulate,
    state: AppRouteSurfaceState.placeholder,
    summary:
        'Coming soon for launch. Local simulation tools are blocked in the active shell.',
  ),
];

AppRouteSurface? appRouteSurfaceFor(String location) {
  for (final AppRouteSurface surface in appRouteInventory) {
    if (surface.location == location) {
      return surface;
    }
  }
  return null;
}

AppDestination _primaryDestinationFor(AppRouteSurface surface) {
  return switch (surface.location) {
    AppRoutes.home => const AppDestination(
      label: 'Club HQ',
      location: AppRoutes.home,
      icon: Icons.home_outlined,
      selectedIcon: Icons.home_rounded,
      subtitle: 'Manager Home',
      surfaceState: AppRouteSurfaceState.live,
    ),
    AppRoutes.matches => const AppDestination(
      label: 'Fixtures',
      location: AppRoutes.matches,
      icon: Icons.sports_soccer_outlined,
      selectedIcon: Icons.sports_soccer_rounded,
      subtitle: '2D Matchday',
      surfaceState: AppRouteSurfaceState.live,
    ),
    AppRoutes.market => const AppDestination(
      label: 'Transfer Market',
      location: AppRoutes.market,
      icon: Icons.storefront_outlined,
      selectedIcon: Icons.storefront_rounded,
      subtitle: 'Sign Players',
      surfaceState: AppRouteSurfaceState.live,
    ),
    AppRoutes.competitions => const AppDestination(
      label: 'Competitions',
      location: AppRoutes.competitions,
      icon: Icons.emoji_events_outlined,
      selectedIcon: Icons.emoji_events_rounded,
      subtitle: 'Fixtures & Prizes',
      surfaceState: AppRouteSurfaceState.live,
    ),
    AppRoutes.profile => const AppDestination(
      label: 'Manager',
      location: AppRoutes.profile,
      icon: Icons.person_outline_rounded,
      selectedIcon: Icons.person_rounded,
      subtitle: 'Club Account',
      surfaceState: AppRouteSurfaceState.live,
    ),
    _ =>
      throw StateError('Unsupported primary destination ${surface.location}'),
  };
}

final List<AppDestination> appDestinations = appRouteInventory
    .where((AppRouteSurface surface) => surface.showInPrimaryNav)
    .map(_primaryDestinationFor)
    .toList(growable: false);
