import 'package:gte_frontend/app/test_runtime_detector.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';

import '../models/gtex_club_ownership_models.dart';

/// Reads the signed-in user's club-share ownership.
///
/// `GET /api/portfolio/clubs` is the D -> B join: the aggregated, live-valued
/// club-ownership book that the portfolio surface renders alongside player
/// holdings. `GET /api/clubs/{id}/ownership` is the single-club deep view
/// (share price, performance signal, my position, treasury, governance).
class GtexClubOwnershipApi {
  GtexClubOwnershipApi({required this.client, GtexClubOwnershipFixtures? fixtures})
    : _fixtures = fixtures;

  final GteAuthedApi client;
  final GtexClubOwnershipFixtures? _fixtures;

  factory GtexClubOwnershipApi.standard({
    required String baseUrl,
    required String? accessToken,
    GteBackendMode mode = GteBackendMode.live,
    GteAuthedApi? client,
  }) {
    final GteBackendMode resolvedMode = gteProductionBackendMode(mode);
    return GtexClubOwnershipApi(
      client:
          client ??
          GteAuthedApi(
            config: GteRepositoryConfig(baseUrl: baseUrl, mode: resolvedMode),
            transport: GteHttpTransport(),
            accessToken: accessToken,
            mode: resolvedMode,
          ),
    );
  }

  factory GtexClubOwnershipApi.fixture() {
    assertFixtureFactoryAllowed('GtexClubOwnershipApi.fixture');
    return GtexClubOwnershipApi(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.fixture,
        ),
        transport: GteHttpTransport(),
        accessToken: 'fixture-token',
        mode: GteBackendMode.fixture,
      ),
      fixtures: GtexClubOwnershipFixtures.seed(),
    );
  }

  Future<GtexClubOwnershipPortfolio> fetchMyClubPortfolio() {
    return client.withFallback<GtexClubOwnershipPortfolio>(() async {
      final Map<String, dynamic> payload = await client.getMap(
        '/api/portfolio/clubs',
      );
      return GtexClubOwnershipPortfolio.fromJson(payload);
    }, () => _requireFixtures().portfolio());
  }

  GtexClubOwnershipFixtures _requireFixtures() {
    final GtexClubOwnershipFixtures? fixtures = _fixtures;
    if (fixtures == null) {
      throw StateError(
        'Club ownership fixtures are available only in fixture mode.',
      );
    }
    return fixtures;
  }
}

class GtexClubOwnershipFixtures {
  GtexClubOwnershipFixtures(this._portfolio);

  final GtexClubOwnershipPortfolio _portfolio;

  static GtexClubOwnershipFixtures seed() {
    const GtexClubShareHolding lagos = GtexClubShareHolding(
      clubId: 'fixture-club-lagos',
      clubName: 'Lagos Eclipse FC',
      sharesOwned: 40,
      averagePriceCoin: 1.0,
      sharePriceCoin: 1.32,
      marketValueCoin: 52.8,
      costBasisCoin: 40,
      unrealizedPlCoin: 12.8,
      unrealizedPlPercent: 32,
      ownershipPercent: 4,
      holderCount: 18,
      circulatingSupply: 1000,
      totalSupply: 1000000,
      rewardSharesEarned: 2,
      performanceScore: 0.42,
      winRate: 0.6,
      fanDemandScore: 0.18,
      treasuryBalanceCoin: 640,
      governanceEnabled: true,
    );
    return GtexClubOwnershipFixtures(
      const GtexClubOwnershipPortfolio(
        clubCount: 1,
        totalMarketValueCoin: 52.8,
        totalCostBasisCoin: 40,
        totalUnrealizedPlCoin: 12.8,
        holdings: <GtexClubShareHolding>[lagos],
      ),
    );
  }

  Future<GtexClubOwnershipPortfolio> portfolio() async => _portfolio;
}
