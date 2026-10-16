import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';
import 'package:gte_frontend/data/gte_mock_api.dart';
import 'package:gte_frontend/domain/value/gtex_value_models.dart';

/// A regression guard on `GteExchangeApiClient.fetchPlayerForm`.
///
/// `gte_exchange_api_client.dart` is a shared file that several workstreams edit
/// and occasionally regenerate wholesale. `fetchPlayerForm` was silently deleted
/// from it once already during Phase 4; the only thing that caught it was a
/// manual `flutter analyze`, which nothing forces anyone to run.
///
/// These tests turn that silent deletion into a failing test. The file will not
/// compile if the method is removed, and the endpoint assertion pins the URL so a
/// rename cannot quietly break the player-detail form card either.
class _RecordingTransport implements GteTransport {
  GteTransportRequest? lastRequest;
  Map<String, Object?> body = const <String, Object?>{};
  Object? rawBody;
  int statusCode = 200;

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    lastRequest = request;
    return GteTransportResponse(
      statusCode: statusCode,
      body: rawBody ?? body,
    );
  }
}

GteExchangeApiClient _client(_RecordingTransport transport) {
  return GteExchangeApiClient(
    config: const GteRepositoryConfig(
      baseUrl: 'https://example.test',
      mode: GteBackendMode.live,
    ),
    transport: transport,
    repository: GteMockApi(),
  );
}

void main() {
  test('fetchPlayerForm targets the documented endpoint', () async {
    final _RecordingTransport transport = _RecordingTransport()
      ..body = <String, Object?>{
        'player_id': 'lamine-yamal',
        'has_sample': true,
        'matches_counted': 6,
        'competitions_counted': 3,
        'average_rating': 8.2,
        'trend': 'rising',
        'trend_delta': 0.4,
        'total_minutes': 540,
        'signal': <String, Object?>{
          'applied': true,
          'adjustment_pct': 0.0121,
          'reason_code': 'matchday_form_positive',
          'minimum_matches_required': 3,
          'matches_counted': 6,
          'effective_max_adjustment_pct': 0.024,
        },
        'performances': <Object?>[],
      };

    final GtexPlayerForm form = await _client(
      transport,
    ).fetchPlayerForm('lamine-yamal');

    expect(transport.lastRequest, isNotNull);
    expect(
      transport.lastRequest!.uri.path,
      contains('/players/lamine-yamal/form'),
    );
    expect(form.hasSample, isTrue);
    expect(form.matchesCounted, 6);
    expect(form.movesValuation, isTrue);
    expect(form.signal?.adjustmentPct, 0.0121);
  });

  test('a live backend failure propagates rather than faking a form', () async {
    // `_loadPublicWithFallback` substitutes the fallback for FIXTURE mode only.
    // In live mode the error is the caller's to handle, and it must not be
    // swallowed into a form that reads as real. `GtexFmPlayerProfileScreen`
    // catches this and shows the honest empty state.
    final _RecordingTransport transport = _RecordingTransport()..statusCode = 500;

    await expectLater(
      _client(transport).fetchPlayerForm('unknown-player'),
      throwsA(isA<GteApiException>()),
    );
  });

  test('fixture mode yields the honest empty form, never invented data', () async {
    final GteExchangeApiClient client = GteExchangeApiClient.fixture();

    final GtexPlayerForm form = await client.fetchPlayerForm('lamine-yamal');

    expect(form.hasSample, isFalse);
    expect(form.averageRating, isNull);
    expect(form.signal, isNull);
    expect(form.movesValuation, isFalse);
  });

  test('a non-map payload degrades instead of throwing a cast error', () async {
    // Guards the copy-not-cast fix: a hard `as Map<String, dynamic>` turned any
    // unexpected shape into a bogus "network" failure.
    final _RecordingTransport transport = _RecordingTransport()..rawBody = 'nonsense';

    final GtexPlayerForm form = await _client(
      transport,
    ).fetchPlayerForm('lamine-yamal');

    expect(form.hasSample, isFalse);
    expect(form.playerId, 'lamine-yamal');
  });

  test('a player with no eligible football reports no sample', () async {
    final _RecordingTransport transport = _RecordingTransport()
      ..body = <String, Object?>{
        'player_id': 'benchwarmer',
        'has_sample': false,
        'matches_counted': 0,
        'competitions_counted': 0,
        'average_rating': null,
        'trend': 'steady',
        'signal': null,
        'performances': <Object?>[],
      };

    final GtexPlayerForm form = await _client(
      transport,
    ).fetchPlayerForm('benchwarmer');

    expect(form.hasSample, isFalse);
    expect(form.averageRating, isNull);
    expect(form.movesValuation, isFalse);
  });
}
