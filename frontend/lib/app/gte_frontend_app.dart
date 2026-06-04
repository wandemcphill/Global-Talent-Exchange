import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/gte_session_identity.dart';
import '../data/gte_api_repository.dart';
import '../data/gte_exchange_api_client.dart';
import '../data/gte_models.dart';
import '../features/navigation_guards/gte_navigation_guards.dart';
import '../providers/gte_exchange_controller.dart';
import '../screens/gte_login_screen.dart';
import '../router/app_router.dart';
import '../services/reliability/reliable_event_queue.dart';
import '../shared/auth/auth_identity_store.dart';
import '../shared/auth/biometric_unlock_service.dart';
import '../shared/models/auth_session.dart';
import '../shared/providers/auth_provider.dart';
import '../theme/gte_theme_controller.dart';
import '../theme/gte_theme_scope.dart';
import '../widgets/gte_shell_theme.dart';
import 'gte_app_config.dart';

class GteFrontendApp extends StatefulWidget {
  const GteFrontendApp({
    super.key,
    this.controller,
    this.config,
    this.themeController,
    this.authSessionStore,
    this.initialPath = '/app/world',
  });

  final GteExchangeController? controller;
  final GteAppConfig? config;
  final GteThemeController? themeController;
  final AuthSessionStore? authSessionStore;
  final String initialPath;

  @override
  State<GteFrontendApp> createState() => _GteFrontendAppState();
}

class _GteFrontendAppState extends State<GteFrontendApp> {
  late final GteAppConfig _config;
  late final GteExchangeController _controller;
  late final bool _ownsController;
  late final AuthSessionStore _authSessionStore;
  late final TrustedDeviceBiometricUnlockController _biometricUnlockController;
  late final GteThemeController _themeController;
  late final bool _ownsThemeController;
  late final GoRouter _router;
  ProviderContainer? _providerContainer;
  ProviderContainer? _ownedProviderContainer;
  ProviderSubscription<AuthSession?>? _authSessionSubscription;
  bool _usesOwnedProviderContainer = false;
  bool _syncingFromController = false;
  bool _syncingFromProvider = false;

  @override
  void initState() {
    super.initState();
    _config = widget.config ?? GteAppConfig.fromRuntimeEnvironment();
    final GteBackendMode activeBackendMode = _config.activeShellBackendMode;
    _ownsController = widget.controller == null;
    _authSessionStore = widget.authSessionStore ?? SecureAuthSessionStore();
    _biometricUnlockController = TrustedDeviceBiometricUnlockController(
      sessionStore: _authSessionStore,
      biometricUnlockService: LocalBiometricUnlockService(),
    );
    _ownsThemeController = widget.themeController == null;
    _controller =
        widget.controller ??
        GteExchangeController(
          api: GteExchangeApiClient.standard(
            baseUrl: _config.apiBaseUrl,
            mode: activeBackendMode,
            authSessionStore: _authSessionStore,
          ),
        );
    gteReliableEventQueue.configure(
      sender: (ReliableQueuedEvent event) async {
        await _controller.api.trackAnalyticsEvent(
          event.name,
          metadata: <String, Object?>{
            'client_event_id': event.id,
            'topic': event.topic,
            'queued_at': event.createdAt.toUtc().toIso8601String(),
            if (event.feedRefreshTrigger != null)
              'feed_refresh_trigger': event.feedRefreshTrigger!.name,
            ...event.payload,
          },
        );
      },
      canSend: () => _controller.isAuthenticated,
    );
    _themeController = widget.themeController ?? GteThemeController();
    _controller.addListener(_handleControllerChanged);
    _router = buildGtexAppRouter(
      initialLocation: widget.initialPath,
      controller: _controller,
      config: _config,
      dependenciesBuilder: _buildNavigationDependencies,
    );
  }

  @override
  void dispose() {
    _authSessionSubscription?.close();
    _ownedProviderContainer?.dispose();
    _controller.removeListener(_handleControllerChanged);
    if (_ownsController) {
      _controller.dispose();
    }
    if (_ownsThemeController) {
      _themeController.dispose();
    }
    super.dispose();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final ({ProviderContainer container, bool owned}) providerBinding =
        _resolveProviderBinding();
    if (identical(_providerContainer, providerBinding.container) &&
        _usesOwnedProviderContainer == providerBinding.owned) {
      return;
    }
    _authSessionSubscription?.close();
    _providerContainer = providerBinding.container;
    _usesOwnedProviderContainer = providerBinding.owned;
    _authSessionSubscription = providerBinding.container.listen<AuthSession?>(
      appSessionControllerProvider,
      (AuthSession? _, AuthSession? next) {
        _syncProviderSessionIntoController(next);
      },
    );
    _syncControllerSessionIntoProvider();
  }

  @override
  Widget build(BuildContext context) {
    final Widget app = GteThemeControllerScope(
      controller: _themeController,
      child: AnimatedBuilder(
        animation: _themeController,
        builder: (BuildContext context, Widget? child) {
          return MaterialApp.router(
            debugShowCheckedModeBanner: false,
            title: 'GTEX Football Universe',
            theme: GteShellTheme.build(_themeController.activeTheme),
            routerConfig: _router,
            restorationScopeId: 'gtex-app',
          );
        },
      ),
    );
    if (_usesOwnedProviderContainer && _providerContainer != null) {
      return UncontrolledProviderScope(
        container: _providerContainer!,
        child: app,
      );
    }
    return app;
  }

