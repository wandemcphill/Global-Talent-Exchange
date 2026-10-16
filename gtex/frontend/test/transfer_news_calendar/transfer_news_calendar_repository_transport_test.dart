import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/features/transfer_news_calendar/data/transfer_news_calendar_models.dart';
import 'package:gte_frontend/features/transfer_news_calendar/data/transfer_news_calendar_repository.dart';

void main() {
  test('transfer news calendar repository uses canonical api routes', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'seasons': <Object?>[_seasonJson],
            'active_events': <Object?>[_eventJson],
            'active_pause_status': _pauseJson,
            'recent_lifecycle_runs': <Object?>[_runJson],
          },
        ),
        GteTransportResponse(statusCode: 200, body: <Object?>[_seasonJson]),
        GteTransportResponse(statusCode: 200, body: <Object?>[_eventJson]),
        GteTransportResponse(statusCode: 200, body: _pauseJson),
        GteTransportResponse(statusCode: 200, body: <Object?>[_runJson]),
        GteTransportResponse(statusCode: 200, body: _seasonJson),
        GteTransportResponse(statusCode: 200, body: _eventJson),
        GteTransportResponse(statusCode: 200, body: _runJson),
        GteTransportResponse(statusCode: 200, body: _runJson),
      ],
    );
    final TransferNewsCalendarApiRepository repository =
        TransferNewsCalendarApiRepository(
          client: GteAuthedApi(
            config: const GteRepositoryConfig(
              baseUrl: 'https://example.test',
              mode: GteBackendMode.live,
            ),
            transport: transport,
            accessToken: 'token-1',
            mode: GteBackendMode.live,
          ),
        );

    await repository.fetchCalendarDashboard();
    await repository.listCalendarSeasons(
      const CalendarSeasonsQuery(activeOnly: true),
    );
    await repository.listCalendarEvents(
      CalendarEventsQuery(
        activeOnly: true,
        family: 'hosted',
        status: 'scheduled',
      ),
    );
    await repository.fetchPauseStatus(
      PauseStatusQuery(asOf: DateTime.utc(2026, 3, 10)),
    );
    await repository.listLifecycleRuns();
    await repository.createCalendarSeason(
      CalendarSeasonCreateRequest(
        seasonKey: 'season-2026',
        title: 'Season 2026',
        startsOn: DateTime.utc(2026, 3, 1),
        endsOn: DateTime.utc(2026, 6, 1),
      ),
    );
    await repository.createCalendarEvent(
      CalendarEventCreateRequest(
        eventKey: 'event-1',
        title: 'Open Window',
        startsOn: DateTime.utc(2026, 3, 10),
        endsOn: DateTime.utc(2026, 3, 12),
      ),
    );
    await repository.launchHostedCompetition(
      'comp-1',
      const HostedCompetitionLaunchRequest(overrideTitle: 'Creator Cup Launch'),
    );
    await repository.launchNationalCompetition(
      'nation-1',
      const NationalCompetitionLaunchRequest(
        overrideTitle: 'Nations Cup Launch',
      ),
    );

    expect(
      transport.requests.map((GteTransportRequest request) => request.uri.path),
      <String>[
        '/api/v2/calendar-engine/dashboard',
        '/api/v2/calendar-engine/seasons',
        '/api/v2/calendar-engine/events',
        '/api/v2/calendar-engine/pause-status',
        '/api/v2/calendar-engine/lifecycle-runs',
        '/api/v2/admin/calendar-engine/seasons',
        '/api/v2/admin/calendar-engine/events',
        '/api/v2/admin/calendar-engine/hosted-competitions/comp-1/launch',
        '/api/v2/admin/calendar-engine/national-competitions/nation-1/launch',
      ],
    );
    expect(transport.requests[1].uri.queryParameters['active_only'], 'true');
    expect(transport.requests[2].uri.queryParameters['family'], 'hosted');
    expect(transport.requests[2].uri.queryParameters['status'], 'scheduled');
    expect(transport.requests[3].uri.queryParameters['as_of'], '2026-03-10');
  });
}

class _RecordingTransport implements GteTransport {
  _RecordingTransport(this._responses);

  final List<GteTransportResponse> _responses;
  final List<GteTransportRequest> requests = <GteTransportRequest>[];

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    requests.add(request);
    return _responses.removeAt(0);
  }
}

const Map<String, Object?> _seasonJson = <String, Object?>{
  'id': 'season-1',
  'season_key': 'season-2026',
  'title': 'Season 2026',
  'starts_on': '2026-03-01',
  'ends_on': '2026-06-01',
  'status': 'scheduled',
  'active': true,
  'metadata_json': <String, Object?>{},
};

const Map<String, Object?> _eventJson = <String, Object?>{
  'id': 'event-1',
  'season_id': 'season-1',
  'event_key': 'event-1',
  'title': 'Open Window',
  'description': 'Calendar event',
  'source_type': 'manual',
  'source_id': 'source-1',
  'family': 'hosted',
  'age_band': 'senior',
  'starts_on': '2026-03-10',
  'ends_on': '2026-03-12',
  'exclusive_windows': false,
  'pause_other_gtx_competitions': false,
  'visibility': 'public',
  'status': 'scheduled',
  'metadata_json': <String, Object?>{},
};

const Map<String, Object?> _pauseJson = <String, Object?>{
  'as_of': '2026-03-10',
  'blocked_competition_families': <Object?>['hosted'],
  'active_event_keys': <Object?>['event-1'],
  'summary': 'Hosted competitions paused.',
};

const Map<String, Object?> _runJson = <String, Object?>{
  'id': 'run-1',
  'event_id': 'event-1',
  'source_type': 'hosted_competition',
  'source_id': 'comp-1',
  'source_title': 'Creator Cup',
  'competition_format': 'cup',
  'status': 'scheduled',
  'stage': 'launch',
  'generated_rounds': 3,
  'generated_matches': 7,
  'scheduled_dates_json': <Object?>['2026-03-10'],
  'summary_text': 'Lifecycle scheduled.',
  'metadata_json': <String, Object?>{},
};
