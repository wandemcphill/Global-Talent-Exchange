import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/world/football_world_pulse_provider.dart';
import 'package:gte_frontend/features/world/widgets/football_world_pulse_widgets.dart';

void main() {
  testWidgets('football world pulse ticker renders truthful empty live state', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          footballWorldPulseProvider.overrideWith(
            (Ref ref) async => FootballWorldPulseData.empty,
          ),
        ],
        child: const MaterialApp(
          home: Scaffold(body: FootballWorldPulseTicker()),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(
      find.byKey(const Key('football-world-pulse-ticker')),
      findsOneWidget,
    );
    expect(find.text('No live pulse events returned'), findsOneWidget);
    expect(find.text('Transfer desk'), findsNothing);
  });

  testWidgets('football world pulse rail renders blocked state on errors', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          footballWorldPulseProvider.overrideWith(
            (Ref ref) async => throw StateError('backend offline'),
          ),
        ],
        child: const MaterialApp(
          home: Scaffold(
            body: SizedBox(width: 318, child: FootballWorldPulseRail()),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Live World Pulse Unavailable'), findsOneWidget);
    expect(find.text('Discovery route'), findsNothing);
  });

  testWidgets('football world pulse rail renders desktop market layers', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1440, 1000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          footballWorldPulseProvider.overrideWith(
            (Ref ref) async => _pulseData,
          ),
        ],
        child: const MaterialApp(
          home: Scaffold(
            body: SizedBox(width: 318, child: FootballWorldPulseRail()),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('football-world-pulse-rail')), findsOneWidget);
    expect(
      find.byKey(const Key('football-world-transfer-route-overlay')),
      findsOneWidget,
    );
    expect(find.text('Football world layer'), findsOneWidget);
    expect(find.text('Transfer ticker'), findsOneWidget);
    expect(find.text('Live negotiations'), findsOneWidget);
    expect(find.text('Competition countdown'), findsOneWidget);
    expect(find.text('Market movers'), findsOneWidget);
    expect(find.text('Discussion rooms'), findsOneWidget);
    expect(find.text('Rivalry activity'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.text('Ranking movement'),
      220,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pumpAndSettle();
    expect(find.text('Ranking movement'), findsOneWidget);
  });
}

const FootballWorldPulseData _pulseData = FootballWorldPulseData(
  transferTicker: <FootballPulseItem>[
    FootballPulseItem(
      label: 'Kobbie Mainoo',
      detail: 'Manchester United - Live transfer listing',
      metric: '80 GTEX Coin',
      intensity: 0.78,
    ),
  ],
  globalActivity: <FootballPulseItem>[
    FootballPulseItem(
      label: 'Scouting desk',
      detail: '12 notes moving through the global feed',
      metric: '12 reports',
      intensity: 0.65,
    ),
  ],
  transferRoutes: <FootballPulseRoute>[
    FootballPulseRoute(
      source: 'Manchester United',
      destination: 'Transfer room',
      label: 'Kobbie Mainoo',
      intensity: 0.7,
    ),
  ],
  onlineClubs: <FootballPulseItem>[
    FootballPulseItem(
      label: 'Creator Cup Night',
      detail: '12/16 clubs present',
      metric: 'ONLINE',
      intensity: 0.75,
    ),
  ],
  competitionCountdowns: <FootballPulseItem>[
    FootballPulseItem(
      label: 'Creator Cup Night',
      detail: '12/16 clubs - published',
      metric: 'T-2h',
      intensity: 0.82,
    ),
  ],
  marketMovers: <FootballPulseItem>[
    FootballPulseItem(
      label: 'Ayo Akin',
      detail: 'Ibadan Lions - Share market is live',
      metric: '92 heat',
      intensity: 0.92,
    ),
  ],
  discussionPreviews: <FootballPulseItem>[
    FootballPulseItem(
      label: 'Matchday derby watch party',
      detail: 'tactics_room - OPEN - now',
      metric: '+12',
      intensity: 0.72,
    ),
  ],
  rivalryCards: <FootballPulseItem>[
    FootballPulseItem(
      label: 'Matchday derby watch party',
      detail: 'Rivalry activity lane',
      metric: 'PINNED',
      intensity: 0.68,
    ),
  ],
  negotiations: <FootballPulseItem>[
    FootballPulseItem(
      label: 'Kobbie Mainoo',
      detail: '2 bids - 4 watchlists - open',
      metric: '10m',
      intensity: 0.55,
    ),
  ],
  rankingMovements: <FootballPulseItem>[
    FootballPulseItem(
      label: 'Legend One',
      detail: 'Hall of fame movement',
      metric: '+1',
      intensity: 0.5,
    ),
  ],
  marketHeat: 0.82,
  userDensity: 0.61,
);
