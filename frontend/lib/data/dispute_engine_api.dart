import 'gte_api_repository.dart';
import 'gte_authed_api.dart';
import 'gte_http_transport.dart';
import '../models/dispute_engine_models.dart';

class DisputeEngineApi {
  DisputeEngineApi({
    required this.client,
    required this.fixtures,
  });

  final GteAuthedApi client;
  final _DisputeEngineFixtures fixtures;

  factory DisputeEngineApi.standard({
    required String baseUrl,
    required String? accessToken,
    GteBackendMode mode = GteBackendMode.liveThenFixture,
  }) {
    return DisputeEngineApi(
      client: GteAuthedApi(
        config: GteRepositoryConfig(baseUrl: baseUrl, mode: mode),
        transport: GteHttpTransport(),
        accessToken: accessToken,
        mode: mode,
      ),
      fixtures: _DisputeEngineFixtures.seed(),
    );
  }

  factory DisputeEngineApi.fixture() {
    return DisputeEngineApi(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.fixture,
        ),
        transport: GteHttpTransport(),
        accessToken: 'fixture-token',
        mode: GteBackendMode.fixture,
      ),
      fixtures: _DisputeEngineFixtures.seed(),
    );
  }

  Future<List<DisputeEngineCase>> listMyDisputes() {
    return client.withFallback<List<DisputeEngineCase>>(
      () async {
        final Map<String, dynamic> payload =
            await client.getMap('/disputes/me');
        final List<dynamic> disputes =
            payload['disputes'] as List<dynamic>? ?? <dynamic>[];
        return disputes
            .map(DisputeEngineCase.fromJson)
            .toList(growable: false);
      },
      fixtures.listMyDisputes,
    );
  }

  Future<DisputeEngineDetail> createDispute({
    required String resourceType,
    required String resourceId,
    required String reference,
    required String subject,
    required String message,
  }) {
    return client.withFallback<DisputeEngineDetail>(
      () async {
        final Object? payload = await client.request(
          'POST',
          '/disputes',
          body: <String, Object?>{
            'resource_type': resourceType,
            'resource_id': resourceId,
            'reference': reference,
            'subject': subject,
            'message': message,
            'metadata_json': <String, Object?>{},
          },
        );
        return DisputeEngineDetail.fromJson(payload);
      },
      () async => fixtures.createDispute(reference: reference),
    );
  }

  Future<DisputeEngineDetail> fetchDispute(String disputeId) {
    return client.withFallback<DisputeEngineDetail>(
      () async {
        final Map<String, dynamic> payload =
            await client.getMap('/disputes/$disputeId');
        return DisputeEngineDetail.fromJson(payload);
      },
      () async => fixtures.detail(disputeId),
    );
  }

  Future<DisputeEngineDetail> addMessage({
    required String disputeId,
    required String message,
  }) {
    return client.withFallback<DisputeEngineDetail>(
      () async {
        final Object? payload = await client.request(
          'POST',
          '/disputes/$disputeId/messages',
          body: <String, Object?>{
            'message': message,
          },
        );
        return DisputeEngineDetail.fromJson(payload);
      },
      () async => fixtures.addMessage(disputeId, message),
    );
  }

  Future<List<DisputeEngineCase>> listAdminDisputes() {
    return client.withFallback<List<DisputeEngineCase>>(
      () async {
        final Map<String, dynamic> payload =
            await client.getMap('/admin/disputes');
        final List<dynamic> disputes =
            payload['disputes'] as List<dynamic>? ?? <dynamic>[];
        return disputes
            .map(DisputeEngineCase.fromJson)
            .toList(growable: false);
      },
      fixtures.listAdminDisputes,
    );
  }

  Future<DisputeEngineCase> assignDispute({
    required String disputeId,
    String? adminUserId,
  }) {
    return client.withFallback<DisputeEngineCase>(
      () async {
        final Object? payload = await client.request(
          'POST',
          '/admin/disputes/$disputeId/assign',
          body: <String, Object?>{
            if (adminUserId != null) 'admin_user_id': adminUserId,
          },
        );
        return DisputeEngineCase.fromJson(payload);
      },
      () async => fixtures.assign(disputeId),
    );
  }

  Future<DisputeEngineCase> updateStatus({
    required String disputeId,
    required String status,
    String? note,
  }) {
    return client.withFallback<DisputeEngineCase>(
      () async {
        final Object? payload = await client.request(
          'POST',
          '/admin/disputes/$disputeId/status',
          body: <String, Object?>{
            'status': status,
            if (note != null) 'note': note,
          },
        );
        return DisputeEngineCase.fromJson(payload);
      },
      () async => fixtures.updateStatus(disputeId, status),
    );
  }
}

class _DisputeEngineFixtures {
  _DisputeEngineFixtures(this._cases, this._messages);

  final List<DisputeEngineCase> _cases;
  final Map<String, List<DisputeEngineMessage>> _messages;

