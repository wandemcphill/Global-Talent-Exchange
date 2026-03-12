import 'package:flutter/material.dart';
import 'package:gte_frontend/features/app_routes/gte_app_route_registry.dart';
import 'package:gte_frontend/features/app_routes/gte_route_data.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';

class GteNavigationHelpers {
  const GteNavigationHelpers._();

  static Uri deepLinkFor(GteAppRouteData route) => route.toUri();

  static String locationFor(GteAppRouteData route) => route.toUri().toString();

  static String normalizeRouteName(String routeName) {
    return GteAppRouteParser.normalizeRouteName(routeName);
  }

  static GteAppRouteData? parseDeepLink(Object? raw) {
    return GteAppRouteParser.parse(raw);
  }

  static bool canHandleDeepLink(Object? raw) {
    return parseDeepLink(raw) != null;
  }

  static GteAppRouteData requireNamedRoute(
    String routeName, {
    Map<String, String> pathParameters = const <String, String>{},
    Map<String, String> queryParameters = const <String, String>{},
  }) {
    final GteAppRouteData? route = GteAppRouteParser.fromNamedRequest(
      routeName,
      pathParameters: pathParameters,
      queryParameters: queryParameters,
    );
    if (route == null) {
      throw ArgumentError(
        'Unable to build a route for "$routeName" with the supplied '
        'parameters.',
      );
    }
    return route;
  }

  static Future<T?> pushRoute<T>(
    BuildContext context, {
    required GteAppRouteData route,
    required GteNavigationDependencies dependencies,
  }) {
    final GteAppRouteRegistry registry =
        GteAppRouteRegistry(dependencies: dependencies);
    return Navigator.of(context).push<T>(registry.routeFor<T>(route));
  }

  static Future<T?> pushNamedRoute<T>(
    BuildContext context, {
    required String routeName,
    required GteNavigationDependencies dependencies,
    Map<String, String> pathParameters = const <String, String>{},
    Map<String, String> queryParameters = const <String, String>{},
  }) {
    final GteAppRouteData route = requireNamedRoute(
      routeName,
      pathParameters: pathParameters,
      queryParameters: queryParameters,
    );
    return pushRoute<T>(
      context,
      route: route,
      dependencies: dependencies,
    );
  }

  static Future<T?> pushDeepLink<T>(
    BuildContext context, {
    required Object deepLink,
    required GteNavigationDependencies dependencies,
  }) {
    final GteAppRouteData? route = parseDeepLink(deepLink);
    if (route == null) {
      return Future<T?>.value(null);
    }
    return pushRoute<T>(
      context,
      route: route,
      dependencies: dependencies,
    );
  }

  static Future<bool> tryPushDeepLink(
    BuildContext context, {
    required Object deepLink,
    required GteNavigationDependencies dependencies,
  }) async {
    final GteAppRouteData? route = parseDeepLink(deepLink);
    if (route == null) {
      return false;
    }
    await pushRoute<void>(
      context,
      route: route,
      dependencies: dependencies,
    );
    return true;
  }
}
