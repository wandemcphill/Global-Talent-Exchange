import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/social/presentation/club_directory_panel.dart';

void main() {
  testWidgets('club directory search shows the matching club', (WidgetTester tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ClubDirectoryPanel(
            baseUrl: 'http://127.0.0.1',
            backendMode: GteBackendMode.live,
            searchClubs: (String query) async {
              return <DiscoveredClub>[
                DiscoveredClub(id: 'club-1', name: 'Alpha FC', city: query),
              ];
            },
          ),
        ),
      ),
    );

    await tester.enterText(find.byKey(const Key('gtex-club-directory-search')), 'Alpha');
    await tester.tap(find.byKey(const Key('gtex-club-directory-submit')));
    await tester.pump();

    expect(find.text('Alpha FC'), findsOneWidget);
    expect(find.byKey(const Key('gtex-club-directory')), findsOneWidget);
  });
}

