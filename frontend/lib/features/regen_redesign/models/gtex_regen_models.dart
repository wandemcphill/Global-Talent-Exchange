import 'package:flutter/material.dart';

/// Batch 5 view models for the GTEX Regen World redesign.
///
/// These are intentionally UI-facing DTOs. The current live API models
/// (`RegenUniverseHubData`, `RegenCreationOrder`, etc.) are adapted into these
/// models instead of changing backend business logic.
enum GtexRegenOrigin {
  nationalPool,
  clubGenerated,
  createSon,
  academy,
  mystery,
}

enum GtexRegenContractStatus {
  unsigned,
  rentalOnly,
  negotiating,
  signed,
  transferRequested,
}

class GtexRegenWorldData {
  const GtexRegenWorldData({
    required this.prospects,
    required this.awards,
    required this.achievementFeed,
    required this.contracts,
    required this.parentPlayers,
    required this.pricing,
    required this.stats,
  });

  final List<GtexRegenProspect> prospects;
  final List<GtexRegenAward> awards;
  final List<GtexRegenAchievement> achievementFeed;
  final List<GtexRegenContractOffer> contracts;
  final List<GtexParentPlayer> parentPlayers;
  final GtexCreateSonPricing pricing;
  final GtexRegenWorldStats stats;
}

class GtexRegenWorldStats {
  const GtexRegenWorldStats({
    required this.totalRegens,
    required this.nationalPoolCount,
    required this.createSonOrders,
    required this.awardsThisSeason,
  });

  final int totalRegens;
  final int nationalPoolCount;
  final int createSonOrders;
  final int awardsThisSeason;
}

class GtexRegenProspect {
  const GtexRegenProspect({
    required this.id,
    required this.displayName,
    required this.countryCode,
    required this.countryName,
    required this.position,
    required this.age,
    required this.currentRating,
    required this.potentialRating,
    required this.archetype,
    required this.origin,
    required this.contractStatus,
    required this.storyline,
    required this.traits,
    required this.valueCoin,
    this.globalScoutingIndex,
    this.clubName,
    this.imageUrl,
    this.rarityTier = 'Elite',
    this.isTradable = true,
    this.isNationalRentalOnly = false,
  });

  final String id;
  final String displayName;
  final String countryCode;
  final String countryName;
  final String position;
  final int age;
  final int currentRating;
  final int potentialRating;
  final int? globalScoutingIndex;
  final String archetype;
  final GtexRegenOrigin origin;
  final GtexRegenContractStatus contractStatus;
  final String storyline;
  final List<String> traits;
  final double valueCoin;
  final String? clubName;
  final String? imageUrl;
  final String rarityTier;
  final bool isTradable;
  final bool isNationalRentalOnly;

  String get ageLabel => '$age yrs';

  String get potentialLabel => '$potentialRating POT';

  int get gsi => (globalScoutingIndex ?? currentRating).clamp(0, 100).toInt();

  String get gsiLabel => 'GSI $gsi';

  String get currentRatingLabel => 'OVR $currentRating';

  String get gsiTierLabel {
    final int score = gsi;
    if (score >= 90) return 'Elite';
    if (score >= 82) return 'High-grade';
    if (score >= 74) return 'First-team';
    if (score >= 66) return 'Developing';
    return 'Prospect';
  }

  String get originLabel {
    switch (origin) {
      case GtexRegenOrigin.nationalPool:
        return 'National Pool';
      case GtexRegenOrigin.clubGenerated:
        return 'Club Generated';
      case GtexRegenOrigin.createSon:
        return 'Create-a-Son';
      case GtexRegenOrigin.academy:
        return 'Academy';
      case GtexRegenOrigin.mystery:
        return 'Mystery';
    }
  }

  String get contractStatusLabel {
    switch (contractStatus) {
      case GtexRegenContractStatus.unsigned:
        return 'Unsigned';
      case GtexRegenContractStatus.rentalOnly:
        return 'Rental Only';
      case GtexRegenContractStatus.negotiating:
        return 'Negotiating';
      case GtexRegenContractStatus.signed:
        return 'Signed';
      case GtexRegenContractStatus.transferRequested:
        return 'Transfer Request';
    }
  }
}

