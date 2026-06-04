import '../../../models/regen_creation_models.dart';
import '../../../models/regen_universe_models.dart';
import '../../../shared/providers/regen_provider.dart';

enum RegenWorldTruthState { complete, degraded, blocked }

class RegenWorldDnaProfile {
  const RegenWorldDnaProfile({required this.ratings});

  final Map<String, int> ratings;

  bool get isComplete =>
      regenDnaStatCodes.every((String code) => ratings.containsKey(code));

  int get publishedCount => ratings.length;

  int? valueFor(String code) => ratings[code.toUpperCase()];

  int get average {
    if (ratings.isEmpty) {
      return 0;
    }
    final int sum = ratings.values.fold<int>(
      0,
      (int total, int value) => total + value,
    );
    return sum ~/ ratings.length;
  }

  int get integritySegments {
    if (ratings.isEmpty || average <= 0) {
      return 0;
    }
    return (average.clamp(0, 99) / 10).ceil().clamp(1, 10);
  }

  List<String> get missingCodes => <String>[
    for (final String code in regenDnaStatCodes)
      if (!ratings.containsKey(code)) code,
  ];

  static RegenWorldDnaProfile? fromCreationProfile(RegenDnaProfile? profile) {
    if (profile == null) {
      return null;
    }
    return RegenWorldDnaProfile(
      ratings: <String, int>{
        for (final String code in regenDnaStatCodes)
          code: profile.valueFor(code).clamp(0, 99),
      },
    );
  }

  static RegenWorldDnaProfile? fromValues(Map<String, double> values) {
    final Map<String, int> ratings = <String, int>{};
    for (final String code in regenDnaStatCodes) {
      final double? value =
          values[code] ??
          values[code.toLowerCase()] ??
          values[code.toUpperCase()];
      if (value == null) {
        continue;
      }
      ratings[code] = value.round().clamp(0, 99);
    }
    if (ratings.isEmpty) {
      return null;
    }
    return RegenWorldDnaProfile(
      ratings: Map<String, int>.unmodifiable(ratings),
    );
  }
}

class RegenWorldEntry {
  const RegenWorldEntry({
    required this.id,
    required this.name,
    required this.position,
    required this.nationality,
    required this.potential,
    required this.currentRating,
    required this.source,
    required this.createdAt,
    this.nationalityCode,
    this.imageUrl,
    this.generationNumber,
    this.generationLabel,
    this.rarityTier,
    this.originStory,
    this.originLabel,
    this.projectedValueCoin,
    this.marketAccess,
    this.traits = const <String>[],
    this.lineage = const <String>[],
    this.dnaProfile,
    this.badges = const <String>[],
  });

  final String id;
  final String name;
  final String position;
  final String nationality;
  final String? nationalityCode;
  final String? imageUrl;
  final int potential;
  final int currentRating;
  final String source;
  final DateTime createdAt;
  final int? generationNumber;
  final String? generationLabel;
  final String? rarityTier;
  final String? originStory;
  final String? originLabel;
  final int? projectedValueCoin;
  final RegenMarketAccess? marketAccess;
  final List<String> traits;
  final List<String> lineage;
  final RegenWorldDnaProfile? dnaProfile;
  final List<String> badges;

  bool get hasBackendTruth => missingFields.isEmpty;

  RegenWorldTruthState get truthState {
    if (blockingMissingFields.isNotEmpty) {
      return RegenWorldTruthState.blocked;
    }
    if (missingFields.isNotEmpty) {
      return RegenWorldTruthState.degraded;
    }
    return RegenWorldTruthState.complete;
  }

  bool get isBlocked => truthState == RegenWorldTruthState.blocked;

  bool get isDegraded => truthState == RegenWorldTruthState.degraded;

  String get generationDisplay {
    final String? label = generationLabel?.trim();
    if (label != null && label.isNotEmpty) {
      return label;
    }
    final int? number = generationNumber;
    if (number != null && number > 0) {
      return 'GEN-$number';
    }
    return 'Generation not published';
  }

  String get nationalityDisplay {
    final String label = nationality.trim();
    return label.isEmpty ? 'Nationality not published' : label;
  }

  String get positionDisplay {
    final String label = position.trim();
    return label.isEmpty ? 'Position not published' : label;
  }

