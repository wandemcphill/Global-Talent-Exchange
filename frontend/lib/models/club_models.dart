import 'package:gte_frontend/features/club_identity/dynasty/data/dynasty_profile_dto.dart';
import 'package:gte_frontend/features/club_identity/jerseys/data/club_identity_dto.dart';
import 'package:gte_frontend/features/club_identity/trophies/data/trophy_cabinet_dto.dart';
import 'package:gte_frontend/models/club_branding_models.dart';
import 'package:gte_frontend/models/club_catalog_models.dart';
import 'package:gte_frontend/models/club_reputation_models.dart';

class ClubShowcasePanel {
  const ClubShowcasePanel({
    required this.title,
    required this.value,
    required this.caption,
  });

  final String title;
  final String value;
  final String caption;
}

class ClubLegacyMilestone {
  const ClubLegacyMilestone({
    required this.title,
    required this.subtitle,
    required this.tagLabel,
    required this.unlocked,
  });

  final String title;
  final String subtitle;
  final String tagLabel;
  final bool unlocked;
}

class ClubDashboardData {
  const ClubDashboardData({
    required this.clubId,
    required this.clubName,
    required this.identity,
    required this.reputation,
    required this.trophyCabinet,
    required this.dynastyProfile,
    required this.branding,
    required this.catalog,
    required this.purchaseHistory,
    required this.showcasePanels,
    required this.legacyMilestones,
    this.countryName,
    this.playerCount,
  });

  final String clubId;
  final String clubName;
  final String? countryName;
  final int? playerCount;
  final ClubIdentityDto identity;
  final ClubReputationSummary reputation;
  final TrophyCabinetDto trophyCabinet;
  final DynastyProfileDto dynastyProfile;
  final ClubBrandingProfile branding;
  final List<ClubCatalogItem> catalog;
  final List<ClubPurchaseRecord> purchaseHistory;
  final List<ClubShowcasePanel> showcasePanels;
  final List<ClubLegacyMilestone> legacyMilestones;

  int get equippedCatalogCount => catalog
      .where((ClubCatalogItem item) =>
          item.ownershipStatus == CatalogOwnershipStatus.equipped)
      .length;

  ClubDashboardData copyWith({
    ClubIdentityDto? identity,
    ClubBrandingProfile? branding,
    List<ClubCatalogItem>? catalog,
    List<ClubPurchaseRecord>? purchaseHistory,
    List<ClubShowcasePanel>? showcasePanels,
    List<ClubLegacyMilestone>? legacyMilestones,
  }) {
    return ClubDashboardData(
      clubId: clubId,
      clubName: clubName,
      countryName: countryName,
      playerCount: playerCount,
      identity: identity ?? this.identity,
      reputation: reputation,
      trophyCabinet: trophyCabinet,
      dynastyProfile: dynastyProfile,
      branding: branding ?? this.branding,
      catalog: catalog ?? this.catalog,
      purchaseHistory: purchaseHistory ?? this.purchaseHistory,
      showcasePanels: showcasePanels ?? this.showcasePanels,
      legacyMilestones: legacyMilestones ?? this.legacyMilestones,
    );
  }
}

class ClubRevenueSummary {
  const ClubRevenueSummary({
    required this.label,
    required this.valueLabel,
    required this.caption,
  });

  final String label;
  final String valueLabel;
  final String caption;
}

class ClubRankingEntry {
  const ClubRankingEntry({
    required this.rank,
    required this.clubName,
    required this.metricLabel,
    required this.valueLabel,
    required this.contextLabel,
  });

  final int rank;
  final String clubName;
  final String metricLabel;
  final String valueLabel;
  final String contextLabel;
}

class ClubAdminAnalytics {
  const ClubAdminAnalytics({
    required this.revenueSummaries,
    required this.topClubs,
    required this.topDynasties,
    required this.moderationHeadline,
    required this.moderationHighlights,
  });

  final List<ClubRevenueSummary> revenueSummaries;
  final List<ClubRankingEntry> topClubs;
  final List<ClubRankingEntry> topDynasties;
  final String moderationHeadline;
  final List<String> moderationHighlights;
}
