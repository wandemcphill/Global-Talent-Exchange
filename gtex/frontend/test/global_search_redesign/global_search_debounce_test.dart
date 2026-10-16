import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';
import 'package:gte_frontend/features/global_search_redesign/global_search_api.dart';
import 'package:gte_frontend/features/global_search_redesign/global_search_controller.dart';
import 'package:gte_frontend/features/global_search_redesign/global_search_models.dart';

/// Records every term it is asked for and lets the test decide when (and in
/// what order) each request completes.
class _ScriptedSearchApi implements GtexGlobalSearchApi {
  _ScriptedSearchApi({required this.client});

  @override
  final GteAuthedApi client;

  final List<String> requestedTerms = <String>[];
  final Map<String, Completer<List<GtexGlobalSearchResult>>> pending =
      <String, Completer<List<GtexGlobalSearchResult>>>{};

  /// When set, every search fails with this error.
  Object? failure;

  @override
  Future<List<GtexGlobalSearchResult>> search(
    String term, {
    bool admin = false,
    int limit = 20,
  }) {
    requestedTerms.add(term);
    final Object? error = failure;
    if (error != null) {
      return Future<List<GtexGlobalSearchResult>>.error(error);
    }
    final Completer<List<GtexGlobalSearchResult>> completer =
        Completer<List<GtexGlobalSearchResult>>();
    pending[term] = completer;
    return completer.future;
  }

  void complete(String term, List<String> titles) {
    pending.remove(term)!.complete(
      titles
          .map(
            (String title) => GtexGlobalSearchResult(
              type: 'player',
              id: title,
              title: title,
              subtitle: '',
              imageUrl: null,
              route: '/app/market',
              score: 1,
              permissionRequired: null,
              metadata: const <String, Object?>{},
            ),
          )
          .toList(growable: false),
    );
  }
}

GtexGlobalSearchController _buildController(_ScriptedSearchApi api) {
  return GtexGlobalSearchController(
    api: api,
    // Admin short-circuits the launch-control flag lookup, which keeps these
    // tests focused on debounce and ordering rather than feature gating.
    admin: true,
    debounce: const Duration(milliseconds: 20),
  );
}

void main() {
  late _ScriptedSearchApi api;
  late GtexGlobalSearchController controller;

  setUp(() {
    api = _ScriptedSearchApi(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.fixture,
        ),
        transport: GteHttpTransport(),
        accessToken: 'test-token',
        mode: GteBackendMode.fixture,
      ),
    );
    controller = _buildController(api);
  });

  tearDown(() => controller.dispose());

  test('short terms never reach the backend', () async {
    controller.search('a');
    await Future<void>.delayed(const Duration(milliseconds: 40));

    expect(api.requestedTerms, isEmpty);
    expect(controller.results, isEmpty);
    expect(controller.loading, isFalse);
  });

  test('collapses a burst of keystrokes into one request', () async {
    controller.search('ars');
    controller.search('arse');
    controller.search('arsen');
    controller.search('arsenal');
    await Future<void>.delayed(const Duration(milliseconds: 40));

    expect(api.requestedTerms, <String>['arsenal']);
  });

  test('shows loading immediately, before the debounce elapses', () async {
    controller.search('lagos');
    expect(controller.loading, isTrue);
    expect(api.requestedTerms, isEmpty);

    await Future<void>.delayed(const Duration(milliseconds: 40));
    expect(api.requestedTerms, <String>['lagos']);
  });

  test('a slow earlier response cannot overwrite a newer one', () async {
    controller.search('lag');
    await Future<void>.delayed(const Duration(milliseconds: 40));
    controller.search('lagos');
    await Future<void>.delayed(const Duration(milliseconds: 40));

    expect(api.requestedTerms, <String>['lag', 'lagos']);

    // Newer request lands first, then the stale one arrives late.
    api.complete('lagos', <String>['Lagos Crown']);
    await Future<void>.delayed(Duration.zero);
    api.complete('lag', <String>['Stale Result']);
    await Future<void>.delayed(Duration.zero);

    expect(
      controller.results.map((r) => r.title),
      <String>['Lagos Crown'],
      reason: 'the stale response must be discarded',
    );
  });

  test('clearing the box abandons an in-flight request', () async {
    controller.search('lagos');
    await Future<void>.delayed(const Duration(milliseconds: 40));
    expect(api.requestedTerms, <String>['lagos']);

    controller.search('');
    api.complete('lagos', <String>['Lagos Crown']);
    await Future<void>.delayed(Duration.zero);

    expect(controller.results, isEmpty);
    expect(controller.loading, isFalse);
  });

  test('searchNow bypasses the debounce', () async {
    unawaited(controller.searchNow('accra'));
    await Future<void>.delayed(Duration.zero);

    expect(api.requestedTerms, <String>['accra']);
  });

  test('surfaces an error and recovers on retry', () async {
    api.failure = StateError('search backend down');
    await controller.searchNow('accra');

    expect(controller.error, isNotNull);
    expect(controller.loading, isFalse);

    api.failure = null;
    final Future<void> retry = controller.retry();
    await Future<void>.delayed(Duration.zero);
    api.complete('accra', <String>['Accra Sentinels']);
    await retry;

    expect(controller.error, isNull);
    expect(controller.results.single.title, 'Accra Sentinels');
  });

  test('does not notify after dispose', () async {
    controller.search('lagos');
    await Future<void>.delayed(const Duration(milliseconds: 40));

    controller.dispose();
    api.complete('lagos', <String>['Lagos Crown']);
    await Future<void>.delayed(Duration.zero);

    // Reaching here without a "used after dispose" assertion is the contract.
    controller = _buildController(api);
  });
}
