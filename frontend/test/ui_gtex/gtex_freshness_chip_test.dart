import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/ui_gtex/components/gtex_freshness_chip.dart';
import 'package:gte_frontend/ui_gtex/models/gtex_freshness.dart';

void main() {
  testWidgets('GtexFreshnessChip renders LIVE badge correctly', (WidgetTester tester) async {
    const info = GtexFreshnessInfo(
      status: GtexFreshnessStatus.live,
      label: 'LIVE',
    );

    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: GtexFreshnessChip(freshness: info),
        ),
      ),
    );

    expect(find.text('LIVE'), findsOneWidget);
  });

  testWidgets('GtexFreshnessChip renders PENDING RECALCULATION badge correctly', (WidgetTester tester) async {
    const info = GtexFreshnessInfo(
      status: GtexFreshnessStatus.pendingRecalculation,
      label: 'PENDING RECALCULATION',
      pendingReason: 'Match ended, snapshot queued',
    );

    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: GtexFreshnessChip(freshness: info),
        ),
      ),
    );

    expect(find.text('PENDING RECALCULATION'), findsOneWidget);
  });

  testWidgets('GtexFreshnessChip renders STALE badge correctly', (WidgetTester tester) async {
    const info = GtexFreshnessInfo(
      status: GtexFreshnessStatus.stale,
      label: 'STALE',
      staleReason: 'Data is 48 hours old',
    );

    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: GtexFreshnessChip(freshness: info),
        ),
      ),
    );

    expect(find.text('STALE'), findsOneWidget);
  });

  testWidgets('GtexFreshnessChip suppresses rendering when status is UNKNOWN', (WidgetTester tester) async {
    const info = GtexFreshnessInfo(
      status: GtexFreshnessStatus.unknown,
    );

    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: GtexFreshnessChip(freshness: info),
        ),
      ),
    );

    expect(find.byType(GtexFreshnessChip), findsOneWidget);
    expect(find.byType(Container), findsNothing);
    expect(find.text('UNKNOWN'), findsNothing);
  });
}