  String get rarityDisplay {
    final String? label = rarityTier?.trim();
    return label == null || label.isEmpty ? 'Rarity not published' : label;
  }

  String get originDisplay {
    final String? story = originStory?.trim();
    if (story != null && story.isNotEmpty) {
      return story;
    }
    final String? label = originLabel?.trim();
    if (label != null && label.isNotEmpty) {
      return 'Origin: $label';
    }
    return 'Origin story not published';
  }

  String get projectedValueLabel =>
      projectedValueCoin == null
          ? 'Projected value not published'
          : formatRegenWorldCoin(projectedValueCoin!);

  bool get hasMarketAccessTruth => marketAccess?.backendProvided == true;

  String get marketAccessDisplay {
    final RegenMarketAccess? access = marketAccess;
    if (access == null || !hasMarketAccessTruth) {
      return 'Market access not published';
    }
    if (access.nationalPoolOnly || access.isPreseededNationalRegen) {
      return 'National pool only';
    }
    if (!access.marketEligible) {
      return 'Market restricted';
    }
    if (!access.tradable) {
      return 'Not tradable';
    }
    if (access.buyable && access.buyCtaAllowed) {
      return 'Backend access published';
    }
    return 'Dossier access published';
  }

  String get marketAccessSummary {
    final RegenMarketAccess? access = marketAccess;
    if (access == null || !hasMarketAccessTruth) {
      return 'Market access not published by backend.';
    }
    if (access.nationalPoolOnly || access.isPreseededNationalRegen) {
      return 'Backend restricts this regen to the national pool; transaction CTAs stay hidden.';
    }
    if (!access.marketEligible) {
      return 'Backend marks this regen outside market access; only published dossier state is shown.';
    }
    if (!access.tradable) {
      return 'Backend marks this regen as not tradable; transfer and buy CTAs stay hidden.';
    }
    if (!access.buyable || !access.buyCtaAllowed) {
      return 'Backend publishes market access, but buy CTAs remain hidden for this regen.';
    }
    return 'Backend publishes market access; only safe dossier, timeline, and watchlist surfaces are shown here.';
  }

  bool get canViewDossier => hasMarketAccessTruth;

  bool get canViewTimeline =>
      hasMarketAccessTruth && marketAccess!.shareMarketEligible;

  bool get canUseWatchlist =>
      hasMarketAccessTruth &&
      marketAccess!.marketEligible &&
      !marketAccess!.nationalPoolOnly;

  String get truthStateLabel {
    switch (truthState) {
      case RegenWorldTruthState.complete:
        return 'Backend truth complete';
      case RegenWorldTruthState.degraded:
        return 'Backend truth degraded';
      case RegenWorldTruthState.blocked:
        return 'Backend truth blocked';
    }
  }

  String get missingFieldsSummary {
    if (missingFields.isEmpty) {
      return 'All required Regen World fields are published.';
    }
    return 'Missing backend fields: ${missingFields.join(', ')}.';
  }

  int get completenessScore {
    return 12 - missingFields.length.clamp(0, 12);
  }

  List<String> get missingFields => <String>[
    if ((generationNumber ?? 0) <= 0 && (generationLabel ?? '').trim().isEmpty)
      'generation',
    if (position.trim().isEmpty) 'position',
    if (potential <= 0) 'potential',
    if (currentRating <= 0) 'current rating',
    if (traits.isEmpty) 'traits',
    if (lineage.isEmpty) 'lineage',
    if (dnaProfile == null) 'DNA',
    if (dnaProfile != null && !dnaProfile!.isComplete)
      'DNA ${dnaProfile!.missingCodes.join('/')}',
    if ((originStory ?? '').trim().isEmpty) 'origin story',
    if (projectedValueCoin == null) 'projected value',
    if (!hasMarketAccessTruth) 'market access',
    if ((rarityTier ?? '').trim().isEmpty) 'rarity',
    if (nationality.trim().isEmpty) 'nationality',
  ];

  List<String> get blockingMissingFields => <String>[
    if (position.trim().isEmpty) 'position',
    if (potential <= 0) 'potential',
    if (currentRating <= 0) 'current rating',
    if (nationality.trim().isEmpty) 'nationality',
  ];

