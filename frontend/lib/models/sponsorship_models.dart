enum SponsorshipContractStatus {
  active,
  renewalDue,
  pendingApproval,
  completed,
}

enum SponsorModerationState { approved, underReview, needsChanges, blocked }

class SponsorshipDashboard {
  const SponsorshipDashboard({
    required this.clubId,
    required this.clubName,
    required this.activeContractValue,
    required this.activeContractCount,
    required this.settledRevenue,
    required this.packages,
    required this.contracts,
    required this.assetSlots,
    required this.notes,
  });

  final String clubId;
  final String clubName;
  final double activeContractValue;
  final int activeContractCount;
  final double settledRevenue;
  final List<SponsorshipPackage> packages;
  final List<SponsorshipContract> contracts;
  final List<SponsorAssetSlot> assetSlots;
  final List<String> notes;
}

class SponsorshipPackage {
  const SponsorshipPackage({
    required this.id,
    required this.code,
    required this.name,
    required this.tierLabel,
    required this.description,
    required this.value,
    required this.currency,
    required this.durationMonths,
    required this.assetCount,
    required this.assetType,
    required this.payoutSchedule,
    required this.inventorySummary,
    required this.deliverables,
    this.isFeatured = false,
  });

  final String id;
  final String code;
  final String name;
  final String tierLabel;
  final String description;
  final double value;
  final String currency;
  final int durationMonths;
  final int assetCount;
  final String assetType;
  final String payoutSchedule;
  final String inventorySummary;
  final List<String> deliverables;
  final bool isFeatured;
}

class SponsorshipContract {
  const SponsorshipContract({
    required this.id,
    required this.sponsorName,
    required this.packageCode,
    required this.packageName,
    required this.status,
    required this.totalValue,
    required this.currency,
    required this.payoutSchedule,
    required this.startDate,
    required this.endDate,
    required this.assetSlotCodes,
    required this.renewalWindowLabel,
    required this.visibilityLabel,
    required this.contactName,
    required this.moderationState,
    required this.moderationRequired,
    required this.settledValue,
    required this.outstandingValue,
    required this.deliverables,
    required this.notes,
    this.customCopy,
    this.customLogoUrl,
  });

  final String id;
  final String sponsorName;
  final String packageCode;
  final String packageName;
  final SponsorshipContractStatus status;
  final double totalValue;
  final String currency;
  final String payoutSchedule;
  final DateTime startDate;
  final DateTime endDate;
  final List<String> assetSlotCodes;
  final String renewalWindowLabel;
  final String visibilityLabel;
  final String contactName;
  final SponsorModerationState moderationState;
  final bool moderationRequired;
  final double settledValue;
  final double outstandingValue;
  final List<String> deliverables;
  final List<String> notes;
  final String? customCopy;
  final String? customLogoUrl;

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

class SponsorshipContractUpdateDraft {
  const SponsorshipContractUpdateDraft({
    this.customCopy,
    this.customLogoUrl,
    this.moderationStatus,
    this.settleDuePayouts = false,
  });

  final String? customCopy;
  final String? customLogoUrl;
  final String? moderationStatus;
  final bool settleDuePayouts;

  Map<String, Object?> toJson() {
    final Map<String, Object?> json = <String, Object?>{
      'settle_due_payouts': settleDuePayouts,
    };
    if (customCopy != null) {
      json['custom_copy'] = customCopy;
    }
    if (customLogoUrl != null) {
      json['custom_logo_url'] = customLogoUrl;
    }
    if (moderationStatus != null) {
      json['moderation_status'] = moderationStatus;
    }
    return json;
  }
}

class SponsorAssetSlot {
  const SponsorAssetSlot({
    required this.id,
    required this.slotCode,
    required this.assetType,
    required this.isVisible,
    required this.surfaceName,
    required this.placementLabel,
    required this.visibilityLabel,
    required this.moderationState,
    this.sponsorName,
    this.note,
  });

  final String id;
  final String slotCode;
  final String assetType;
  final bool isVisible;
  final String surfaceName;
  final String placementLabel;
  final String visibilityLabel;
  final SponsorModerationState moderationState;
  final String? sponsorName;
  final String? note;
}

class SponsorshipApplicationDraft {
  const SponsorshipApplicationDraft({
    required this.packageCode,
    required this.sponsorName,
    required this.durationMonths,
    this.currency = 'USD',
    this.customCopy,
    this.customLogoUrl,
    this.activateImmediately = true,
  });

  final String packageCode;
  final String sponsorName;
  final int durationMonths;
  final String currency;
  final String? customCopy;
  final String? customLogoUrl;
  final bool activateImmediately;

  Map<String, Object?> toJson() {
    return <String, Object?>{
      'package_code': packageCode,
      'sponsor_name': sponsorName,
      'duration_months': durationMonths,
      'currency': currency,
      'custom_copy': customCopy,
      'custom_logo_url': customLogoUrl,
      'activate_immediately': activateImmediately,
    };
  }
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
