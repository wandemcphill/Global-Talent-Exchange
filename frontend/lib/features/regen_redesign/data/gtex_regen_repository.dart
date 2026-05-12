import 'package:gte_frontend/data/regen_creation_api.dart';
import 'package:gte_frontend/data/regen_universe_api.dart';
import 'package:gte_frontend/models/regen_creation_models.dart';
import 'package:gte_frontend/models/regen_universe_models.dart';

import '../models/gtex_regen_models.dart';

abstract class GtexRegenRepository {
  Future<GtexRegenWorldData> loadWorld();
  Future<GtexCreateSonOrder> createSon(GtexCreateSonDraft draft);
  Future<GtexRegenContractOffer> submitContract(String offerId);
}

class LiveGtexRegenRepository implements GtexRegenRepository {
  const LiveGtexRegenRepository({
    required this.universeApi,
    this.creationApi,
    this.isAuthenticated = false,
  });

  final RegenUniverseApi universeApi;
  final RegenCreationApi? creationApi;
  final bool isAuthenticated;

  @override
  Future<GtexRegenWorldData> loadWorld() async {
    final List<Object?> criticalPayload =
        await Future.wait<Object?>(<Future<Object?>>[
          _safe<List<NationalRegenSeed>>(
            universeApi.listNationalRegens(limit: 48, ageMax: 99),
          ),
          _safe<RegenGenerationTracking>(universeApi.fetchTracking()),
        ]);

    final _LiveLoadResult<List<NationalRegenSeed>> nationalRegens =
        criticalPayload[0] as _LiveLoadResult<List<NationalRegenSeed>>;
    final _LiveLoadResult<RegenGenerationTracking> tracking =
        criticalPayload[1] as _LiveLoadResult<RegenGenerationTracking>;

    final List<Object?> sidePayload =
        await Future.wait<Object?>(<Future<Object?>>[
          _safe<List<RegenRisingStar>>(universeApi.listRisingStars(limit: 24)),
          _safe<List<RegenAwardResult>>(universeApi.listAwards(limit: 16)),
          _safe<List<RegenScoutingFeedItem>>(
            universeApi.listScoutingFeed(limit: 20),
          ),
          isAuthenticated && creationApi != null
              ? _safe<RequestSonOptions>(creationApi!.fetchRequestSonOptions())
              : Future<_LiveLoadResult<RequestSonOptions>>.value(
                const _LiveLoadResult<RequestSonOptions>(),
              ),
          isAuthenticated && creationApi != null
              ? _safe<RegenCreationOrderList>(
                creationApi!.listCreationOrders(limit: 24),
              )
              : Future<_LiveLoadResult<RegenCreationOrderList>>.value(
                const _LiveLoadResult<RegenCreationOrderList>(),
              ),
        ]).timeout(
          const Duration(seconds: 8),
          onTimeout:
              () => <Object?>[
                const _LiveLoadResult<List<RegenRisingStar>>(),
                const _LiveLoadResult<List<RegenAwardResult>>(),
                const _LiveLoadResult<List<RegenScoutingFeedItem>>(),
                const _LiveLoadResult<RequestSonOptions>(),
                const _LiveLoadResult<RegenCreationOrderList>(),
              ],
        );

    final _LiveLoadResult<List<RegenRisingStar>> risingStars =
        sidePayload[0] as _LiveLoadResult<List<RegenRisingStar>>;
    final _LiveLoadResult<List<RegenAwardResult>> awards =
        sidePayload[1] as _LiveLoadResult<List<RegenAwardResult>>;
    final _LiveLoadResult<List<RegenScoutingFeedItem>> feed =
        sidePayload[2] as _LiveLoadResult<List<RegenScoutingFeedItem>>;
    final _LiveLoadResult<RequestSonOptions> options =
        sidePayload[3] as _LiveLoadResult<RequestSonOptions>;
    final _LiveLoadResult<RegenCreationOrderList> orders =
        sidePayload[4] as _LiveLoadResult<RegenCreationOrderList>;

    final bool hasLiveData =
        risingStars.value != null ||
        nationalRegens.value != null ||
        awards.value != null ||
        feed.value != null ||
        tracking.value != null ||
        orders.value != null;
    if (!hasLiveData) {
      throw tracking.error ??
          risingStars.error ??
          nationalRegens.error ??
          awards.error ??
          feed.error ??
          StateError('Unable to load the live regen universe.');
    }

    final List<RegenRisingStar> liveStars =
        risingStars.value ?? const <RegenRisingStar>[];
    final List<NationalRegenSeed> parsedNationalRegens =
        nationalRegens.value ?? const <NationalRegenSeed>[];
    final List<RegenAwardResult> liveAwards =
        awards.value ?? const <RegenAwardResult>[];
    final List<RegenScoutingFeedItem> liveFeed =
        feed.value ?? const <RegenScoutingFeedItem>[];
    final RegenGenerationTracking liveTracking =
        tracking.value ?? _emptyTracking;
    final List<NationalRegenSeed> liveNationalRegens =
        parsedNationalRegens.isNotEmpty
            ? parsedNationalRegens
            : _nationalSeedsFromTracking(liveTracking);
    final List<RegenCreationOrder> liveOrders =
        orders.value?.items ?? const <RegenCreationOrder>[];
    final RequestSonOptions? liveOptions = options.value;

    final List<GtexRegenProspect> prospects = <GtexRegenProspect>[
      ...liveStars.map(_prospectFromRisingStar),
      ...liveNationalRegens.map(_prospectFromNationalSeed),
      ...liveOrders
          .where((RegenCreationOrder order) => order.generatedPlayer != null)
          .map(_prospectFromCreationOrder),
    ];

    return GtexRegenWorldData(
      stats: GtexRegenWorldStats(
        totalRegens:
            liveTracking.totalSeededPlayers == 0
                ? prospects.length
                : liveTracking.totalSeededPlayers,
        nationalPoolCount: liveNationalRegens.length,
        createSonOrders: liveOrders.length,
        awardsThisSeason: liveAwards.length,
      ),
      pricing: _pricingFromOptions(liveOptions),
      parentPlayers: _parentsFromOptions(liveOptions, liveStars),
      prospects: prospects,
      awards: liveAwards.map(_awardFromResult).toList(growable: false),
      achievementFeed: liveFeed
          .map(_achievementFromFeed)
          .toList(growable: false),
      contracts: const <GtexRegenContractOffer>[],
    );
  }

