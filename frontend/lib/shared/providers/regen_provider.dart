import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/regen_creation_api.dart';
import '../../data/regen_universe_api.dart';
import '../../models/regen_creation_models.dart';
import '../../models/regen_universe_models.dart';
import '../models/competition.dart';
import '../models/federation.dart';
import '../models/player.dart';
import 'auth_provider.dart';

class RegenUniverseHubData {
  const RegenUniverseHubData({
    required this.risingStars,
    required this.awards,
    required this.nationalRegens,
    required this.scoutingFeed,
    required this.tracking,
    required this.creationOrders,
  });

  final List<RegenRisingStar> risingStars;
  final List<RegenAwardResult> awards;
  final List<NationalRegenSeed> nationalRegens;
  final List<RegenScoutingFeedItem> scoutingFeed;
  final RegenGenerationTracking tracking;
  final List<RegenCreationOrder> creationOrders;

  List<RegenCreationOrder> get requestedSonOrders => creationOrders
      .where((RegenCreationOrder order) => order.requestType == 'son')
      .toList(growable: false);

  List<RegenCreationOrder> get generatedRequestedSons => requestedSonOrders
      .where((RegenCreationOrder order) => order.generatedPlayer != null)
      .toList(growable: false);
}

class _RegenLoadResult<T> {
  const _RegenLoadResult({this.value, this.error});

  final T? value;
  final Object? error;
}

Future<_RegenLoadResult<T>> _safeRegenLoad<T>(Future<T> future) async {
  try {
    return _RegenLoadResult<T>(value: await future);
  } catch (error) {
    return _RegenLoadResult<T>(error: error);
  }
}

const RegenGenerationTracking _emptyRegenTracking = RegenGenerationTracking(
  totalSeededPlayers: 0,
  seedTypes: <RegenGenerationTrackingEntry>[],
  rarityBreakdown: <RegenGenerationTrackingEntry>[],
  countryDistribution: <RegenGenerationTrackingEntry>[],
  globalPeakRating: 0,
  trackedAchievements: <String>[],
);

final Provider<RegenUniverseApi> regenUniverseApiProvider =
    Provider<RegenUniverseApi>((Ref ref) {
      return RegenUniverseApi.standard(
        baseUrl: ref.watch(apiBaseUrlProvider),
        mode: ref.watch(criticalBackendModeProvider),
      );
    });

final Provider<RegenCreationApi> regenCreationApiProvider =
    Provider<RegenCreationApi>((Ref ref) {
      return RegenCreationApi.standard(
        baseUrl: ref.watch(apiBaseUrlProvider),
        mode: ref.watch(criticalBackendModeProvider),
        accessToken: ref.watch(accessTokenProvider),
        authSession: ref.watch(authProvider),
        authSessionStore: ref.watch(authSessionStoreProvider),
        onSessionChanged:
            ref.read(appSessionControllerProvider.notifier).updateSession,
        deviceId: ref.watch(deviceIdProvider),
      );
    });

