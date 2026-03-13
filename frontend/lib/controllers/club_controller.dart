import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:gte_frontend/data/club_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/club_identity/jerseys/data/club_identity_dto.dart';
import 'package:gte_frontend/features/club_identity/jerseys/data/jersey_set_dto.dart';
import 'package:gte_frontend/features/club_identity/jerseys/data/jersey_variant_dto.dart';
import 'package:gte_frontend/features/club_identity/reputation/data/reputation_models.dart';
import 'package:gte_frontend/models/club_branding_models.dart';
import 'package:gte_frontend/models/club_catalog_models.dart';
import 'package:gte_frontend/models/club_models.dart';
import 'package:gte_frontend/models/club_reputation_models.dart';

class ClubController extends ChangeNotifier {
  ClubController({
    required this.api,
    required this.clubId,
    this.clubName,
  });

  factory ClubController.standard({
    required String clubId,
    String? clubName,
    required String baseUrl,
    GteBackendMode backendMode = GteBackendMode.liveThenFixture,
  }) {
    return ClubController(
      api: ClubApi.standard(baseUrl: baseUrl, mode: backendMode),
      clubId: clubId,
      clubName: clubName,
    );
  }

  final ClubApi api;
  final String clubId;
  Future<void>? _loadFuture;
  DateTime? dataSyncedAt;
  final String? clubName;

  bool isLoading = false;
  bool isSavingIdentity = false;
  bool isSavingBranding = false;
  bool isProcessingCatalog = false;
  bool isLoadingAdmin = false;

  String? errorMessage;
  String? noticeMessage;
  String catalogCategory = 'All';
  JerseyType selectedKit = JerseyType.home;

  ClubDashboardData? _savedData;
  ClubDashboardData? _data;
  ClubAdminAnalytics? adminAnalytics;
  List<BrandingReviewCase> moderationQueue = const <BrandingReviewCase>[];

  ClubDashboardData? get data => _data;
  ClubIdentityDto? get identity => _data?.identity;
  ClubBrandingProfile? get branding => _data?.branding;
  ClubReputationSummary? get reputation => _data?.reputation;
  JerseyVariantDto? get selectedKitVariant =>
      identity?.jerseySet.variantFor(selectedKit);

  List<ClubCatalogItem> get catalog => _data?.catalog ?? const <ClubCatalogItem>[];
  List<ClubPurchaseRecord> get purchaseHistory =>
      _data?.purchaseHistory ?? const <ClubPurchaseRecord>[];

  List<ClubCatalogItem> get filteredCatalog {
    final List<ClubCatalogItem> items = catalog;
    if (catalogCategory == 'All') {
      return items;
    }
    return items
        .where((ClubCatalogItem item) => item.category == catalogCategory)
        .toList(growable: false);
  }

  List<String> get catalogCategories {
    final Set<String> categories = <String>{'All'};
    for (final ClubCatalogItem item in catalog) {
      categories.add(item.category);
    }
    return categories.toList(growable: false);
  }

  bool get hasData => _data != null;

  bool get hasIdentityChanges {
    final ClubDashboardData? current = _data;
    final ClubDashboardData? saved = _savedData;
    if (current == null || saved == null) {
      return false;
    }
    return jsonEncode(current.identity.toJson()) !=
        jsonEncode(saved.identity.toJson());
  }

  bool get hasBrandingChanges {
    final ClubDashboardData? current = _data;
    final ClubDashboardData? saved = _savedData;
    if (current == null || saved == null) {
      return false;
    }
    return jsonEncode(current.branding.toJson()) !=
        jsonEncode(saved.branding.toJson());
  }

  String get displayClubName =>
      _data?.clubName ?? clubName ?? prettifyClubId(clubId);

  Future<void> ensureLoaded() async {
    if (isLoading || hasData) {
      return;
    }
    await load();
  }

  Future<void> load() {
    if (_loadFuture != null) {
      return _loadFuture!;
    }
    isLoading = true;
    errorMessage = null;
    notifyListeners();
    final Future<void> task = () async {
      try {
        final ClubDashboardData dashboard = await api.fetchDashboard(
          clubId: clubId,
          clubName: clubName,
        );
        _savedData = dashboard;
        _data = dashboard;
        dataSyncedAt = DateTime.now().toUtc();
        noticeMessage = null;
      } catch (error) {
        errorMessage = 'Unable to load club identity surfaces. $error';
      } finally {
        isLoading = false;
        _loadFuture = null;
        notifyListeners();
      }
    }();
    _loadFuture = task;
    return task;
  }

  Future<void> refresh() => load();

  Future<void> loadAdmin() async {
    isLoadingAdmin = true;
    notifyListeners();
    try {
      adminAnalytics = await api.fetchAdminAnalytics();
      moderationQueue = await api.fetchBrandingModerationQueue();
    } catch (error) {
      errorMessage = 'Unable to load club admin surfaces. $error';
    } finally {
      isLoadingAdmin = false;
      notifyListeners();
    }
  }

  void setCatalogCategory(String category) {
    if (catalogCategory == category) {
      return;
    }
    catalogCategory = category;
    notifyListeners();
  }

  void setSelectedKit(JerseyType type) {
    if (selectedKit == type) {
      return;
    }
    selectedKit = type;
    notifyListeners();
  }

