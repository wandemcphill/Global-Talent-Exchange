import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/competition_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';

void main() {
  for (final String? token in <String?>['read-token', null]) {
    final String tokenLabel =
        token == null ? 'without a token' : 'with a token';

    test(
      'competition collection reads are opportunistically authenticated $tokenLabel',
      () async {
        final _RecordingTransport transport = _RecordingTransport();
        final CompetitionApi api = _api(transport, token);

        await expectLater(
          api.fetchCompetitions(),
          throwsA(
            isA<GteApiException>().having(
              (GteApiException error) => error.statusCode,
              'statusCode',
              403,
            ),
          ),
        );

        expect(transport.requests, hasLength(1));
        expect(
          transport.requests.single.headers['Authorization'],
          token == null ? isNull : 'Bearer read-token',
        );
      },
    );

    test(
      'competition detail reads are opportunistically authenticated $tokenLabel',
      () async {
        final _RecordingTransport transport = _RecordingTransport();
        final CompetitionApi api = _api(transport, token);

        await expectLater(
          api.fetchCompetition('competition-1'),
          throwsA(
            isA<GteApiException>().having(
              (GteApiException error) => error.statusCode,
              'statusCode',
              403,
            ),
          ),
        );

        expect(transport.requests, hasLength(1));
        expect(
          transport.requests.single.headers['Authorization'],
          token == null ? isNull : 'Bearer read-token',
        );
      },
    );
  }
}

CompetitionApi _api(_RecordingTransport transport, String? token) {
  return CompetitionApi(
    config: const GteRepositoryConfig(baseUrl: 'https://example.test'),
    transport: transport,
    accessToken: token,
  );
}

class _RecordingTransport implements GteTransport {
  final List<GteTransportRequest> requests = <GteTransportRequest>[];

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    requests.add(request);
    return const GteTransportResponse(
      statusCode: 403,
      body: <String, Object?>{'detail': 'forbidden'},
    );
  }
}
