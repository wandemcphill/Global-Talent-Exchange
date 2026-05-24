import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/competition_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/hosted_competition_api.dart';
import 'package:gte_frontend/features/competitions/live_competitions_provider.dart';
import 'package:gte_frontend/features/streamer_tournament_engine/data/streamer_tournament_engine_models.dart';
import 'package:gte_frontend/features/streamer_tournament_engine/data/streamer_tournament_engine_repository.dart';
import 'package:gte_frontend/models/hosted_competition_models.dart';
import 'package:gte_frontend/shared/providers/live_clients_provider.dart';

void main() {
  test('competition hub loads hosted competitions from hosted API', () async {
    final _RecordingHostedCompetitionApi hostedApi =
        _RecordingHostedCompetitionApi();
    final ProviderContainer container = ProviderContainer(
      overrides: [
        competitionApiProvider.overrideWithValue(
          CompetitionApi(
            config: const GteRepositoryConfig(
              baseUrl: 'https://example.test',
              mode: GteBackendMode.live,
            ),
            transport: const _EmptyCompetitionTransport(),
          ),
        ),
        hostedCompetitionApiProvider.overrideWithValue(hostedApi),
        streamerTournamentRepositoryProvider.overrideWithValue(
          _EmptyStreamerTournamentRepository(),
        ),
      ],
    );
    addTearDown(container.dispose);

    final CompetitionHubData data = await container.read(
      competitionHubProvider.future,
    );

    expect(hostedApi.listCompetitionsCalls, 1);
    expect(data.hostedCompetitions, hasLength(1));
    expect(data.hostedCompetitions.single.id, 'hosted-live-1');
  });
}

class _RecordingHostedCompetitionApi implements HostedCompetitionApi {
  int listCompetitionsCalls = 0;

  @override
  GteAuthedApi get client => _unusedAuthedApi();

  @override
  Future<List<HostedCompetition>> listCompetitions() async {
    listCompetitionsCalls += 1;
    return <HostedCompetition>[
      HostedCompetition(
        id: 'hosted-live-1',
        templateId: 'template-1',
        hostUserId: 'user-1',
        title: 'Friday Night Creator Cup',
        slug: 'friday-night-creator-cup',
        description: 'Live hosted cup from the hosted API.',
        status: 'open',
        visibility: 'public',
        startsAt: DateTime.utc(2026, 3, 15, 18),
        lockAt: DateTime.utc(2026, 3, 15, 17, 30),
        maxParticipants: 16,
        entryFeeFancoin: 5,
        rewardPoolFancoin: 80,
        platformFeeAmount: 6,
        metadata: const <String, Object?>{},
        createdAt: DateTime.utc(2026, 3, 10),
        updatedAt: DateTime.utc(2026, 3, 12),
      ),
    ];
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _EmptyStreamerTournamentRepository
    implements StreamerTournamentEngineRepository {
  @override
  Future<StreamerTournamentList> listPublicTournaments() async {
    return const StreamerTournamentList.empty();
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _EmptyCompetitionTransport implements GteTransport {
  const _EmptyCompetitionTransport();

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    return const GteTransportResponse(
      statusCode: 200,
      body: <String, Object?>{'total': 0, 'items': <Object?>[]},
    );
  }
}

GteAuthedApi _unusedAuthedApi() {
  return GteAuthedApi(
    config: const GteRepositoryConfig(
      baseUrl: 'https://example.test',
      mode: GteBackendMode.live,
    ),
    transport: const _EmptyCompetitionTransport(),
  );
}
