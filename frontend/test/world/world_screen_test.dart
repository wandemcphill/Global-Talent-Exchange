import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:gte_frontend/core/theme/app_theme.dart';
import 'package:gte_frontend/features/competitions/live_competitions_provider.dart';
import 'package:gte_frontend/features/streamer_tournament_engine/data/streamer_tournament_engine_models.dart';
import 'package:gte_frontend/features/world/live_world_provider.dart';
import 'package:gte_frontend/features/world/world_screen.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/hosted_competition_models.dart';

void main() {
  testWidgets('loads world summaries and federation links', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1280, 1800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    const CompetitionHubData emptyHub = CompetitionHubData(
      gtexCompetitions: <CompetitionSummary>[],
      hostedCompetitions: <HostedCompetition>[],
      streamerTournaments: <StreamerTournament>[],
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          worldAggregateProvider.overrideWith((Ref ref) async {
            return const WorldAggregateData(
              risingStars: <Map<String, Object?>>[
                <String, Object?>{
                  'player_name': 'Ayo Akin',
                  'position': 'ST',
                  'nationality': 'Nigeria',
                },
              ],
              scoutingFeed: <Map<String, Object?>>[
                <String, Object?>{
                  'headline': 'Ayo Akin spikes in scouting feed',
                },
              ],
              seasons: <Map<String, Object?>>[
                <String, Object?>{'name': '2031 season'},
              ],
              awards: <Map<String, Object?>>[
                <String, Object?>{'name': 'Golden Regen'},
              ],
              hallOfFame: <Map<String, Object?>>[
                <String, Object?>{'player_name': 'Legend One'},
              ],
              federations: <Map<String, Object?>>[
                <String, Object?>{
                  'id': 'west-africa',
                  'name': 'West Africa Federation',
                },
              ],
              tracking: <String, Object?>{'season_phase': 'midseason'},
              competitions: emptyHub,
              federationJoinReason:
                  'Federation membership is blocked: this session has no verified club context.',
            );
          }),
        ],
        child: MaterialApp(
          theme: AppTheme.dark(),
          home: const Scaffold(body: WorldScreen()),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('World route'), findsOneWidget);
    expect(find.text('Competition families'), findsOneWidget);
    expect(find.text('Rising stars'), findsOneWidget);
    expect(find.text('Federations'), findsOneWidget);
    expect(find.widgetWithText(FilledButton, 'Open federations hub'), findsOneWidget);

    await tester.scrollUntilVisible(
      find.text('Ayo Akin'),
      240,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pumpAndSettle();
    expect(find.text('Ayo Akin'), findsOneWidget);

    await tester.scrollUntilVisible(
      find.text('West Africa Federation'),
      240,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pumpAndSettle();
    expect(find.text('West Africa Federation'), findsOneWidget);
    expect(find.widgetWithText(FilledButton, 'Open'), findsWidgets);
  });
}
