import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app/gte_app_config.dart';
import 'navigation/app_router.dart';
import 'services/reliability/reliable_event_queue.dart';
import 'shared/auth/auth_identity_store.dart';
import 'shared/models/auth_session.dart';
import 'shared/providers/auth_provider.dart';
import 'shared/providers/live_clients_provider.dart';
import 'theme/gte_theme_controller.dart';
import 'theme/gte_theme_registry.dart';
import 'theme/gte_theme_scope.dart';
import 'widgets/gte_shell_theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final GteAppConfig appConfig = GteAppConfig.fromEnvironment();
  final SecureAuthSessionStore authSessionStore = SecureAuthSessionStore();
  final SecureDeviceIdentityStore deviceIdentityStore =
      SecureDeviceIdentityStore();
  final AuthSession? authSession = await authSessionStore.readSession();
  final String deviceId = await ensureDeviceId(deviceIdentityStore);
  final GteThemeController themeController = await GteThemeController.bootstrap(
    initialThemeId: GteThemeRegistry.defaultTheme.metadata.id,
  );

  runApp(
    ProviderScope(
      overrides: [
        appConfigProvider.overrideWithValue(appConfig),
        authSessionStoreProvider.overrideWithValue(authSessionStore),
        deviceIdentityStoreProvider.overrideWithValue(deviceIdentityStore),
        initialAuthSessionProvider.overrideWithValue(authSession),
        deviceIdProvider.overrideWithValue(deviceId),
      ],
      child: GtexApp(themeController: themeController),
    ),
  );
}

class GtexApp extends ConsumerStatefulWidget {
  const GtexApp({super.key, this.themeController});

  final GteThemeController? themeController;

  @override
  ConsumerState<GtexApp> createState() => _GtexAppState();
}

class _GtexAppState extends ConsumerState<GtexApp> {
  bool _wasAuthenticated = false;
  late final GteThemeController _themeController;
  late final bool _ownsThemeController;

  @override
  void initState() {
    super.initState();
    _ownsThemeController = widget.themeController == null;
    _themeController =
        widget.themeController ??
        GteThemeController(
          initialThemeId: GteThemeRegistry.defaultTheme.metadata.id,
        );
  }

  @override
  void dispose() {
    if (_ownsThemeController) {
      _themeController.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    ref.watch(sessionHydrationProvider);
    final bool isAuthenticated = ref.watch(isAuthenticatedProvider);
    final exchangeApi = ref.watch(exchangeApiClientProvider);
    gteReliableEventQueue.configure(
      sender: (ReliableQueuedEvent event) async {
        await exchangeApi.trackAnalyticsEvent(
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
      canSend: () => ref.read(isAuthenticatedProvider),
    );
    if (isAuthenticated && !_wasAuthenticated) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        gteReliableEventQueue.markConnectionRestored();
      });
    }
    _wasAuthenticated = isAuthenticated;
    return GteThemeControllerScope(
      controller: _themeController,
      child: AnimatedBuilder(
        animation: _themeController,
        builder: (BuildContext context, Widget? child) {
          return MaterialApp.router(
            debugShowCheckedModeBanner: false,
            title: 'GTEX',
            theme: GteShellTheme.build(_themeController.activeTheme),
            routerConfig: ref.watch(appRouterProvider),
          );
        },
      ),
    );
  }
}
