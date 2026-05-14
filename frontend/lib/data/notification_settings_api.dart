import 'gte_api_repository.dart';
import 'gte_authed_api.dart';
import 'gte_http_transport.dart';
import '../models/notification_settings_models.dart';

class NotificationSettingsApi {
  NotificationSettingsApi({required this.client, required this.fixtures});

  final GteAuthedApi client;
  final _NotificationFixtures fixtures;

  factory NotificationSettingsApi.standard({
    required String baseUrl,
    required String? accessToken,
    GteBackendMode mode = GteBackendMode.live,
    GteTransport? transport,
  }) {
    final GteBackendMode resolvedMode = gteProductionBackendMode(mode);
    return NotificationSettingsApi(
      client: GteAuthedApi(
        config: GteRepositoryConfig(baseUrl: baseUrl, mode: resolvedMode),
        transport: transport ?? GteHttpTransport(),
        accessToken: accessToken,
        mode: resolvedMode,
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
    return client.withFallback<NotificationPreference>(() async {
      final Map<String, dynamic> payload = await client.getMap(
        '/api/notifications/preferences',
      );
      return NotificationPreference.fromJson(payload);
    }, fixtures.preferences);
  }

  Future<NotificationPreference> updatePreferences(
    NotificationPreference preference,
  ) {
    return client.withFallback<NotificationPreference>(
      () async {
        final Object? payload = await client.request(
          'PUT',
          '/api/notifications/preferences',
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
    return client.withFallback<List<NotificationSubscription>>(() async {
      final List<dynamic> payload = await client.getList(
        '/api/notifications/subscriptions',
      );
      return payload
          .map(NotificationSubscription.fromJson)
          .toList(growable: false);
    }, fixtures.subscriptions);
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
          '/api/notifications/subscriptions',
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
      () async => fixtures.upsertSubscription(
        subscriptionKey: subscriptionKey,
        label: label,
        subscriptionType: subscriptionType,
        active: active,
      ),
    );
  }

  Future<void> deleteSubscription(String subscriptionId) {
    return client.withFallback<void>(() async {
      await client.request(
        'DELETE',
        '/api/notifications/subscriptions/$subscriptionId',
      );
    }, () async => fixtures.removeSubscription(subscriptionId));
  }

  Future<List<PlatformAnnouncement>> listAnnouncements() {
    return client.withFallback<List<PlatformAnnouncement>>(() async {
      final List<dynamic> payload = await client.getList(
        '/api/notifications/announcements',
        auth: false,
      );
      return payload.map(PlatformAnnouncement.fromJson).toList(growable: false);
    }, fixtures.announcements);
  }

  Future<List<PlatformAnnouncement>> adminListAnnouncements() {
    return client.withFallback<List<PlatformAnnouncement>>(() async {
      final List<dynamic> payload = await client.getList(
        '/api/admin/notifications/announcements',
      );
      return payload.map(PlatformAnnouncement.fromJson).toList(growable: false);
    }, fixtures.announcements);
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
          '/api/admin/notifications/announcements',
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

  Future<List<NotificationEventMatrixItem>> adminListEventMatrix() {
    return client.withFallback<List<NotificationEventMatrixItem>>(() async {
      final List<dynamic> payload = await client.getList(
        '/api/admin/notifications/event-matrix',
      );
      return payload
          .map(NotificationEventMatrixItem.fromJson)
          .toList(growable: false);
    }, fixtures.eventMatrix);
  }

  Future<NotificationTestEventResult> adminPublishTestEvent({
    required String eventKey,
    required String targetUserId,
    String? resourceId,
    String? message,
  }) {
    return client.withFallback<NotificationTestEventResult>(
      () async {
        final Object? payload = await client.post(
          '/api/admin/notifications/test-event',
          body: <String, Object?>{
            'event_key': eventKey.trim(),
            'target_user_id': targetUserId.trim(),
            if (resourceId != null && resourceId.trim().isNotEmpty)
              'resource_id': resourceId.trim(),
            if (message != null && message.trim().isNotEmpty)
              'message': message.trim(),
            'metadata_json': const <String, Object?>{},
          },
        );
        return NotificationTestEventResult.fromJson(payload);
      },
      () async => fixtures.publishTestEvent(
        eventKey: eventKey,
        targetUserId: targetUserId,
        resourceId: resourceId,
        message: message,
      ),
    );
  }
}

class _NotificationFixtures {
  _NotificationFixtures(
    this._preference,
    this._subscriptions,
    this._announcements,
    this._eventMatrix,
  );

  NotificationPreference _preference;
  final List<NotificationSubscription> _subscriptions;
  final List<PlatformAnnouncement> _announcements;
  final List<NotificationEventMatrixItem> _eventMatrix;

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
          body:
              'Benchmark pricing has been recalibrated for the latest market window.',
          audience: 'all',
          severity: 'info',
          active: true,
          deliverAsNotification: true,
          publishedAt: DateTime.parse('2026-01-15T09:30:00Z'),
          metadata: const <String, Object?>{},
        ),
      ],
      const <NotificationEventMatrixItem>[
        NotificationEventMatrixItem(
          eventKey: 'transfer_offer_received',
          topic: 'market',
          templateKey: 'transfer.offer.received',
          title: 'Transfer offer received',
          defaultMessage: 'A club has sent you a transfer offer.',
          audience: 'club_owner',
          deepLinkRoute: '/football/transfer-center',
          preferenceKey: 'allow_market',
          metadata: <String, Object?>{'source': 'fixture'},
        ),
        NotificationEventMatrixItem(
          eventKey: 'coin_trader_order_accepted',
          topic: 'wallet',
          templateKey: 'coin_trader.order.accepted',
          title: 'Coin trader order accepted',
          defaultMessage: 'A coin trader accepted your order.',
          audience: 'user',
          deepLinkRoute: '/app/coin-traders',
          preferenceKey: 'allow_wallet',
          metadata: <String, Object?>{'source': 'fixture'},
        ),
        NotificationEventMatrixItem(
          eventKey: 'academy_regen_generated',
          topic: 'club',
          templateKey: 'academy.regen.generated',
          title: 'Academy regen generated',
          defaultMessage: 'Your academy has discovered a new prospect.',
          audience: 'club_owner',
          deepLinkRoute: '/club/academy',
          preferenceKey: 'allow_competition',
          metadata: <String, Object?>{'source': 'fixture'},
        ),
        NotificationEventMatrixItem(
          eventKey: 'sponsorship_paid',
          topic: 'wallet',
          templateKey: 'sponsorship.paid',
          title: 'Sponsorship paid',
          defaultMessage: 'A sponsorship payout reached your club wallet.',
          audience: 'club_owner',
          deepLinkRoute: '/club/sponsorships',
          preferenceKey: 'allow_wallet',
          metadata: <String, Object?>{'source': 'fixture'},
        ),
        NotificationEventMatrixItem(
          eventKey: 'ticket_purchased',
          topic: 'ticketing',
          templateKey: 'ticket.purchased',
          title: 'Ticket purchased',
          defaultMessage: 'Your match ticket has been confirmed.',
          audience: 'fan',
          deepLinkRoute: '/app/tickets',
          preferenceKey: 'allow_competition',
          metadata: <String, Object?>{'source': 'fixture'},
        ),
        NotificationEventMatrixItem(
          eventKey: 'kill_switch_enabled',
          topic: 'admin',
          templateKey: 'launch.kill_switch.enabled',
          title: 'Kill switch enabled',
          defaultMessage: 'A launch-control kill switch was enabled.',
          audience: 'admin',
          deepLinkRoute: '/admin/launch-control',
          preferenceKey: null,
          metadata: <String, Object?>{'source': 'fixture'},
        ),
      ],
    );
  }

  Future<NotificationPreference> preferences() async => _preference;

  Future<List<NotificationSubscription>> subscriptions() async =>
      List<NotificationSubscription>.of(_subscriptions, growable: false);

  Future<NotificationSubscription> upsertSubscription({
    required String subscriptionKey,
    required String label,
    required String subscriptionType,
    required bool active,
  }) async {
    final int existingIndex = _subscriptions.indexWhere(
      (NotificationSubscription item) =>
          item.subscriptionKey == subscriptionKey,
    );
    if (existingIndex != -1) {
      final NotificationSubscription existing = _subscriptions[existingIndex];
      final NotificationSubscription updated = NotificationSubscription(
        id: existing.id,
        subscriptionKey: existing.subscriptionKey,
        subscriptionType: subscriptionType,
        label: label,
        active: active,
        metadata: existing.metadata,
      );
      _subscriptions[existingIndex] = updated;
      return updated;
    }

    final NotificationSubscription created = NotificationSubscription(
      id: 'sub-${_subscriptions.length + 1}',
      subscriptionKey: subscriptionKey,
      subscriptionType: subscriptionType,
      label: label,
      active: active,
      metadata: const <String, Object?>{},
    );
    _subscriptions.insert(0, created);
    return created;
  }

  Future<void> removeSubscription(String subscriptionId) async {
    _subscriptions.removeWhere(
      (NotificationSubscription item) => item.id == subscriptionId,
    );
  }

  Future<List<PlatformAnnouncement>> announcements() async =>
      List<PlatformAnnouncement>.of(_announcements, growable: false);

  Future<List<NotificationEventMatrixItem>> eventMatrix() async =>
      List<NotificationEventMatrixItem>.of(_eventMatrix, growable: false);

  Future<NotificationTestEventResult> publishTestEvent({
    required String eventKey,
    required String targetUserId,
    String? resourceId,
    String? message,
  }) async {
    final String normalized = eventKey.trim().toLowerCase();
    final NotificationEventMatrixItem item = _eventMatrix.firstWhere(
      (NotificationEventMatrixItem entry) => entry.eventKey == normalized,
      orElse: () => _eventMatrix.first,
    );
    return NotificationTestEventResult(
      notificationId:
          'fixture-${item.eventKey}-${targetUserId.trim().isEmpty ? 'user' : targetUserId.trim()}',
      message:
          message != null && message.trim().isNotEmpty
              ? message.trim()
              : item.defaultMessage,
      matrixItem: item,
    );
  }

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
      publishedAt: DateTime.now().toUtc(),
      metadata: const <String, Object?>{},
    );
    _announcements.insert(0, created);
    return created;
  }
}