class GtexRegenAward {
  const GtexRegenAward({
    required this.id,
    required this.name,
    required this.seasonLabel,
    required this.winnerName,
    required this.scoreLabel,
    required this.category,
  });

  final String id;
  final String name;
  final String seasonLabel;
  final String winnerName;
  final String scoreLabel;
  final String category;
}

class GtexRegenAchievement {
  const GtexRegenAchievement({
    required this.id,
    required this.title,
    required this.body,
    required this.timestampLabel,
    this.icon = Icons.auto_awesome,
  });

  final String id;
  final String title;
  final String body;
  final String timestampLabel;
  final IconData icon;
}

class GtexRegenContractOffer {
  const GtexRegenContractOffer({
    required this.id,
    required this.regenId,
    required this.regenName,
    required this.status,
    required this.weeklyWageCoin,
    required this.signingBonusCoin,
    required this.durationSeasons,
    required this.personalityNote,
  });

  final String id;
  final String regenId;
  final String regenName;
  final GtexRegenContractStatus status;
  final double weeklyWageCoin;
  final double signingBonusCoin;
  final int durationSeasons;
  final String personalityNote;

  double get totalCommitmentCoin =>
      signingBonusCoin + weeklyWageCoin * durationSeasons * 38;
}

class GtexParentPlayer {
  const GtexParentPlayer({
    required this.id,
    required this.name,
    required this.position,
    required this.countryCode,
    required this.clubName,
    required this.rating,
    this.imageUrl,
  });

  final String id;
  final String name;
  final String position;
  final String countryCode;
  final String clubName;
  final int rating;
  final String? imageUrl;
}

class GtexCreateSonPricing {
  const GtexCreateSonPricing({
    required this.baseCostCoin,
    required this.nameCustomizationCoin,
    required this.nationalityCustomizationCoin,
    required this.positionCustomizationCoin,
    required this.specialRequestMinimumCoin,
  });

  final double baseCostCoin;
  final double nameCustomizationCoin;
  final double nationalityCustomizationCoin;
  final double positionCustomizationCoin;
  final double specialRequestMinimumCoin;
}

class GtexCreateSonDraft {
  const GtexCreateSonDraft({
    required this.parentPlayerId,
    required this.paymentMethod,
    this.requestedName,
    this.requestedCountryCode,
    this.requestedPosition,
    this.specialRequest,
    this.adminPriority = false,
  });

  final String parentPlayerId;
  final String paymentMethod;
  final String? requestedName;
  final String? requestedCountryCode;
  final String? requestedPosition;
  final String? specialRequest;
  final bool adminPriority;

  double estimateCost(GtexCreateSonPricing pricing) {
    double total = pricing.baseCostCoin;
    if ((requestedName ?? '').trim().isNotEmpty) {
      total += pricing.nameCustomizationCoin;
    }
    if ((requestedCountryCode ?? '').trim().isNotEmpty) {
      total += pricing.nationalityCustomizationCoin;
    }
    if ((requestedPosition ?? '').trim().isNotEmpty) {
      total += pricing.positionCustomizationCoin;
    }
    if ((specialRequest ?? '').trim().isNotEmpty) {
      total += pricing.specialRequestMinimumCoin;
    }
    if (adminPriority) {
      total *= 1.25;
    }
    return total;
  }
}

class GtexCreateSonOrder {
  const GtexCreateSonOrder({
    required this.id,
    required this.parentPlayerName,
    required this.status,
    required this.amountCoin,
    required this.paymentMethod,
    required this.createdAtLabel,
    this.generatedRegenName,
  });

  final String id;
  final String parentPlayerName;
  final String status;
  final double amountCoin;
  final String paymentMethod;
  final String createdAtLabel;
  final String? generatedRegenName;
}
