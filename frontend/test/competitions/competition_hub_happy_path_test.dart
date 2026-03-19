import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/controllers/competition_controller.dart';
import 'package:gte_frontend/data/competition_api.dart';
import 'package:gte_frontend/features/competitions_hub/presentation/gte_competitions_hub_screen.dart';
import 'package:gte_frontend/features/competitions_hub/routing/competition_hub_destination.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

class _SeededCompetitionController extends CompetitionController {
  _SeededCompetitionController(this._seeded)
      : super(
          api: CompetitionApi.fixture(),
          currentUserId: 'arena-user',
          currentUserName: 'Arena User',
        ) {
    competitions = List<CompetitionSummary>.of(_seeded);
    discoverySyncedAt = DateTime.utc(2026, 3, 19, 8, 30);
  }

  final List<CompetitionSummary> _seeded;

  @override
  Future<void> bootstrap() => Future<void>.value();

  @override
  Future<void> loadDiscovery() async {
    competitions = List<CompetitionSummary>.of(_seeded);
    discoverySyncedAt = DateTime.utc(2026, 3, 19, 8, 30);
    notifyListeners();
  }
}

void main() {
  testWidgets(
      'arena overview renders fixture snapshots when valid seeded data exists',
      (WidgetTester tester) async {
    final CompetitionController controller = CompetitionController(
      api: CompetitionApi.fixture(),
      currentUserId: 'demo-user',
      currentUserName: 'Demo Fan',
    );

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
      find.text('Live fixture desk'),
      find.byType(ListView).first,
      const Offset(0, -300),
    );
    await tester.pumpAndSettle();

    expect(find.text('Live fixture desk'), findsOneWidget);
    expect(find.text('Coastal Creator Cup'), findsWidgets);

    await tester.dragUntilVisible(
      find.text('User-hosted competitions'),
      find.byType(ListView).first,
      const Offset(0, -300),
    );
    await tester.pumpAndSettle();

    expect(find.text('User-hosted competitions'), findsOneWidget);

    await tester.dragUntilVisible(
      find.text('Featured now'),
      find.byType(ListView).first,
      const Offset(0, -300),
    );
    await tester.pumpAndSettle();

    expect(find.text('Featured now'), findsOneWidget);
  });

  testWidgets(
      'arena overview separates live, final, and replay-ready sections for valid payloads',
      (WidgetTester tester) async {
    final CompetitionController controller = _SeededCompetitionController(
      <CompetitionSummary>[
        _competition(
          id: 'arena-live-league',
          name: 'Arena Live League',
          creatorName: 'GTEX Arena',
          format: CompetitionFormat.league,
          status: CompetitionStatus.inProgress,
          participantCount: 12,
          capacity: 12,
          updatedAt: DateTime.utc(2026, 3, 19, 7, 0),
        ),
        _competition(
          id: 'arena-up-next-cup',
          name: 'Up Next Creator Cup',
          creatorName: 'Creator Channel',
          format: CompetitionFormat.cup,
          status: CompetitionStatus.published,
          participantCount: 6,
          capacity: 8,
          updatedAt: DateTime.utc(2026, 3, 19, 6, 30),
        ),
        _competition(
          id: 'arena-replay-showcase',
          name: 'Replay Showcase Cup',
          creatorName: 'Replay Studio',
          format: CompetitionFormat.cup,
          status: CompetitionStatus.completed,
          participantCount: 8,
          capacity: 8,
          updatedAt: DateTime.utc(2026, 3, 19, 5, 30),
        ),
        _competition(
          id: 'arena-final-whistle',
          name: 'Final Whistle Classic',
          creatorName: 'Replay Studio',
          format: CompetitionFormat.league,
          status: CompetitionStatus.completed,
          participantCount: 10,
          capacity: 10,
          updatedAt: DateTime.utc(2026, 3, 19, 4, 45),
        ),
      ],
    );

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
      find.text('Live fixture desk'),
      find.byType(ListView).first,
      const Offset(0, -300),
    );
    await tester.dragUntilVisible(
      find.text('Arena Live League'),
      find.byType(ListView).first,
      const Offset(0, -200),
    );
    await tester.pumpAndSettle();
    expect(find.text('Arena Live League'), findsWidgets);

    await tester.dragUntilVisible(
      find.text('Up Next Creator Cup'),
      find.byType(ListView).first,
      const Offset(0, -200),
    );
    await tester.pumpAndSettle();
    expect(find.text('Up Next Creator Cup'), findsWidgets);

    await tester.dragUntilVisible(
      find.text('Recently settled'),
      find.byType(ListView).first,
      const Offset(0, -300),
    );
    await tester.pumpAndSettle();
    expect(find.text('Recently settled'), findsOneWidget);

    await tester.dragUntilVisible(
      find.text('Replay Showcase Cup'),
      find.byType(ListView).first,
      const Offset(0, -200),
    );
    await tester.pumpAndSettle();
    expect(find.text('Replay Showcase Cup'), findsWidgets);

    await tester.dragUntilVisible(
      find.text('Highlight-ready competitions'),
      find.byType(ListView).first,
      const Offset(0, -300),
    );
    await tester.pumpAndSettle();
    expect(find.text('Highlight-ready competitions'), findsOneWidget);

    await tester.dragUntilVisible(
      find.text('Final Whistle Classic'),
      find.byType(ListView).first,
      const Offset(0, -200),
    );
    await tester.pumpAndSettle();
    expect(find.text('Final Whistle Classic'), findsWidgets);
  });
}

CompetitionSummary _competition({
  required String id,
  required String name,
  required String creatorName,
  required CompetitionFormat format,
  required CompetitionStatus status,
  required int participantCount,
  required int capacity,
  required DateTime updatedAt,
}) {
  return CompetitionSummary(
    id: id,
    name: name,
    format: format,
    visibility: CompetitionVisibility.public,
    status: status,
    creatorId: creatorName.toLowerCase().replaceAll(' ', '-'),
    creatorName: creatorName,
    participantCount: participantCount,
    capacity: capacity,
    currency: 'credit',
    entryFee: 10,
    platformFeePct: 0.10,
    hostFeePct: 0.03,
    platformFeeAmount: participantCount.toDouble(),
    hostFeeAmount: participantCount * 0.3,
    prizePool: participantCount * 8.7,
    payoutStructure: const <CompetitionPayoutBreakdown>[
      CompetitionPayoutBreakdown(place: 1, percent: 0.6, amount: 52.2),
      CompetitionPayoutBreakdown(place: 2, percent: 0.4, amount: 34.8),
    ],
    rulesSummary:
        'Verified fixtures, transparent payout logic, and stable replay handoff for the Arena happy path.',
    joinEligibility: const CompetitionJoinEligibility(eligible: true),
    beginnerFriendly: false,
    createdAt: updatedAt.subtract(const Duration(days: 1)),
    updatedAt: updatedAt,
  );
}