  @override
  Future<GtexCreateSonOrder> createSon(GtexCreateSonDraft draft) async {
    final RegenCreationApi? api = creationApi;
    if (!isAuthenticated || api == null) {
      throw StateError('Sign in to create a son.');
    }
    RegenCreationOrder order = await api.createRequestSonOrder(
      RequestSonOrderDraft(
        parentPlayerId: draft.parentPlayerId,
        paymentMethod: draft.paymentMethod,
        requestedName: draft.requestedName,
        requestedCountryCode: draft.requestedCountryCode,
        requestedPosition: draft.requestedPosition,
      ),
    );
    if (order.usesWallet && order.isPendingPayment) {
      order = await api.payWithWallet(order.id);
    }
    return _createSonOrderFromLive(order);
  }

  @override
  Future<GtexRegenContractOffer> submitContract(String offerId) {
    throw UnsupportedError(
      'Live regen contract submission is not exposed yet.',
    );
  }

  static Future<_LiveLoadResult<T>> _safe<T>(Future<T> future) async {
    try {
      return _LiveLoadResult<T>(value: await future);
    } catch (error) {
      return _LiveLoadResult<T>(error: error);
    }
  }

  static GtexRegenProspect _prospectFromRisingStar(RegenRisingStar star) {
    final RegenUniversePlayer player = star.player;
    return GtexRegenProspect(
      id: player.id,
      displayName: player.name,
      countryCode: player.nationalityCode ?? player.nationality,
      countryName: player.nationality,
      position: player.position,
      age: player.age,
      currentRating: player.currentRating,
      potentialRating: player.potential,
      globalScoutingIndex: player.globalScoutingIndex,
      archetype: star.momentumLabel,
      origin: _originFromPlayer(player),
      contractStatus:
          player.isNationalPoolOnly
              ? GtexRegenContractStatus.rentalOnly
              : GtexRegenContractStatus.unsigned,
      storyline: star.storySnippet ?? 'Live rising regen tracked by GTEX.',
      traits: star.displayBadges.take(4).toList(growable: false),
      valueCoin: (star.marketValueCoin ?? 0).toDouble(),
      clubName: player.clubId,
      imageUrl: player.imageUrl,
      rarityTier: _rarityForPotential(player.potential),
      isTradable: player.marketAccess.tradable,
      isNationalRentalOnly: player.isNationalPoolOnly,
    );
  }

