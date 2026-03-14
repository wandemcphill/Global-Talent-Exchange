import 'package:gte_frontend/data/gte_models.dart';

class ModerationReport {
  const ModerationReport({
    required this.id,
    required this.reporterUserId,
    required this.subjectUserId,
    required this.targetType,
    required this.targetId,
    required this.reasonCode,
    required this.description,
    required this.evidenceUrl,
    required this.status,
    required this.priority,
    required this.assignedAdminUserId,
    required this.resolutionAction,
    required this.resolutionNote,
    required this.resolvedByUserId,
    required this.reportCountForTarget,
    required this.createdAt,
    required this.updatedAt,
  });

  final String id;
  final String reporterUserId;
  final String? subjectUserId;
  final String targetType;
  final String targetId;
  final String reasonCode;
  final String description;
  final String? evidenceUrl;
  final String status;
  final String priority;
  final String? assignedAdminUserId;
  final String resolutionAction;
  final String? resolutionNote;
  final String? resolvedByUserId;
  final int reportCountForTarget;
  final DateTime createdAt;
  final DateTime updatedAt;

  factory ModerationReport.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'moderation report');
    return ModerationReport(
      id: GteJson.string(json, <String>['id']),
      reporterUserId:
          GteJson.string(json, <String>['reporter_user_id', 'reporterUserId']),
      subjectUserId:
          GteJson.stringOrNull(json, <String>['subject_user_id', 'subjectUserId']),
      targetType:
          GteJson.string(json, <String>['target_type', 'targetType']),
      targetId: GteJson.string(json, <String>['target_id', 'targetId']),
      reasonCode:
          GteJson.string(json, <String>['reason_code', 'reasonCode']),
      description: GteJson.string(json, <String>['description']),
      evidenceUrl:
          GteJson.stringOrNull(json, <String>['evidence_url', 'evidenceUrl']),
      status: GteJson.string(json, <String>['status'], fallback: 'open'),
      priority: GteJson.string(json, <String>['priority'], fallback: 'medium'),
      assignedAdminUserId: GteJson.stringOrNull(
          json, <String>['assigned_admin_user_id', 'assignedAdminUserId']),
      resolutionAction: GteJson.string(
          json, <String>['resolution_action', 'resolutionAction'],
          fallback: 'none'),
      resolutionNote:
          GteJson.stringOrNull(json, <String>['resolution_note', 'resolutionNote']),
      resolvedByUserId: GteJson.stringOrNull(
          json, <String>['resolved_by_user_id', 'resolvedByUserId']),
      reportCountForTarget: GteJson.integer(
          json, <String>['report_count_for_target', 'reportCountForTarget'],
          fallback: 0),
      createdAt: GteJson.dateTime(json, <String>['created_at', 'createdAt']),
      updatedAt: GteJson.dateTime(json, <String>['updated_at', 'updatedAt']),
    );
  }
}

class ModerationSummary {
  const ModerationSummary({
    required this.openCount,
    required this.inReviewCount,
    required this.actionedCount,
    required this.dismissedCount,
    required this.criticalCount,
    required this.highPriorityCount,
    required this.recentReports,
  });

  final int openCount;
  final int inReviewCount;
  final int actionedCount;
  final int dismissedCount;
  final int criticalCount;
  final int highPriorityCount;
  final List<ModerationReport> recentReports;

  factory ModerationSummary.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'moderation summary');
    return ModerationSummary(
      openCount:
          GteJson.integer(json, <String>['open_count', 'openCount'], fallback: 0),
      inReviewCount: GteJson.integer(
          json, <String>['in_review_count', 'inReviewCount'],
          fallback: 0),
      actionedCount: GteJson.integer(
          json, <String>['actioned_count', 'actionedCount'],
          fallback: 0),
      dismissedCount: GteJson.integer(
          json, <String>['dismissed_count', 'dismissedCount'],
          fallback: 0),
      criticalCount: GteJson.integer(
          json, <String>['critical_count', 'criticalCount'],
          fallback: 0),
      highPriorityCount: GteJson.integer(
          json, <String>['high_priority_count', 'highPriorityCount'],
          fallback: 0),
      recentReports: GteJson.typedList(
        json,
        <String>['recent_reports', 'recentReports'],
        ModerationReport.fromJson,
      ),
    );
  }
}
