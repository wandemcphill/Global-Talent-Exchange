import 'package:flutter_riverpod/flutter_riverpod.dart';

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

final Provider<AuthSession?> authProvider = Provider<AuthSession?>(
  (Ref ref) => null,
);

final Provider<String> deviceIdProvider = Provider<String>(
  (Ref ref) => throw UnimplementedError('deviceIdProvider must be overridden.'),
);

final Provider<AuthPresentation> authPresentationProvider =
    Provider<AuthPresentation>(
      (Ref ref) => const AuthPresentation(
        userName: 'Ayo McGregor',
        role: 'Club President',
        clubName: 'Lagos Atlas FC',
        avatarAsset: 'assets/branding/gtex_icon.png',
        notifications: 3,
      ),
    );
