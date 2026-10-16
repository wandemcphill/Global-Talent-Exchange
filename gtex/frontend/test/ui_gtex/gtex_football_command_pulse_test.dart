import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/ui_gtex/components/gtex_football_command_pulse.dart';

void main() {
  testWidgets('renders the football command pulse with authoritative labels', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: ThemeData.dark(),
        home: const Scaffold(
          body: GtexFootballCommandPulse(
            kicker: 'Football Command Centre',
            title: 'Regen operations cockpit',
            metrics: <GtexCommandPulseMetric>[
              GtexCommandPulseMetric(
                label: 'World regens',
                value: '48',
                icon: Icons.auto_awesome,
              ),
              GtexCommandPulseMetric(
                label: 'National pool',
                value: '48',
                icon: Icons.flag_outlined,
              ),
            ],
          ),
        ),
      ),
    );

    expect(find.text('FOOTBALL COMMAND CENTRE'), findsOneWidget);
    expect(find.text('Regen operations cockpit'), findsOneWidget);
    expect(find.text('WORLD REGENS'), findsOneWidget);
    expect(find.text('48'), findsNWidgets(2));
  });

  testWidgets('keeps pulse metrics horizontally accessible on narrow screens', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      MaterialApp(
        theme: ThemeData.dark(),
        home: const Scaffold(
          body: GtexFootballCommandPulse(
            kicker: 'Football Command Centre',
            title: 'Transfer market operations',
            metrics: <GtexCommandPulseMetric>[
              GtexCommandPulseMetric(
                label: 'Listings loaded',
                value: '120/500',
              ),
              GtexCommandPulseMetric(
                label: 'Watched',
                value: '7',
              ),
              GtexCommandPulseMetric(
                label: 'Shortlist',
                value: '2',
              ),
              GtexCommandPulseMetric(
                label: 'Market state',
                value: 'Live snapshot',
              ),
            ],
          ),
        ),
      ),
    );

    expect(find.text('Transfer market operations'), findsOneWidget);
    expect(find.text('LISTINGS LOADED'), findsOneWidget);
    expect(find.byType(Scrollable), findsWidgets);
  });
}