  static GtexRegenProspect _prospectFromNationalSeed(NationalRegenSeed seed) {
    return GtexRegenProspect(
      id: seed.id,
      displayName: seed.displayName,
      countryCode: seed.countryCode,
      countryName: seed.countryName,
      position: seed.primaryPosition,
      age: seed.age ?? 17,
      currentRating: seed.currentRating,
      potentialRating: seed.potentialRating,
      globalScoutingIndex: seed.globalScoutingIndex,
      archetype: seed.rarityTier,
      origin: GtexRegenOrigin.nationalPool,
      contractStatus: GtexRegenContractStatus.rentalOnly,
      storyline:
          'Pre-seeded national-pool regen for national-team rental depth.',
      traits: seed.badgeLabels.take(4).toList(growable: false),
      valueCoin: 0,
      imageUrl: seed.imageUrl,
      rarityTier: seed.rarityTier,
      isTradable: seed.tradable,
      isNationalRentalOnly: seed.nationalPoolOnly,
    );
  }

  static GtexRegenProspect _prospectFromCreationOrder(
    RegenCreationOrder order,
  ) {
    final RegenCreationGeneratedPlayer player = order.generatedPlayer!;
    return GtexRegenProspect(
      id: player.playerId,
      displayName: player.fullName,
      countryCode: player.countryCode ?? 'GTEX',
      countryName: player.countryName ?? player.countryCode ?? 'GTEX',
      position: player.position,
      age: player.age,
      currentRating: player.currentRating,
      potentialRating: player.potentialRating,
      archetype: 'Create-a-Son',
      origin: GtexRegenOrigin.createSon,
      contractStatus: GtexRegenContractStatus.signed,
      storyline:
          'Generated through a paid Create-a-Son order and attached to the live regen universe.',
      traits: const <String>['Bloodline Regen', 'Requested Son'],
      valueCoin: order.amountCoin,
      clubName: player.clubName,
      imageUrl: player.imageUrl,
      rarityTier: _rarityForPotential(player.potentialRating),
      isTradable: true,
    );
  }

  static List<NationalRegenSeed> _nationalSeedsFromTracking(
    RegenGenerationTracking tracking,
  ) {
    if (tracking.countryDistribution.isEmpty) {
      return const <NationalRegenSeed>[];
    }
    return tracking.countryDistribution
        .take(48)
        .toList(growable: false)
        .asMap()
        .entries
        .map((MapEntry<int, RegenGenerationTrackingEntry> entry) {
          final RegenGenerationTrackingEntry item = entry.value;
          final String countryName =
              item.bucket.trim().isEmpty ? 'GTEX' : item.bucket.trim();
          final int codeLength =
              countryName.length < 3 ? countryName.length : 3;
          final String countryCode =
              item.metadata['country_code']?.toString().trim().toUpperCase() ??
              countryName.substring(0, codeLength).toUpperCase();
          final int potential = item.peakRating.clamp(70, 99).toInt();
          final int current = (potential - 18).clamp(55, 82).toInt();
          return NationalRegenSeed(
            id: 'tracking-seed-${entry.key}-$countryCode',
            seedKey: 'tracking:$countryCode:${entry.key}',
            displayName: '$countryName Regen ${entry.key + 1}',
            age: 18,
            ageBand: 'u21',
            countryCode: countryCode,
            countryName: countryName,
            seedType: 'preseeded_national_pool',
            primaryPosition: _positionForIndex(entry.key),
            currentRating: current,
            potentialRating: potential,
            growthCurve: 0.7,
            rarityTier: potential >= 92 ? 'elite' : 'rare',
            status: 'active',
            preseedBatch: 'live_tracking_fallback',
            metadata: item.metadata,
          );
        })
        .toList(growable: false);
  }

  static String _positionForIndex(int index) {
    const List<String> positions = <String>[
      'GK',
      'CB',
      'LB',
      'RB',
      'DM',
      'CM',
      'AM',
      'LW',
      'RW',
      'ST',
    ];
    return positions[index % positions.length];
  }

