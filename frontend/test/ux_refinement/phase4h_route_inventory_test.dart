import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/navigation/app_destinations.dart';

/// PHASE 4H - the route inventory and the router must agree.
///
/// `appRouteInventory` is what the product publishes as its route surface,
/// and screens navigate by those constants: the personalised Home turns every
/// `quickAction` entry into a button. `/profile/admin` was published there,
/// navigated to by Home's admin action, and never registered in the router,
/// so the tap fell through to the router's "Route unavailable" page. Nothing
/// caught it, because the drift is invisible until someone taps the control.
///
/// This compares the two lists directly rather than rendering each route,
/// because three different screens in this app render the text "Route
/// unavailable" and only one of them means "not registered".
void main() {
  /// Published entries nothing registers, in either the router or the
  /// feature-route registry - verified by grep as well as by this test: none
  /// of the six is referenced anywhere outside the inventory itself.
  ///
  /// Registering a path means choosing where it goes, and for these that is a
  /// product decision this phase did not have the standing to make:
  ///
  ///  * `/national-teams` and `/tasks` are published as live surfaces but the
  ///    navigation shell has no lane for either, so there is no destination
  ///    to redirect them onto.
  ///  * `/competitions/streamer/engine`, `/matches/native-3d`,
  ///    `/matches/spectate` and `/matches/simulate` each document their own
  ///    intended redirect in the inventory summary, so those four are
  ///    mechanical - but they belong in a change about matchday and
  ///    competition routing, not this one.
  ///
  /// Nothing may be added to this list. Removing an entry - by registering
  /// the route - is the point.
  const Set<String> unregistered = <String>{
    '/national-teams',
    '/tasks',
    '/competitions/streamer/engine',
    '/matches/native-3d',
    '/matches/spectate',
    '/matches/simulate',
  };

  late Set<String> registeredPaths;

  setUpAll(() {
    // Routes reach the app two ways: literal `GoRoute`s in the router, and
    // the feature-route registry's own path table. `/competitions/create`
    // lives only in the second, so a scan of the router alone reports it as
    // dead when it is not.
    final String router =
        File('lib/router/app_router.dart').readAsStringSync() +
        File('lib/features/app_routes/gte_route_data.dart').readAsStringSync();
    final String destinations =
        File('lib/navigation/app_destinations.dart').readAsStringSync();

    final Map<String, String> constants = <String, String>{
      for (final RegExpMatch match in RegExp(
        r"static const String (\w+) = '([^']+)';",
      ).allMatches(destinations))
        match.group(1)!: match.group(2)!,
    };

    registeredPaths = <String>{
      for (final RegExpMatch match in RegExp(
        r"path:\s*'([^']+)'",
      ).allMatches(router))
        match.group(1)!,
      // Routes registered through the shared constants rather than a literal.
      for (final RegExpMatch match in RegExp(
        r'path:\s*AppRoutes\.(\w+)',
      ).allMatches(router))
        if (constants[match.group(1)!] != null) constants[match.group(1)!]!,
    };
  });

  test('the router registers every concrete route the inventory publishes', () {
    final List<String> published = appRouteInventory
        .map((AppRouteSurface surface) => surface.location)
        // Parameterised entries are templates, not destinations.
        .where((String location) => !location.contains(':'))
        .toSet()
        .toList(growable: false);

    final List<String> missing = published
        .where((String location) => !registeredPaths.contains(location))
        .where((String location) => !unregistered.contains(location))
        .toList(growable: false);

    expect(
      missing,
      isEmpty,
      reason:
          'these routes are published in appRouteInventory - and any with '
          'quickAction: true are rendered as buttons on the personalised '
          'Home - but nothing in app_router.dart registers them, so tapping '
          'one lands on "Route unavailable": ${missing.join(', ')}',
    );
  });

  test('the admin entry Home navigates to is registered', () {
    // The one this phase fixed, pinned on its own so it cannot regress back
    // into the quarantine list above.
    expect(
      registeredPaths,
      contains(AppRoutes.profileAdmin),
      reason:
          'HomeScreen\'s admin quick action navigates to '
          '${AppRoutes.profileAdmin}; unregistering it makes that a dead '
          'button again',
    );
  });

  test('the quarantine list holds only routes that are really unregistered', () {
    // Keeps the list honest: once a route is registered its entry here has to
    // go, rather than sitting on as a stale excuse.
    final List<String> stale = unregistered
        .where(registeredPaths.contains)
        .toList(growable: false);

    expect(
      stale,
      isEmpty,
      reason:
          'these are now registered and must be removed from the '
          'unregistered list: ${stale.join(', ')}',
    );
  });
}