  Iterable<String> get searchableValues sync* {
    yield name;
    yield position;
    yield nationality;
    yield source;
    yield generationDisplay;
    yield rarityDisplay;
    yield originDisplay;
    yield projectedValueLabel;
    yield marketAccessDisplay;
    yield marketAccessSummary;
    if (projectedValueCoin != null) {
      yield projectedValueCoin.toString();
    }
    yield* traits;
    yield* lineage;
    yield* badges;
    final RegenWorldDnaProfile? profile = dnaProfile;
    if (profile != null) {
      for (final String code in regenDnaStatCodes) {
        final int? value = profile.valueFor(code);
        yield code;
        if (value != null) {
          yield '$code $value';
          yield value.toString();
        }
      }
    }
  }

  RegenWorldEntry copyWith({
    int? generationNumber,
    String? generationLabel,
    String? originLabel,
    List<String>? lineage,
  }) {
    final int? resolvedGenerationNumber =
        generationNumber ?? this.generationNumber;
    return RegenWorldEntry(
      id: id,
      name: name,
      position: position,
      nationality: nationality,
      nationalityCode: nationalityCode,
      imageUrl: imageUrl,
      potential: potential,
      currentRating: currentRating,
      source: source,
      createdAt: createdAt,
      generationNumber: resolvedGenerationNumber,
      generationLabel:
          generationLabel ??
          this.generationLabel ??
          (resolvedGenerationNumber == null || resolvedGenerationNumber <= 0
              ? null
              : 'GEN-$resolvedGenerationNumber'),
      rarityTier: rarityTier,
      originStory: originStory,
      originLabel: originLabel ?? this.originLabel,
      projectedValueCoin: projectedValueCoin,
      marketAccess: marketAccess,
      traits: traits,
      lineage: lineage ?? this.lineage,
      dnaProfile: dnaProfile,
      badges: badges,
    );
  }
}

List<RegenWorldEntry> buildRegenWorldEntries(RegenUniverseHubData data) {
  final Map<String, RegenWorldEntry> entries = <String, RegenWorldEntry>{};

  void put(RegenWorldEntry entry) {
    final RegenWorldEntry? existing = entries[entry.id];
    if (existing == null ||
        entry.completenessScore > existing.completenessScore) {
      entries[entry.id] = entry;
    }
  }

  for (final NationalRegenSeed seed in data.nationalRegens) {
    put(_withBloodline(_entryFromNationalSeed(seed), data.bloodlines));
  }
  for (final RegenRisingStar star in data.risingStars) {
    put(_withBloodline(_entryFromRisingStar(star), data.bloodlines));
  }
  for (final RegenCreationOrder order in data.generatedRequestedSons) {
    final RegenCreationGeneratedPlayer? player = order.generatedPlayer;
    if (player != null) {
      put(
        _withBloodline(_entryFromGeneratedSon(order, player), data.bloodlines),
      );
    }
  }

  return entries.values.toList(growable: false);
}

String formatRegenWorldCoin(int value) {
  if (value >= 1000000) {
    return 'GTC ${(value / 1000000).toStringAsFixed(1)}M';
  }
  if (value >= 1000) {
    return 'GTC ${(value / 1000).toStringAsFixed(0)}K';
  }
  return 'GTC $value';
}

RegenWorldEntry _withBloodline(
  RegenWorldEntry entry,
  List<RegenBloodlineChain> bloodlines,
) {
  if (entry.lineage.isNotEmpty &&
      (entry.originLabel ?? '').trim().isNotEmpty &&
      (entry.generationNumber ?? 0) > 0) {
    return entry;
  }

  for (final RegenBloodlineChain chain in bloodlines) {
    RegenBloodlinePlayer? match;
    for (final RegenBloodlinePlayer player in chain.entries) {
      final String? playerId = player.playerId;
      if (playerId == entry.id ||
          player.regenId == entry.id ||
          player.displayName.toLowerCase() == entry.name.toLowerCase()) {
        match = player;
        break;
      }
    }
    if (match == null) {
      continue;
    }

    return entry.copyWith(
      lineage:
          entry.lineage.isEmpty
              ? chain.entries
                  .map((RegenBloodlinePlayer player) => player.displayName)
                  .toList(growable: false)
              : entry.lineage,
      originLabel:
          (entry.originLabel ?? '').trim().isEmpty
              ? chain.originLabel
              : entry.originLabel,
      generationNumber:
          (entry.generationNumber ?? 0) > 0
              ? entry.generationNumber
              : match.generationIndex,
    );
  }
  return entry;
}

