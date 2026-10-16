import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/matchday_economy_redesign/matchday_economy_api.dart';
import 'package:gte_frontend/features/matchday_economy_redesign/matchday_economy_controller.dart';
import 'package:gte_frontend/features/matchday_economy_redesign/matchday_economy_models.dart';
import 'package:gte_frontend/features/matchday_economy_redesign/matchday_economy_widgets.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  test('matchday economy model parses backend overview payload', () {
    final GtexMatchdayEconomyOverview overview =
        GtexMatchdayEconomyOverview.fromJson(<String, Object?>{
          'generated_at': '2026-05-11T10:00:00Z',
          'audience': 'admin',
          'totals': <String, Object?>{'sections': 1},
          'sections': <Object?>[
            <String, Object?>{
              'key': 'fan_economy',
              'title': 'Fan Economy',
              'description': 'Predictions and fan wars.',
              'feature_key': 'fan_coin',
              'route': '/app/community',
              'launch_state': 'public',
              'enabled': true,
              'health_status': 'online',
              'alerts': <Object?>['Prediction settlement pending.'],
              'metrics': <Object?>[
                <String, Object?>{
                  'key': 'prediction_fixtures',
                  'label': 'Prediction fixtures',
                  'value': 3,
                  'display_value': '3',
                  'status': 'live',
                },
              ],
            },
          ],
        });

    expect(overview.audience, 'admin');
    expect(overview.section('fan_economy')?.featureKey, 'fan_coin');
    expect(overview.section('fan_economy')?.metrics.single.value, 3);
    expect(overview.section('fan_economy')?.needsAttention, isTrue);
  });

  test('matchday economy action model parses admin response payload', () {
    final GtexMatchdayEconomyAction action = GtexMatchdayEconomyAction.fromJson(
      <String, Object?>{
        'action': 'settle_prediction_rewards',
        'status': 'ok',
        'resource_id': 'fixture-1',
        'message': 'Prediction fixture settled.',
        'metrics': <String, Object?>{
          'reward_grants_created': 3,
          'fan_coin_debited': '75.5',
        },
        'metadata': <String, Object?>{
          'notification_event': 'prediction_settled',
        },
      },
    );

    expect(action.succeeded, isTrue);
    expect(action.resourceId, 'fixture-1');
    expect(action.metrics['reward_grants_created'], 3);
    expect(action.metrics['fan_coin_debited'], 75.5);
    expect(action.metadata['notification_event'], 'prediction_settled');
  });

  test('matchday economy controller loads fixture fallback', () async {
    final GtexMatchdayEconomyController controller =
        GtexMatchdayEconomyController(api: GtexMatchdayEconomyApi.fixture());

    await controller.load(admin: true);

    expect(controller.errorMessage, isNull);
    expect(controller.overview?.sections.length, 5);
    expect(controller.overview?.section('ticketing_stadium'), isNotNull);
    controller.dispose();
  });

  test(
    'matchday economy controller exposes fixture admin action adapters',
    () async {
      final GtexMatchdayEconomyController controller =
          GtexMatchdayEconomyController(api: GtexMatchdayEconomyApi.fixture());

      final GtexMatchdayEconomyAction? action = await controller
          .settlePredictionRewards(
            'prediction-fixture-1',
            fancoinAmount: '30.0000',
            maxWinners: 1,
          );

      expect(controller.errorMessage, isNull);
      expect(controller.isMutating, isFalse);
      expect(action?.action, 'settle_prediction_rewards');
      expect(controller.lastAction?.resourceId, 'prediction-fixture-1');
      controller.dispose();
    },
  );

  testWidgets('matchday economy widget renders fixture sections', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1400, 2200);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: const Scaffold(
          body: SingleChildScrollView(
            child: GtexMatchdayEconomyPanel(
              baseUrl: 'http://127.0.0.1:8000',
              backendMode: GteBackendMode.fixture,
              accessToken: 'fixture-token',
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Matchday economy'), findsOneWidget);
    expect(find.text('Federation Governance'), findsOneWidget);
    expect(find.text('Fan Economy'), findsOneWidget);
    expect(find.text('Player Card Collectibles'), findsOneWidget);
  });
}
