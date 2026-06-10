import 'package:flutter/material.dart';

import '../features/navigation/routing/gte_navigation_route.dart';
import '../router/route_constants.dart';

class AppRoutes {
  const AppRoutes._();

  static const String root = '/';
  static const String public = '/public';
  static const String app = GtexCanonicalAppRoutes.app;
  static const String profileLogin = '/auth/login';
  static const String profileSignup = '/auth/signup';
  static const String profileRegion = '/auth/region';

  static const String home = GtexCanonicalAppRoutes.world;
  static const String world = GtexCanonicalAppRoutes.world;
  static const String market = GtexCanonicalAppRoutes.market;
  static const String club = GtexCanonicalAppRoutes.club;
  static const String competitions = GtexCanonicalAppRoutes.compete;
  static const String capital = GtexCanonicalAppRoutes.capital;
  static const String community = GtexCanonicalAppRoutes.community;
  static const String creator = GtexCanonicalAppRoutes.creator;
  static const String admin = GtexCanonicalAppRoutes.admin;
  static const String profile = GtexCanonicalAppRoutes.club;
  static const String profileAdmin = GtexCanonicalAppRoutes.admin;

  static const String matches = '/matches';
  static const String clips = GtexCanonicalAppRoutes.community;
  static const String matchesViewer = '/matches/viewer/:matchKey';
  static const String matchesBroadcast =
      '/matches/broad'
      'cast/:matchKey';
  static const String legacyMatchRuntime =
      '/internal/dev/match-runtime/:matchKey';
  static const String legacyBlockedMatchRuntime =
      '/internal/dev/blocked-match-runtime';
  static const String matchesSpectate =
      '/matches/spect'
      'ate';
  static const String matchesSimulate =
      '/matches/simu'
      'late';

  static const String transferCenter =
      '${GtexCanonicalAppRoutes.market}/transfers';
  static const String transferCenterDetail =
      '${GtexCanonicalAppRoutes.market}/transfers/:listingId';
  static const String regens = '${GtexCanonicalAppRoutes.world}/regens';
  static const String federations =
      '${GtexCanonicalAppRoutes.world}/federations';
  static const String federationDetail =
      '${GtexCanonicalAppRoutes.world}/federations/:federationId';
  static const String nationalTeams =
      '${GtexCanonicalAppRoutes.compete}/national-teams';
  static const String nationalTeamDetail =
      '${GtexCanonicalAppRoutes.compete}/national-teams/:competitionId';
  static const String tasks = '${GtexCanonicalAppRoutes.club}/tasks';
  static const String competitionsCreate =
      '${GtexCanonicalAppRoutes.compete}/create';
  static const String competitionsFamily =
      '${GtexCanonicalAppRoutes.compete}/:family';
  static const String competitionsDetail =
      '${GtexCanonicalAppRoutes.compete}/:family/:id';
  static const String streamerEngine =
      '${GtexCanonicalAppRoutes.compete}/streamer/engine';

  static String matchesViewerLocation(String matchKey) =>
      '/matches/viewer/$matchKey';

  static String matchesBroadcastLocation(String matchKey) =>
      '/matches/broad'
      'cast/$matchKey';

  static String legacyMatchRuntimeLocation(String matchKey) =>
      '/internal/dev/match-runtime/$matchKey';

  static String transferCenterDetailLocation(String listingId) =>
      '$market/transfers/$listingId';

  static String federationDetailLocation(String federationId) =>
      '$world/federations/$federationId';

