import '../../../data/gte_api_repository.dart';
import '../../../data/gte_http_transport.dart';
import '../../../shared/auth/auth_identity_store.dart';
import '../domain/squad_models.dart';

abstract class ISquadRepository {
  Future<SquadOperationsSnapshot> fetchSquadOperations(String clubId);
  Future<List<SquadPlayerDTO>> getSquadRoster(String clubId);
  Future<AvailabilityMatrix> getAvailabilityMatrix(String clubId);
  Future<List<InjuryDTO>> getInjuries(String clubId);
  Future<ChemistryReport> getChemistryReport(String clubId);
  Future<List<ContractStatusDTO>> getContracts(String clubId);
  Future<List<ScoutingNoteDTO>> getScoutingNotes(String clubId);
}

class SquadRepositoryBlockedException implements Exception {
  const SquadRepositoryBlockedException(this.reason);

  final String reason;

  @override
  String toString() => reason;
}

class BackendSquadRepository implements ISquadRepository {
  BackendSquadRepository({
    required this.config,
    required this.transport,
    this.accessToken,
    AuthSessionStore? authSessionStore,
  }) : authSessionStore = authSessionStore ?? SecureAuthSessionStore();

  factory BackendSquadRepository.standard({
    String baseUrl = const String.fromEnvironment('GTEX_API_BASE_URL'),
    String? accessToken,
  }) {
    return BackendSquadRepository(
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
  Future<SquadOperationsSnapshot> fetchSquadOperations(String clubId) async {
    final Future<List<SquadPlayerDTO>> roster = getSquadRoster(clubId);
    final Future<AvailabilityMatrix> matrix = getAvailabilityMatrix(clubId);
    final Future<List<InjuryDTO>> injuries = getInjuries(clubId);
    final Future<ChemistryReport> chemistry = getChemistryReport(clubId);
    final Future<List<ContractStatusDTO>> contracts = getContracts(clubId);
    final Future<List<ScoutingNoteDTO>> scouting = getScoutingNotes(clubId);

    final List<SquadPlayerDTO> resolvedRoster = await roster;
    final List<ScoutingNoteDTO> embeddedNotes = resolvedRoster
        .expand((SquadPlayerDTO player) => player.scoutingNotes)
        .toList(growable: false);

    return SquadOperationsSnapshot(
      roster: resolvedRoster,
      availabilityMatrix: await matrix,
      injuries: await injuries,
      chemistry: await chemistry,
      contracts: await contracts,
      scoutingNotes: <ScoutingNoteDTO>[...await scouting, ...embeddedNotes],
    );
  }

  @override
  Future<List<SquadPlayerDTO>> getSquadRoster(String clubId) async {
    final Object? payload = await _request('/api/clubs/$clubId/squad');
    return _listPayload(payload, const <String>[
      'players',
      'roster',
      'squad',
    ]).map(SquadPlayerDTO.fromJson).toList(growable: false);
  }

  @override
  Future<AvailabilityMatrix> getAvailabilityMatrix(String clubId) async {
    return AvailabilityMatrix.fromJson(
      await _request('/api/clubs/$clubId/squad/availability'),
    );
  }

  @override
  Future<List<InjuryDTO>> getInjuries(String clubId) async {
    final Object? payload = await _request('/api/clubs/$clubId/squad/injuries');
    return _listPayload(payload, const <String>[
      'injuries',
      'items',
    ]).map(InjuryDTO.fromJson).toList(growable: false);
  }

  @override
  Future<ChemistryReport> getChemistryReport(String clubId) async {
    return ChemistryReport.fromJson(
      await _request('/api/clubs/$clubId/squad/chemistry'),
    );
  }

  @override
  Future<List<ContractStatusDTO>> getContracts(String clubId) async {
    final Object? payload = await _request(
      '/api/clubs/$clubId/squad/contracts',
    );
    return _listPayload(payload, const <String>[
      'contracts',
      'items',
    ]).map(ContractStatusDTO.fromJson).toList(growable: false);
  }

  @override
  Future<List<ScoutingNoteDTO>> getScoutingNotes(String clubId) async {
    final Object? payload = await _request('/api/clubs/$clubId/squad/scouting');
    return _listPayload(payload, const <String>[
      'scouting_notes',
      'scoutingNotes',
      'notes',
      'items',
    ]).map(ScoutingNoteDTO.fromJson).toList(growable: false);
  }

  Future<Object?> _request(String path) async {
    if (config.baseUrl.trim().isEmpty) {
      throw const SquadRepositoryBlockedException(
        'Squad backend endpoint is not configured.',
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
            fallback: 'Squad backend request failed.',
          ),
          statusCode: response.statusCode,
          cause: response.body,
        );
      }
      return gteApiSuccessPayload(response.body);
    } on GteApiException {
      rethrow;
    } on SquadRepositoryBlockedException {
      rethrow;
    } catch (error) {
      throw GteApiException(
        type: GteApiErrorType.network,
        message: 'Unable to reach the Squad backend.',
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
  final SquadJson json = squadAsMap(payload);
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
