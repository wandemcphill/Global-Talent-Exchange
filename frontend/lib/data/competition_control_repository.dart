import 'gte_api_repository.dart';
import 'gte_http_transport.dart';

class CompetitionControlRepository {
  CompetitionControlRepository({required this.config, required this.transport, required this.accessToken});

  final GteRepositoryConfig config;
  final GteTransport transport;
  final String accessToken;

  factory CompetitionControlRepository.standard({required String baseUrl, required String accessToken, GteBackendMode mode = GteBackendMode.liveThenFixture}) {
    return CompetitionControlRepository(
      config: GteRepositoryConfig(baseUrl: baseUrl, mode: mode),
      transport: GteHttpTransport(),
      accessToken: accessToken,
    );
  }

  Future<Map<String, dynamic>> fetchRuntime(String code, {required int participants, String region = 'africa'}) => _getMap('/api/competitions/runtime/$code', query: <String, Object?>{'participants': participants, 'region': region}, auth: false);
  Future<List<Map<String, dynamic>>> fetchAdminCompetitions() => _getList('/api/competitions/admin');
  Future<Map<String, dynamic>> updateCompetition(String code, Map<String, Object?> body) => _patchMap('/api/competitions/admin/$code', body: body);
  Future<Map<String, dynamic>> fetchOrchestrationPreview(String code, {int participants = 6, String region = 'africa'}) => _getMap('/api/competitions/admin/$code/orchestrate', query: <String, Object?>{'participants': participants, 'region': region});

  Future<Map<String, dynamic>> _getMap(String path, {Map<String, Object?> query = const <String, Object?>{}, bool auth = true}) async {
    final Object? body = await _request('GET', path, query: query, auth: auth);
    if (body is Map<String, dynamic>) return body;
    throw const GteApiException(type: GteApiErrorType.parsing, message: 'Unexpected competition response shape.');
  }

  Future<List<Map<String, dynamic>>> _getList(String path, {Map<String, Object?> query = const <String, Object?>{}, bool auth = true}) async {
    final Object? body = await _request('GET', path, query: query, auth: auth);
    if (body is List) return body.whereType<Map>().map((dynamic item) => Map<String, dynamic>.from(item as Map)).toList(growable: false);
    throw const GteApiException(type: GteApiErrorType.parsing, message: 'Unexpected competition list response shape.');
  }

  Future<Map<String, dynamic>> _patchMap(String path, {Object? body}) async {
    final Object? payload = await _request('PATCH', path, body: body);
    if (payload is Map<String, dynamic>) return payload;
    throw const GteApiException(type: GteApiErrorType.parsing, message: 'Unexpected competition response shape.');
  }

  Future<Object?> _request(String method, String path, {Map<String, Object?> query = const <String, Object?>{}, Object? body, bool auth = true}) async {
    final Map<String, String> headers = <String, String>{'Content-Type': 'application/json'};
    if (auth) headers['Authorization'] = 'Bearer $accessToken';
    final GteTransportResponse response = await transport.send(GteTransportRequest(method: method, uri: config.uriFor(path, query), headers: headers, body: body));
    if (response.statusCode >= 400) throw _toException(response);
    return response.body;
  }

  GteApiException _toException(GteTransportResponse response) {
    final Object? body = response.body;
    String message = 'Competition request failed.';
    if (body is Map<String, dynamic>) {
      message = (body['detail'] ?? body['message'] ?? message).toString();
    } else if (body is String && body.trim().isNotEmpty) {
      message = body;
    }
    return GteApiException(type: _errorType(response.statusCode), message: message, statusCode: response.statusCode);
  }

  GteApiErrorType _errorType(int statusCode) {
    if (statusCode == 401 || statusCode == 403) return GteApiErrorType.unauthorized;
    if (statusCode == 404) return GteApiErrorType.notFound;
    if (statusCode == 422) return GteApiErrorType.validation;
    if (statusCode >= 500) return GteApiErrorType.unavailable;
    return GteApiErrorType.unknown;
  }
}
