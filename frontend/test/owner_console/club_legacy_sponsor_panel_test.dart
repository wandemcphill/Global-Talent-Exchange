import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/owner_console/widgets/club_legacy_sponsor_panel.dart';

void main() {
  testWidgets('sponsor panel previews without publishing and shows delivery plus renewal', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(900, 1800);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    final List<String> actions = <String>[];
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ClubLegacySponsorPanel(
            data: const ClubLegacySponsorData(
              zones: <String>['shirt_front', 'sleeve', 'board'],
              sponsorName: 'Harbour Trust',
              contractZones: <String>['shirt_front', 'sleeve'],
              fee: '2500.00',
              previewPublished: false,
              suggestion: 'Suggestion cannot publish',
              kitStatus: 'Waiting for approval',
              impressions: 1200,
              note: 'Board ran for the full friendly.',
              renewedFrom: 'contract-1',
            ),
            onAction: actions.add,
          ),
        ),
      ),
    );
    expect(find.text('shirt_front'), findsOneWidget);
    expect(find.text('sleeve'), findsWidgets);
    expect(find.text('board'), findsOneWidget);
    expect(find.text('shirt_front, sleeve'), findsOneWidget);
    expect(find.text('Fee 2500.00'), findsOneWidget);
    expect(find.text('Preview only'), findsOneWidget);
    expect(find.text('Suggestion cannot publish'), findsOneWidget);
    expect(find.text('Waiting for approval'), findsOneWidget);
    expect(find.text('1200 impressions'), findsOneWidget);
    expect(find.text('Board ran for the full friendly.'), findsOneWidget);
    expect(find.text('Renewed from contract-1'), findsOneWidget);
    await tester.ensureVisible(find.byKey(const Key('club-sponsor-preview-action')));
    await tester.tap(find.byKey(const Key('club-sponsor-preview-action')));
    await tester.tap(find.byKey(const Key('club-sponsor-suggest')));
    await tester.tap(find.byKey(const Key('club-sponsor-approve')));
    await tester.ensureVisible(find.byKey(const Key('club-sponsor-publish')));
    await tester.tap(find.byKey(const Key('club-sponsor-publish')));
    await tester.ensureVisible(find.byKey(const Key('club-sponsor-deliver')));
    await tester.tap(find.byKey(const Key('club-sponsor-deliver')));
    await tester.ensureVisible(find.byKey(const Key('club-sponsor-renew')));
    await tester.tap(find.byKey(const Key('club-sponsor-renew')));
    expect(actions, <String>['preview', 'suggest', 'approve', 'publish', 'deliver', 'renew']);
  });
}
