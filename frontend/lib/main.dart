import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/theme/app_theme.dart';
import 'navigation/app_router.dart';
import 'shared/auth/auth_identity_store.dart';
import 'shared/models/auth_session.dart';
import 'shared/providers/auth_provider.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final SecureAuthSessionStore authSessionStore = SecureAuthSessionStore();
  final SecureDeviceIdentityStore deviceIdentityStore =
      SecureDeviceIdentityStore();
  final AuthSession? authSession = await authSessionStore.readSession();
  final String deviceId = await ensureDeviceId(deviceIdentityStore);

  runApp(
    ProviderScope(
      overrides: [
        authSessionStoreProvider.overrideWithValue(authSessionStore),
        deviceIdentityStoreProvider.overrideWithValue(deviceIdentityStore),
        initialAuthSessionProvider.overrideWithValue(authSession),
        deviceIdProvider.overrideWithValue(deviceId),
      ],
      child: const GtexApp(),
    ),
  );
}

class GtexApp extends ConsumerWidget {
  const GtexApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    ref.watch(sessionHydrationProvider);
    return MaterialApp.router(
      debugShowCheckedModeBanner: false,
      title: 'GTEX',
      theme: AppTheme.dark(),
      routerConfig: ref.watch(appRouterProvider),
    );
  }
}
