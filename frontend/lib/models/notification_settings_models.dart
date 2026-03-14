import 'package:gte_frontend/data/gte_models.dart';

class NotificationPreference {
  const NotificationPreference({
    required this.id,
    required this.allowWallet,
    required this.allowMarket,
    required this.allowStory,
    required this.allowCompetition,
    required this.allowSocial,
    required this.allowBroadcasts,
    required this.quietHoursEnabled,
    required this.quietHoursStart,
    required this.quietHoursEnd,
    required this.metadata,
  });

  final String id;
  final bool allowWallet;
  final bool allowMarket;
  final bool allowStory;
  final bool allowCompetition;
  final bool allowSocial;
  final bool allowBroadcasts;
  final bool quietHoursEnabled;
  final String? quietHoursStart;
  final String? quietHoursEnd;
  final Map<String, Object?> metadata;

  factory NotificationPreference.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'notification preference');
    return NotificationPreference(
      id: GteJson.string(json, <String>['id']),
      allowWallet:
          GteJson.boolean(json, <String>['allow_wallet', 'allowWallet'], fallback: true),
      allowMarket:
          GteJson.boolean(json, <String>['allow_market', 'allowMarket'], fallback: true),
      allowStory:
          GteJson.boolean(json, <String>['allow_story', 'allowStory'], fallback: true),
      allowCompetition:
          GteJson.boolean(json, <String>['allow_competition', 'allowCompetition'], fallback: true),
      allowSocial:
          GteJson.boolean(json, <String>['allow_social', 'allowSocial'], fallback: true),
      allowBroadcasts: GteJson.boolean(
          json, <String>['allow_broadcasts', 'allowBroadcasts'],
          fallback: true),
      quietHoursEnabled: GteJson.boolean(
          json, <String>['quiet_hours_enabled', 'quietHoursEnabled'],
          fallback: false),
      quietHoursStart: GteJson.stringOrNull(
          json, <String>['quiet_hours_start', 'quietHoursStart']),
      quietHoursEnd: GteJson.stringOrNull(
          json, <String>['quiet_hours_end', 'quietHoursEnd']),
      metadata: GteJson.map(
          json, <String>['metadata_json', 'metadataJson', 'metadata'],
          fallback: const <String, Object?>{}),
    );
  }

  NotificationPreference copyWith({
    bool? allowWallet,
    bool? allowMarket,
    bool? allowStory,
    bool? allowCompetition,
    bool? allowSocial,
    bool? allowBroadcasts,
    bool? quietHoursEnabled,
    String? quietHoursStart,
    String? quietHoursEnd,
    Map<String, Object?>? metadata,
  }) {
    return NotificationPreference(
      id: id,
      allowWallet: allowWallet ?? this.allowWallet,
      allowMarket: allowMarket ?? this.allowMarket,
      allowStory: allowStory ?? this.allowStory,
      allowCompetition: allowCompetition ?? this.allowCompetition,
      allowSocial: allowSocial ?? this.allowSocial,
      allowBroadcasts: allowBroadcasts ?? this.allowBroadcasts,
      quietHoursEnabled: quietHoursEnabled ?? this.quietHoursEnabled,
      quietHoursStart: quietHoursStart ?? this.quietHoursStart,
      quietHoursEnd: quietHoursEnd ?? this.quietHoursEnd,
      metadata: metadata ?? this.metadata,
    );
  }
}

class NotificationSubscription {
  const NotificationSubscription({
    required this.id,
    required this.subscriptionKey,
    required this.subscriptionType,
    required this.label,
    required this.active,
    required this.metadata,
  });

  final String id;
  final String subscriptionKey;
  final String subscriptionType;
  final String label;
  final bool active;
  final Map<String, Object?> metadata;

  factory NotificationSubscription.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'notification subscription');
    return NotificationSubscription(
      id: GteJson.string(json, <String>['id']),
      subscriptionKey:
          GteJson.string(json, <String>['subscription_key', 'subscriptionKey']),
      subscriptionType: GteJson.string(
          json, <String>['subscription_type', 'subscriptionType'],
          fallback: 'general'),
      label: GteJson.string(json, <String>['label']),
      active: GteJson.boolean(json, <String>['active'], fallback: true),
      metadata: GteJson.map(
          json, <String>['metadata_json', 'metadataJson', 'metadata'],
          fallback: const <String, Object?>{}),
    );
  }
}

class PlatformAnnouncement {
  const PlatformAnnouncement({
    required this.id,
    required this.announcementKey,
    required this.title,
    required this.body,
    required this.audience,
    required this.severity,
    required this.active,
    required this.deliverAsNotification,
    required this.metadata,
  });

  final String id;
  final String announcementKey;
  final String title;
  final String body;
  final String audience;
  final String severity;
  final bool active;
  final bool deliverAsNotification;
  final Map<String, Object?> metadata;

  factory PlatformAnnouncement.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'announcement');
    return PlatformAnnouncement(
      id: GteJson.string(json, <String>['id']),
      announcementKey: GteJson.string(
          json, <String>['announcement_key', 'announcementKey']),
      title: GteJson.string(json, <String>['title']),
      body: GteJson.string(json, <String>['body']),
      audience: GteJson.string(json, <String>['audience'], fallback: 'all'),
      severity: GteJson.string(json, <String>['severity'], fallback: 'info'),
      active: GteJson.boolean(json, <String>['active'], fallback: true),
      deliverAsNotification: GteJson.boolean(
          json, <String>['deliver_as_notification', 'deliverAsNotification'],
          fallback: true),
      metadata: GteJson.map(
          json, <String>['metadata_json', 'metadataJson', 'metadata'],
          fallback: const <String, Object?>{}),
    );
  }
}
