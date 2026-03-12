import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/club_identity/jerseys/data/badge_profile_dto.dart';
import 'package:gte_frontend/features/club_identity/jerseys/data/club_identity_defaults.dart';
import 'package:gte_frontend/features/club_identity/jerseys/data/club_identity_dto.dart';
import 'package:gte_frontend/features/club_identity/jerseys/data/club_identity_repository.dart';
import 'package:gte_frontend/features/club_identity/jerseys/data/jersey_set_dto.dart';
import 'package:gte_frontend/features/club_identity/jerseys/presentation/club_identity_controller.dart';

void main() {
  test('save identity success clears unsaved changes', () async {
    final _StubRepository repository =
        _StubRepository(ClubIdentityDefaults.generate(
      clubId: 'atlas-fc',
      clubName: 'Atlas FC',
    ));
    final ClubIdentityController controller = ClubIdentityController(
      clubId: 'atlas-fc',
      repository: repository,
    );

    await controller.load();
    controller.updateShortClubCode('AFC');

    expect(controller.hasUnsavedChanges, isTrue);

    await controller.saveAll();

    expect(repository.patchIdentityCalls, 1);
    expect(repository.patchJerseysCalls, 1);
    expect(controller.hasUnsavedChanges, isFalse);
    expect(controller.successMessage, isNotNull);
    expect(controller.errorMessage, isNull);
  });

  test('optimistic save rolls back on failure', () async {
    final _StubRepository repository =
        _StubRepository(ClubIdentityDefaults.generate(
      clubId: 'atlas-fc',
      clubName: 'Atlas FC',
    ))
          ..failPatch = true;
    final ClubIdentityController controller = ClubIdentityController(
      clubId: 'atlas-fc',
      repository: repository,
    );

    await controller.load();
    controller.updateJerseyVariant(
      JerseyType.home,
      primaryColor: '#FFFFFF',
    );

    expect(controller.hasUnsavedChanges, isTrue);

    await controller.saveAll();

    expect(repository.patchIdentityCalls, 1);
    expect(repository.patchJerseysCalls, 0);
    expect(controller.errorMessage, isNotNull);
    expect(controller.hasUnsavedChanges, isTrue);
  });
}

class _StubRepository extends ClubIdentityRepository {
  _StubRepository(this._identity);

  ClubIdentityDto _identity;
  bool failPatch = false;
  int patchIdentityCalls = 0;
  int patchJerseysCalls = 0;

  @override
  Future<BadgeProfileDto> fetchBadge(String clubId) async {
    return _identity.badgeProfile;
  }

  @override
  Future<ClubIdentityDto> fetchIdentity(String clubId) async {
    return _identity;
  }

  @override
  Future<JerseySetDto> fetchJerseys(String clubId) async {
    return _identity.jerseySet;
  }

  @override
  Future<ClubIdentityDto> patchIdentity({
    required String clubId,
    required Map<String, dynamic> patch,
  }) async {
    patchIdentityCalls += 1;
    if (failPatch) {
      throw Exception('patch failed');
    }
    _identity = _identity.copyWith(
      clubName: patch['club_name'] as String? ?? _identity.clubName,
      shortClubCode:
          patch['short_club_code'] as String? ?? _identity.shortClubCode,
      colorPalette: patch['color_palette'] is Map<String, dynamic>
          ? ColorPaletteProfileDto.fromJson(
              patch['color_palette'] as Map<String, dynamic>)
          : _identity.colorPalette,
      badgeProfile: patch['badge_profile'] is Map<String, dynamic>
          ? BadgeProfileDto.fromJson(
              patch['badge_profile'] as Map<String, dynamic>)
          : _identity.badgeProfile,
    );
    return _identity;
  }

  @override
  Future<JerseySetDto> patchJerseys({
    required String clubId,
    required Map<String, dynamic> patch,
  }) async {
    patchJerseysCalls += 1;
    _identity = _identity.copyWith(
      jerseySet: JerseySetDto.fromJson(patch),
    );
    return _identity.jerseySet;
  }
}
