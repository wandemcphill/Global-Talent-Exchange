import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/features/tasks/tasks_screen.dart';
import 'package:gte_frontend/shared/models/auth_session.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';

void main() {
  testWidgets(
    'tasks screen shows backend claim reward details and refreshed streak state',
    (WidgetTester tester) async {
      const AuthSession session = AuthSession(
        userId: 'user-1',
        accessToken: 'token-1',
        refreshToken: 'refresh-token-1',
        sessionId: 'session-1',
        role: 'user',
      );
      final _QueuedTransport
      transport = _QueuedTransport(<String, List<GteTransportResponse>>{
        'GET /api/v2/daily-challenges': <GteTransportResponse>[
          _dailyChallengesResponse(),
          _dailyChallengesResponse(),
        ],
        'GET /api/v2/daily-challenges/me': <GteTransportResponse>[
          _dailyChallengesMeResponse(
            currentStreak: 4,
            longestStreak: 8,
            nextBonusAmount: 25,
            availableChallengeKeys: const <String>['daily-login'],
            claimsToday: const <Object?>[],
            todayClaimed: false,
          ),
          _dailyChallengesMeResponse(
            currentStreak: 5,
            longestStreak: 8,
            nextBonusAmount: 25,
            availableChallengeKeys: const <String>[],
            claimsToday: const <Object?>[
              <String, Object?>{
                'id': 'claim-1',
                'user_id': 'user-1',
                'challenge_id': 'challenge-1',
                'claim_date': '2026-04-12',
                'reward_amount': 50.0,
                'reward_unit': 'credit',
                'reward_settlement_id': 'settlement-1',
                'metadata_json': <String, Object?>{
                  'challenge_key': 'daily-login',
                  'streak_before_claim': 4,
                  'bonus_amount': '25.0000',
                },
                'claimed_at': '2026-04-12T08:15:00Z',
              },
            ],
            todayClaimed: true,
          ),
        ],
        'POST /api/v2/daily-challenges/daily-login/claim': <
          GteTransportResponse
        >[
          const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'challenge': <String, Object?>{
                'id': 'challenge-1',
                'challenge_key': 'daily-login',
                'title': 'Daily Login Bonus',
                'description':
                    'Check in once per day to keep your club heartbeat alive.',
                'reward_amount': 25.0,
                'reward_unit': 'credit',
                'claim_limit_per_day': 1,
                'sort_order': 10,
                'status': 'active',
                'metadata_json': <String, Object?>{'action': 'login'},
              },
              'claim': <String, Object?>{
                'id': 'claim-1',
                'user_id': 'user-1',
                'challenge_id': 'challenge-1',
                'claim_date': '2026-04-12',
                'reward_amount': 50.0,
                'reward_unit': 'credit',
                'reward_settlement_id': 'settlement-1',
                'metadata_json': <String, Object?>{
                  'challenge_key': 'daily-login',
                  'streak_before_claim': 4,
                  'bonus_amount': '25.0000',
                },
                'claimed_at': '2026-04-12T08:15:00Z',
              },
              'reward_summary': 'Claimed 50.0000 credit from daily-login.',
            },
          ),
        ],
      });
      final GteAuthedApi api = GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'https://example.test',
          mode: GteBackendMode.live,
        ),
        transport: transport,
        authSession: session,
        deviceId: 'device-test',
        mode: GteBackendMode.live,
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authProvider.overrideWith((Ref ref) => session),
            authedApiProvider.overrideWith((Ref ref) => api),
          ],
          child: const MaterialApp(home: Scaffold(body: TasksScreen())),
        ),
      );
      await tester.pumpAndSettle();

      await _scrollTo(tester, find.text('Daily Login Bonus'));
      expect(find.text('Daily Login Bonus'), findsOneWidget);
      expect(find.textContaining('Available to claim now.'), findsOneWidget);

      await tester.tap(find.widgetWithText(FilledButton, 'Claim'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      expect(find.text('Live reward settled'), findsOneWidget);
      expect(find.text('50 credit'), findsOneWidget);
      expect(find.text('Bonus 25 credit'), findsOneWidget);
      expect(find.text('5 day streak'), findsOneWidget);
      expect(find.text('Next bonus 25'), findsOneWidget);
      expect(
        find.textContaining('Claimed 50.0000 credit from daily-login.'),
        findsOneWidget,
      );
      expect(find.textContaining('Login streak is now 5.'), findsOneWidget);

      await tester.pump(const Duration(milliseconds: 1800));
      await tester.pumpAndSettle();

      expect(
        find.textContaining('Claim already settled today.'),
        findsOneWidget,
      );
      await _scrollTo(
        tester,
        find.text('Settled reward 50 credit with streak bonus 25 credit.'),
      );
      expect(
        find.text('Settled reward 50 credit with streak bonus 25 credit.'),
        findsOneWidget,
      );
      expect(transport.requestLog, <String>[
        'GET /api/v2/daily-challenges',
        'GET /api/v2/daily-challenges/me',
        'POST /api/v2/daily-challenges/daily-login/claim',
        'GET /api/v2/daily-challenges',
        'GET /api/v2/daily-challenges/me',
      ]);
    },
  );
}

Future<void> _scrollTo(WidgetTester tester, Finder finder) async {
  await tester.scrollUntilVisible(
    finder,
    220,
    scrollable: find.byType(Scrollable).first,
  );
  await tester.pumpAndSettle();
}

GteTransportResponse _dailyChallengesResponse() {
  return const GteTransportResponse(
    statusCode: 200,
    body: <String, Object?>{
      'feature_enabled': true,
      'challenges': <Object?>[
        <String, Object?>{
          'id': 'challenge-1',
          'challenge_key': 'daily-login',
          'title': 'Daily Login Bonus',
          'description':
              'Check in once per day to keep your club heartbeat alive.',
          'reward_amount': 25.0,
          'reward_unit': 'credit',
          'claim_limit_per_day': 1,
          'sort_order': 10,
          'status': 'active',
          'metadata_json': <String, Object?>{'action': 'login'},
        },
      ],
    },
  );
}

GteTransportResponse _dailyChallengesMeResponse({
  required int currentStreak,
  required int longestStreak,
  required double nextBonusAmount,
  required List<String> availableChallengeKeys,
  required List<Object?> claimsToday,
  required bool todayClaimed,
}) {
  return GteTransportResponse(
    statusCode: 200,
    body: <String, Object?>{
      'feature_enabled': true,
      'claims_today': claimsToday,
      'available_challenge_keys': availableChallengeKeys,
      'login_streak': <String, Object?>{
        'current_streak': currentStreak,
        'longest_streak': longestStreak,
        'today_claimed': todayClaimed,
        'next_bonus_amount': nextBonusAmount,
      },
    },
  );
}

class _QueuedTransport implements GteTransport {
  _QueuedTransport(this.responses);

  final Map<String, List<GteTransportResponse>> responses;
  final List<String> requestLog = <String>[];

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    final String key = '${request.method.toUpperCase()} ${request.uri.path}';
    requestLog.add(key);
    final List<GteTransportResponse>? queue = responses[key];
    if (queue == null || queue.isEmpty) {
      return const GteTransportResponse(
        statusCode: 404,
        body: <String, Object?>{'detail': 'Not found.'},
      );
    }
    return queue.removeAt(0);
  }
}
