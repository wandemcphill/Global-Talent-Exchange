import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/gte_app_config.dart';
import '../../data/gte_api_repository.dart';
import '../../data/gte_authed_api.dart';
import '../../data/gte_http_transport.dart';
import '../auth/auth_identity_store.dart';
import '../models/auth_presentation.dart';
import '../models/auth_session.dart';

final Provider<AuthSessionStore> authSessionStoreProvider =
    Provider<AuthSessionStore>(
      (Ref ref) =>
          throw UnimplementedError(
            'authSessionStoreProvider must be overridden.',
          ),
    );

final Provider<DeviceIdentityStore> deviceIdentityStoreProvider =
    Provider<DeviceIdentityStore>(
      (Ref ref) =>
          throw UnimplementedError(
            'deviceIdentityStoreProvider must be overridden.',
          ),
    );

final Provider<AuthSession?> initialAuthSessionProvider =
    Provider<AuthSession?>((Ref ref) => null);

final NotifierProvider<AppSessionController, AuthSession?>
appSessionControllerProvider =
    NotifierProvider<AppSessionController, AuthSession?>(
      AppSessionController.new,
    );

final Provider<AuthSession?> authProvider = Provider<AuthSession?>(
  (Ref ref) => ref.watch(appSessionControllerProvider),
);

final Provider<String> deviceIdProvider = Provider<String>(
  (Ref ref) => throw UnimplementedError('deviceIdProvider must be overridden.'),
);

final Provider<bool> isAuthenticatedProvider = Provider<bool>(
  (Ref ref) => ref.watch(authProvider)?.isAuthenticated ?? false,
);

final Provider<String?> accessTokenProvider = Provider<String?>(
  (Ref ref) => ref.watch(authProvider)?.accessToken,
);

final Provider<String?> currentUserIdProvider = Provider<String?>(
  (Ref ref) => ref.watch(authProvider)?.userId,
);

final Provider<String?> currentUserNameProvider = Provider<String?>((Ref ref) {
  final AuthSession? session = ref.watch(authProvider);
  if (session == null) {
    return null;
  }
  final String resolved = session.resolvedUserName.trim();
  return resolved.isEmpty || resolved == 'Guest' ? null : resolved;
});

final Provider<String> currentUserRoleProvider = Provider<String>(
  (Ref ref) => ref.watch(authProvider)?.role ?? 'guest',
);

final Provider<List<String>> currentUserPermissionsProvider =
    Provider<List<String>>(
      (Ref ref) => ref.watch(authProvider)?.permissions ?? const <String>[],
    );

final Provider<bool> isAdminProvider = Provider<bool>(
  (Ref ref) => ref.watch(authProvider)?.isAdmin ?? false,
);

final Provider<ClubContext?> clubContextProvider = Provider<ClubContext?>((
  Ref ref,
) {
  final AuthSession? session = ref.watch(authProvider);
  final String? clubId = session?.clubId?.trim();
  if (clubId == null || clubId.isEmpty) {
    return null;
  }
  return ClubContext(id: clubId, name: session?.clubName);
});

final Provider<GteAppConfig> appConfigProvider = Provider<GteAppConfig>(
  (Ref ref) => GteAppConfig.fromEnvironment(),
);

final Provider<String> apiBaseUrlProvider = Provider<String>(
  (Ref ref) => ref.watch(appConfigProvider).apiBaseUrl,
);

final Provider<GteBackendMode> criticalBackendModeProvider =
    Provider<GteBackendMode>((Ref ref) {
      final GteBackendMode configured =
          ref.watch(appConfigProvider).backendMode;
      return configured == GteBackendMode.fixture
          ? GteBackendMode.fixture
          : GteBackendMode.live;
    });

final Provider<GteAuthedApi> authedApiProvider = Provider<GteAuthedApi>(
  (Ref ref) => GteAuthedApi(
    config: GteRepositoryConfig(
      baseUrl: ref.watch(apiBaseUrlProvider),
      mode: ref.watch(criticalBackendModeProvider),
    ),
    transport: GteHttpTransport(),
    authSession: ref.watch(authProvider),
    deviceId: ref.watch(deviceIdProvider),
    mode: ref.watch(criticalBackendModeProvider),
  ),
);

final FutureProvider<void> sessionHydrationProvider = FutureProvider<void>((
  Ref ref,
) async {
  final AuthSession? session = ref.watch(authProvider);
  if (session == null || !session.isAuthenticated) {
    return;
  }
  final bool alreadyHydrated =
      session.role != 'guest' ||
      session.clubId != null ||
      session.rawJson.containsKey('user') ||
      session.rawJson.containsKey('memberships');
  if (alreadyHydrated) {
    return;
  }
  try {
    final Map<String, dynamic> payload = await ref
        .read(authedApiProvider)
        .getMap('/api/auth/me');
    await ref
        .read(appSessionControllerProvider.notifier)
        .mergeProfile(Map<String, Object?>.from(payload));
  } catch (_) {
    // The shipped path will surface auth failures per-screen without
    // falling back to fixtures. Session hydration is best-effort only.
  }
});

final Provider<AuthPresentation> authPresentationProvider =
    Provider<AuthPresentation>((Ref ref) {
      final AuthSession? session = ref.watch(authProvider);
      return AuthPresentation(
        userName: session?.resolvedUserName ?? 'Guest',
        role: session?.role ?? 'Guest',
        clubName: session?.clubName ?? 'No club context',
        avatarAsset: 'assets/branding/gtex_icon.png',
        notifications: 0,
      );
    });

class AppSessionController extends Notifier<AuthSession?> {
  @override
  AuthSession? build() => ref.watch(initialAuthSessionProvider);

  Future<void> updateSession(AuthSession? session) async {
    state = session;
    await ref.read(authSessionStoreProvider).writeSession(session);
  }

  Future<void> mergeProfile(Map<String, Object?> profileJson) async {
    final AuthSession? current = state;
    if (current == null) {
      return;
    }
    final AuthSession merged = current.mergeProfile(profileJson);
    state = merged;
    await ref.read(authSessionStoreProvider).writeSession(merged);
  }

  Future<void> clear() => updateSession(null);
}
