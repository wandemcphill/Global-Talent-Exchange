import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/compete/providers/competition_controller.dart';
import 'package:gte_frontend/data/competition_api.dart';
import 'package:gte_frontend/features/compete/presentation/gte_competitions_hub_screen.dart';
import 'package:gte_frontend/features/compete/domain/competition_hub_destination.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_type.dart';
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
      tester.view.physicalSize = const Size(1600, 2200);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      final CompetitionController controller = CompetitionController(
        api: CompetitionApi.fixture(),
        currentUserId: 'fixture-user',
        currentUserName: 'Fixture Trader',
      );
      await controller.bootstrap();

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

      await _dragUntilTextVisible(tester, 'Live competition desk');

      expect(find.text('Live competition desk'), findsOneWidget);
      expect(find.text('GTEX Spotlight Cup'), findsWidgets);

      await _dragUntilTextVisible(tester, 'User-created competitions');

      expect(find.text('User-created competitions'), findsOneWidget);

      await _dragUntilTextVisible(tester, 'Featured now');

      expect(find.text('Featured now'), findsOneWidget);
    },
  );

  testWidgets(
    'arena overview separates live, final, and replay-ready sections for valid payloads',
    (WidgetTester tester) async {
      final CompetitionController controller =
          _SeededCompetitionController(<CompetitionSummary>[
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
          ]);

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

      await _dragUntilTextVisible(tester, 'Live competition desk');
      await _dragUntilTextVisible(tester, 'Arena Live League');
      expect(find.text('Arena Live League'), findsWidgets);

      await _dragUntilTextVisible(tester, 'Up Next Creator Cup');
      expect(find.text('Up Next Creator Cup'), findsWidgets);

      await _dragUntilTextVisible(tester, 'Recently settled');
      expect(find.text('Recently settled'), findsOneWidget);

      await _dragUntilTextVisible(tester, 'Replay Showcase Cup');
      expect(find.text('Replay Showcase Cup'), findsWidgets);

      await _dragUntilTextVisible(tester, 'Highlight-ready competitions');
      expect(find.text('Highlight-ready competitions'), findsOneWidget);

      await _dragUntilTextVisible(tester, 'Final Whistle Classic');
      expect(find.text('Final Whistle Classic'), findsWidgets);
    },
  );

  testWidgets('arena host CTA lets authenticated launch users create', (
    WidgetTester tester,
  ) async {
    final CompetitionController controller = CompetitionController(
      api: CompetitionApi.fixture(),
      currentUserId: 'fixture-user',
      currentUserName: 'Fixture Trader',
    );
    bool openedCreatorAccess = false;

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GteCompetitionsHubScreen(
          controller: controller,
          currentDestination: CompetitionHubDestination.overview,
          onDestinationChanged: (_) {},
          isAuthenticated: true,
          canHostCompetitions: false,
          onOpenCreatorAccessRequest: () {
            openedCreatorAccess = true;
          },
        ),
      ),
    );
    await tester.pumpAndSettle();

    await _dragUntilTextVisible(tester, 'Host your own competition');

    expect(find.text('Create competition'), findsWidgets);
    expect(find.text('Request creator access to host'), findsNothing);
    expect(find.text('Host Competition'), findsNothing);

    expect(openedCreatorAccess, isFalse);
  });

  testWidgets('arena host CTA opens competition creation for launch users', (
    WidgetTester tester,
  ) async {
    final CompetitionController controller = CompetitionController(
      api: CompetitionApi.fixture(),
      currentUserId: 'fixture-user',
      currentUserName: 'Fixture Trader',
    );
    bool openedCreatorAccess = false;

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GteCompetitionsHubScreen(
          controller: controller,
          currentDestination: CompetitionHubDestination.overview,
          onDestinationChanged: (_) {},
          isAuthenticated: true,
          canHostCompetitions: false,
          onOpenCreatorAccessRequest: () {
            openedCreatorAccess = true;
          },
        ),
      ),
    );
    await tester.pumpAndSettle();

    await _dragUntilTextVisible(tester, 'Host your own competition');

    expect(find.text('Create competition'), findsWidgets);
    expect(find.text('Request creator access to host'), findsNothing);
    expect(find.text('Host competition'), findsNothing);

    await tester.tap(find.widgetWithText(FilledButton, 'Create competition'));
    await tester.pumpAndSettle();

    expect(find.text('Create competition'), findsWidgets);
    await _dragUntilTextVisible(tester, 'Preview & publish');
    expect(find.text('Preview & publish'), findsOneWidget);
    expect(openedCreatorAccess, isFalse);
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
    matchType: MatchType.gtexHosted,
    joinEligibility: const CompetitionJoinEligibility(eligible: true),
    beginnerFriendly: false,
    createdAt: updatedAt.subtract(const Duration(days: 1)),
    updatedAt: updatedAt,
  );
}

Future<void> _dragUntilTextVisible(
  WidgetTester tester,
  String text, {
  int maxDrags = 24,
}) async {
  final Finder textFinder = find.text(text);
  final Finder scrollable = find.byType(Scrollable).first;
  for (int attempt = 0; attempt < maxDrags; attempt += 1) {
    if (textFinder.evaluate().isNotEmpty) {
      await tester.ensureVisible(textFinder);
      await tester.pump();
      return;
    }
    await tester.drag(scrollable, const Offset(0, -500));
    await tester.pump();
  }
  expect(textFinder, findsOneWidget);
}