final FutureProvider<RegenUniverseHubData>
regenUniverseHubProvider = FutureProvider<RegenUniverseHubData>((
  Ref ref,
) async {
  final RegenUniverseApi universeApi = ref.watch(regenUniverseApiProvider);
  final RegenCreationApi creationApi = ref.watch(regenCreationApiProvider);
  final bool authenticated = ref.watch(isAuthenticatedProvider);
  final List<Object?> payload = await Future.wait<Object?>(<Future<Object?>>[
    _safeRegenLoad<List<RegenRisingStar>>(
      universeApi.listRisingStars(limit: 8),
    ),
    _safeRegenLoad<List<RegenAwardResult>>(universeApi.listAwards(limit: 8)),
    _safeRegenLoad<List<NationalRegenSeed>>(
      universeApi.listNationalRegens(limit: 12, ageMax: 20),
    ),
    _safeRegenLoad<List<RegenScoutingFeedItem>>(
      universeApi.listScoutingFeed(limit: 8),
    ),
    _safeRegenLoad<RegenGenerationTracking>(universeApi.fetchTracking()),
    authenticated
        ? _safeRegenLoad<RegenCreationOrderList>(
          creationApi.listCreationOrders(limit: 12),
        )
        : Future<_RegenLoadResult<RegenCreationOrderList>>.value(
          const _RegenLoadResult<RegenCreationOrderList>(
            value: RegenCreationOrderList(items: <RegenCreationOrder>[]),
          ),
        ),
  ]);
  final _RegenLoadResult<List<RegenRisingStar>> risingStarsResult =
      payload[0] as _RegenLoadResult<List<RegenRisingStar>>;
  final _RegenLoadResult<List<RegenAwardResult>> awardsResult =
      payload[1] as _RegenLoadResult<List<RegenAwardResult>>;
  final _RegenLoadResult<List<NationalRegenSeed>> nationalRegensResult =
      payload[2] as _RegenLoadResult<List<NationalRegenSeed>>;
  final _RegenLoadResult<List<RegenScoutingFeedItem>> scoutingFeedResult =
      payload[3] as _RegenLoadResult<List<RegenScoutingFeedItem>>;
  final _RegenLoadResult<RegenGenerationTracking> trackingResult =
      payload[4] as _RegenLoadResult<RegenGenerationTracking>;
  final _RegenLoadResult<RegenCreationOrderList> creationOrdersResult =
      payload[5] as _RegenLoadResult<RegenCreationOrderList>;

  final bool hasAnyData =
      risingStarsResult.value != null ||
      awardsResult.value != null ||
      nationalRegensResult.value != null ||
      scoutingFeedResult.value != null ||
      trackingResult.value != null ||
      creationOrdersResult.value != null;
  if (!hasAnyData) {
    throw trackingResult.error ??
        risingStarsResult.error ??
        scoutingFeedResult.error ??
        awardsResult.error ??
        nationalRegensResult.error ??
        creationOrdersResult.error ??
        StateError('Unable to load the regen universe.');
  }
  return RegenUniverseHubData(
    risingStars: risingStarsResult.value ?? const <RegenRisingStar>[],
    awards: awardsResult.value ?? const <RegenAwardResult>[],
    nationalRegens: nationalRegensResult.value ?? const <NationalRegenSeed>[],
    scoutingFeed: scoutingFeedResult.value ?? const <RegenScoutingFeedItem>[],
    tracking: trackingResult.value ?? _emptyRegenTracking,
    creationOrders:
        creationOrdersResult.value?.items ?? const <RegenCreationOrder>[],
  );
});

final Provider<List<Player>> regenProvider = Provider<List<Player>>((Ref ref) {
  final RegenUniverseHubData? hub =
      ref.watch(regenUniverseHubProvider).asData?.value;
  if (hub == null) {
    return const <Player>[];
  }
  return hub.risingStars
      .map(
        (RegenRisingStar star) => Player(
          id: star.player.id,
          name: star.player.name,
          position: star.player.position,
          country: star.player.nationality,
          age: star.player.age,
          rating: star.player.currentRating,
          potential: star.player.potential,
          valueInMillions:
              ((star.marketValueCoin ?? 0) / 1000000).clamp(0, 9999).toDouble(),
          pace: star.player.growthCurve.clamp(0, 1),
          technique: (star.player.currentRating / 100).clamp(0, 1),
          mentality: (star.player.potential / 100).clamp(0, 1),
          image: 'assets/branding/gtex_icon.png',
          isHot: star.player.currentRating >= 72,
        ),
      )
      .toList(growable: false);
});

final Provider<List<Competition>> competitionsProvider =
    Provider<List<Competition>>((Ref ref) => const <Competition>[]);

final Provider<List<String>> historyProvider = Provider<List<String>>((
  Ref ref,
) {
  final RegenUniverseHubData? hub =
      ref.watch(regenUniverseHubProvider).asData?.value;
  if (hub == null) {
    return const <String>[];
  }
  return hub.awards
      .where((RegenAwardResult result) => result.winners.isNotEmpty)
      .map(
        (RegenAwardResult result) =>
            '${result.winners.first.playerName} won ${result.award.name} in season ${result.season.seasonNumber}.',
      )
      .toList(growable: false);
});

final Provider<List<Federation>> federationsProvider =
    Provider<List<Federation>>((Ref ref) => const <Federation>[]);
