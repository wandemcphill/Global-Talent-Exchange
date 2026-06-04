import '../../../data/gte_api_repository.dart';
import '../../../data/gte_http_transport.dart';
import '../../../shared/auth/auth_identity_store.dart';
import '../domain/club_hq_models.dart';

abstract class IClubHqRepository {
  Future<ClubHqSnapshot> fetchClubHq(String clubId);
  Future<ClubDashboardDTO> getDashboard(String clubId);
  Future<ClubFinanceDTO> getFinance(String clubId);
  Future<SquadReadinessDTO> getSquadReadiness(String clubId);
  Future<ClubAcademyDTO> getAcademy(String clubId);
  Future<ClubStaffDTO> getStaff(String clubId);
  Future<List<SponsorshipDTO>> getSponsorships(String clubId);
  Future<ClubBrandingDTO> getBranding(String clubId);
  Future<List<TrophyDTO>> getTrophies(String clubId);
  Future<List<ClubRankingDTO>> getRankings(String clubId);
}

class ClubHqRepositoryBlockedException implements Exception {
  const ClubHqRepositoryBlockedException(this.reason);

  final String reason;

  @override
  String toString() => reason;
}

class BackendClubHqRepository implements IClubHqRepository {
  BackendClubHqRepository({
    required this.config,
    required this.transport,
    this.accessToken,
    AuthSessionStore? authSessionStore,
  }) : authSessionStore = authSessionStore ?? SecureAuthSessionStore();

  factory BackendClubHqRepository.standard({
    String baseUrl = const String.fromEnvironment('GTEX_API_BASE_URL'),
    String? accessToken,
  }) {
    return BackendClubHqRepository(
      config: GteRepositoryConfig(baseUrl: baseUrl),
      transport: GteHttpTransport(
        connectionTimeout: const Duration(seconds: 6),
      ),
      accessToken: accessToken,
    );
  }

  final GteRepositoryConfig config;
  final GteTransport transport;
  final String? accessToken;
  final AuthSessionStore authSessionStore;

  @override
  Future<ClubHqSnapshot> fetchClubHq(String clubId) async {
    final Future<ClubDashboardDTO> dashboard = getDashboard(clubId);
    final Future<ClubFinanceDTO> finance = getFinance(clubId);
    final Future<SquadReadinessDTO> readiness = getSquadReadiness(clubId);
    final Future<ClubAcademyDTO> academy = getAcademy(clubId);
    final Future<ClubStaffDTO> staff = getStaff(clubId);
    final Future<List<SponsorshipDTO>> sponsorships = getSponsorships(clubId);
    final Future<ClubBrandingDTO> branding = getBranding(clubId);
    final Future<List<TrophyDTO>> trophies = getTrophies(clubId);
    final Future<List<ClubRankingDTO>> rankings = getRankings(clubId);

    return ClubHqSnapshot(
      dashboard: await dashboard,
      finance: await finance,
      readiness: await readiness,
      academy: await academy,
      staff: await staff,
      sponsorships: await sponsorships,
      branding: await branding,
      trophies: await trophies,
      rankings: await rankings,
    );
  }

  @override
  Future<ClubDashboardDTO> getDashboard(String clubId) async {
    return ClubDashboardDTO.fromJson(
      await _request('/api/clubs/$clubId/dashboard'),
    );
  }

  @override
  Future<ClubFinanceDTO> getFinance(String clubId) async {
    return ClubFinanceDTO.fromJson(
      await _request('/api/clubs/$clubId/finances'),
      fallbackClubId: clubId,
    );
  }

  @override
  Future<SquadReadinessDTO> getSquadReadiness(String clubId) async {
    return SquadReadinessDTO.fromJson(
      await _request('/api/clubs/$clubId/squad/readiness'),
    );
  }

  @override
  Future<ClubAcademyDTO> getAcademy(String clubId) async {
    return ClubAcademyDTO.fromJson(
      await _request('/api/clubs/$clubId/academy'),
    );
  }

