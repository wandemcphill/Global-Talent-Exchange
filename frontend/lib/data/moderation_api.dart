import 'gte_api_repository.dart';
import 'gte_authed_api.dart';
import 'gte_http_transport.dart';
import '../models/moderation_models.dart';

class ModerationApi {
  ModerationApi({
    required this.client,
    required this.fixtures,
  });

  final GteAuthedApi client;
  final _ModerationFixtures fixtures;

  factory ModerationApi.standard({
    required String baseUrl,
    required String? accessToken,
    GteBackendMode mode = GteBackendMode.liveThenFixture,
  }) {
    return ModerationApi(
      client: GteAuthedApi(
        config: GteRepositoryConfig(baseUrl: baseUrl, mode: mode),
        transport: GteHttpTransport(),
        accessToken: accessToken,
        mode: mode,
      ),
      fixtures: _ModerationFixtures.seed(),
    );
  }

  factory ModerationApi.fixture() {
    return ModerationApi(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.fixture,
        ),
        transport: GteHttpTransport(),
        accessToken: 'fixture-token',
        mode: GteBackendMode.fixture,
      ),
      fixtures: _ModerationFixtures.seed(),
    );
  }

  Future<ModerationReport> createReport({
    required String targetType,
    required String targetId,
    String? subjectUserId,
    required String reasonCode,
    required String description,
    String? evidenceUrl,
  }) {
    return client.withFallback<ModerationReport>(
      () async {
        final Object? payload = await client.request(
          'POST',
          '/moderation/reports',
          body: <String, Object?>{
            'target_type': targetType,
            'target_id': targetId,
            if (subjectUserId != null) 'subject_user_id': subjectUserId,
            'reason_code': reasonCode,
            'description': description,
            if (evidenceUrl != null) 'evidence_url': evidenceUrl,
          },
        );
        return ModerationReport.fromJson(payload);
      },
      () async => fixtures.createReport(targetId: targetId, description: description),
    );
  }

  Future<List<ModerationReport>> listMyReports() {
    return client.withFallback<List<ModerationReport>>(
      () async {
        final List<dynamic> payload =
            await client.getList('/moderation/me/reports');
        return payload.map(ModerationReport.fromJson).toList(growable: false);
      },
      fixtures.listReports,
    );
  }

  Future<List<ModerationReport>> listReports({
    String? status,
    String? priority,
    String? targetType,
  }) {
    return client.withFallback<List<ModerationReport>>(
      () async {
        final List<dynamic> payload = await client.getList(
          '/admin/moderation/reports',
          query: <String, Object?>{
            if (status != null && status.isNotEmpty) 'status': status,
            if (priority != null && priority.isNotEmpty) 'priority': priority,
            if (targetType != null && targetType.isNotEmpty)
              'target_type': targetType,
          },
        );
        return payload.map(ModerationReport.fromJson).toList(growable: false);
      },
      fixtures.listReports,
    );
  }

  Future<ModerationSummary> fetchSummary() {
    return client.withFallback<ModerationSummary>(
      () async {
        final Map<String, dynamic> payload =
            await client.getMap('/admin/moderation/reports/summary');
        return ModerationSummary.fromJson(payload);
      },
      fixtures.summary,
    );
  }

  Future<ModerationReport> assignReport({
    required String reportId,
    String? adminUserId,
    String? priority,
  }) {
    return client.withFallback<ModerationReport>(
      () async {
        final Object? payload = await client.request(
          'POST',
          '/admin/moderation/reports/$reportId/assign',
          body: <String, Object?>{
            if (adminUserId != null) 'admin_user_id': adminUserId,
            if (priority != null) 'priority': priority,
          },
        );
        return ModerationReport.fromJson(payload);
      },
      () async => fixtures.assignReport(reportId, priority),
    );
  }

  Future<ModerationReport> resolveReport({
    required String reportId,
    required String resolutionAction,
    required String resolutionNote,
    bool dismiss = false,
  }) {
    return client.withFallback<ModerationReport>(
      () async {
        final Object? payload = await client.request(
          'POST',
          '/admin/moderation/reports/$reportId/resolve',
          body: <String, Object?>{
            'resolution_action': resolutionAction,
            'resolution_note': resolutionNote,
            'dismiss': dismiss,
          },
        );
        return ModerationReport.fromJson(payload);
      },
      () async => fixtures.resolveReport(reportId, resolutionAction),
    );
  }
}

