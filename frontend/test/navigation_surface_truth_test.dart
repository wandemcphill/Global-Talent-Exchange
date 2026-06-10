import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/navigation/app_destinations.dart';

void main() {
  test('primary nav excludes placeholder routes and records live routes', () {
    final Set<String> primaryLocations =
        appDestinations
            .map((AppDestination destination) => destination.location)
            .toSet();

    expect(primaryLocations, contains(AppRoutes.world));
    expect(
      primaryLocations,
      isNot(contains(AppRoutes.legacyBlockedMatchRuntime)),
    );
    expect(
      appRouteSurfaceFor(AppRoutes.world)?.state,
      AppRouteSurfaceState.live,
    );
    expect(
      appRouteSurfaceFor(AppRoutes.legacyBlockedMatchRuntime)?.state,
      AppRouteSurfaceState.hidden,
    );
    expect(
      appRouteSurfaceFor(AppRoutes.matchesSimulate)?.state,
      AppRouteSurfaceState.hidden,
    );
    expect(appRouteSurfaceFor('/profile/admin/god-mode'), isNull);
  });

  test('quick-action inventory excludes placeholder and hidden routes', () {
    final Set<String> quickActionLocations =
        appRouteInventory
            .where((AppRouteSurface surface) => surface.showInQuickActions)
            .map((AppRouteSurface surface) => surface.location)
            .toSet();

    expect(quickActionLocations, contains(AppRoutes.world));
    expect(
      quickActionLocations,
      isNot(contains(AppRoutes.legacyBlockedMatchRuntime)),
    );
    expect(quickActionLocations, isNot(contains(AppRoutes.matchesSimulate)));
  });

  test('all visible route surfaces stay live', () {
    final Iterable<AppRouteSurface> visibleSurfaces = appRouteInventory.where(
      (AppRouteSurface surface) =>
          surface.showInPrimaryNav || surface.showInQuickActions,
    );

    expect(visibleSurfaces, isNotEmpty);
    for (final AppRouteSurface surface in visibleSurfaces) {
      expect(
        surface.state,
        AppRouteSurfaceState.live,
        reason:
            'Visible route surface ${surface.label} (${surface.location}) '
            'must stay live.',
      );
    }
  });

  test('legacy match rendering inventory stays hidden', () {
    final AppRouteSurface? runtime = appRouteSurfaceFor(
      AppRoutes.legacyMatchRuntime,
    );

    expect(runtime, isNotNull);
    expect(runtime!.state, AppRouteSurfaceState.hidden);
    expect(runtime.label, 'Legacy match runtime');
    expect(runtime.summary, contains('quarantined'));
  });

  test('simulation inventory stays hidden for launch', () {
    final AppRouteSurface? simulation = appRouteSurfaceFor(
      AppRoutes.matchesSimulate,
    );

    expect(simulation, isNotNull);
    expect(simulation!.state, AppRouteSurfaceState.hidden);
    expect(simulation.summary, contains('hidden from launch navigation'));
    expect(simulation.summary.toLowerCase(), contains('backend-authored'));
  });
}
