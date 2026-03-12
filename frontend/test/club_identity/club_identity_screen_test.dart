import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/club_identity/jerseys/data/badge_profile_dto.dart';
import 'package:gte_frontend/features/club_identity/jerseys/data/club_identity_defaults.dart';
import 'package:gte_frontend/features/club_identity/jerseys/data/club_identity_dto.dart';
import 'package:gte_frontend/features/club_identity/jerseys/data/club_identity_repository.dart';
import 'package:gte_frontend/features/club_identity/jerseys/data/jersey_set_dto.dart';
import 'package:gte_frontend/features/club_identity/jerseys/presentation/club_identity_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('shows loading spinner while identity is fetching',
      (WidgetTester tester) async {
    final Completer<ClubIdentityDto> completer = Completer<ClubIdentityDto>();
    final _DelayedRepository repository =
        _DelayedRepository(completer, _sampleIdentity());

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: ClubIdentityScreen(
          clubId: 'atlas-fc',
          repository: repository,
        ),
      ),
    );

    expect(find.byType(CircularProgressIndicator), findsOneWidget);

    completer.complete(_sampleIdentity());
    await tester.pumpAndSettle();

    expect(find.text('Club Identity'), findsOneWidget);
  });

  testWidgets('shows error and retries on reload',
      (WidgetTester tester) async {
    final _FlakyRepository repository = _FlakyRepository(_sampleIdentity());

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: ClubIdentityScreen(
          clubId: 'atlas-fc',
          repository: repository,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.textContaining('Could not load club identity'), findsOneWidget);

    await tester.ensureVisible(find.text('Reload'));
    await tester.tap(find.text('Reload'));
    await tester.pumpAndSettle();

    expect(find.textContaining('Could not load club identity'), findsNothing);
    expect(find.text('Atlas FC'), findsOneWidget);
  });
}

ClubIdentityDto _sampleIdentity() {
  return ClubIdentityDefaults.generate(
    clubId: 'atlas-fc',
    clubName: 'Atlas FC',
  );
}

class _DelayedRepository extends ClubIdentityRepository {
  _DelayedRepository(this.completer, this.fallback);

  final Completer<ClubIdentityDto> completer;
  final ClubIdentityDto fallback;

  @override
  Future<BadgeProfileDto> fetchBadge(String clubId) async {
    return fallback.badgeProfile;
  }

  @override
  Future<ClubIdentityDto> fetchIdentity(String clubId) => completer.future;

  @override
  Future<JerseySetDto> fetchJerseys(String clubId) async {
    return fallback.jerseySet;
  }

  @override
  Future<ClubIdentityDto> patchIdentity({
    required String clubId,
    required Map<String, dynamic> patch,
  }) async {
    return fallback;
  }

  @override
  Future<JerseySetDto> patchJerseys({
    required String clubId,
    required Map<String, dynamic> patch,
  }) async {
    return fallback.jerseySet;
  }
}

class _FlakyRepository extends ClubIdentityRepository {
  _FlakyRepository(this.identity);

  final ClubIdentityDto identity;
  int attempts = 0;

  @override
  Future<BadgeProfileDto> fetchBadge(String clubId) async {
    return identity.badgeProfile;
  }

  @override
  Future<ClubIdentityDto> fetchIdentity(String clubId) async {
    attempts += 1;
    if (attempts == 1) {
      throw Exception('network down');
    }
    return identity;
  }

  @override
  Future<JerseySetDto> fetchJerseys(String clubId) async {
    return identity.jerseySet;
  }

  @override
  Future<ClubIdentityDto> patchIdentity({
    required String clubId,
    required Map<String, dynamic> patch,
  }) async {
    return identity;
  }

  @override
  Future<JerseySetDto> patchJerseys({
    required String clubId,
    required Map<String, dynamic> patch,
  }) async {
    return identity.jerseySet;
  }
}
