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
  /// The one published entry nothing registers, in either the router or the
  /// feature-route registry.
  ///
  /// `/tasks` is published as a surface, but `lib/features/tasks/` holds a
  /// provider and no screen at all - there is nothing for a route to open, so
  /// registering one would mean building the feature. It is declared a
  /// placeholder instead, which is what stops Home rendering it as a working
  /// button into an error page.
  ///
  /// Nothing may be added to this list. Removing the entry - by building the
  /// surface and registering it - is the point.
  const Set<String> unregistered = <String>{'/tasks'};

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

  /// A published template is served when some registered path has the same
  /// shape: same segment count, with a `:param` on either side matching
  /// anything. `/matches/broadcast/:matchKey` was invisible to an
  /// equality-only check, and stayed dead because of it.
  bool isServedBy(String published, String registered) {
    if (published == registered) {
      return true;
    }
    final List<String> a = published.split('/');
    final List<String> b = registered.split('/');
    if (a.length != b.length) {
      return false;
    }
    for (int i = 0; i < a.length; i += 1) {
      if (a[i].startsWith(':') || b[i].startsWith(':')) {
        continue;
      }
      if (a[i] != b[i]) {
        return false;
      }
    }
    return true;
  }

  test('the router registers every route the inventory publishes', () {
    // Templates are included. Excluding them is what let two published match
    // redirects sit unregistered through the first pass of this audit.
    final List<String> published = appRouteInventory
        .map((AppRouteSurface surface) => surface.location)
        .toSet()
        .toList(growable: false);

    final List<String> missing = published
        .where(
          (String location) =>
              !registeredPaths.any((String p) => isServedBy(location, p)),
        )
        .where((String location) => !unregistered.contains(location))
        .toList(growable: false);

    expect(
      missing,
      isEmpty,
      reason:
          'these routes are published in appRouteInventory - and any with '
          'quickAction: true are rendered as buttons on the personalised '
          'Home - but nothing registers them, so opening one lands on '
          '"Route unavailable": ${missing.join(', ')}',
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
        .where(
          (String location) =>
              registeredPaths.any((String p) => isServedBy(location, p)),
        )
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