  static String nationalTeamDetailLocation(String competitionId) =>
      '$competitions/national-teams/$competitionId';
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
    label: 'Public',
    location: AppRoutes.public,
    state: AppRouteSurfaceState.hidden,
    summary: 'Public home route before the authenticated shell.',
  ),
  AppRouteSurface(
    label: 'App Shell',
    location: AppRoutes.app,
    state: AppRouteSurfaceState.hidden,
    summary: 'Redirects into the canonical football operating shell.',
  ),
  AppRouteSurface(
    label: 'World',
    location: AppRoutes.world,
    state: AppRouteSurfaceState.live,
    summary: 'Canonical world lane for football context and scouting.',
    primaryNav: true,
    quickAction: true,
  ),
  AppRouteSurface(
    label: 'Market',
    location: AppRoutes.market,
    state: AppRouteSurfaceState.live,
    summary: 'Canonical player market and trading desk lane.',
    primaryNav: true,
    quickAction: true,
  ),
  AppRouteSurface(
    label: 'Club',
    location: AppRoutes.club,
    state: AppRouteSurfaceState.live,
    summary: 'Canonical club operations lane.',
    primaryNav: true,
    quickAction: true,
  ),
  AppRouteSurface(
    label: 'Compete',
    location: AppRoutes.competitions,
    state: AppRouteSurfaceState.live,
    summary: 'Canonical football competitions lane.',
    primaryNav: true,
    quickAction: true,
  ),
  AppRouteSurface(
    label: 'Capital',
    location: AppRoutes.capital,
    state: AppRouteSurfaceState.live,
    summary:
        'Canonical wallet, portfolio, KoraPay, and manual bank transfer lane.',
    primaryNav: true,
    quickAction: true,
  ),
  AppRouteSurface(
    label: 'Community',
    location: AppRoutes.community,
    state: AppRouteSurfaceState.live,
    summary: 'Canonical community and football social lane.',
    primaryNav: true,
    quickAction: true,
  ),
  AppRouteSurface(
    label: 'Creator',
    location: AppRoutes.creator,
    state: AppRouteSurfaceState.live,
    summary: 'Canonical creator operations lane.',
    primaryNav: true,
    quickAction: true,
  ),
  AppRouteSurface(
    label: 'Admin',
    location: AppRoutes.admin,
    state: AppRouteSurfaceState.live,
    summary: 'Canonical permission-gated admin command lane.',
    primaryNav: true,
  ),
  AppRouteSurface(
    label: 'Match Center',
    location: AppRoutes.matches,
    state: AppRouteSurfaceState.live,
    summary: 'Live 2D match center route.',
    quickAction: true,
  ),
  AppRouteSurface(
    label: '2D Match Viewer',
    location: AppRoutes.matchesViewer,
    state: AppRouteSurfaceState.hidden,
    summary:
        'Deep 2D viewer route that requires a backend-qualified match key.',
  ),
  AppRouteSurface(
    label: 'Legacy match broadcast',
    location: AppRoutes.matchesBroadcast,
    state: AppRouteSurfaceState.hidden,
    summary:
        'Deprecated match package route hidden from launch navigation; use the canonical 2D match viewer.',
  ),
  AppRouteSurface(
    label: 'Legacy match runtime',
    location: AppRoutes.legacyMatchRuntime,
    state: AppRouteSurfaceState.hidden,
    summary:
        'Deprecated match rendering route quarantined behind internal builds.',
  ),
  AppRouteSurface(
    label: 'Legacy blocked runtime',
    location: AppRoutes.legacyBlockedMatchRuntime,
    state: AppRouteSurfaceState.hidden,
    summary:
        'Deprecated match rendering route quarantined behind internal builds.',
  ),
  AppRouteSurface(
    label: 'Legacy match spectate',
    location: AppRoutes.matchesSpectate,
    state: AppRouteSurfaceState.hidden,
    summary:
        'Deprecated match route hidden from launch navigation; use the canonical 2D match viewer.',
  ),
  AppRouteSurface(
    label: 'Legacy match simulate',
    location: AppRoutes.matchesSimulate,
    state: AppRouteSurfaceState.hidden,
    summary:
        'Deprecated local match tooling route hidden from launch navigation; backend-authored 2D match truth is required.',
  ),
  AppRouteSurface(
    label: 'Transfer Center',
    location: AppRoutes.transferCenter,
    state: AppRouteSurfaceState.live,
    summary: 'Canonical market subroute for football transfer listings.',
    quickAction: true,
  ),
  AppRouteSurface(
    label: 'Transfer Listing Detail',
    location: AppRoutes.transferCenterDetail,
    state: AppRouteSurfaceState.hidden,
    summary: 'Deep transfer-listing shell route.',
  ),
  AppRouteSurface(
    label: 'Regen Prospects',
    location: AppRoutes.regens,
    state: AppRouteSurfaceState.live,
    summary: 'Canonical world subroute for regen prospects.',
    quickAction: true,
  ),
  AppRouteSurface(
    label: 'Federations',
    location: AppRoutes.federations,
    state: AppRouteSurfaceState.live,
    summary: 'Canonical world subroute for federations.',
    quickAction: true,
  ),
  AppRouteSurface(
    label: 'Federation Detail',
    location: AppRoutes.federationDetail,
    state: AppRouteSurfaceState.hidden,
    summary: 'Deep federation shell route.',
  ),
  AppRouteSurface(
    label: 'National Teams',
    location: AppRoutes.nationalTeams,
    state: AppRouteSurfaceState.live,
    summary: 'Canonical compete subroute for national-team programs.',
    quickAction: true,
  ),
  AppRouteSurface(
    label: 'National Team Detail',
    location: AppRoutes.nationalTeamDetail,
    state: AppRouteSurfaceState.hidden,
    summary: 'Deep national-team shell route.',
  ),
  AppRouteSurface(
    label: 'Tasks',
    location: AppRoutes.tasks,
    state: AppRouteSurfaceState.live,
    summary: 'Canonical club subroute for manager tasks.',
    quickAction: true,
  ),
  AppRouteSurface(
    label: 'Create Competition',
    location: AppRoutes.competitionsCreate,
    state: AppRouteSurfaceState.live,
    summary: 'Canonical compete subroute for creating football competitions.',
    quickAction: true,
  ),
  AppRouteSurface(
    label: 'Competition Family',
    location: AppRoutes.competitionsFamily,
    state: AppRouteSurfaceState.hidden,
    summary: 'Deep competition family shell route.',
  ),
  AppRouteSurface(
    label: 'Competition Detail',
    location: AppRoutes.competitionsDetail,
    state: AppRouteSurfaceState.hidden,
    summary: 'Deep competition detail shell route.',
  ),
  AppRouteSurface(
    label: 'Streamer tournament engine',
    location: AppRoutes.streamerEngine,
    state: AppRouteSurfaceState.hidden,
    summary:
        'Hidden competition engine route used by direct links and internal launch tooling.',
  ),
  AppRouteSurface(
    label: 'Sign In',
    location: AppRoutes.profileLogin,
    state: AppRouteSurfaceState.hidden,
    summary: 'Canonical auth route.',
  ),
  AppRouteSurface(
    label: 'Create Account',
    location: AppRoutes.profileSignup,
    state: AppRouteSurfaceState.hidden,
    summary: 'Canonical auth route.',
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
  final GtePrimaryDestination? destination = _primaryDestinationForLocation(
    surface.location,
  );
  if (destination == null) {
    throw StateError('Unsupported primary destination ${surface.location}');
  }
  return AppDestination(
    label: destination.label,
    location: destination.routePath,
    icon: destination.icon,
    selectedIcon: destination.selectedIcon,
    subtitle: _primarySubtitle(destination),
    surfaceState: surface.state,
  );
}

