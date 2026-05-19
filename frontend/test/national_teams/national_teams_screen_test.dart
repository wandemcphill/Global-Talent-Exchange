import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/core/theme/app_theme.dart';
import 'package:gte_frontend/features/national_teams/live_national_teams_provider.dart';
import 'package:gte_frontend/features/national_teams/national_teams_screen.dart';
import 'package:gte_frontend/models/national_team_models.dart';
import 'package:gte_frontend/models/regen_universe_models.dart';

void main() {
  testWidgets('national teams screen marks preseeded regens as rental only', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          nationalTeamsHubProvider.overrideWith(
            (Ref ref) async => NationalTeamsHubData(
              competitions: <NationalTeamCompetition>[
                NationalTeamCompetition(
                  id: 'competition-1',
                  key: 'u17-world-cup',
                  title: 'GTEX U17 World Cup',
                  seasonLabel: '2031',
                  regionType: 'global',
                  ageBand: 'u17',
                  formatType: 'cup',
                  status: 'open',
                  notes: 'Live youth competition',
                  active: true,
                  createdAt: DateTime.utc(2031, 1, 1),
                  updatedAt: DateTime.utc(2031, 1, 2),
                ),
              ],
              rankings: const <NationalTeamCountryRankingRecord>[
                NationalTeamCountryRankingRecord(
                  countryCode: 'NG',
                  countryName: 'Nigeria',
                  eloRating: 1890,
                  matchesPlayed: 20,
                  wins: 13,
                  draws: 4,
                  losses: 3,
                  titles: 2,
                ),
              ],
              nationalRegens: const <NationalRegenSeed>[
                NationalRegenSeed(
                  id: 'seed-1',
                  seedKey: 'seed:ng:1',
                  displayName: 'Azeez Salisu',
                  age: 16,
                  ageBand: 'u17',
                  countryCode: 'NG',
                  countryName: 'Nigeria',
                  seedType: 'national_seed',
                  primaryPosition: 'RW',
                  currentRating: 71,
                  potentialRating: 90,
                  growthCurve: 0.82,
                  rarityTier: 'elite',
                  status: 'active',
                  metadata: <String, Object?>{},
                  marketEligible: false,
                  shareMarketEligible: false,
                  tradable: false,
                  buyable: false,
                  transferable: false,
                  cardMintEligible: false,
                  buyCtaAllowed: false,
                  isPreseededNationalRegen: true,
                  nationalPoolOnly: true,
                ),
              ],
              regenScoutingFeed: <RegenScoutingFeedItem>[
                RegenScoutingFeedItem(
                  feedId: 'feed-1',
                  feedType: 'hidden_gem',
                  title: 'Scouts found a Lagos winger',
                  summary: 'National scouts flagged elite winger upside.',
                  occurredAt: DateTime.utc(2031, 1, 3),
                  importance: 0.88,
                  badges: const <String>['hidden_gem', 'national_pool'],
                ),
              ],
              history: null,
            ),
          ),
        ],
        child: MaterialApp(
          theme: AppTheme.dark(),
          home: const Scaffold(body: NationalTeamsScreen()),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Azeez Salisu'), findsWidgets);
    expect(find.text('National Pool'), findsOneWidget);
    expect(find.text('Rental Only'), findsOneWidget);
    expect(find.text('Not Tradable'), findsOneWidget);
    expect(find.text('Regen scouting'), findsOneWidget);
    expect(find.text('Scouts found a Lagos winger'), findsOneWidget);
    expect(find.widgetWithText(FilledButton, 'Buy'), findsNothing);
  });
}