  @override
  Future<ClubStaffDTO> getStaff(String clubId) async {
    return ClubStaffDTO.fromJson(await _request('/api/clubs/$clubId/staff'));
  }

  @override
  Future<List<SponsorshipDTO>> getSponsorships(String clubId) async {
    final Object? payload = await _request('/api/clubs/$clubId/sponsorships');
    return _listPayload(payload, const <String>[
      'sponsorships',
      'contracts',
      'items',
    ]).map(SponsorshipDTO.fromJson).toList(growable: false);
  }

  @override
  Future<ClubBrandingDTO> getBranding(String clubId) async {
    return ClubBrandingDTO.fromJson(
      await _request('/api/clubs/$clubId/branding'),
    );
  }

  @override
  Future<List<TrophyDTO>> getTrophies(String clubId) async {
    final Object? payload = await _request('/api/clubs/$clubId/trophies');
    return _listPayload(payload, const <String>[
      'trophies',
      'items',
    ]).map(TrophyDTO.fromJson).toList(growable: false);
  }

  @override
  Future<List<ClubRankingDTO>> getRankings(String clubId) async {
    final Object? payload = await _request('/api/clubs/$clubId/rankings');
    return _listPayload(payload, const <String>[
      'rankings',
      'standings',
      'items',
    ]).map(ClubRankingDTO.fromJson).toList(growable: false);
  }

  Future<Object?> _request(String path) async {
    if (config.baseUrl.trim().isEmpty) {
      throw const ClubHqRepositoryBlockedException(
        'Club HQ backend endpoint is not configured.',
      );
    }

    try {
      final Map<String, String> headers = <String, String>{
        'Accept': 'application/json',
      };
      final String? token = await _readAccessToken();
      if (token != null && token.isNotEmpty) {
        headers['Authorization'] = 'Bearer $token';
      }
      final GteTransportResponse response = await transport.send(
        GteTransportRequest(
          method: 'GET',
          uri: config.uriFor(path),
          headers: headers,
        ),
      );
      if (response.statusCode >= 400) {
        throw GteApiException(
          type: _errorTypeFromStatus(response.statusCode),
          message: gteApiErrorMessage(
            response.body,
            fallback: 'Club HQ backend request failed.',
          ),
          statusCode: response.statusCode,
          cause: response.body,
        );
      }
      return gteApiSuccessPayload(response.body);
    } on GteApiException {
      rethrow;
    } on ClubHqRepositoryBlockedException {
      rethrow;
    } catch (error) {
      throw GteApiException(
        type: GteApiErrorType.network,
        message: 'Unable to reach the Club HQ backend.',
        cause: error,
      );
    }
  }

  Future<String?> _readAccessToken() async {
    final String direct = accessToken?.trim() ?? '';
    if (direct.isNotEmpty) {
      return direct;
    }
    try {
      final session = await authSessionStore.readSession();
      final String token = session?.accessToken.trim() ?? '';
      return token.isEmpty ? null : token;
    } catch (_) {
      return null;
    }
  }
}

List<Object?> _listPayload(Object? payload, List<String> keys) {
  if (payload is List) {
    return List<Object?>.from(payload);
  }
  final ClubJson json = clubAsMap(payload);
  for (final String key in keys) {
    final Object? value = json[key];
    if (value is List) {
      return List<Object?>.from(value);
    }
  }
  return const <Object?>[];
}

GteApiErrorType _errorTypeFromStatus(int statusCode) {
  if (statusCode == 401) {
    return GteApiErrorType.unauthorized;
  }
  if (statusCode == 404) {
    return GteApiErrorType.notFound;
  }
  if (statusCode >= 500) {
    return GteApiErrorType.unavailable;
  }
  if (statusCode >= 400) {
    return GteApiErrorType.validation;
  }
  return GteApiErrorType.unknown;
}
