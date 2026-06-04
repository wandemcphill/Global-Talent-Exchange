import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/club_hub/formation/formation_editor_models.dart';
import 'package:gte_frontend/features/club_hub/formation/formation_editor_provider.dart';

void main() {
  test('formation snapshot parses backend roles and audit trail', () {
    final FormationEditorSnapshot snapshot = FormationEditorSnapshot.fromJson(
      <String, Object?>{
        'club_id': 'club-live',
        'formation_id': 'formation-1',
        'shape': '4-2-3-1',
        'status': 'published',
        'version': 7,
        'health': <String, Object?>{
          'score': 91,
          'warnings': <Object?>['One role is pending player confirmation.'],
        },
        'slots': <Object?>[
          <String, Object?>{
            'id': 'slot-gk',
            'role_code': 'GK',
            'role_label': 'Goalkeeper',
            'player_id': 'player-1',
            'player_name': 'Ayo Keeper',
            'x': 50,
            'y': 92,
          },
          <String, Object?>{
            'id': 'slot-am',
            'role_code': 'AM',
            'role_label': 'Attacking midfielder',
          },
        ],
        'audit_trail': <Object?>[
          <String, Object?>{
            'id': 'audit-1',
            'action': 'published',
            'actor': 'sporting-director',
            'occurred_at': '2026-06-02T08:00:00Z',
            'version': 7,
          },
        ],
      },
    );

    expect(snapshot.clubId, 'club-live');
    expect(snapshot.shape, '4-2-3-1');
    expect(snapshot.health.score, 91);
    expect(snapshot.snapshotState, FormationSnapshotState.degraded);
    expect(snapshot.positionedSlots.single.displayPlayer, 'Ayo Keeper');
    expect(
      snapshot.unpositionedSlots.single.displayRole,
      'Attacking midfielder',
    );
    expect(snapshot.auditTrail.single.action, 'published');
  });

  test('formation controller renders missing endpoint as blocked', () async {
    final FormationEditorController controller = FormationEditorController(
      clubId: 'club-live',
      baseUrl: 'http://example.com',
      transport: _QueueTransport(<_QueuedResponse>[
        const _QueuedResponse(statusCode: 404, body: <String, Object?>{}),
      ]),
    );

    await controller.load();

    expect(controller.state, FormationEditorLoadState.blocked);
    expect(controller.errorMessage, contains('not mounted'));
    expect(controller.snapshot, isNull);
  });

  test(
    'formation controller saves and publishes through backend audit endpoints',
    () async {
      final _QueueTransport transport = _QueueTransport(<_QueuedResponse>[
        _QueuedResponse(
          statusCode: 200,
          body: _snapshot(canSave: true, canPublish: true),
        ),
        _QueuedResponse(
          statusCode: 200,
          body: _snapshot(version: 8, canPublish: true),
        ),
        _QueuedResponse(
          statusCode: 200,
          body: _snapshot(
            status: 'published',
            version: 9,
            auditTrail: <Object?>[
              <String, Object?>{
                'id': 'audit-publish',
                'action': 'published',
                'occurred_at': '2026-06-02T08:15:00Z',
              },
            ],
          ),
        ),
      ]);
      final FormationEditorController controller = FormationEditorController(
        clubId: 'club-live',
        baseUrl: 'http://example.com',
        accessToken: 'formation-token',
        transport: transport,
      );

      await controller.load();
      await controller.saveDraft();
      await controller.publish();

      expect(transport.requests[0].method, 'GET');
      expect(
        transport.requests[0].uri.path,
        '/api/v2/clubs/club-live/formation',
      );
      expect(transport.requests[1].method, 'PATCH');
      expect(
        transport.requests[1].uri.path,
        '/api/v2/clubs/club-live/formation/draft',
      );
      expect(transport.requests[2].method, 'POST');
      expect(
        transport.requests[2].uri.path,
        '/api/v2/clubs/club-live/formation/publish',
      );
      expect(
        transport.requests[2].headers['Authorization'],
        'Bearer formation-token',
      );
      expect(controller.snapshot?.auditTrail.single.action, 'published');
    },
  );
}

Map<String, Object?> _snapshot({
  String status = 'draft',
  int version = 7,
  bool canSave = false,
  bool canPublish = false,
  List<Object?> auditTrail = const <Object?>[],
}) {
  return <String, Object?>{
    'club_id': 'club-live',
    'formation_id': 'formation-1',
    'shape': '4-2-3-1',
    'status': status,
    'version': version,
    'sync_token': 'sync-$version',
    'can_save_draft': canSave,
    'can_publish': canPublish,
    'health': <String, Object?>{'score': 96},
    'slots': <Object?>[
      <String, Object?>{
        'id': 'slot-gk',
        'role_code': 'GK',
        'role_label': 'Goalkeeper',
        'player_id': 'player-1',
        'player_name': 'Ayo Keeper',
        'x': 50,
        'y': 92,
      },
    ],
    'audit_trail': auditTrail,
  };
}

class _QueuedResponse {
  const _QueuedResponse({required this.statusCode, required this.body});

  final int statusCode;
  final Object? body;
}

class _QueueTransport implements GteTransport {
  _QueueTransport(List<_QueuedResponse> responses)
    : _responses = List<_QueuedResponse>.from(responses);

  final List<_QueuedResponse> _responses;
  final List<GteTransportRequest> requests = <GteTransportRequest>[];

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    requests.add(request);
    final _QueuedResponse response = _responses.removeAt(0);
    return GteTransportResponse(
      statusCode: response.statusCode,
      body: response.body,
    );
  }
}