  void updateSelectedKit({
    String? primaryColor,
    String? secondaryColor,
    String? accentColor,
    String? shortsColor,
    String? socksColor,
    PatternType? patternType,
    CollarStyle? collarStyle,
    SleeveStyle? sleeveStyle,
    String? badgePlacement,
  }) {
    final ClubDashboardData? current = _data;
    if (current == null) {
      return;
    }
    final JerseyVariantDto variant =
        current.identity.jerseySet.variantFor(selectedKit);
    final JerseyVariantDto updated = variant.copyWith(
      primaryColor: primaryColor,
      secondaryColor: secondaryColor,
      accentColor: accentColor,
      shortsColor: shortsColor,
      socksColor: socksColor,
      patternType: patternType,
      collarStyle: collarStyle,
      sleeveStyle: sleeveStyle,
      badgePlacement: badgePlacement,
    );
    final JerseySetDto updatedSet =
        current.identity.jerseySet.updateVariant(selectedKit, updated);
    _data = current.copyWith(
      identity: current.identity.copyWith(jerseySet: updatedSet),
    );
    notifyListeners();
  }

  void updateBrandingTheme(String themeId) {
    final ClubDashboardData? current = _data;
    if (current == null) {
      return;
    }
    _data = current.copyWith(
      branding: current.branding.copyWith(selectedThemeId: themeId),
    );
    notifyListeners();
  }

  void updateBackdrop(String backdropId) {
    final ClubDashboardData? current = _data;
    if (current == null) {
      return;
    }
    _data = current.copyWith(
      branding: current.branding.copyWith(selectedBackdropId: backdropId),
    );
    notifyListeners();
  }

  void updateMotto(String motto) {
    final ClubDashboardData? current = _data;
    if (current == null) {
      return;
    }
    _data = current.copyWith(
      branding: current.branding.copyWith(motto: motto),
    );
    notifyListeners();
  }

  Future<void> saveIdentity() async {
    final ClubDashboardData? current = _data;
    if (current == null || isSavingIdentity) {
      return;
    }
    isSavingIdentity = true;
    errorMessage = null;
    notifyListeners();
    try {
      final ClubIdentityDto saved = await api.saveIdentity(
        clubId: clubId,
        identity: current.identity,
      );
      _savedData = current.copyWith(identity: saved);
      _data = _savedData;
      noticeMessage = 'Jersey design and club identity updates were saved.';
    } catch (error) {
      errorMessage = 'Unable to save jersey design changes. $error';
    } finally {
      isSavingIdentity = false;
      notifyListeners();
    }
  }

  Future<void> saveBranding() async {
    final ClubDashboardData? current = _data;
    if (current == null || isSavingBranding) {
      return;
    }
    isSavingBranding = true;
    errorMessage = null;
    notifyListeners();
    try {
      final ClubBrandingProfile saved = await api.saveBranding(
        clubId: clubId,
        branding: current.branding,
      );
      _savedData = current.copyWith(branding: saved);
      _data = _savedData;
      noticeMessage = 'Branding theme, motto, and showcase backdrop were saved.';
    } catch (error) {
      errorMessage = 'Unable to save club branding updates. $error';
    } finally {
      isSavingBranding = false;
      notifyListeners();
    }
  }

  Future<void> purchaseCatalogItem(ClubCatalogItem item) async {
    if (isProcessingCatalog) {
      return;
    }
    isProcessingCatalog = true;
    errorMessage = null;
    notifyListeners();
    try {
      await api.purchaseCatalogItem(clubId: clubId, item: item);
      await _reloadDashboardWithMessage(
        'Catalog purchase confirmed. The cosmetic is now in your club locker.',
      );
    } catch (error) {
      errorMessage = 'Unable to complete the catalog purchase. $error';
    } finally {
      isProcessingCatalog = false;
      notifyListeners();
    }
  }

  Future<void> equipCatalogItem(ClubCatalogItem item) async {
    if (isProcessingCatalog) {
      return;
    }
    isProcessingCatalog = true;
    errorMessage = null;
    notifyListeners();
    try {
      await api.equipCatalogItem(clubId: clubId, item: item);
      await _reloadDashboardWithMessage(
        '${item.title} is now equipped in the club showcase.',
      );
    } catch (error) {
      errorMessage = 'Unable to equip the selected cosmetic. $error';
    } finally {
      isProcessingCatalog = false;
      notifyListeners();
    }
  }

  Future<void> moderateBranding({
    required String reviewId,
    required bool approved,
  }) async {
    try {
      await api.updateBrandingReview(reviewId: reviewId, approved: approved);
      await loadAdmin();
      noticeMessage = approved
          ? 'Branding review approved for showcase publication.'
          : 'Branding review sent back for identity refinements.';
    } catch (error) {
      errorMessage = 'Unable to update branding review. $error';
      notifyListeners();
    }
  }

  void clearNotice() {
    if (noticeMessage == null) {
      return;
    }
    noticeMessage = null;
    notifyListeners();
  }

  Future<void> _reloadDashboardWithMessage(String message) async {
    final ClubDashboardData dashboard = await api.fetchDashboard(
      clubId: clubId,
      clubName: clubName,
    );
    _savedData = dashboard;
    _data = dashboard;
    noticeMessage = message;
  }
}
