import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/features/profile/live_profile_provider.dart';
import 'package:gte_frontend/features/profile/profile_admin_screen.dart';
import 'package:gte_frontend/features/profile/profile_screen.dart';
import 'package:gte_frontend/shared/auth/auth_identity_store.dart';
import 'package:gte_frontend/shared/models/auth_session.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';

void main() {
  testWidgets('authenticated admins see the active-shell admin entry', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          authSessionStoreProvider.overrideWithValue(MemoryAuthSessionStore()),
          initialAuthSessionProvider.overrideWithValue(
            const AuthSession(
              userId: 'admin-1',
              accessToken: 'token-1',
              sessionId: 'session-1',
              role: 'admin',
            ),
          ),
          profileDataProvider.overrideWith(
            (Ref ref) async => const ProfileData(
              authenticated: true,
              user: <String, Object?>{
                'id': 'admin-1',
                'display_name': 'Admin User',
                'role': 'admin',
              },
              affinityProfile: <String, Object?>{},
              club: null,
              followers: 10,
              following: 5,
            ),
          ),
        ],
        child: const MaterialApp(home: Scaffold(body: ProfileScreen())),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('Open Admin'), findsOneWidget);
  });

  testWidgets('non-admin users do not see the active-shell admin entry', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          authSessionStoreProvider.overrideWithValue(MemoryAuthSessionStore()),
          initialAuthSessionProvider.overrideWithValue(
            const AuthSession(
              userId: 'user-1',
              accessToken: 'token-1',
              sessionId: 'session-1',
              role: 'user',
            ),
          ),
          profileDataProvider.overrideWith(
            (Ref ref) async => const ProfileData(
              authenticated: true,
              user: <String, Object?>{
                'id': 'user-1',
                'display_name': 'Regular User',
                'role': 'user',
              },
              affinityProfile: <String, Object?>{},
              club: null,
              followers: 3,
              following: 7,
            ),
          ),
        ],
        child: const MaterialApp(home: Scaffold(body: ProfileScreen())),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('Open Admin'), findsNothing);
  });

  testWidgets(
    'scoped admins only see admin actions backed by their permissions',
    (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authSessionStoreProvider.overrideWithValue(
              MemoryAuthSessionStore(),
            ),
            initialAuthSessionProvider.overrideWithValue(
              const AuthSession(
                userId: 'scoped-admin-1',
                accessToken: 'token-1',
                sessionId: 'session-1',
                role: 'scoped_admin',
                permissions: <String>['manage_manager_supply'],
              ),
            ),
          ],
          child: const MaterialApp(home: Scaffold(body: ProfileAdminScreen())),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('Issue share market'), findsOneWidget);
      expect(find.text('Trigger import'), findsNothing);
      expect(find.text('Resume selected batch'), findsNothing);
      expect(find.text('Open God Mode'), findsNothing);
      expect(find.text('Player import is blocked'), findsOneWidget);
    },
  );
}
