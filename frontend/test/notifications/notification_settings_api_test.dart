import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/notification_settings_api.dart';
import 'package:gte_frontend/models/notification_settings_models.dart';

void main() {
  test(
    'notification settings api uses canonical api notification routes',
    () async {
      final _RecordingTransport transport = _RecordingTransport(
        <GteTransportResponse>[
          GteTransportResponse(
            statusCode: 200,
            body: const <String, Object?>{
              'id': 'pref-1',
              'allow_wallet': true,
              'allow_market': true,
              'allow_story': true,
              'allow_competition': true,
              'allow_social': true,
              'allow_broadcasts': true,
              'quiet_hours_enabled': false,
              'metadata_json': <String, Object?>{},
            },
          ),
          GteTransportResponse(
            statusCode: 200,
            body: const <String, Object?>{
              'id': 'pref-1',
              'allow_wallet': false,
              'allow_market': true,
              'allow_story': true,
              'allow_competition': true,
              'allow_social': true,
              'allow_broadcasts': true,
              'quiet_hours_enabled': false,
              'metadata_json': <String, Object?>{},
            },
          ),
          GteTransportResponse(
            statusCode: 200,
            body: const <Object?>[
              <String, Object?>{
                'id': 'sub-1',
                'subscription_key': 'market-open',
                'subscription_type': 'market',
                'label': 'Market open alerts',
                'active': true,
                'metadata_json': <String, Object?>{},
              },
            ],
          ),
          GteTransportResponse(
            statusCode: 200,
            body: const <String, Object?>{
              'id': 'sub-2',
              'subscription_key': 'broadcast-live',
              'subscription_type': 'broadcast',
              'label': 'Broadcast live',
              'active': true,
              'metadata_json': <String, Object?>{},
            },
          ),
          const GteTransportResponse(statusCode: 204, body: null),
          GteTransportResponse(
            statusCode: 200,
            body: const <Object?>[
              <String, Object?>{
                'id': 'ann-1',
                'announcement_key': 'market-reset',
                'title': 'Market reset',
                'body': 'Pricing recalibrated.',
                'audience': 'all',
                'severity': 'info',
                'active': true,
                'deliver_as_notification': true,
                'published_at': '2026-01-15T09:30:00Z',
                'metadata_json': <String, Object?>{},
              },
            ],
          ),
          GteTransportResponse(
            statusCode: 200,
            body: const <Object?>[
              <String, Object?>{
                'id': 'ann-1',
                'announcement_key': 'market-reset',
                'title': 'Market reset',
                'body': 'Pricing recalibrated.',
                'audience': 'all',
                'severity': 'info',
                'active': true,
                'deliver_as_notification': true,
                'published_at': '2026-01-15T09:30:00Z',
                'metadata_json': <String, Object?>{},
              },
            ],
          ),
          GteTransportResponse(
            statusCode: 200,
            body: const <String, Object?>{
              'id': 'ann-2',
              'announcement_key': 'creator-cup',
              'title': 'Creator Cup',
              'body': 'Registration is live.',
              'audience': 'all',
              'severity': 'info',
              'active': true,
              'deliver_as_notification': true,
              'published_at': '2026-01-16T09:30:00Z',
              'metadata_json': <String, Object?>{},
            },
          ),
        ],
      );
      final NotificationSettingsApi api = NotificationSettingsApi.standard(
        baseUrl: 'http://127.0.0.1:8000',
        accessToken: 'token-1',
        mode: GteBackendMode.live,
        transport: transport,
      );

      await api.fetchPreferences();
      await api.updatePreferences(
        const NotificationPreference(
          id: 'pref-1',
          allowWallet: false,
          allowMarket: true,
          allowStory: true,
          allowCompetition: true,
          allowSocial: true,
          allowBroadcasts: true,
          quietHoursEnabled: false,
          quietHoursStart: null,
          quietHoursEnd: null,
          metadata: <String, Object?>{},
        ),
      );
      await api.listSubscriptions();
      await api.upsertSubscription(
        subscriptionKey: 'broadcast-live',
        label: 'Broadcast live',
        subscriptionType: 'broadcast',
      );
      await api.deleteSubscription('sub-2');
      await api.listAnnouncements();
      await api.adminListAnnouncements();
      await api.publishAnnouncement(
        announcementKey: 'creator-cup',
        title: 'Creator Cup',
        body: 'Registration is live.',
      );

      expect(
        transport.requests.map(
          (GteTransportRequest request) => request.uri.path,
        ),
        <String>[
          '/api/v1/notifications/preferences',
          '/api/v1/notifications/preferences',
          '/api/v1/notifications/subscriptions',
          '/api/v1/notifications/subscriptions',
          '/api/v1/notifications/subscriptions/sub-2',
          '/api/v1/notifications/announcements',
          '/api/v1/admin/notifications/announcements',
          '/api/v1/admin/notifications/announcements',
        ],
      );
    },
  );
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
