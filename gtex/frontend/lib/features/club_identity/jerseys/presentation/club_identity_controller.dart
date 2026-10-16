import 'dart:convert';

import 'package:flutter/foundation.dart';

import '../data/badge_profile_dto.dart';
import '../data/club_identity_defaults.dart';
import '../data/club_identity_dto.dart';
import '../data/club_identity_repository.dart';
import '../data/club_identity_validation.dart';
import '../data/jersey_variant_dto.dart';

class ClubIdentityController extends ChangeNotifier {
  ClubIdentityController({
    required this.clubId,
    required ClubIdentityRepository repository,
    this.initialClubName,
  }) : _repository = repository;

  final String clubId;
  final String? initialClubName;
  final ClubIdentityRepository _repository;

  bool isLoading = false;
  bool isSaving = false;
  String? errorMessage;
  String? successMessage;

  ClubIdentityDto? _saved;
  ClubIdentityDto? _draft;
  ClubIdentityDto? _optimisticBackup;

  ClubIdentityDto? get identity => _draft;

  bool get hasIdentity => _draft != null;

  bool get hasUnsavedChanges {
    if (_saved == null || _draft == null) {
      return false;
    }
    return jsonEncode(_saved!.toJson()) != jsonEncode(_draft!.toJson());
  }

  List<String> get warnings {
    final ClubIdentityDto? value = _draft;
    if (value == null) {
      return const <String>[];
    }
    final List<String> issues = <String>[];
    final String? clashWarning =
        ClubIdentityValidation.homeAwayClashWarning(value.jerseySet);
    if (clashWarning != null) {
      issues.add(clashWarning);
    }
    issues.addAll(ClubIdentityValidation.lowContrastWarnings(value.jerseySet));
    return issues;
  }

  Future<void> load() async {
    isLoading = true;
    errorMessage = null;
    notifyListeners();
    try {
      final ClubIdentityDto profile = await _repository.fetchIdentity(clubId);
      _saved = profile;
      _draft = profile;
      successMessage = null;
    } catch (error) {
      errorMessage = 'Could not load club identity. $error';
      _draft = ClubIdentityDefaults.generate(
        clubId: clubId,
        clubName: initialClubName,
      );
      _saved = _draft;
    } finally {
      isLoading = false;
      notifyListeners();
    }
  }

  Future<void> reload() async {
    successMessage = null;
    await load();
  }

  Future<void> saveAll() async {
    final ClubIdentityDto? draft = _draft;
    if (draft == null || isSaving) {
      return;
    }
    isSaving = true;
    errorMessage = null;
    successMessage = null;
    _optimisticBackup = _saved;
    _saved = draft;
    notifyListeners();
    try {
      await _repository.patchIdentity(
        clubId: clubId,
        patch: draft.toIdentityPatchJson(),
      );
      await _repository.patchJerseys(
        clubId: clubId,
        patch: draft.jerseySet.toJson(),
      );
      final ClubIdentityDto reloaded = await _repository.fetchIdentity(clubId);
      _saved = reloaded;
      _draft = reloaded;
      successMessage =
          'Identity saved and reloaded from the latest profile snapshot.';
    } catch (error) {
      _saved = _optimisticBackup;
      errorMessage = 'Could not save identity changes. $error';
    } finally {
      isSaving = false;
      _optimisticBackup = null;
      notifyListeners();
    }
  }

  void discardUnsavedChanges() {
    if (_saved == null) {
      return;
    }
    _draft = _saved;
    successMessage = null;
    errorMessage = null;
    _optimisticBackup = null;
    notifyListeners();
  }

  void resetToGeneratedDefaults() {
    final ClubIdentityDto generated = ClubIdentityDefaults.generate(
      clubId: clubId,
      clubName: _draft?.clubName ?? initialClubName,
    );
    _draft = generated;
    successMessage =
        'Generated a fresh badge and default kit set for this club.';
    notifyListeners();
  }

  void regenerateFallbackKit(JerseyType type) {
    final ClubIdentityDto? current = _draft;
    if (current == null) {
      return;
    }
    final JerseyVariantDto generated = ClubIdentityDefaults.defaultVariant(
      type: type,
      shortCode: current.shortClubCode,
      palette: current.colorPalette,
    );
    _updateIdentity(current.copyWith(
      jerseySet: current.jerseySet.updateVariant(type, generated),
    ));
  }