  GteNavigationDependencies _buildNavigationDependencies(BuildContext context) {
    final GteSessionIdentity identity =
        GteSessionIdentity.fromExchangeController(_controller);
    return GteNavigationDependencies(
      apiBaseUrl: _config.apiBaseUrl,
      backendMode: _config.activeShellBackendMode,
      currentUserId: identity.userId,
      currentUserName: identity.userName,
      currentUserRole: _controller.session?.user.role,
      currentClubId: identity.clubId,
      currentClubName: identity.clubName,
      accessToken: _controller.accessToken,
      isAuthenticated: _controller.isAuthenticated,
      onOpenLogin: (BuildContext context) async {
        final bool? signedIn = await Navigator.of(context).push<bool>(
          MaterialPageRoute<bool>(
            builder:
                (BuildContext context) => GteLoginScreen(
                  controller: _controller,
                  biometricUnlockController: _biometricUnlockController,
                ),
          ),
        );
        return signedIn == true;
      },
      currentUserIdProvider:
          () => GteSessionIdentity.fromExchangeController(_controller).userId,
      currentUserNameProvider:
          () => GteSessionIdentity.fromExchangeController(_controller).userName,
      currentUserRoleProvider: () => _controller.session?.user.role,
      currentClubIdProvider:
          () => GteSessionIdentity.fromExchangeController(_controller).clubId,
      currentClubNameProvider:
          () => GteSessionIdentity.fromExchangeController(_controller).clubName,
      accessTokenProvider: () => _controller.accessToken,
      isAuthenticatedProvider: () => _controller.isAuthenticated,
    );
  }

  void _handleControllerChanged() {
    if (_syncingFromProvider) {
      return;
    }
    _syncControllerSessionIntoProvider();
  }

  void _syncControllerSessionIntoProvider() {
    final ProviderContainer? container = _providerContainer;
    if (container == null || _syncingFromProvider) {
      return;
    }
    final AuthSession? next = _authSessionFromGteSession(_controller.session);
    final AuthSession? current = container.read(appSessionControllerProvider);
    if (_authSessionsEquivalent(current, next)) {
      return;
    }
    _syncingFromController = true;
    container
        .read(appSessionControllerProvider.notifier)
        .updateSession(next)
        .whenComplete(() {
          _syncingFromController = false;
        });
  }

  void _syncProviderSessionIntoController(AuthSession? session) {
    if (_syncingFromController) {
      return;
    }
    final GteAuthSession? next = _gteSessionFromAuthSession(session);
    if (_gteSessionsEquivalent(_controller.session, next)) {
      return;
    }
    _syncingFromProvider = true;
    _controller.syncSession(next);
    _syncingFromProvider = false;
  }

  ({ProviderContainer container, bool owned}) _resolveProviderBinding() {
    try {
      return (
        container: ProviderScope.containerOf(context, listen: false),
        owned: false,
      );
    } on StateError {
      _ownedProviderContainer ??= ProviderContainer();
      return (container: _ownedProviderContainer!, owned: true);
    }
  }
}

AuthSession? _authSessionFromGteSession(GteAuthSession? session) {
  if (session == null) {
    return null;
  }
  return AuthSession.fromJson(<String, Object?>{
    ...session.rawJson,
    'access_token': session.accessToken,
    'refresh_token': session.refreshToken,
    'session_id': session.sessionId,
    'refresh_expires_in': session.refreshExpiresIn,
    'permissions': session.permissions,
    'user': <String, Object?>{
      ...session.user.rawJson,
      'id': session.user.id,
      'email': session.user.email,
      'username': session.user.username,
      if (session.user.fullName != null) 'full_name': session.user.fullName,
      if (session.user.phoneNumber != null)
        'phone_number': session.user.phoneNumber,
      if (session.user.displayName != null)
        'display_name': session.user.displayName,
      'role': session.user.role,
      if (session.user.kycStatus != null) 'kyc_status': session.user.kycStatus,
      'is_active': session.user.isActive,
      if (session.user.ageConfirmedAt != null)
        'age_confirmed_at': session.user.ageConfirmedAt!.toIso8601String(),
    },
  });
}

GteAuthSession? _gteSessionFromAuthSession(AuthSession? session) {
  if (session == null) {
    return null;
  }
  return GteAuthSession.fromJson(<String, Object?>{
    ...session.rawJson,
    'access_token': session.accessToken,
    'refresh_token': session.refreshToken,
    'session_id': session.sessionId,
    'refresh_expires_in': session.refreshExpiresIn,
    'role': session.role,
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

bool _authSessionsEquivalent(AuthSession? left, AuthSession? right) {
  if (identical(left, right)) {
    return true;
  }
  if (left == null || right == null) {
    return left == right;
  }
  return left.userId == right.userId &&
      left.accessToken == right.accessToken &&
      left.refreshToken == right.refreshToken &&
      left.sessionId == right.sessionId &&
      left.role == right.role &&
      left.clubId == right.clubId &&
      left.clubName == right.clubName &&
      left.federationId == right.federationId &&
      left.federationName == right.federationName &&
      _stringListsEquivalent(left.permissions, right.permissions);
}

bool _gteSessionsEquivalent(GteAuthSession? left, GteAuthSession? right) {
  if (identical(left, right)) {
    return true;
  }
  if (left == null || right == null) {
    return left == right;
  }
  return left.user.id == right.user.id &&
      left.accessToken == right.accessToken &&
      left.refreshToken == right.refreshToken &&
      left.sessionId == right.sessionId &&
      left.user.role == right.user.role &&
      _stringListsEquivalent(left.permissions, right.permissions);
}

bool _stringListsEquivalent(List<String> left, List<String> right) {
  if (left.length != right.length) {
    return false;
  }
  for (int index = 0; index < left.length; index += 1) {
    if (left[index] != right[index]) {
      return false;
    }
  }
  return true;
}