  static _DisputeEngineFixtures seed() {
    final List<DisputeEngineCase> cases = <DisputeEngineCase>[
      DisputeEngineCase(
        id: 'case-1',
        userId: 'user-1',
        adminUserId: null,
        resourceType: 'competition',
        resourceId: 'comp-1',
        reference: 'COMP-001',
        status: 'open',
        subject: 'Score dispute',
        metadata: const <String, Object?>{},
        createdAt: DateTime.parse('2026-03-12T12:00:00Z'),
        updatedAt: DateTime.parse('2026-03-12T12:00:00Z'),
        lastMessageAt: DateTime.parse('2026-03-12T12:00:00Z'),
        resolvedAt: null,
        closedAt: null,
      ),
    ];
    final Map<String, List<DisputeEngineMessage>> messages =
        <String, List<DisputeEngineMessage>>{
      'case-1': <DisputeEngineMessage>[
        DisputeEngineMessage(
          id: 'dmsg-1',
          disputeId: 'case-1',
          senderUserId: 'user-1',
          senderRole: 'user',
          message: 'The points awarded do not match the fixture.',
          attachmentId: null,
          createdAt: DateTime.parse('2026-03-12T12:00:00Z'),
        ),
      ],
    };
    return _DisputeEngineFixtures(cases, messages);
  }

  Future<List<DisputeEngineCase>> listMyDisputes() async =>
      List<DisputeEngineCase>.of(_cases, growable: false);

  Future<DisputeEngineDetail> createDispute({required String reference}) async {
    final DisputeEngineCase dispute = DisputeEngineCase(
      id: 'case-${_cases.length + 1}',
      userId: 'user-1',
      adminUserId: null,
      resourceType: 'general',
      resourceId: reference,
      reference: reference,
      status: 'open',
      subject: 'New dispute',
      metadata: const <String, Object?>{},
      createdAt: DateTime.now().toUtc(),
      updatedAt: DateTime.now().toUtc(),
      lastMessageAt: DateTime.now().toUtc(),
      resolvedAt: null,
      closedAt: null,
    );
    _cases.insert(0, dispute);
    return DisputeEngineDetail(dispute: dispute, messages: const <DisputeEngineMessage>[]);
  }

  Future<DisputeEngineDetail> detail(String disputeId) async {
    final DisputeEngineCase dispute =
        _cases.firstWhere((DisputeEngineCase item) => item.id == disputeId);
    return DisputeEngineDetail(
      dispute: dispute,
      messages: List<DisputeEngineMessage>.of(_messages[disputeId] ?? const <DisputeEngineMessage>[], growable: false),
    );
  }

  Future<DisputeEngineDetail> addMessage(String disputeId, String message) async {
    final DisputeEngineMessage msg = DisputeEngineMessage(
      id: 'dmsg-${DateTime.now().millisecondsSinceEpoch}',
      disputeId: disputeId,
      senderUserId: 'user-1',
      senderRole: 'user',
      message: message,
      attachmentId: null,
      createdAt: DateTime.now().toUtc(),
    );
    _messages.putIfAbsent(disputeId, () => <DisputeEngineMessage>[]).add(msg);
    return detail(disputeId);
  }

  Future<List<DisputeEngineCase>> listAdminDisputes() async => listMyDisputes();

  Future<DisputeEngineCase> assign(String disputeId) async {
    final int index =
        _cases.indexWhere((DisputeEngineCase item) => item.id == disputeId);
    if (index == -1) {
      return _cases.first;
    }
    final DisputeEngineCase updated = DisputeEngineCase(
      id: _cases[index].id,
      userId: _cases[index].userId,
      adminUserId: 'admin-1',
      resourceType: _cases[index].resourceType,
      resourceId: _cases[index].resourceId,
      reference: _cases[index].reference,
      status: _cases[index].status,
      subject: _cases[index].subject,
      metadata: _cases[index].metadata,
      createdAt: _cases[index].createdAt,
      updatedAt: DateTime.now().toUtc(),
      lastMessageAt: _cases[index].lastMessageAt,
      resolvedAt: _cases[index].resolvedAt,
      closedAt: _cases[index].closedAt,
    );
    _cases[index] = updated;
    return updated;
  }

  Future<DisputeEngineCase> updateStatus(String disputeId, String status) async {
    final int index =
        _cases.indexWhere((DisputeEngineCase item) => item.id == disputeId);
    if (index == -1) {
      return _cases.first;
    }
    final DisputeEngineCase updated = DisputeEngineCase(
      id: _cases[index].id,
      userId: _cases[index].userId,
      adminUserId: _cases[index].adminUserId,
      resourceType: _cases[index].resourceType,
      resourceId: _cases[index].resourceId,
      reference: _cases[index].reference,
      status: status,
      subject: _cases[index].subject,
      metadata: _cases[index].metadata,
      createdAt: _cases[index].createdAt,
      updatedAt: DateTime.now().toUtc(),
      lastMessageAt: _cases[index].lastMessageAt,
      resolvedAt: status == 'resolved' ? DateTime.now().toUtc() : _cases[index].resolvedAt,
      closedAt: status == 'closed' ? DateTime.now().toUtc() : _cases[index].closedAt,
    );
    _cases[index] = updated;
    return updated;
  }
}
