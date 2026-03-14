import 'gte_api_repository.dart';
import 'gte_authed_api.dart';
import 'gte_http_transport.dart';
import '../models/notification_settings_models.dart';

class NotificationSettingsApi {
  NotificationSettingsApi({
    required this.client,
    required this.fixtures,
  });

  final GteAuthedApi client;
  final _NotificationFixtures fixtures;

  factory NotificationSettingsApi.standard({
    required String baseUrl,
    required String? accessToken,
    GteBackendMode mode = GteBackendMode.liveThenFixture,
  }) {
    return NotificationSettingsApi(
      client: GteAuthedApi(
        config: GteRepositoryConfig(baseUrl: baseUrl, mode: mode),
        transport: GteHttpTransport(),
        accessToken: accessToken,
        mode: mode,
      ),
      fixtures: _NotificationFixtures.seed(),
    );
  }

  factory NotificationSettingsApi.fixture() {
    return NotificationSettingsApi(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.fixture,
        ),
        transport: GteHttpTransport(),
        accessToken: 'fixture-token',
        mode: GteBackendMode.fixture,
      ),
      fixtures: _NotificationFixtures.seed(),
    );
  }

  Future<NotificationPreference> fetchPreferences() {
    return client.withFallback<NotificationPreference>(
      () async {
        final Map<String, dynamic> payload =
            await client.getMap('/notifications/preferences');
        return NotificationPreference.fromJson(payload);
      },
      fixtures.preferences,
    );
  }

  Future<NotificationPreference> updatePreferences(
    NotificationPreference preference,
  ) {
    return client.withFallback<NotificationPreference>(
      () async {
        final Object? payload = await client.request(
          'PUT',
          '/notifications/preferences',
          body: <String, Object?>{
            'allow_wallet': preference.allowWallet,
            'allow_market': preference.allowMarket,
            'allow_story': preference.allowStory,
            'allow_competition': preference.allowCompetition,
            'allow_social': preference.allowSocial,
            'allow_broadcasts': preference.allowBroadcasts,
            'quiet_hours_enabled': preference.quietHoursEnabled,
            'quiet_hours_start': preference.quietHoursStart,
            'quiet_hours_end': preference.quietHoursEnd,
            'metadata_json': preference.metadata,
          },
        );
        return NotificationPreference.fromJson(payload);
      },
      () async {
        fixtures._preference = preference;
        return preference;
      },
    );
  }

  Future<List<NotificationSubscription>> listSubscriptions() {
    return client.withFallback<List<NotificationSubscription>>(
      () async {
        final List<dynamic> payload =
            await client.getList('/notifications/subscriptions');
        return payload
            .map(NotificationSubscription.fromJson)
            .toList(growable: false);
      },
      fixtures.subscriptions,
    );
  }

  Future<NotificationSubscription> upsertSubscription({
    required String subscriptionKey,
    required String label,
    String subscriptionType = 'general',
    bool active = true,
  }) {
    return client.withFallback<NotificationSubscription>(
      () async {
        final Object? payload = await client.request(
          'POST',
          '/notifications/subscriptions',
          body: <String, Object?>{
            'subscription_key': subscriptionKey,
            'label': label,
            'subscription_type': subscriptionType,
            'active': active,
            'metadata_json': <String, Object?>{},
          },
        );
        return NotificationSubscription.fromJson(payload);
      },
      () async => fixtures.addSubscription(
        subscriptionKey: subscriptionKey,
        label: label,
      ),
    );
  }

  Future<void> deleteSubscription(String subscriptionId) {
    return client.withFallback<void>(
      () async {
        await client.request(
          'DELETE',
          '/notifications/subscriptions/$subscriptionId',
        );
      },
      () async => fixtures.removeSubscription(subscriptionId),
    );
  }

  Future<List<PlatformAnnouncement>> listAnnouncements() {
    return client.withFallback<List<PlatformAnnouncement>>(
      () async {
        final List<dynamic> payload =
            await client.getList('/notifications/announcements', auth: false);
        return payload
            .map(PlatformAnnouncement.fromJson)
            .toList(growable: false);
      },
      fixtures.announcements,
    );
  }

  Future<List<PlatformAnnouncement>> adminListAnnouncements() {
    return client.withFallback<List<PlatformAnnouncement>>(
      () async {
        final List<dynamic> payload =
            await client.getList('/admin/notifications/announcements');
        return payload
            .map(PlatformAnnouncement.fromJson)
            .toList(growable: false);
      },
      fixtures.announcements,
    );
  }

  Future<PlatformAnnouncement> publishAnnouncement({
    required String announcementKey,
    required String title,
    required String body,
    String audience = 'all',
    String severity = 'info',
    bool active = true,
    bool deliverAsNotification = true,
  }) {
    return client.withFallback<PlatformAnnouncement>(
      () async {
        final Object? payload = await client.request(
          'POST',
          '/admin/notifications/announcements',
          body: <String, Object?>{
            'announcement_key': announcementKey,
            'title': title,
            'body': body,
            'audience': audience,
            'severity': severity,
            'active': active,
            'deliver_as_notification': deliverAsNotification,
            'metadata_json': <String, Object?>{},
          },
        );
        return PlatformAnnouncement.fromJson(payload);
      },
      () async => fixtures.publishAnnouncement(
        key: announcementKey,
        title: title,
        body: body,
      ),
    );
  }
}

