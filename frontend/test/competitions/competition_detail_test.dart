import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/controllers/competition_controller.dart';
import 'package:gte_frontend/data/competition_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/screens/competitions/competition_detail_screen.dart';
import 'package:gte_frontend/screens/competitions/competition_join_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('detail screen renders transparent financials and payout',
      (WidgetTester tester) async {
    final CompetitionController controller = CompetitionController(
      api: CompetitionApi.fixture(),
      currentUserId: 'fixture-user',
      currentUserName: 'Fixture Trader',
    );
    await controller.openCompetition('ugc-101');

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: CompetitionDetailScreen(
          controller: controller,
          competitionId: 'ugc-101',
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.scrollUntilVisible(
      find.text('Transparent financials'),
      300,
    );
    expect(find.text('Transparent financials'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.text('Transparent payout'),
      300,
    );
    expect(find.text('Transparent payout'), findsOneWidget);
    expect(find.textContaining('secure escrow'), findsWidgets);
    expect(find.textContaining('Platform service fee'), findsOneWidget);
    expect(find.textContaining('Host fee'), findsOneWidget);
    expect(find.textContaining('Prize pool'), findsOneWidget);
  });

  testWidgets('detail screen explains a failed competition load', (
    WidgetTester tester,
  ) async {
    final CompetitionController controller = CompetitionController(
      api: _missingCompetitionApi(),
      currentUserId: 'fixture-user',
    );
    addTearDown(controller.dispose);

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: CompetitionDetailScreen(
          controller: controller,
          competitionId: 'missing',
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text("We couldn't load this competition."), findsOneWidget);
    expect(find.text('Retry'), findsOneWidget);
    expect(find.text('Select a tournament'), findsNothing);
  });

  testWidgets('join screen explains a failed competition load', (
    WidgetTester tester,
  ) async {
    final CompetitionController controller = CompetitionController(
      api: _missingCompetitionApi(),
      currentUserId: 'fixture-user',
    );
    addTearDown(controller.dispose);

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: CompetitionJoinScreen(
          controller: controller,
          competitionId: 'missing',
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text("We couldn't load this competition."), findsOneWidget);
    expect(find.text('Retry'), findsOneWidget);
  });
}

CompetitionApi _missingCompetitionApi() {
  return CompetitionApi(
    config: const GteRepositoryConfig(baseUrl: 'https://example.test'),
    transport: _MissingCompetitionTransport(),
  );
}

class _MissingCompetitionTransport implements GteTransport {
  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    return const GteTransportResponse(
      statusCode: 404,
      body: <String, Object?>{'detail': 'competition not found'},
    );
  }
}