  void updateClubName(String value) {
    final ClubIdentityDto? current = _draft;
    if (current == null) {
      return;
    }
    _updateIdentity(current.copyWith(clubName: value));
  }

  void updateShortClubCode(String value) {
    final ClubIdentityDto? current = _draft;
    if (current == null) {
      return;
    }
    final String normalized = value.trim().toUpperCase();
    _updateIdentity(current.copyWith(
      shortClubCode: normalized,
      jerseySet: current.jerseySet.copyWith(
        home: current.jerseySet.home.copyWith(frontText: normalized),
        away: current.jerseySet.away.copyWith(frontText: normalized),
        third: current.jerseySet.third.copyWith(frontText: '$normalized ALT'),
        goalkeeper: current.jerseySet.goalkeeper.copyWith(
          frontText: '$normalized GK',
        ),
      ),
      badgeProfile: current.badgeProfile.copyWith(
        initials: normalized,
      ),
    ));
  }

  void updatePalette(ColorPaletteProfileDto palette) {
    final ClubIdentityDto? current = _draft;
    if (current == null) {
      return;
    }
    _updateIdentity(
      ClubIdentityDefaults.buildIdentity(
        clubId: current.clubId,
        clubName: current.clubName,
        shortClubCode: current.shortClubCode,
        colorPalette: palette,
        badgeProfile: current.badgeProfile.copyWith(
          primaryColor: palette.primaryColor,
          secondaryColor: palette.secondaryColor,
          accentColor: palette.accentColor,
        ),
        jerseySet: current.jerseySet.copyWith(
          home: current.jerseySet.home.copyWith(
            shortsColor: palette.shortsColor,
            socksColor: palette.socksColor,
          ),
          away: current.jerseySet.away.copyWith(
            accentColor: palette.accentColor,
          ),
          third: current.jerseySet.third.copyWith(
            accentColor: palette.secondaryColor,
          ),
        ),
      ),
    );
  }

  void bindBadgeToPalette() {
    final ClubIdentityDto? current = _draft;
    if (current == null) {
      return;
    }
    _updateIdentity(current.copyWith(
      badgeProfile: current.badgeProfile.copyWith(
        primaryColor: current.colorPalette.primaryColor,
        secondaryColor: current.colorPalette.secondaryColor,
        accentColor: current.colorPalette.accentColor,
      ),
    ));
  }

  void updateBadge({
    String? initials,
    BadgeShape? shape,
    BadgeIconFamily? iconFamily,
  }) {
    final ClubIdentityDto? current = _draft;
    if (current == null) {
      return;
    }
    _updateIdentity(current.copyWith(
      badgeProfile: current.badgeProfile.copyWith(
        initials: initials ?? current.badgeProfile.initials,
        shape: shape ?? current.badgeProfile.shape,
        iconFamily: iconFamily ?? current.badgeProfile.iconFamily,
      ),
    ));
  }

  void updateJerseyVariant(
    JerseyType type, {
    String? primaryColor,
    String? secondaryColor,
    String? accentColor,
    PatternType? patternType,
    CollarStyle? collarStyle,
    SleeveStyle? sleeveStyle,
    String? shortsColor,
    String? socksColor,
  }) {
    final ClubIdentityDto? current = _draft;
    if (current == null) {
      return;
    }
    final JerseyVariantDto base = current.jerseySet.variantFor(type);
    final JerseyVariantDto updated = base.copyWith(
      primaryColor: primaryColor,
      secondaryColor: secondaryColor,
      accentColor: accentColor,
      patternType: patternType,
      collarStyle: collarStyle,
      sleeveStyle: sleeveStyle,
      shortsColor: shortsColor,
      socksColor: socksColor,
    );
    _updateIdentity(current.copyWith(
      jerseySet: current.jerseySet.updateVariant(type, updated),
    ));
  }

  void _updateIdentity(ClubIdentityDto next) {
    _draft = ClubIdentityDefaults.buildIdentity(
      clubId: next.clubId,
      clubName: next.clubName,
      shortClubCode: next.shortClubCode,
      colorPalette: next.colorPalette,
      badgeProfile: next.badgeProfile,
      jerseySet: next.jerseySet,
    );
    errorMessage = null;
    successMessage = null;
    notifyListeners();
  }
}
