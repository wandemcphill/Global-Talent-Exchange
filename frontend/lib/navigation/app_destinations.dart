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
  static const String coaches = '/coaches';
  static const String lineup = '/lineup';
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
    label: 'Matchday',
    location: AppRoutes.matches,
    state: AppRouteSurfaceState.live,
    summary: 'Matchday desk with live 2D viewing, fixtures, and results.',
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
    label: 'Market',
    location: AppRoutes.market,
    state: AppRouteSurfaceState.live,
    summary:
        'Buy, bid, sign, and list players from the live player market desk.',
    primaryNav: true,
    quickAction: true,
  ),
  AppRouteSurface(
    label: 'World',
    location: AppRoutes.world,
    state: AppRouteSurfaceState.live,
    summary:
        'Live world desk with routed federation, national team, and arena-family entry points. Deeper world programs stay gated to explicit routes as they ship.',
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
  // The live surface is `/national-team`; this plural was the wrong spelling
  // of it and reached the router's error page for want of an alias, which is
  // now registered. Live, as it always claimed to be.
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
  // Both of these have had a live `GoRoute` and a real screen all along -
  // the manager market and the lineup editor, each with its own no-club
  // blocked state - and the personalised Home's club-owner quick actions
  // navigate to them. They were simply never published here, and
  // `appRouteSurfaceFor` returns null for anything absent, so building those
  // quick actions threw a null-check error and replaced the whole panel with
  // a red error box on a club owner's Home.
  AppRouteSurface(
    label: 'Coaches',
    location: AppRoutes.coaches,
    state: AppRouteSurfaceState.live,
    summary: 'Live manager market for hiring and comparing coaches.',
  ),
  AppRouteSurface(
    label: 'Lineup',
    location: AppRoutes.lineup,
    state: AppRouteSurfaceState.live,
    summary: 'Formation and starting-lineup editor for the active club.',
  ),
  AppRouteSurface(
    label: 'Tasks',
    location: AppRoutes.tasks,
    state: AppRouteSurfaceState.live,
    summary: 'Live daily-challenge and streak workflow.',
    quickAction: true,
  ),
  AppRouteSurface(
    label: 'Profile',
    location: AppRoutes.profile,
    state: AppRouteSurfaceState.live,
    summary: 'Profile, club wallet, and admin access.',
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
    label: 'Arena',
    location: AppRoutes.competitions,
    state: AppRouteSurfaceState.live,
    summary:
        'Create, join, manage, and review football competitions from one arena desk.',
    primaryNav: true,
    quickAction: true,
  ),
  AppRouteSurface(
    label: 'Create Arena',
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
    label: 'Streamer Engine Redirect',
    location: AppRoutes.streamerEngine,
    state: AppRouteSurfaceState.hidden,
    summary:
        'Legacy streamer-engine route redirects to the live Competition OS hub.',
  ),
  AppRouteSurface(
    label: '2D Match Viewer',
    location: AppRoutes.matchesViewer,
    state: AppRouteSurfaceState.hidden,
    summary:
        'Deep 2D viewer route that opens the qualified live viewer session or a truthful fallback when the session feed is unavailable.',
  ),
  AppRouteSurface(
    label: 'Broadcast Redirect',
    location: AppRoutes.matchesBroadcast,
    state: AppRouteSurfaceState.hidden,
    summary:
        'Legacy broadcast route redirects to the canonical 2D match viewer.',
  ),
  AppRouteSurface(
    label: '3D Match Redirect',
    location: AppRoutes.matchesThreeD,
    state: AppRouteSurfaceState.hidden,
    summary:
        '3D match route is hidden while Unity is blocked and redirects to the 2D viewer.',
  ),
  AppRouteSurface(
    label: 'Native 3D Redirect',
    location: AppRoutes.matchesNativeThreeD,
    state: AppRouteSurfaceState.hidden,
    summary:
        'Native 3D route is hidden while Unity is blocked and redirects to Matchday.',
  ),
  AppRouteSurface(
    label: 'Spectate Redirect',
    location: AppRoutes.matchesSpectate,
    state: AppRouteSurfaceState.hidden,
    summary: 'Legacy spectate route redirects to the active Matchday surface.',
  ),
  AppRouteSurface(
    label: 'Simulation Redirect',
    location: AppRoutes.matchesSimulate,
    state: AppRouteSurfaceState.hidden,
    summary:
        'Legacy local simulation route redirects to the active Matchday surface.',
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
      label: 'Home',
      location: AppRoutes.home,
      icon: Icons.home_outlined,
      selectedIcon: Icons.home_rounded,
      subtitle: 'Live football board',
      surfaceState: AppRouteSurfaceState.live,
    ),
    AppRoutes.matches => const AppDestination(
      label: 'Matchday',
      location: AppRoutes.matches,
      icon: Icons.sports_soccer_outlined,
      selectedIcon: Icons.sports_soccer_rounded,
      subtitle: '2D live viewer',
      surfaceState: AppRouteSurfaceState.live,
    ),
    AppRoutes.market => const AppDestination(
      label: 'Market',
      location: AppRoutes.market,
      icon: Icons.storefront_outlined,
      selectedIcon: Icons.storefront_rounded,
      subtitle: 'Player trading desk',
      surfaceState: AppRouteSurfaceState.live,
    ),
    AppRoutes.competitions => const AppDestination(
      label: 'Arena',
      location: AppRoutes.competitions,
      icon: Icons.emoji_events_outlined,
      selectedIcon: Icons.emoji_events_rounded,
      subtitle: 'Competitions and prizes',
      surfaceState: AppRouteSurfaceState.live,
    ),
    AppRoutes.profile => const AppDestination(
      label: 'Profile',
      location: AppRoutes.profile,
      icon: Icons.person_outline_rounded,
      selectedIcon: Icons.person_rounded,
      subtitle: 'Identity and controls',
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