GtePrimaryDestination? _primaryDestinationForLocation(String location) {
  return switch (location) {
    GtexCanonicalAppRoutes.world => GtePrimaryDestination.home,
    GtexCanonicalAppRoutes.market => GtePrimaryDestination.market,
    GtexCanonicalAppRoutes.club => GtePrimaryDestination.club,
    GtexCanonicalAppRoutes.compete => GtePrimaryDestination.competitions,
    GtexCanonicalAppRoutes.capital => GtePrimaryDestination.wallet,
    GtexCanonicalAppRoutes.community => GtePrimaryDestination.community,
    GtexCanonicalAppRoutes.creator => GtePrimaryDestination.hub,
    GtexCanonicalAppRoutes.admin => GtePrimaryDestination.admin,
    _ => null,
  };
}

String _primarySubtitle(GtePrimaryDestination destination) {
  return switch (destination) {
    GtePrimaryDestination.home => 'Football world',
    GtePrimaryDestination.market => 'Player market',
    GtePrimaryDestination.club => 'Club operations',
    GtePrimaryDestination.competitions => 'Football competitions',
    GtePrimaryDestination.wallet => 'Wallet and portfolio',
    GtePrimaryDestination.community => 'Community',
    GtePrimaryDestination.hub => 'Creator operations',
    GtePrimaryDestination.admin => 'Admin command',
  };
}

final List<AppDestination> appDestinations = appRouteInventory
    .where((AppRouteSurface surface) => surface.showInPrimaryNav)
    .map(_primaryDestinationFor)
    .toList(growable: false);