class _ModerationFixtures {
  _ModerationFixtures(this._reports);

  final List<ModerationReport> _reports;

  static _ModerationFixtures seed() {
    return _ModerationFixtures(<ModerationReport>[
      ModerationReport(
        id: 'mod-1',
        reporterUserId: 'user-1',
        subjectUserId: 'user-2',
        targetType: 'message',
        targetId: 'msg-1',
        reasonCode: 'abuse',
        description: 'Harassment in live thread.',
        evidenceUrl: null,
        status: 'open',
        priority: 'high',
        assignedAdminUserId: null,
        resolutionAction: 'none',
        resolutionNote: null,
        resolvedByUserId: null,
        reportCountForTarget: 1,
        createdAt: DateTime.parse('2026-03-13T12:00:00Z'),
        updatedAt: DateTime.parse('2026-03-13T12:00:00Z'),
      ),
    ]);
  }

  Future<List<ModerationReport>> listReports() async =>
      List<ModerationReport>.of(_reports, growable: false);

  Future<ModerationReport> createReport({
    required String targetId,
    required String description,
  }) async {
    final ModerationReport report = ModerationReport(
      id: 'mod-${_reports.length + 1}',
      reporterUserId: 'user-1',
      subjectUserId: null,
      targetType: 'content',
      targetId: targetId,
      reasonCode: 'other',
      description: description,
      evidenceUrl: null,
      status: 'open',
      priority: 'medium',
      assignedAdminUserId: null,
      resolutionAction: 'none',
      resolutionNote: null,
      resolvedByUserId: null,
      reportCountForTarget: 1,
      createdAt: DateTime.now().toUtc(),
      updatedAt: DateTime.now().toUtc(),
    );
    _reports.insert(0, report);
    return report;
  }

  Future<ModerationSummary> summary() async {
    return ModerationSummary(
      openCount: _reports.length,
      inReviewCount: 0,
      actionedCount: 0,
      dismissedCount: 0,
      criticalCount: 0,
      highPriorityCount: 1,
      recentReports: _reports,
    );
  }

  Future<ModerationReport> assignReport(String reportId, String? priority) async {
    final int index =
        _reports.indexWhere((ModerationReport item) => item.id == reportId);
    if (index == -1) {
      return _reports.first;
    }
    final ModerationReport updated = ModerationReport(
      id: _reports[index].id,
      reporterUserId: _reports[index].reporterUserId,
      subjectUserId: _reports[index].subjectUserId,
      targetType: _reports[index].targetType,
      targetId: _reports[index].targetId,
      reasonCode: _reports[index].reasonCode,
      description: _reports[index].description,
      evidenceUrl: _reports[index].evidenceUrl,
      status: _reports[index].status,
      priority: priority ?? _reports[index].priority,
      assignedAdminUserId: 'admin-1',
      resolutionAction: _reports[index].resolutionAction,
      resolutionNote: _reports[index].resolutionNote,
      resolvedByUserId: _reports[index].resolvedByUserId,
      reportCountForTarget: _reports[index].reportCountForTarget,
      createdAt: _reports[index].createdAt,
      updatedAt: DateTime.now().toUtc(),
    );
    _reports[index] = updated;
    return updated;
  }

  Future<ModerationReport> resolveReport(String reportId, String action) async {
    final int index =
        _reports.indexWhere((ModerationReport item) => item.id == reportId);
    if (index == -1) {
      return _reports.first;
    }
    final ModerationReport updated = ModerationReport(
      id: _reports[index].id,
      reporterUserId: _reports[index].reporterUserId,
      subjectUserId: _reports[index].subjectUserId,
      targetType: _reports[index].targetType,
      targetId: _reports[index].targetId,
      reasonCode: _reports[index].reasonCode,
      description: _reports[index].description,
      evidenceUrl: _reports[index].evidenceUrl,
      status: 'resolved',
      priority: _reports[index].priority,
      assignedAdminUserId: _reports[index].assignedAdminUserId,
      resolutionAction: action,
      resolutionNote: 'Resolved via fixture.',
      resolvedByUserId: 'admin-1',
      reportCountForTarget: _reports[index].reportCountForTarget,
      createdAt: _reports[index].createdAt,
      updatedAt: DateTime.now().toUtc(),
    );
    _reports[index] = updated;
    return updated;
  }
}
