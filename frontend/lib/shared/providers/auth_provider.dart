import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/auth_session.dart';

const String _environmentAccessToken = String.fromEnvironment(
  'GTE_ACCESS_TOKEN',
  defaultValue: '',
);

final Provider<AuthSession> authProvider = Provider<AuthSession>(
  (Ref ref) => AuthSession(
    userName: 'Ayo McGregor',
    role: 'Club President',
    clubName: 'Lagos Atlas FC',
    avatarAsset: 'assets/branding/gtex_icon.png',
    notifications: 3,
    accessToken:
        _environmentAccessToken.isEmpty ? null : _environmentAccessToken,
  ),
);
