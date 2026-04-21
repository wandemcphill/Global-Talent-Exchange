import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/dispute_engine_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';

void main() {
  test('dispute engine api resolves to versioned dispute routes', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'disputes': <Object?>[_caseJson('case-1')],
            'total_open': 1,
          },
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'dispute': _caseJson('case-1'),
            'messages': <Object?>[_messageJson('msg-1', 'case-1')],
          },
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'dispute': _caseJson('case-1'),
            'messages': <Object?>[_messageJson('msg-1', 'case-1')],
          },
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'dispute': _caseJson('case-1'),
            'messages': <Object?>[
              _messageJson('msg-1', 'case-1'),
              _messageJson('msg-2', 'case-1'),
            ],
          },
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'disputes': <Object?>[_caseJson('case-1')],
            'total_open': 1,
          },
        ),
        GteTransportResponse(statusCode: 200, body: _caseJson('case-1')),
        GteTransportResponse(statusCode: 200, body: _caseJson('case-1')),
      ],
    );
    final DisputeEngineApi api = DisputeEngineApi.standard(
      baseUrl: 'https://example.test',
      accessToken: 'token-1',
      mode: GteBackendMode.live,
      transport: transport,
    );

    await api.listMyDisputes();
    await api.createDispute(
      resourceType: 'competition',
      resourceId: 'comp-1',
      reference: 'COMP-001',
      subject: 'Score dispute',
      message: 'The scoreline looks wrong.',
    );
    await api.fetchDispute('case-1');
    await api.addMessage(disputeId: 'case-1', message: 'Adding more context.');
    await api.listAdminDisputes();
    await api.assignDispute(disputeId: 'case-1', adminUserId: 'admin-1');
    await api.updateStatus(
      disputeId: 'case-1',
      status: 'resolved',
      note: 'Reviewed and resolved.',
    );

    expect(
      transport.requests.map((GteTransportRequest request) => request.uri.path),
      <String>[
        '/api/v1/disputes/me',
        '/api/v1/disputes',
        '/api/v1/disputes/case-1',
        '/api/v1/disputes/case-1/messages',
        '/api/v1/admin/disputes',
        '/api/v1/admin/disputes/case-1/assign',
        '/api/v1/admin/disputes/case-1/status',
      ],
    );
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

Map<String, Object?> _caseJson(String id) => <String, Object?>{
  'id': id,
  'user_id': 'user-1',
  'admin_user_id': 'admin-1',
  'resource_type': 'competition',
  'resource_id': 'comp-1',
  'reference': 'COMP-001',
  'status': 'open',
  'subject': 'Score dispute',
  'metadata_json': const <String, Object?>{},
  'created_at': '2026-04-18T10:00:00Z',
  'updated_at': '2026-04-18T10:00:00Z',
  'last_message_at': '2026-04-18T10:05:00Z',
  'resolved_at': null,
  'closed_at': null,
};

Map<String, Object?> _messageJson(String id, String disputeId) =>
    <String, Object?>{
      'id': id,
      'dispute_id': disputeId,
      'sender_user_id': 'user-1',
      'sender_role': 'user',
      'message': 'The scoreline looks wrong.',
      'attachment_id': null,
      'created_at': '2026-04-18T10:00:00Z',
    };
