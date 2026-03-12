enum SponsorshipContractStatus {
  active,
  renewalDue,
  pendingApproval,
  completed,
}

enum SponsorModerationState {
  approved,
  underReview,
  needsChanges,
  blocked,
}

class SponsorshipDashboard {
  const SponsorshipDashboard({
    required this.clubId,
    required this.clubName,
    required this.activeContractValue,
    required this.projectedRenewalValue,
    required this.packages,
    required this.contracts,
    required this.assetSlots,
    required this.notes,
  });

  final String clubId;
  final String clubName;
  final double activeContractValue;
  final double projectedRenewalValue;
  final List<SponsorshipPackage> packages;
  final List<SponsorshipContract> contracts;
  final List<SponsorAssetSlot> assetSlots;
  final List<String> notes;
}

class SponsorshipPackage {
  const SponsorshipPackage({
    required this.id,
    required this.name,
    required this.tierLabel,
    required this.description,
    required this.value,
    required this.durationMonths,
    required this.assetCount,
    required this.inventorySummary,
    required this.deliverables,
    this.isFeatured = false,
  });

  final String id;
  final String name;
  final String tierLabel;
  final String description;
  final double value;
  final int durationMonths;
  final int assetCount;
  final String inventorySummary;
  final List<String> deliverables;
  final bool isFeatured;
}

class SponsorshipContract {
  const SponsorshipContract({
    required this.id,
    required this.sponsorName,
    required this.packageName,
    required this.status,
    required this.totalValue,
    required this.startDate,
    required this.endDate,
    required this.renewalWindowLabel,
    required this.visibilityLabel,
    required this.contactName,
    required this.moderationState,
    required this.deliverables,
    required this.notes,
  });

  final String id;
  final String sponsorName;
  final String packageName;
  final SponsorshipContractStatus status;
  final double totalValue;
  final DateTime startDate;
  final DateTime endDate;
  final String renewalWindowLabel;
  final String visibilityLabel;
  final String contactName;
  final SponsorModerationState moderationState;
  final List<String> deliverables;
  final List<String> notes;

  double get annualizedValue =>
      durationMonths == 0 ? totalValue : totalValue * (12 / durationMonths);

  int get durationMonths {
    final int days = endDate.difference(startDate).inDays;
    if (days <= 0) {
      return 0;
    }
    return (days / 30).round();
  }
}

class SponsorAssetSlot {
  const SponsorAssetSlot({
    required this.id,
    required this.surfaceName,
    required this.placementLabel,
    required this.visibilityLabel,
    required this.moderationState,
    this.sponsorName,
    this.note,
  });

  final String id;
  final String surfaceName;
  final String placementLabel;
  final String visibilityLabel;
  final SponsorModerationState moderationState;
  final String? sponsorName;
  final String? note;
}

class SponsorshipAnalyticsSnapshot {
  const SponsorshipAnalyticsSnapshot({
    required this.totalRevenue,
    required this.averageContractValue,
    required this.renewalRatePercent,
    required this.assetUtilizationPercent,
    required this.pendingReviews,
    required this.flaggedAssets,
    required this.topContracts,
    required this.reviewQueue,
  });

  final double totalRevenue;
  final double averageContractValue;
  final double renewalRatePercent;
  final double assetUtilizationPercent;
  final int pendingReviews;
  final int flaggedAssets;
  final List<SponsorshipContract> topContracts;
  final List<SponsorAssetSlot> reviewQueue;
}