class _NotificationFixtures {
  _NotificationFixtures(this._preference, this._subscriptions, this._announcements);

  NotificationPreference _preference;
  final List<NotificationSubscription> _subscriptions;
  final List<PlatformAnnouncement> _announcements;

  static _NotificationFixtures seed() {
    return _NotificationFixtures(
      NotificationPreference(
        id: 'pref-1',
        allowWallet: true,
        allowMarket: true,
        allowStory: true,
        allowCompetition: true,
        allowSocial: true,
        allowBroadcasts: true,
        quietHoursEnabled: false,
        quietHoursStart: null,
        quietHoursEnd: null,
        metadata: const <String, Object?>{},
      ),
      <NotificationSubscription>[
        NotificationSubscription(
          id: 'sub-1',
          subscriptionKey: 'market-open',
          subscriptionType: 'market',
          label: 'Market open alerts',
          active: true,
          metadata: const <String, Object?>{},
        ),
      ],
      <PlatformAnnouncement>[
        PlatformAnnouncement(
          id: 'ann-1',
          announcementKey: 'market-reset',
          title: 'Announcement: Jude benchmark pricing reset',
          body: 'Benchmark pricing has been recalibrated for the latest market window.',
          audience: 'all',
          severity: 'info',
          active: true,
          deliverAsNotification: true,
          metadata: const <String, Object?>{},
        ),
      ],
    );
  }

  Future<NotificationPreference> preferences() async => _preference;

  Future<List<NotificationSubscription>> subscriptions() async =>
      List<NotificationSubscription>.of(_subscriptions, growable: false);

  Future<NotificationSubscription> addSubscription({
    required String subscriptionKey,
    required String label,
  }) async {
    final NotificationSubscription created = NotificationSubscription(
      id: 'sub-${_subscriptions.length + 1}',
      subscriptionKey: subscriptionKey,
      subscriptionType: 'general',
      label: label,
      active: true,
      metadata: const <String, Object?>{},
    );
    _subscriptions.insert(0, created);
    return created;
  }

  Future<void> removeSubscription(String subscriptionId) async {
    _subscriptions
        .removeWhere((NotificationSubscription item) => item.id == subscriptionId);
  }

  Future<List<PlatformAnnouncement>> announcements() async =>
      List<PlatformAnnouncement>.of(_announcements, growable: false);

  Future<PlatformAnnouncement> publishAnnouncement({
    required String key,
    required String title,
    required String body,
  }) async {
    final PlatformAnnouncement created = PlatformAnnouncement(
      id: 'ann-${_announcements.length + 1}',
      announcementKey: key,
      title: title,
      body: body,
      audience: 'all',
      severity: 'info',
      active: true,
      deliverAsNotification: true,
      metadata: const <String, Object?>{},
    );
    _announcements.insert(0, created);
    return created;
  }
}