  static GtexRegenOrigin _originFromPlayer(RegenUniversePlayer player) {
    if (player.isPreseededNationalRegen || player.isNationalPoolOnly) {
      return GtexRegenOrigin.nationalPool;
    }
    if (player.isRequestedSon) {
      return GtexRegenOrigin.createSon;
    }
    if (player.isClubRegen) {
      return GtexRegenOrigin.clubGenerated;
    }
    if (player.sourceType.toLowerCase().contains('academy')) {
      return GtexRegenOrigin.academy;
    }
    return GtexRegenOrigin.mystery;
  }

  static GtexRegenAward _awardFromResult(RegenAwardResult result) {
    final RegenAwardWinner? winner =
        result.winners.isEmpty ? null : result.winners.first;
    return GtexRegenAward(
      id: result.award.id,
      name: result.award.name,
      seasonLabel: 'Season ${result.season.seasonNumber}',
      winnerName: winner?.playerName ?? 'Winner pending',
      scoreLabel: winner?.rankingScore.toStringAsFixed(1) ?? '--',
      category: result.award.category,
    );
  }

  static GtexRegenAchievement _achievementFromFeed(RegenScoutingFeedItem item) {
    return GtexRegenAchievement(
      id: item.feedId,
      title: item.title,
      body: item.summary,
      timestampLabel: _relativeTime(item.occurredAt),
    );
  }

  static List<GtexParentPlayer> _parentsFromOptions(
    RequestSonOptions? options,
    List<RegenRisingStar> fallbackStars,
  ) {
    if (options != null && options.eligibleParents.isNotEmpty) {
      return options.eligibleParents
          .map(
            (RegenCreationParentPlayer parent) => GtexParentPlayer(
              id: parent.playerId,
              name: parent.fullName,
              position: parent.position ?? 'POS',
              countryCode: parent.countryCode ?? 'GTEX',
              clubName: parent.clubName ?? options.clubName,
              rating: 75,
              imageUrl: parent.imageUrl,
            ),
          )
          .toList(growable: false);
    }
    return fallbackStars
        .take(6)
        .map(
          (RegenRisingStar star) => GtexParentPlayer(
            id: star.player.id,
            name: star.player.name,
            position: star.player.position,
            countryCode: star.player.nationalityCode ?? 'GTEX',
            clubName: star.player.clubId ?? 'GTEX Regen World',
            rating: star.player.currentRating,
            imageUrl: star.player.imageUrl,
          ),
        )
        .toList(growable: false);
  }

  static GtexCreateSonPricing _pricingFromOptions(RequestSonOptions? options) {
    final RegenCreationPricing? pricing = options?.pricing;
    if (pricing == null) {
      return demoWorldData.pricing;
    }
    return GtexCreateSonPricing(
      baseCostCoin: pricing.baseCostCoin,
      nameCustomizationCoin: pricing.nameCostCoin,
      nationalityCustomizationCoin: pricing.customizationCostCoin,
      positionCustomizationCoin: pricing.customizationCostCoin,
      specialRequestMinimumCoin: pricing.customizationCostCoin,
    );
  }

  static GtexCreateSonOrder _createSonOrderFromLive(RegenCreationOrder order) {
    return GtexCreateSonOrder(
      id: order.id,
      parentPlayerName: order.parentPlayerId ?? 'Live parent',
      status: order.status,
      amountCoin: order.amountCoin,
      paymentMethod: order.paymentMethod,
      createdAtLabel: _relativeTime(order.createdAt),
      generatedRegenName: order.generatedPlayer?.fullName,
    );
  }

  static String _rarityForPotential(int potential) {
    if (potential >= 93) return 'Legendary';
    if (potential >= 88) return 'Elite';
    if (potential >= 82) return 'High Potential';
    return 'Prospect';
  }

  static String _relativeTime(DateTime value) {
    final Duration diff = DateTime.now().toUtc().difference(value.toUtc());
    if (diff.inMinutes < 1) return 'Just now';
    if (diff.inHours < 1) return '${diff.inMinutes}m ago';
    if (diff.inDays < 1) return '${diff.inHours}h ago';
    return '${diff.inDays}d ago';
  }
}

class _LiveLoadResult<T> {
  const _LiveLoadResult({this.value, this.error});

  final T? value;
  final Object? error;
}

