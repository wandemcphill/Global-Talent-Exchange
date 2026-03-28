import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/auth_session.dart';

final Provider<AuthSession> authProvider = Provider<AuthSession>(
  (Ref ref) => const AuthSession(
    userName: 'Ayo McGregor',
    role: 'Club President',
    clubName: 'Lagos Atlas FC',
    avatarAsset: 'assets/branding/gtex_icon.png',
    notifications: 3,
  ),
);