RegenWorldEntry _entryFromNationalSeed(NationalRegenSeed seed) {
  final RegenWorldDetails details = RegenWorldDetails.fromNationalSeed(seed);
  return RegenWorldEntry(
    id: seed.id,
    name: seed.displayName,
    position: seed.primaryPosition,
    nationality: seed.countryName,
    nationalityCode: seed.countryCode,
    imageUrl: seed.imageUrl,
    potential: seed.potentialRating,
    currentRating: seed.currentRating,
    source: seed.seedType,
    createdAt: DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
    generationNumber: seed.generationIndex > 0 ? seed.generationIndex : null,
    generationLabel: details.generationLabel,
    rarityTier: details.rarityLabel,
    originStory: details.originStory,
    originLabel: details.originLabel,
    projectedValueCoin: details.projectedValueCoin,
    marketAccess: seed.marketAccess,
    traits: details.traits,
    lineage: details.lineage,
    dnaProfile: RegenWorldDnaProfile.fromValues(details.dna),
    badges: seed.badgeLabels,
  );
}

RegenWorldEntry _entryFromRisingStar(RegenRisingStar star) {
  final RegenUniversePlayer player = star.player;
  final RegenWorldDetails? details = star.details;
  final List<String> detailsTraits = details?.traits ?? const <String>[];
  final List<String> detailsLineage = details?.lineage ?? const <String>[];
  final RegenWorldDnaProfile? detailsDna =
      details == null ? null : RegenWorldDnaProfile.fromValues(details.dna);
  final int? detailsGenerationNumber = _generationNumberFromLabel(
    details?.generationLabel,
  );

  return RegenWorldEntry(
    id: star.playerId,
    name: player.name,
    position: player.position,
    nationality: player.nationality,
    nationalityCode: player.nationalityCode,
    imageUrl: player.imageUrl,
    potential: player.potential,
    currentRating: player.currentRating,
    source: player.sourceType,
    createdAt: DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
    generationNumber: detailsGenerationNumber ?? player.generationNumber,
    generationLabel: details?.generationLabel ?? player.generationLabel,
    rarityTier: details?.rarityLabel ?? player.rarityTier,
    originStory: details?.originStory ?? player.originStory,
    originLabel: details?.originLabel,
    projectedValueCoin:
        details?.projectedValueCoin ??
        player.projectedValueCoin ??
        star.marketValueCoin,
    marketAccess: player.marketAccess,
    traits: detailsTraits.isNotEmpty ? detailsTraits : player.traits,
    lineage: detailsLineage.isNotEmpty ? detailsLineage : player.lineage,
    dnaProfile:
        detailsDna ??
        RegenWorldDnaProfile.fromCreationProfile(player.dnaProfile),
    badges: star.displayBadges,
  );
}

RegenWorldEntry _entryFromGeneratedSon(
  RegenCreationOrder order,
  RegenCreationGeneratedPlayer player,
) {
  return RegenWorldEntry(
    id: player.playerId,
    name: player.fullName,
    position: player.position,
    nationality: player.countryName ?? player.countryCode ?? '',
    nationalityCode: player.countryCode,
    imageUrl: player.imageUrl,
    potential: player.potentialRating,
    currentRating: player.currentRating,
    source: order.requestType,
    createdAt: order.generatedAt ?? order.updatedAt,
    generationNumber: player.generationNumber,
    generationLabel: player.generationLabel,
    rarityTier: player.rarityTier,
    originStory: player.originStory,
    projectedValueCoin: player.projectedValueCoin,
    marketAccess: null,
    traits: player.traits,
    lineage: player.lineage,
    dnaProfile: RegenWorldDnaProfile.fromCreationProfile(player.dnaProfile),
    badges: const <String>['Requested Son', 'Bloodline Regen'],
  );
}

int? _generationNumberFromLabel(String? label) {
  if (label == null) {
    return null;
  }
  final RegExpMatch? match = RegExp(
    r'GEN-?(\d+)',
  ).firstMatch(label.toUpperCase());
  return match == null ? null : int.tryParse(match.group(1) ?? '');
}