const RegenGenerationTracking _emptyTracking = RegenGenerationTracking(
  totalSeededPlayers: 0,
  seedTypes: <RegenGenerationTrackingEntry>[],
  rarityBreakdown: <RegenGenerationTrackingEntry>[],
  countryDistribution: <RegenGenerationTrackingEntry>[],
  globalPeakRating: 0,
  trackedAchievements: <String>[],
);

/// Safe demo repository for local smoke tests and for Codex wiring.
///
/// Production routes should replace this with an adapter around the existing
/// `RegenUniverseApi` and `RegenCreationApi` rather than using demo data.
class DemoGtexRegenRepository implements GtexRegenRepository {
  const DemoGtexRegenRepository();

  @override
  Future<GtexRegenWorldData> loadWorld() async {
    await Future<void>.delayed(const Duration(milliseconds: 80));
    return demoWorldData;
  }

  @override
  Future<GtexCreateSonOrder> createSon(GtexCreateSonDraft draft) async {
    await Future<void>.delayed(const Duration(milliseconds: 80));
    final GtexParentPlayer parent = demoWorldData.parentPlayers.firstWhere(
      (GtexParentPlayer player) => player.id == draft.parentPlayerId,
      orElse: () => demoWorldData.parentPlayers.first,
    );
    return GtexCreateSonOrder(
      id: 'son-${DateTime.now().millisecondsSinceEpoch}',
      parentPlayerName: parent.name,
      status:
          draft.paymentMethod == 'wallet'
              ? 'paid_generating'
              : 'payment_pending',
      amountCoin: draft.estimateCost(demoWorldData.pricing),
      paymentMethod: draft.paymentMethod,
      createdAtLabel: 'Just now',
      generatedRegenName:
          draft.paymentMethod == 'wallet'
              ? (draft.requestedName?.isNotEmpty == true
                  ? draft.requestedName
                  : 'Generated Son')
              : null,
    );
  }

  @override
  Future<GtexRegenContractOffer> submitContract(String offerId) async {
    await Future<void>.delayed(const Duration(milliseconds: 80));
    return demoWorldData.contracts.firstWhere(
      (GtexRegenContractOffer offer) => offer.id == offerId,
      orElse: () => demoWorldData.contracts.first,
    );
  }
}

