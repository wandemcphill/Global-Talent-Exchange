import 'package:flutter/foundation.dart';

int _inboxInt(Object? value) =>
    value is num ? value.toInt() : int.tryParse('${value ?? ''}') ?? 0;

String? _inboxText(Object? value) {
  final String text = '${value ?? ''}'.trim();
  return text.isEmpty || text == 'null' ? null : text;
}

Map<String, dynamic> _inboxMap(Object? value) =>
    value is Map ? Map<String, dynamic>.from(value) : <String, dynamic>{};

List<Map<String, dynamic>> _inboxMaps(Object? value) =>
    (value is List ? value : const <dynamic>[])
        .whereType<Map<dynamic, dynamic>>()
        .map((Map<dynamic, dynamic> map) => Map<String, dynamic>.from(map))
        .toList(growable: false);

@immutable
class OwnerDecisionAction {
  const OwnerDecisionAction({
    required this.key,
    required this.label,
    this.style = 'ghost',
  });

  factory OwnerDecisionAction.fromJson(Map<String, dynamic> json) =>
      OwnerDecisionAction(
        key: '${json['key']}',
        label: _inboxText(json['label']) ?? '${json['key']}',
        style: _inboxText(json['style']) ?? 'ghost',
      );

  final String key;
  final String label;
  final String style;

  bool get isPrimary => style == 'primary';
}

@immutable
class OwnerInboxEntry {
  const OwnerInboxEntry({
    required this.id,
    required this.kind,
    required this.title,
    required this.isDecision,
    this.clubId,
    this.saveContextId,
    this.category = 'requests',
    this.priority,
    this.why,
    this.what,
    this.body,
    this.sender,
    this.status,
    this.resolution,
    this.outcome,
    this.respondBy,
    this.deadlineAt,
    this.isRead = false,
    this.readAt,
    this.archivedAt,
    this.createdAt,
    this.payload = const <String, dynamic>{},
    this.actions = const <OwnerDecisionAction>[],
  });

  factory OwnerInboxEntry.fromJson(Map<String, dynamic> json) {
    final DateTime? parsedRespondBy = DateTime.tryParse(
      _inboxText(json['respond_by']) ?? '',
    );
    final DateTime? parsedDeadlineAt =
        DateTime.tryParse(_inboxText(json['deadline_at']) ?? '') ??
        parsedRespondBy;
    return OwnerInboxEntry(
      id: '${json['id']}',
      kind: _inboxText(json['kind']) ?? 'update',
      title:
          _inboxText(json['title']) ?? _inboxText(json['what']) ?? 'Update',
      isDecision: json['is_decision'] == true,
      clubId: _inboxText(json['club_id']),
      saveContextId: _inboxText(json['save_context_id']),
      category: _inboxText(json['category']) ?? 'requests',
      priority: _inboxText(json['priority']),
      why: _inboxText(json['why']) ?? _inboxText(json['body']),
      what: _inboxText(json['what']),
      body: _inboxText(json['body']),
      sender: _inboxText(json['sender']),
      status: _inboxText(json['status']),
      resolution: _inboxText(json['resolution']),
      outcome: _inboxText(json['outcome']),
      respondBy: parsedRespondBy,
      deadlineAt: parsedDeadlineAt,
      isRead: json['is_read'] == true || _inboxText(json['read_at']) != null,
      readAt: DateTime.tryParse(_inboxText(json['read_at']) ?? ''),
      archivedAt: DateTime.tryParse(_inboxText(json['archived_at']) ?? ''),
      createdAt: DateTime.tryParse(_inboxText(json['created_at']) ?? ''),
      payload: _inboxMap(json['payload']),
      actions:
          _inboxMaps(json['actions'])
              .map(OwnerDecisionAction.fromJson)
              .toList(growable: false),
    );
  }

  final String id;
  final String kind;
  final String title;
  final bool isDecision;
  final String? clubId;
  final String? saveContextId;
  final String category;
  final String? priority;
  final String? why;
  final String? what;
  final String? body;
  final String? sender;
  final String? status;
  final String? resolution;
  final String? outcome;
  final DateTime? respondBy;
  final DateTime? deadlineAt;
  final bool isRead;
  final DateTime? readAt;
  final DateTime? archivedAt;
  final DateTime? createdAt;
  final Map<String, dynamic> payload;
  final List<OwnerDecisionAction> actions;

  bool get isArchived =>
      archivedAt != null ||
      (status ?? '').trim().toLowerCase() == 'archived';

  bool get isResolved =>
      (status ?? '').trim().toLowerCase() == 'resolved' ||
      (resolution != null && resolution!.trim().isNotEmpty);

  bool get isOpen =>
      !isArchived &&
      !isResolved &&
      ((status ?? '').trim().isEmpty ||
          (status ?? '').trim().toLowerCase() == 'open');

