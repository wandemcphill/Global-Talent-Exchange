import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/features/app_routes/gte_app_route_registry.dart';
import 'package:gte_frontend/features/app_routes/gte_route_data.dart';
import 'package:gte_frontend/features/match/replay_archive_route_screen.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';
import 'package:gte_frontend/shared/models/auth_session.dart';

void main() {
  test(
    'replay archive repository uses policy endpoints for public and signed-in lanes',
    () async {
      final _RecordingTransport
      transport = _RecordingTransport(<String, GteTransportResponse>{
        'GET /api/v2/replays/public/featured': const GteTransportResponse(
          statusCode: 200,
          body: <Object?>[
            <String, Object?>{
              'replay_id': 'replay-final',
              'fixture_id': 'fixture-final',
              'scheduled_start': '2030-07-12T19:00:00Z',
              'final_whistle_at': '2030-07-12T21:00:00Z',
              'live': false,
              'home_club': <String, Object?>{
                'club_id': 'club-home',
                'club_name': 'Lagos Stars',
              },
              'away_club': <String, Object?>{
                'club_id': 'club-away',
                'club_name': 'Abuja City',
              },
              'scoreline': <String, Object?>{'home_goals': 2, 'away_goals': 1},
              'competition_context': <String, Object?>{
                'competition_id': 'comp-final',
                'competition_type': 'cup',
                'competition_name': 'GTEX Super Cup',
                'stage_name': 'Final',
                'is_final': true,
                'resolved_visibility': 'public',
                'replay_visibility': 'public',
                'competition_allows_public': true,
                'allow_early_round_public': false,
                'presentation_duration_minutes': 15,
                'public_metadata_visible': true,
                'featured_public': true,
              },
            },
          ],
        ),
        'GET /api/v2/replays/me': const GteTransportResponse(
          statusCode: 200,
          body: <Object?>[
            <String, Object?>{
              'replay_id': 'replay-private',
              'fixture_id': 'fixture-private',
              'scheduled_start': '2030-07-10T18:00:00Z',
              'final_whistle_at': '2030-07-10T20:00:00Z',
              'live': false,
              'home_club': <String, Object?>{
                'club_id': 'club-home',
                'club_name': 'Your Club',
              },
              'away_club': <String, Object?>{
                'club_id': 'club-away',
                'club_name': 'Port Harcourt Wave',
              },
              'scoreline': <String, Object?>{'home_goals': 1, 'away_goals': 0},
              'competition_context': <String, Object?>{
                'competition_id': 'comp-private',
                'competition_type': 'league',
                'competition_name': 'Creator League',
                'stage_name': 'Quarterfinal',
                'is_final': false,
                'resolved_visibility': 'competition',
                'replay_visibility': 'competition',
                'competition_allows_public': false,
                'allow_early_round_public': false,
                'presentation_duration_minutes': 15,
                'public_metadata_visible': false,
                'featured_public': false,
              },
            },
          ],
        ),
      });
      final ApiReplayArchiveRouteRepository repository =
          ApiReplayArchiveRouteRepository(
            api: GteAuthedApi(
              config: const GteRepositoryConfig(
                baseUrl: 'https://example.test',
                mode: GteBackendMode.live,
              ),
              transport: transport,
              authSession: const AuthSession(
                userId: 'user-1',
                accessToken: 'token-1',
                refreshToken: '',
                sessionId: 'session-1',
                role: 'user',
              ),
              mode: GteBackendMode.live,
            ),
          );

      final ReplayArchiveOverview overview = await repository.loadOverview(
        isAuthenticated: true,
      );

      expect(overview.publicFeatured, hasLength(1));
      expect(overview.myReplays, hasLength(1));
      expect(transport.requestLog, <String>[
        'GET /api/v2/replays/public/featured',
        'GET /api/v2/replays/me',
      ]);
    },
  );

  testWidgets('club replay route mounts the replay archive screen', (
    WidgetTester tester,
  ) async {
    const GteNavigationDependencies dependencies = GteNavigationDependencies(
      apiBaseUrl: 'https://example.test',
      backendMode: GteBackendMode.fixture,
      currentClubId: 'club-1',
      currentClubName: 'Lagos Stars',
    );
    final GteAppRouteRegistry registry = GteAppRouteRegistry(
      dependencies: dependencies,
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Builder(
          builder:
              (BuildContext context) => registry.buildScreen(
                context,
                const ClubReplaysRouteData(
                  clubId: 'club-1',
                  clubName: 'Lagos Stars',
                ),
              ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Replay archive'), findsOneWidget);
    expect(
      find.textContaining(
        'replay discovery now runs through the replay-archive policy layer',
      ),
      findsOneWidget,
    );
    expect(find.text('Matchday hub'), findsNothing);
  });
}

class _RecordingTransport implements GteTransport {
  _RecordingTransport(this._responses);

  final Map<String, GteTransportResponse> _responses;
  final List<String> requestLog = <String>[];

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    final String key = '${request.method.toUpperCase()} ${request.uri.path}';
    requestLog.add(key);
    final GteTransportResponse? response = _responses[key];
    if (response != null) {
      return response;
    }
    return const GteTransportResponse(
      statusCode: 404,
      body: <String, Object?>{'detail': 'missing response'},
    );
  }
}

