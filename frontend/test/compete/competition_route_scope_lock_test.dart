import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/app_routes/gte_app_route_registry.dart';
import 'package:gte_frontend/features/app_routes/gte_route_data.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';

void main() {
  group('competition route scope lock', () {
    test(
      'classifies launch-ready competition routes and hidden backend feeds',
      () {
        expect(
          GteAppRouteParser.parse('/competitions'),
          isA<CompetitionsDiscoveryRouteData>(),
        );
        expect(
          GteAppRouteParser.parse('/competitions/create'),
          isA<CompetitionCreateRouteData>(),
        );
        expect(
          GteAppRouteParser.parse('/competitions/world-super-cup'),
          isA<CompetitionWorldSuperCupRouteData>(),
        );
        expect(
          GteAppRouteParser.parse('/competitions/competition-1'),
          isA<CompetitionDetailRouteData>(),
        );

        final CompetitionJoinRouteData joinRoute =
            GteAppRouteParser.parse(
                  '/competitions/competition-1/join?inviteCode=invite-7',
                )
                as CompetitionJoinRouteData;
        expect(joinRoute.competitionId, 'competition-1');
        expect(joinRoute.inviteCode, 'invite-7');
        expect(
          GteAppRouteParser.parse('/competitions/competition-1/share'),
          isA<CompetitionShareRouteData>(),
        );

        for (final String backendFeedPath in <String>[
          '/competitions/competition-1/fixtures',
          '/competitions/competition-1/standings',
          '/competitions/competition-1/results',
          '/competitions/competition-1/bracket',
          '/competitions/competition-1/rounds',
          '/competitions/competition-1/matches/match-1/result',
        ]) {
          expect(
            GteAppRouteParser.parse(backendFeedPath),
            isNull,
            reason:
                '$backendFeedPath is backend-authored data for the competition detail surface, not a launch route.',
          );
        }

        final Set<String> registeredPaths =
            GteAppRouteCatalog.registrations
                .map((GteAppRouteRegistration route) => route.path)
                .toSet();
        expect(
          registeredPaths.where(
            (String path) =>
                path.contains('/fixtures') ||
                path.contains('/standings') ||
                path.contains('/results') ||
                path.contains('/bracket') ||
                path.contains('/rounds'),
          ),
          isEmpty,
        );
      },
    );

    test(
      'classifies streamer tournament routes as blocked launch surfaces',
      () {
        expect(
          GteAppRouteParser.parse('/competitions/streamer'),
          isA<StreamerTournamentsListRouteData>(),
        );
        expect(
          GteAppRouteParser.parse('/competitions/streamer/tournament-1'),
          isA<StreamerTournamentDetailRouteData>(),
        );
        expect(
          GteAppRouteParser.parse('/streamer-tournaments'),
          isA<StreamerTournamentsListRouteData>(),
        );
        expect(
          GteAppRouteParser.parse('/streamer-tournaments/tournament-1'),
          isA<StreamerTournamentDetailRouteData>(),
        );
      },
    );

    testWidgets(
      'renders streamer tournament engine routes',
      (WidgetTester tester) async {
        await tester.pumpWidget(
          _routeHost(const StreamerTournamentsListRouteData()),
        );
        await tester.pumpAndSettle();
        expect(find.text('Streamer tournament engine'), findsOneWidget);
        expect(find.text('Streamer tournaments coming soon'), findsNothing);

        await tester.pumpWidget(
          _routeHost(
            const StreamerTournamentDetailRouteData(
              tournamentId: 'tournament-1',
            ),
          ),
        );
        await tester.pumpAndSettle();
        expect(find.text('Streamer tournament engine'), findsOneWidget);
        expect(find.text('Streamer tournament detail coming soon'), findsNothing);
      },
    );
  });
}

Widget _routeHost(GteAppRouteData route) {
  const GteNavigationDependencies dependencies = GteNavigationDependencies(
    apiBaseUrl: 'https://example.test',
    backendMode: GteBackendMode.fixture,
    currentUserId: 'route-scope-user',
    currentUserName: 'Route Scope User',
    isAuthenticated: true,
  );
  const GteAppRouteRegistry registry = GteAppRouteRegistry(
    dependencies: dependencies,
  );
  return MaterialApp(
    home: Builder(
      builder: (BuildContext context) => registry.buildScreen(context, route),
    ),
  );
}
