import 'package:gte_frontend/data/regen_creation_api.dart';
import 'package:gte_frontend/data/regen_universe_api.dart';
import 'package:gte_frontend/models/regen_creation_models.dart';
import 'package:gte_frontend/models/regen_universe_models.dart';

import '../models/gtex_regen_dossier.dart';
import '../models/gtex_regen_living_star.dart';
import '../models/gtex_regen_models.dart';
import '../models/gtex_regen_wire_models.dart';
import 'gtex_regen_demo_dossier.dart';
import 'gtex_regen_world_api.dart';

abstract class GtexRegenRepository {
  Future<GtexRegenWorldData> loadWorld();
  Future<GtexRegenProspectPage> loadMoreNationalRegens({required int page});
  Future<GtexCreateSonOrder> createSon(GtexCreateSonDraft draft);
  /// Live Create-a-Son operational queue for the signed-in account.
  Future<List<RegenCreationOrder>> listCreationOrders({int limit = 40});
  Future<RegenCreationOrder> payCreationOrder(String orderId);
  Future<RegenCreationOrder> generateCreationOrder(String orderId);
  Future<RegenLifecycleState?> submitContractOffer(
    String playerId,
    GtexRegenOfferDraft draft,
  );
  Future<GtexRegenDossierResult> loadDossier(String playerId);
  Future<List<RegenBloodlineChain>> loadBloodlines();
  Future<List<RegenRankingEntry>> loadRankings();
  Future<List<RegenHallOfFameEntry>> loadHallOfFame();
  Future<RegenLifecycleState?> setTransferListing(
    String playerId, {
    required bool listed,
    String? reason,
  });
  Future<RegenOfferQuote> quoteContractOffer(
    String playerId,
    GtexRegenOfferDraft draft,
  );
  Future<GtexRegenLivingStar?> petitionExit(
    String playerId, {
    String? reason,
  });
  Future<void> resolveRegenBid(String playerId);
  bool get canActOnOwnership;
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
          _safe<NationalRegenSeedPage>(
            universeApi.listNationalRegensPage(
              page: 1,
              perPage: 48,
              ageMax: 99,
            ),
          ),
          _safe<RegenGenerationTracking>(universeApi.fetchTracking()),
        ]);

    final _LiveLoadResult<NationalRegenSeedPage> nationalRegens =
        criticalPayload[0] as _LiveLoadResult<NationalRegenSeedPage>;
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
    final NationalRegenSeedPage? nationalRegenPage = nationalRegens.value;
    final List<NationalRegenSeed> parsedNationalRegens =
        nationalRegenPage?.items ?? const <NationalRegenSeed>[];
    final List<RegenAwardResult> liveAwards =
        awards.value ?? const <RegenAwardResult>[];
    final List<RegenScoutingFeedItem> liveFeed =
        feed.value ?? const <RegenScoutingFeedItem>[];
    final RegenGenerationTracking liveTracking =
        tracking.value ?? _emptyTracking;
    // Aggregate country-level counters are not player records. Only API seed rows
    // create individual national-pool player cards.
    final List<NationalRegenSeed> liveNationalRegens = parsedNationalRegens;
    final List<RegenCreationOrder> liveOrders =
        orders.value?.items ?? const <RegenCreationOrder>[];
    final RequestSonOptions? liveOptions = options.value;
    final List<GtexParentPlayer> liveParents = _parentsFromOptions(liveOptions);
    final GtexCreateSonPricing livePricing = _pricingFromOptions(liveOptions);
    final bool createSonAvailable =
        isAuthenticated &&
        creationApi != null &&
        liveOptions != null &&
        liveParents.isNotEmpty;

    final List<GtexRegenProspect> prospects = <GtexRegenProspect>[
      ...liveStars.map(_prospectFromRisingStar),
      ...liveNationalRegens.map(_prospectFromNationalSeed),
      ...liveOrders
          .where((RegenCreationOrder order) => order.generatedPlayer != null)
          .map(_prospectFromCreationOrder),
    ];

    final List<GtexRegenContractOffer> contracts =
        await _realContractOfferInbox(fallbackStars: liveStars);

    return GtexRegenWorldData(
      stats: GtexRegenWorldStats(
        totalRegens:
            liveTracking.totalSeededPlayers == 0
                ? prospects.length
                : liveTracking.totalSeededPlayers,
        nationalPoolCount: nationalRegenPage?.total ?? liveNationalRegens.length,
        createSonOrders: liveOrders.length,
        awardsThisSeason: liveAwards.length,
      ),
      pricing: livePricing,
      parentPlayers: liveParents,
      createSonAvailable: createSonAvailable,
      createSonBlockedReason:
          createSonAvailable
              ? null
              : _createSonBlockedReason(
                liveOptions: liveOptions,
                optionsError: options.error,
                hasParents: liveParents.isNotEmpty,
              ),
      prospects: prospects,
      nationalRegensPage: nationalRegenPage?.page ?? 1,
      hasMoreNationalRegens: nationalRegenPage?.hasNext ?? false,
      awards: liveAwards.map(_awardFromResult).toList(growable: false),
      achievementFeed: liveFeed
          .map(_achievementFromFeed)
          .toList(growable: false),
      contracts: contracts,
    );
  }

  @override
  Future<GtexRegenProspectPage> loadMoreNationalRegens({required int page}) async {
    final NationalRegenSeedPage result =
        await universeApi.listNationalRegensPage(
      page: page,
      perPage: 48,
      ageMax: 99,
    );
    return GtexRegenProspectPage(
      prospects: result.items
          .map(_prospectFromNationalSeed)
          .toList(growable: false),
      page: result.page,
      total: result.total,
      hasNext: result.hasNext,
    );
  }

  /// Prefer real RegenContractOffer inbox rows; fall back to exit-pressure cues.
  Future<List<GtexRegenContractOffer>> _realContractOfferInbox({
    required List<RegenRisingStar> fallbackStars,
  }) async {
    if (isAuthenticated) {
      try {
        final List<Map<String, Object?>> rows =
            await _worldApi.listContractOfferInbox();
        if (rows.isNotEmpty) {
          return List<GtexRegenContractOffer>.unmodifiable(
            rows.map(_contractOfferFromInboxRow),
          );
        }
      } catch (_) {
        // Fall through to living-star pressure cues.
      }
    }
    return _livingStarPressureInbox(fallbackStars);
  }

  GtexRegenContractOffer _contractOfferFromInboxRow(Map<String, Object?> row) {
    final double annual =
        double.tryParse(
          '${row['offered_salary_fancoin_per_year'] ?? row['offeredSalaryFancoinPerYear'] ?? 0}',
        ) ??
        0;
    final int years =
        int.tryParse(
          '${row['contract_years'] ?? row['contractYears'] ?? 1}',
        ) ??
        1;
    final String statusRaw =
        (row['status'] ?? 'negotiating').toString().toLowerCase();
    return GtexRegenContractOffer(
      id: (row['offer_id'] ?? row['offerId'] ?? '').toString(),
      regenId: (row['regen_id'] ?? row['regenId'] ?? '').toString(),
      regenName: (row['player_name'] ?? row['playerName'] ?? 'Regen').toString(),
      status:
          statusRaw.contains('transfer')
              ? GtexRegenContractStatus.transferRequested
              : GtexRegenContractStatus.negotiating,
      weeklyWageCoin: annual / 52.0,
      signingBonusCoin: 0,
      durationSeasons: years,
      personalityNote:
          (row['personality_note'] ??
                  row['personalityNote'] ??
                  row['offering_club_name'] ??
                  row['offeringClubName'] ??
                  '')
              .toString(),
    );
  }

  /// Living-star exit pressure cues when no open RegenContractOffer rows exist.
  Future<List<GtexRegenContractOffer>> _livingStarPressureInbox(
    List<RegenRisingStar> stars,
  ) async {
    final List<RegenRisingStar> sample = stars.take(8).toList(growable: false);
    if (sample.isEmpty) {
      return const <GtexRegenContractOffer>[];
    }
    final List<GtexRegenLivingStar?> results = await Future.wait(
      sample.map((RegenRisingStar star) async {
        try {
          return await _worldApi.fetchLivingStar(star.playerId);
        } catch (_) {
          return null;
        }
      }),
    );
    final List<GtexRegenContractOffer> offers = <GtexRegenContractOffer>[];
    for (int i = 0; i < sample.length; i++) {
      final GtexRegenLivingStar? star = results[i];
      if (star == null) {
        continue;
      }
      if (star.exitSeverity <= 0 && star.moodSeverity <= 0) {
        continue;
      }
      final RegenRisingStar rising = sample[i];
      offers.add(
        GtexRegenContractOffer(
          id: 'living-star-${star.playerId}',
          regenId: star.regenId ?? star.playerId,
          regenName: rising.player.name,
          status:
              star.exitSeverity >= 2
                  ? GtexRegenContractStatus.transferRequested
                  : GtexRegenContractStatus.negotiating,
          weeklyWageCoin: 0,
          signingBonusCoin: 0,
          durationSeasons: 0,
          personalityNote:
              '${star.archetypeLabel} · ${star.moodLabel} · ${star.voiceLine}',
        ),
      );
    }
    return List<GtexRegenContractOffer>.unmodifiable(offers);
  }

  @override
  Future<List<RegenCreationOrder>> listCreationOrders({int limit = 40}) async {
    final RegenCreationApi? api = creationApi;
    if (!isAuthenticated || api == null) {
      return const <RegenCreationOrder>[];
    }
    final RegenCreationOrderList list = await api.listCreationOrders(
      limit: limit,
    );
    return List<RegenCreationOrder>.unmodifiable(list.items);
  }

  @override
  Future<RegenCreationOrder> payCreationOrder(String orderId) async {
    final RegenCreationApi? api = creationApi;
    if (!isAuthenticated || api == null) {
      throw StateError('Sign in to pay a Create-a-Son order.');
    }
    return api.payWithWallet(orderId);
  }

  @override
  Future<RegenCreationOrder> generateCreationOrder(String orderId) async {
    final RegenCreationApi? api = creationApi;
    if (!isAuthenticated || api == null) {
      throw StateError('Sign in to generate a Create-a-Son order.');
    }
    return api.generateAfterPayment(orderId);
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
  Future<RegenLifecycleState?> submitContractOffer(
    String playerId,
    GtexRegenOfferDraft draft,
  ) {
    if (!isAuthenticated) {
      throw StateError('Sign in to submit a regen contract offer.');
    }
    return _worldApi.submitContractOffer(playerId, draft);
  }

  GtexRegenWorldApi get _worldApi =>
      GtexRegenWorldApi(client: universeApi.client);

  @override
  Future<GtexRegenDossierResult> loadDossier(String playerId) async {
    final RegenPlayerShowcase showcase;
    try {
      showcase = await _worldApi.fetchDossier(playerId);
    } on GtexRegenDossierUnavailable {
      return const GtexRegenDossierResult.absent(
        absence: GtexRegenDossierAbsence.notPublished,
        message:
            'This regen has no published profile, so GTEX holds no lineage, '
            'personality or development record for them yet.',
      );
    } catch (error) {
      return GtexRegenDossierResult.absent(
        absence: GtexRegenDossierAbsence.loadFailed,
        message: 'The regen dossier could not be loaded: $error',
      );
    }

    List<RegenLineageChainNode> chain = const <RegenLineageChainNode>[];
    bool chainUnavailable = false;
    try {
      chain = await _worldApi.fetchLineageChain(showcase.profile.id);
    } catch (_) {
      chainUnavailable = true;
    }

    RegenLifecycleState? lifecycle;
    try {
      lifecycle = await _worldApi.fetchLifecycle(playerId);
    } catch (_) {
      lifecycle = null;
    }

    GtexRegenLivingStar? livingStar;
    try {
      livingStar = await _worldApi.fetchLivingStar(playerId);
    } catch (_) {
      livingStar = null;
    }

    return GtexRegenDossierResult.loaded(
      GtexRegenDossier(
        playerId: playerId,
        showcase: showcase,
        lineageChain: chain,
        lineageChainUnavailable: chainUnavailable,
        lifecycle: lifecycle,
        livingStar: livingStar,
      ),
    );
  }

  @override
  Future<List<RegenBloodlineChain>> loadBloodlines() =>
      _worldApi.listBloodlines();

  @override
  Future<List<RegenRankingEntry>> loadRankings() => _worldApi.listRankings();

  @override
  Future<List<RegenHallOfFameEntry>> loadHallOfFame() =>
      _worldApi.listHallOfFame();

  @override
  bool get canActOnOwnership => isAuthenticated;

  @override
  Future<RegenLifecycleState?> setTransferListing(
    String playerId, {
    required bool listed,
    String? reason,
  }) {
    if (!isAuthenticated) {
      throw StateError('Sign in to change a regen transfer listing.');
    }
    return _worldApi.setTransferListing(
      playerId,
      listed: listed,
      reason: reason,
    );
  }

  @override
  Future<RegenOfferQuote> quoteContractOffer(
    String playerId,
    GtexRegenOfferDraft draft,
  ) {
    if (!isAuthenticated) {
      throw StateError('Sign in to price a contract offer.');
    }
    return _worldApi.quoteContractOffer(playerId, draft);
  }

  @override
  Future<GtexRegenLivingStar?> petitionExit(
    String playerId, {
    String? reason,
  }) {
    if (!isAuthenticated) {
      throw StateError('Sign in to petition a regen exit.');
    }
    return _worldApi.petitionExit(playerId, reason: reason);
  }

  @override
  Future<void> resolveRegenBid(String playerId) {
    if (!isAuthenticated) {
      throw StateError('Sign in to resolve a regen bid.');
    }
    return _worldApi.resolveRegenBid(playerId);
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
    final String? parentId = order.parentPlayerId;
    return GtexRegenProspect(
      lineageLabel: parentId == null ? null : 'Son of $parentId',
      parentPlayerId: parentId,
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
    return const <GtexParentPlayer>[];
  }

  static GtexCreateSonPricing _pricingFromOptions(RequestSonOptions? options) {
    final RegenCreationPricing? pricing = options?.pricing;
    if (pricing == null) {
      return const GtexCreateSonPricing(
        baseCostCoin: 0,
        nameCustomizationCoin: 0,
        nationalityCustomizationCoin: 0,
        positionCustomizationCoin: 0,
        specialRequestMinimumCoin: 0,
      );
    }
    return GtexCreateSonPricing(
      baseCostCoin: pricing.baseCostCoin,
      nameCustomizationCoin: pricing.nameCostCoin,
      nationalityCustomizationCoin: pricing.customizationCostCoin,
      positionCustomizationCoin: pricing.customizationCostCoin,
      specialRequestMinimumCoin: pricing.customizationCostCoin,
    );
  }

  static String _createSonBlockedReason({
    required RequestSonOptions? liveOptions,
    required Object? optionsError,
    required bool hasParents,
  }) {
    if (!hasParents) {
      return 'The backend did not return any eligible parent players for this account.';
    }
    if (liveOptions?.pricing == null) {
      return 'The backend did not return live Create-a-Son pricing.';
    }
    if (optionsError != null) {
      return optionsError.toString();
    }
    return 'Create-a-Son is not available for this account right now.';
  }

  static GtexCreateSonOrder _createSonOrderFromLive(RegenCreationOrder order) {
    return GtexCreateSonOrder(
      id: order.id,
      parentPlayerId: order.parentPlayerId,
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

class DemoGtexRegenRepository implements GtexRegenRepository {
  const DemoGtexRegenRepository();

  @override
  Future<GtexRegenWorldData> loadWorld() async {
    await Future<void>.delayed(const Duration(milliseconds: 80));
    return demoWorldData;
  }

  @override
  Future<GtexRegenProspectPage> loadMoreNationalRegens({required int page}) async {
    await Future<void>.delayed(const Duration(milliseconds: 80));
    final List<GtexRegenProspect> nationalPool = demoWorldData.prospects
        .where((GtexRegenProspect item) => item.origin == GtexRegenOrigin.nationalPool)
        .toList(growable: false);
    const int pageSize = 48;
    final int start = (page - 1) * pageSize;
    final List<GtexRegenProspect> items = nationalPool
        .skip(start)
        .take(pageSize)
        .toList(growable: false);
    final int totalPages =
        nationalPool.isEmpty ? 0 : (nationalPool.length + pageSize - 1) ~/ pageSize;
    return GtexRegenProspectPage(
      prospects: items,
      page: page,
      total: nationalPool.length,
      hasNext: page < totalPages,
    );
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
      parentPlayerId: parent.id,
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
  Future<List<RegenCreationOrder>> listCreationOrders({int limit = 40}) async {
    await Future<void>.delayed(const Duration(milliseconds: 40));
    final List<GtexParentPlayer> parents = demoWorldData.parentPlayers;
    return List<RegenCreationOrder>.unmodifiable(<RegenCreationOrder>[
      RegenCreationOrder(
        id: 'order-demo-pending',
        userId: 'fixture-user',
        requestType: 'request_son',
        parentPlayerId: parents.isNotEmpty ? parents.first.id : null,
        requestedName: 'Adebayo Jr',
        amountCoin: 20500,
        currency: 'COIN',
        paymentMethod: 'wallet',
        status: 'pending_payment',
        createdAt: DateTime.now().toUtc().subtract(const Duration(hours: 2)),
        updatedAt: DateTime.now().toUtc().subtract(const Duration(hours: 2)),
      ),
      RegenCreationOrder(
        id: 'order-demo-paid',
        userId: 'fixture-user',
        requestType: 'request_son',
        parentPlayerId: parents.length > 1 ? parents[1].id : null,
        requestedName: 'Theo II',
        amountCoin: 18000,
        currency: 'COIN',
        paymentMethod: 'wallet',
        status: 'paid',
        createdAt: DateTime.now().toUtc().subtract(const Duration(days: 1)),
        updatedAt: DateTime.now().toUtc().subtract(const Duration(hours: 6)),
        paidAt: DateTime.now().toUtc().subtract(const Duration(hours: 6)),
      ),
      RegenCreationOrder(
        id: 'order-demo-generated',
        userId: 'fixture-user',
        requestType: 'request_son',
        parentPlayerId: parents.length > 2 ? parents[2].id : null,
        requestedName: 'Lucasito Reyes',
        amountCoin: 22500,
        currency: 'COIN',
        paymentMethod: 'wallet',
        status: 'generated',
        createdAt: DateTime.now().toUtc().subtract(const Duration(days: 3)),
        updatedAt: DateTime.now().toUtc().subtract(const Duration(days: 2)),
        paidAt: DateTime.now().toUtc().subtract(const Duration(days: 2)),
        generatedAt: DateTime.now().toUtc().subtract(const Duration(days: 2)),
        generatedPlayer: const RegenCreationGeneratedPlayer(
          playerId: 'regen-demo-1',
          regenProfileId: 'regen-profile-demo-1',
          fullName: 'Lucasito Reyes',
          age: 17,
          position: 'LW',
          currentRating: 68,
          potentialRating: 86,
        ),
      ),
    ].take(limit));
  }

  @override
  Future<RegenCreationOrder> payCreationOrder(String orderId) async {
    final List<RegenCreationOrder> orders = await listCreationOrders();
    final RegenCreationOrder order = orders.firstWhere(
      (RegenCreationOrder item) => item.id == orderId,
      orElse: () => throw StateError('Unknown Create-a-Son order: $orderId'),
    );
    return RegenCreationOrder(
      id: order.id,
      userId: order.userId,
      requestType: order.requestType,
      amountCoin: order.amountCoin,
      currency: order.currency,
      paymentMethod: order.paymentMethod,
      status: 'paid',
      createdAt: order.createdAt,
      updatedAt: DateTime.now().toUtc(),
      clubId: order.clubId,
      parentPlayerId: order.parentPlayerId,
      requestedName: order.requestedName,
      requestedCountryCode: order.requestedCountryCode,
      requestedPosition: order.requestedPosition,
      paidAt: DateTime.now().toUtc(),
    );
  }

  @override
  Future<RegenCreationOrder> generateCreationOrder(String orderId) async {
    final List<RegenCreationOrder> orders = await listCreationOrders();
    final RegenCreationOrder order = orders.firstWhere(
      (RegenCreationOrder item) => item.id == orderId,
      orElse: () => throw StateError('Unknown Create-a-Son order: $orderId'),
    );
    final String name = order.requestedName?.trim().isNotEmpty == true
        ? order.requestedName!.trim()
        : 'Generated Son';
    return RegenCreationOrder(
      id: order.id,
      userId: order.userId,
      requestType: order.requestType,
      amountCoin: order.amountCoin,
      currency: order.currency,
      paymentMethod: order.paymentMethod,
      status: 'generated',
      createdAt: order.createdAt,
      updatedAt: DateTime.now().toUtc(),
      clubId: order.clubId,
      parentPlayerId: order.parentPlayerId,
      requestedName: order.requestedName,
      requestedCountryCode: order.requestedCountryCode,
      requestedPosition: order.requestedPosition,
      paidAt: order.paidAt ?? DateTime.now().toUtc(),
      generatedAt: DateTime.now().toUtc(),
      generatedPlayer: RegenCreationGeneratedPlayer(
        playerId: 'regen-${order.id}',
        regenProfileId: 'regen-profile-${order.id}',
        fullName: name,
        age: 17,
        position: order.requestedPosition ?? 'CM',
        currentRating: 66,
        potentialRating: 84,
      ),
    );
  }

  @override
  Future<RegenLifecycleState?> submitContractOffer(
    String playerId,
    GtexRegenOfferDraft draft,
  ) async {
    await Future<void>.delayed(const Duration(milliseconds: 80));
    return demoRegenLifecycle();
  }

  @override
  Future<GtexRegenDossierResult> loadDossier(String playerId) async {
    await Future<void>.delayed(const Duration(milliseconds: 40));
    if (playerId == 'r-002') {
      return const GtexRegenDossierResult.absent(
        absence: GtexRegenDossierAbsence.notPublished,
        message:
            'This regen has no published profile, so GTEX holds no lineage, '
            'personality or development record for them yet.',
      );
    }
    return GtexRegenDossierResult.loaded(demoRegenDossier(playerId));
  }

  @override
  Future<List<RegenBloodlineChain>> loadBloodlines() async {
    await Future<void>.delayed(const Duration(milliseconds: 40));
    return demoRegenBloodlines();
  }

  @override
  Future<List<RegenRankingEntry>> loadRankings() async {
    await Future<void>.delayed(const Duration(milliseconds: 40));
    return demoRegenRankings();
  }

  @override
  Future<List<RegenHallOfFameEntry>> loadHallOfFame() async {
    await Future<void>.delayed(const Duration(milliseconds: 40));
    return demoRegenHallOfFame();
  }

  @override
  bool get canActOnOwnership => true;

  @override
  Future<RegenLifecycleState?> setTransferListing(
    String playerId, {
    required bool listed,
    String? reason,
  }) async {
    await Future<void>.delayed(const Duration(milliseconds: 40));
    return demoRegenLifecycle(transferListed: listed);
  }

  @override
  Future<RegenOfferQuote> quoteContractOffer(
    String playerId,
    GtexRegenOfferDraft draft,
  ) async {
    await Future<void>.delayed(const Duration(milliseconds: 40));
    return demoRegenOfferQuote(draft);
  }

  @override
  Future<GtexRegenLivingStar?> petitionExit(
    String playerId, {
    String? reason,
  }) async {
    await Future<void>.delayed(const Duration(milliseconds: 40));
    return null;
  }

  @override
  Future<void> resolveRegenBid(String playerId) async {
    await Future<void>.delayed(const Duration(milliseconds: 40));
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
