import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../app/gte_app_config.dart';
import '../data/gte_exchange_api_client.dart';
import '../data/gte_models.dart';
import '../features/navigation_guards/gte_navigation_guards.dart';
import '../providers/gte_exchange_controller.dart';
import '../router/app_router.dart' as canonical;
import '../shared/models/auth_session.dart';
import '../shared/providers/auth_provider.dart';
import 'app_destinations.dart';

export '../router/app_router.dart' show buildGtexAppRouter;

final Provider<GteExchangeController> _navigationExchangeControllerProvider =
    Provider<GteExchangeController>((Ref ref) {
      final GteAppConfig config = ref.watch(appConfigProvider);
      final GteExchangeController controller = GteExchangeController(
        api: GteExchangeApiClient.standard(
          baseUrl: config.apiBaseUrl,
          mode: config.activeShellBackendMode,
          authSessionStore: ref.watch(authSessionStoreProvider),
          deviceIdentityStore: ref.watch(deviceIdentityStoreProvider),
        ),
      );
      ref.onDispose(controller.dispose);
      return controller;
    });

final Provider<GoRouter> appRouterProvider = Provider<GoRouter>((Ref ref) {
  final GteAppConfig config = ref.watch(appConfigProvider);
  final AuthSession? authSession = ref.watch(authProvider);
  final GteExchangeController controller = ref.watch(
    _navigationExchangeControllerProvider,
  );

  _syncControllerSession(controller, authSession);

  final GoRouter router = canonical.buildGtexAppRouter(
    initialLocation: AppRoutes.home,
    controller: controller,
    config: config,
    dependenciesBuilder:
        (BuildContext context) =>
            _navigationDependencies(ref, config, authSession),
  );
  ref.onDispose(router.dispose);
  return router;
});

GteNavigationDependencies _navigationDependencies(
  Ref ref,
  GteAppConfig config,
  AuthSession? authSession,
) {
  return GteNavigationDependencies(
    apiBaseUrl: config.apiBaseUrl,
    backendMode: config.activeShellBackendMode,
    currentUserId: authSession?.userId ?? 'guest-user',
    currentUserName: _resolvedUserName(authSession),
    currentUserRole: authSession?.role,
    currentClubId: authSession?.clubId,
    currentClubName: authSession?.clubName,
    accessToken: authSession?.accessToken,
    isAuthenticated: authSession?.isAuthenticated ?? false,
    onOpenLogin: (BuildContext context) async {
      context.go(AppRoutes.profileLogin);
      return false;
    },
    currentUserIdProvider: () => ref.read(authProvider)?.userId ?? 'guest-user',
    currentUserNameProvider: () => _resolvedUserName(ref.read(authProvider)),
    currentUserRoleProvider: () => ref.read(authProvider)?.role,
    currentClubIdProvider: () => ref.read(authProvider)?.clubId,
    currentClubNameProvider: () => ref.read(authProvider)?.clubName,
    accessTokenProvider: () => ref.read(authProvider)?.accessToken,
    isAuthenticatedProvider:
        () => ref.read(authProvider)?.isAuthenticated ?? false,
  );
}

void _syncControllerSession(
  GteExchangeController controller,
  AuthSession? session,
) {
  controller.syncSession(_gteSessionFromAuthSession(session));
}

GteAuthSession? _gteSessionFromAuthSession(AuthSession? session) {
  if (session == null || !session.isAuthenticated) {
    return null;
  }
  return GteAuthSession.fromJson(<String, Object?>{
    ...session.rawJson,
    'access_token': session.accessToken,
    'refresh_token': session.refreshToken,
    'session_id': session.sessionId,
    'refresh_expires_in': session.refreshExpiresIn,
    'permissions': session.permissions,
    'user': _normalizedUserPayload(session),
  });
}

Map<String, Object?> _normalizedUserPayload(AuthSession session) {
  final Object? rawUser = session.rawJson['user'];
  final Map<String, Object?> existing =
      rawUser is Map<String, Object?>
          ? Map<String, Object?>.from(rawUser)
          : rawUser is Map
          ? Map<String, Object?>.from(
            rawUser.map(
              (Object? key, Object? value) =>
                  MapEntry<String, Object?>(key.toString(), value),
            ),
          )
          : <String, Object?>{};
  return <String, Object?>{
    ...existing,
    'id': session.userId,
    'email':
        (existing['email']?.toString().trim().isNotEmpty ?? false)
            ? existing['email']
            : '${session.userId}@gtex.local',
    'username':
        (existing['username']?.toString().trim().isNotEmpty ?? false)
            ? existing['username']
            : (session.userName?.trim().isNotEmpty ?? false)
            ? session.userName!.trim()
            : session.userId,
    'display_name':
        session.displayName ??
        session.userName ??
        existing['display_name']?.toString() ??
        'GTEX User',
    'role': session.role,
  };
}

String? _resolvedUserName(AuthSession? session) {
  final String? resolved = session?.resolvedUserName.trim();
  if (resolved == null || resolved.isEmpty || resolved == 'Guest') {
    return null;
  }
  return resolved;
}
