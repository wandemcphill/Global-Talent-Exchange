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
      );
    });

final FutureProvider<RegenUniverseHubData> regenUniverseHubProvider =
    FutureProvider<RegenUniverseHubData>((Ref ref) async {
      final RegenUniverseApi universeApi = ref.watch(regenUniverseApiProvider);
      final RegenCreationApi creationApi = ref.watch(regenCreationApiProvider);
      final bool authenticated = ref.watch(isAuthenticatedProvider);
      final List<Object> payload = await Future.wait<Object>(<Future<Object>>[
        universeApi.listRisingStars(limit: 8),
        universeApi.listAwards(limit: 8),
        universeApi.listNationalRegens(limit: 12, ageMax: 20),
        universeApi.listScoutingFeed(limit: 8),
        universeApi.fetchTracking(),
        authenticated
            ? creationApi.listCreationOrders(limit: 12)
            : Future<RegenCreationOrderList>.value(
              const RegenCreationOrderList(items: <RegenCreationOrder>[]),
            ),
      ]);
      return RegenUniverseHubData(
        risingStars: payload[0] as List<RegenRisingStar>,
        awards: payload[1] as List<RegenAwardResult>,
        nationalRegens: payload[2] as List<NationalRegenSeed>,
        scoutingFeed: payload[3] as List<RegenScoutingFeedItem>,
        tracking: payload[4] as RegenGenerationTracking,
        creationOrders: (payload[5] as RegenCreationOrderList).items,
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
