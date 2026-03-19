import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/controllers/competition_controller.dart';
import 'package:gte_frontend/data/competition_api.dart';
import 'package:gte_frontend/features/competitions_hub/presentation/gte_competitions_hub_screen.dart';
import 'package:gte_frontend/features/competitions_hub/routing/competition_hub_destination.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

class _IdleCompetitionController extends CompetitionController {
  _IdleCompetitionController()
      : super(
          api: CompetitionApi.fixture(),
          currentUserId: 'arena-user',
          currentUserName: 'Arena User',
        );

  @override
  Future<void> bootstrap() => Future<void>.value();

  @override
  Future<void> loadDiscovery() => Future<void>.value();
}

void main() {
  testWidgets(
      'competitions hub shows an empty state when no competitions are available',
      (WidgetTester tester) async {
    final CompetitionController controller = _IdleCompetitionController();

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GteCompetitionsHubScreen(
          controller: controller,
          currentDestination: CompetitionHubDestination.overview,
          onDestinationChanged: (_) {},
        ),
      ),
    );
    await tester.pumpAndSettle();
    await tester.dragUntilVisible(
      find.text('Competition map is warming up'),
      find.byType(ListView).first,
      const Offset(0, -300),
    );
    await tester.pumpAndSettle();

    expect(find.text('Competition map is warming up'), findsOneWidget);
    expect(find.text('Pull to refresh when new competitions publish.'),
        findsOneWidget);
  });
}