const GtexRegenWorldData demoWorldData = GtexRegenWorldData(
  stats: GtexRegenWorldStats(
    totalRegens: 842,
    nationalPoolCount: 214,
    createSonOrders: 18,
    awardsThisSeason: 9,
  ),
  pricing: GtexCreateSonPricing(
    baseCostCoin: 12000,
    nameCustomizationCoin: 2000,
    nationalityCustomizationCoin: 1500,
    positionCustomizationCoin: 1000,
    specialRequestMinimumCoin: 5000,
  ),
  parentPlayers: <GtexParentPlayer>[
    GtexParentPlayer(
      id: 'p-001',
      name: 'Victor Adebayo',
      position: 'ST',
      countryCode: 'NGA',
      clubName: 'Lagos Monarchs',
      rating: 87,
    ),
    GtexParentPlayer(
      id: 'p-002',
      name: 'Theo Marin',
      position: 'CM',
      countryCode: 'FRA',
      clubName: 'Paris Forge',
      rating: 84,
    ),
    GtexParentPlayer(
      id: 'p-003',
      name: 'Lucas Reyes',
      position: 'LW',
      countryCode: 'ARG',
      clubName: 'Buenos Aires City',
      rating: 85,
    ),
  ],
  prospects: <GtexRegenProspect>[
    GtexRegenProspect(
      id: 'r-001',
      displayName: 'Kelechi Aruna',
      countryCode: 'NGA',
      countryName: 'Nigeria',
      position: 'AM',
      age: 17,
      currentRating: 69,
      potentialRating: 91,
      archetype: 'Street Maestro',
      origin: GtexRegenOrigin.createSon,
      contractStatus: GtexRegenContractStatus.negotiating,
      storyline:
          'Created from a premium parent line; wants a club that promises first-team minutes before 19.',
      traits: <String>['Flair', 'Big Match', 'Ambitious'],
      valueCoin: 68000,
      clubName: 'Lagos Monarchs',
      rarityTier: 'Mythic',
    ),
    GtexRegenProspect(
      id: 'r-002',
      displayName: 'Mateo Silvestri',
      countryCode: 'ITA',
      countryName: 'Italy',
      position: 'CB',
      age: 18,
      currentRating: 71,
      potentialRating: 88,
      archetype: 'Modern Stopper',
      origin: GtexRegenOrigin.nationalPool,
      contractStatus: GtexRegenContractStatus.rentalOnly,
      storyline:
          'Pre-seeded national-pool defender. Rental-only depth for youth national competitions.',
      traits: <String>['Leader', 'Aerial', 'Composed'],
      valueCoin: 42000,
      rarityTier: 'Elite',
      isTradable: false,
      isNationalRentalOnly: true,
    ),
    GtexRegenProspect(
      id: 'r-003',
      displayName: 'João Varella',
      countryCode: 'BRA',
      countryName: 'Brazil',
      position: 'RW',
      age: 16,
      currentRating: 66,
      potentialRating: 94,
      archetype: 'Touchline Spark',
      origin: GtexRegenOrigin.academy,
      contractStatus: GtexRegenContractStatus.unsigned,
      storyline:
          'Academy wonderkid with high volatility; scouts believe his ceiling is world-class.',
      traits: <String>['Explosive', 'Raw', 'Showman'],
      valueCoin: 95000,
      clubName: 'Rio Galaxy',
      rarityTier: 'Legendary',
    ),
    GtexRegenProspect(
      id: 'r-004',
      displayName: 'Ethan Brooks',
      countryCode: 'ENG',
      countryName: 'England',
      position: 'GK',
      age: 19,
      currentRating: 73,
      potentialRating: 86,
      archetype: 'Sweeper Keeper',
      origin: GtexRegenOrigin.clubGenerated,
      contractStatus: GtexRegenContractStatus.transferRequested,
      storyline:
          'Submitted a transfer request after losing the captaincy. Prefers clubs with strong defensive systems.',
      traits: <String>['Brave', 'Demanding', 'Vocal'],
      valueCoin: 52000,
      clubName: 'North London Pulse',
      rarityTier: 'Elite',
    ),
  ],
  awards: <GtexRegenAward>[
    GtexRegenAward(
      id: 'a-001',
      name: 'GTEX Regen World Player of the Year',
      seasonLabel: 'Season 4',
      winnerName: 'Kelechi Aruna',
      scoreLabel: '94.2',
      category: 'World',
    ),
    GtexRegenAward(
      id: 'a-002',
      name: 'U17 Breakthrough',
      seasonLabel: 'Season 4',
      winnerName: 'João Varella',
      scoreLabel: '91.7',
      category: 'Youth',
    ),
    GtexRegenAward(
      id: 'a-003',
      name: 'National Pool Defender',
      seasonLabel: 'Season 4',
      winnerName: 'Mateo Silvestri',
      scoreLabel: '88.5',
      category: 'National Pool',
    ),
  ],
  achievementFeed: <GtexRegenAchievement>[
    GtexRegenAchievement(
      id: 'ach-001',
      title: 'First senior hat-trick',
      body: 'Kelechi Aruna scored three in the GTEX U20 semi-final.',
      timestampLabel: '12m ago',
    ),
    GtexRegenAchievement(
      id: 'ach-002',
      title: 'Transfer request submitted',
      body: 'Ethan Brooks wants a new project with guaranteed cup starts.',
      timestampLabel: '1h ago',
    ),
    GtexRegenAchievement(
      id: 'ach-003',
      title: 'New national-pool seed promoted',
      body: 'Italy U20 depth pool received a rental-only defender.',
      timestampLabel: '3h ago',
    ),
  ],
  contracts: <GtexRegenContractOffer>[
    GtexRegenContractOffer(
      id: 'c-001',
      regenId: 'r-001',
      regenName: 'Kelechi Aruna',
      status: GtexRegenContractStatus.negotiating,
      weeklyWageCoin: 850,
      signingBonusCoin: 6200,
      durationSeasons: 3,
      personalityNote:
          'Wants first-team minutes and a release clause if ignored.',
    ),
    GtexRegenContractOffer(
      id: 'c-002',
      regenId: 'r-004',
      regenName: 'Ethan Brooks',
      status: GtexRegenContractStatus.transferRequested,
      weeklyWageCoin: 620,
      signingBonusCoin: 2400,
      durationSeasons: 2,
      personalityNote:
          'Will choose a club with defensive identity and cup exposure.',
    ),
  ],
);
