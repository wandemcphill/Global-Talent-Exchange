import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/shell/shell.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('connection badge renders every canonical realtime status', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _Harness(
        child: Wrap(
          spacing: 8,
          runSpacing: 8,
          children: GtexRealtimeStatus.values
              .map(
                (GtexRealtimeStatus status) =>
                    GtexConnectionStatusBadge(status: status),
              )
              .toList(growable: false),
        ),
      ),
    );

    for (final GtexRealtimeStatus status in GtexRealtimeStatus.values) {
      expect(find.text(status.label), findsOneWidget);
    }
  });

  testWidgets('context rail renders canonical state fallbacks', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const _Harness(
        child: SizedBox(
          width: 360,
          height: 320,
          child: GtexContextRail(
            items: <GtexContextRailItem>[
              GtexContextRailItem(
                id: 'pending-context',
                eyebrow: '',
                title: '',
                state: GtexSurfaceState.empty,
                icon: Icons.inbox_outlined,
              ),
            ],
          ),
        ),
      ),
    );

    expect(find.text('EMPTY'), findsWidgets);
    expect(find.text('No backend record'), findsOneWidget);
    expect(
      find.text('No confirmed record is available for this context yet.'),
      findsOneWidget,
    );
  });

  testWidgets('notification and activity streams render event affordances', (
    WidgetTester tester,
  ) async {
    final DateTime timestamp = DateTime.now();
    final List<GtexRealtimeEvent> events = <GtexRealtimeEvent>[
      GtexRealtimeEvent(
        type: 'notification_created',
        topic: 'notifications',
        payload: const <String, Object?>{
          'title': 'Manual transfer confirmed',
          'message': 'KoraPay/manual rail proof reviewed.',
          'status': 'live',
        },
        timestamp: timestamp,
      ),
      GtexRealtimeEvent(
        type: 'activity_event',
        topic: 'activity',
        payload: const <String, Object?>{
          'actor': 'admin',
          'action': 'confirmed settlement window',
          'status': 'degraded',
        },
        timestamp: timestamp,
      ),
    ];

    await tester.pumpWidget(
      _Harness(
        child: SingleChildScrollView(
          child: Column(
            children: <Widget>[
              GtexNotificationStream(events: events),
              const SizedBox(height: 16),
              GtexActivityEventStream(events: events),
            ],
          ),
        ),
      ),
    );

    expect(find.text('NOTIFICATION STREAM'), findsOneWidget);
    expect(find.text('Manual transfer confirmed'), findsOneWidget);
    expect(find.text('KoraPay/manual rail proof reviewed.'), findsOneWidget);
    expect(find.text('ACTIVITY EVENTS'), findsOneWidget);
    expect(find.text('Activity event'), findsOneWidget);
    expect(find.text('admin confirmed settlement window'), findsOneWidget);
  });

  testWidgets('missing notification stream renders canonical empty state', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const _Harness(
        child: GtexNotificationStream(events: <GtexRealtimeEvent>[]),
      ),
    );

    expect(find.text('NOTIFICATIONS'), findsOneWidget);
    expect(find.text('No notifications'), findsOneWidget);
    expect(
      find.text('Waiting for backend notification events.'),
      findsOneWidget,
    );
  });

  testWidgets('live pulse card renders pulse and empty canonical state', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const _Harness(
        child: Column(
          children: <Widget>[
            GtexLivePulseCard(
              event: GtexRealtimeEvent(
                type: 'live_pulse',
                topic: 'live_pulse',
                payload: <String, Object?>{
                  'headline': '2D broadcast pulse received',
                  'detail': 'Match center is following the active 2D route.',
                  'status': 'syncing',
                },
              ),
            ),
            SizedBox(height: 16),
            GtexLivePulseCard(),
          ],
        ),
      ),
    );

    expect(find.text('LIVE PULSE'), findsWidgets);
    expect(find.text('2D broadcast pulse received'), findsOneWidget);
    expect(
      find.text('Match center is following the active 2D route.'),
      findsOneWidget,
    );
    expect(find.text('SYNCING'), findsOneWidget);
    expect(find.text('No live pulse'), findsOneWidget);
  });

  testWidgets('command palette route action exposes and invokes local route', (
    WidgetTester tester,
  ) async {
    String? selectedRoute;

    await tester.pumpWidget(
      _Harness(
        child: GtexCommandPalette(
          actions: <GtexCommandAction>[
            GtexCommandAction.route(
              id: 'broadcast.live',
              label: 'Open broadcast',
              description: 'Open active 2D broadcast route.',
              icon: Icons.live_tv_outlined,
              routePath: '/broadcast/live',
              onRouteSelected: (String routePath) {
                selectedRoute = routePath;
              },
            ),
          ],
        ),
      ),
    );

    expect(find.text('/broadcast/live'), findsOneWidget);

    await tester.tap(find.text('Open broadcast'));
    await tester.pump();

    expect(selectedRoute, '/broadcast/live');
  });
}

class _Harness extends StatelessWidget {
  const _Harness({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      theme: GteShellTheme.build(),
      home: Scaffold(body: Center(child: child)),
    );
  }
}
