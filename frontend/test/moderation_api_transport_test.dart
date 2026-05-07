import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/moderation_api.dart';

void main() {
  test('moderation api uses canonical api routes', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        GteTransportResponse(statusCode: 201, body: _reportJson('report-1')),
        GteTransportResponse(
          statusCode: 200,
          body: <Object?>[_reportJson('report-1')],
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <Object?>[_reportJson('report-1')],
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'open_count': 1,
            'in_review_count': 0,
            'actioned_count': 0,
            'dismissed_count': 0,
            'critical_count': 0,
            'high_priority_count': 1,
            'recent_reports': <Object?>[_reportJson('report-1')],
          },
        ),
        GteTransportResponse(statusCode: 200, body: _reportJson('report-1')),
        GteTransportResponse(statusCode: 200, body: _reportJson('report-1')),
      ],
    );
    final ModerationApi api = ModerationApi.standard(
      baseUrl: 'https://example.test',
      accessToken: 'token-1',
      mode: GteBackendMode.live,
      transport: transport,
    );

    await api.createReport(
      targetType: 'user',
      targetId: 'user-2',
      reasonCode: 'abuse',
      description: 'Harassment in live thread.',
    );
    await api.listMyReports();
    await api.listReports(status: 'open');
    await api.fetchSummary();
    await api.assignReport(reportId: 'report-1', priority: 'critical');
    await api.resolveReport(
      reportId: 'report-1',
      resolutionAction: 'wallet_review',
      resolutionNote: 'Escalated to treasury.',
    );

    expect(
      transport.requests.map((GteTransportRequest request) => request.uri.path),
      <String>[
        '/api/v2/moderation/reports',
        '/api/v2/moderation/me/reports',
        '/api/v2/admin/moderation/reports',
        '/api/v2/admin/moderation/reports/summary',
        '/api/v2/admin/moderation/reports/report-1/assign',
        '/api/v2/admin/moderation/reports/report-1/resolve',
      ],
    );
    expect(transport.requests[2].uri.queryParameters['status'], 'open');
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

Map<String, Object?> _reportJson(String id) => <String, Object?>{
  'id': id,
  'reporter_user_id': 'user-1',
  'subject_user_id': 'user-2',
  'target_type': 'user',
  'target_id': 'user-2',
  'reason_code': 'abuse',
  'description': 'Harassment in live thread.',
  'evidence_url': null,
  'status': 'open',
  'priority': 'high',
  'assigned_admin_user_id': null,
  'resolution_action': 'none',
  'resolution_note': null,
  'resolved_by_user_id': null,
  'report_count_for_target': 1,
  'created_at': '2026-04-18T10:00:00Z',
  'updated_at': '2026-04-18T10:00:00Z',
};
