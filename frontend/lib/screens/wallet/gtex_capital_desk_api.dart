import 'package:gte_frontend/app/test_runtime_detector.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';
import 'package:gte_frontend/data/gte_models.dart';

/// PHASE4-B networking for the capital desk's ownership experience.
///
/// `GET /api/portfolio/snapshot` returns player positions plus the cash posture
/// (available / reserved / total) in one call. Club-share holdings come from
/// PHASE4-D's `GET /api/portfolio/clubs` via [GtexClubOwnershipApi]; this class
/// only owns the snapshot read so the two portfolio surfaces stay one desk.
class GtexCapitalDeskApi {
  GtexCapitalDeskApi({required this.client});

  final GteAuthedApi client;

  factory GtexCapitalDeskApi.standard({
    required String baseUrl,
    required String? accessToken,
    GteBackendMode mode = GteBackendMode.live,
    GteAuthedApi? client,
  }) {
    final GteBackendMode resolvedMode = gteProductionBackendMode(mode);
    return GtexCapitalDeskApi(
      client:
          client ??
          GteAuthedApi(
            config: GteRepositoryConfig(
              baseUrl: baseUrl,
              mode: resolvedMode,
            ),
            transport: GteHttpTransport(),
            accessToken: accessToken,
            mode: resolvedMode,
          ),
    );
  }

  Future<GtePortfolioSnapshot> fetchPortfolioSnapshot() async {
    final Map<String, dynamic> payload = await client.getMap(
      '/api/portfolio/snapshot',
    );
    return GtePortfolioSnapshot.fromJson(payload);
  }
}