  OwnerInboxEntry copyWith({
    String? id,
    String? kind,
    String? title,
    bool? isDecision,
    String? clubId,
    String? saveContextId,
    String? category,
    String? priority,
    String? why,
    String? what,
    String? body,
    String? sender,
    String? status,
    String? resolution,
    String? outcome,
    DateTime? respondBy,
    DateTime? deadlineAt,
    bool? isRead,
    DateTime? readAt,
    DateTime? archivedAt,
    DateTime? createdAt,
    Map<String, dynamic>? payload,
    List<OwnerDecisionAction>? actions,
  }) {
    return OwnerInboxEntry(
      id: id ?? this.id,
      kind: kind ?? this.kind,
      title: title ?? this.title,
      isDecision: isDecision ?? this.isDecision,
      clubId: clubId ?? this.clubId,
      saveContextId: saveContextId ?? this.saveContextId,
      category: category ?? this.category,
      priority: priority ?? this.priority,
      why: why ?? this.why,
      what: what ?? this.what,
      body: body ?? this.body,
      sender: sender ?? this.sender,
      status: status ?? this.status,
      resolution: resolution ?? this.resolution,
      outcome: outcome ?? this.outcome,
      respondBy: respondBy ?? this.respondBy,
      deadlineAt: deadlineAt ?? this.deadlineAt,
      isRead: isRead ?? this.isRead,
      readAt: readAt ?? this.readAt,
      archivedAt: archivedAt ?? this.archivedAt,
      createdAt: createdAt ?? this.createdAt,
      payload: payload ?? this.payload,
      actions: actions ?? this.actions,
    );
  }
}

@immutable
class GtexOwnerInboxCounts {
  const GtexOwnerInboxCounts({
    this.all = 0,
    this.requests = 0,
    this.deadlines = 0,
    this.staffRecommendations = 0,
    this.playerIssues = 0,
    this.scoutingReports = 0,
    this.negotiations = 0,
    this.scheduling = 0,
    this.archive = 0,
    this.unread = 0,
    this.open = 0,
    this.raw = const <String, int>{},
  });

  factory GtexOwnerInboxCounts.fromJson(Map<String, dynamic> json) {
    final Map<String, int> mapped = <String, int>{
      for (final MapEntry<String, dynamic> entry in json.entries)
        entry.key: _inboxInt(entry.value),
    };
    return GtexOwnerInboxCounts(
      all: _inboxInt(json['all']),
      requests: _inboxInt(json['requests']),
      deadlines: _inboxInt(json['deadlines']),
      staffRecommendations: _inboxInt(json['staff_recommendations']),
      playerIssues: _inboxInt(json['player_issues']),
      scoutingReports: _inboxInt(json['scouting_reports']),
      negotiations: _inboxInt(json['negotiations']),
      scheduling: _inboxInt(json['scheduling']),
      archive: _inboxInt(json['archive']),
      unread: _inboxInt(json['unread']),
      open: _inboxInt(json['open']),
      raw: mapped,
    );
  }

  final int all;
  final int requests;
  final int deadlines;
  final int staffRecommendations;
  final int playerIssues;
  final int scoutingReports;
  final int negotiations;
  final int scheduling;
  final int archive;
  final int unread;
  final int open;
  final Map<String, int> raw;

  int countForCategory(String category) {
    return switch (category) {
      'all' => all,
      'requests' => requests,
      'deadlines' => deadlines,
      'staff_recommendations' => staffRecommendations,
      'player_issues' => playerIssues,
      'scouting_reports' => scoutingReports,
      'negotiations' => negotiations,
      'scheduling' => scheduling,
      'archive' => archive,
      _ => raw[category] ?? 0,
    };
  }
}

typedef OwnerInboxCounts = GtexOwnerInboxCounts;

@immutable
class GtexOwnerInboxFeed {
  const GtexOwnerInboxFeed({
    required this.items,
    required this.counts,
  });

  factory GtexOwnerInboxFeed.fromJson(Map<String, dynamic> json) {
    return GtexOwnerInboxFeed(
      items:
          _inboxMaps(json['items'])
              .map(OwnerInboxEntry.fromJson)
              .toList(growable: false),
      counts: GtexOwnerInboxCounts.fromJson(_inboxMap(json['counts'])),
    );
  }

  final List<OwnerInboxEntry> items;
  final GtexOwnerInboxCounts counts;
}

typedef OwnerInboxFeed = GtexOwnerInboxFeed;

abstract class GtexOwnerInboxDataSource {
  Future<GtexOwnerInboxFeed> fetchInbox({
    String? status,
    String? category,
    String? clubId,
    String? saveContextId,
    bool unreadOnly = false,
  });

  Future<OwnerInboxEntry> markInboxItemRead(String itemId);

  Future<OwnerInboxEntry> archiveInboxItem(String itemId);

  Future<OwnerInboxEntry> decideInboxItem(
    String itemId, {
    required String action,
    String? idempotencyKey,
  });
}
