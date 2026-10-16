import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/domain/ownership/gtex_ownership_models.dart';
import 'package:gte_frontend/features/club_redesign/models/gtex_club_ownership_models.dart';
import 'package:gte_frontend/screens/wallet/gtex_ownership_experience.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

GtePortfolioHolding _holding({
  required String id,
  required String name,
  required String club,
  double qty = 2,
  double avg = 10,
  double price = 12,
  double value = 24,
  double pl = 4,
  double plPct = 20,
}) {
  return GtePortfolioHolding.fromJson(<String, Object?>{
    'player_id': id,
    'player_name': name,
    'club_name': club,
    'quantity': qty.toString(),
    'average_cost': avg.toString(),
    'current_price': price.toString(),
    'market_value': value.toString(),
    'unrealized_pl': pl.toString(),
    'unrealized_pl_percent': plPct.toString(),
  });
}

GtexOwnershipBook _book(List<GtePortfolioHolding> holdings) =>
    GtexOwnershipBook.fromPortfolio(GtePortfolioView(holdings: holdings));

Future<void> _pump(
  WidgetTester tester,
  Widget child, {
  double width = 1024,
}) async {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = Size(width, 4000);
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(
    MaterialApp(
      theme: GteShellTheme.build(),
      home: Scaffold(body: child),
    ),
  );
  await tester.pump(const Duration(milliseconds: 50));
}

void main() {
  testWidgets('empty squad and no club shares states the truth', (
    WidgetTester tester,
  ) async {
    await _pump(
      tester,
      GtexOwnershipExperience(book: GtexOwnershipBook.empty()),
    );
    expect(find.text('Your squad is empty'), findsOneWidget);
    // No fabricated zeros anywhere.
    expect(find.textContaining('0.0%'), findsNothing);
    expect(find.text('MY SQUAD'), findsNothing);
  });

  testWidgets('load error shows a blocked state with retry, not a spreadsheet', (
    WidgetTester tester,
  ) async {
    await _pump(
      tester,
      GtexOwnershipExperience(
        book: GtexOwnershipBook.empty(),
        portfolioError: 'Network unreachable',
        onRetry: () async {},
      ),
    );
    expect(find.text('Squad could not be loaded'), findsOneWidget);
    expect(find.text('Retry'), findsOneWidget);
  });

  testWidgets('one holding renders as a player identity with its stake', (
    WidgetTester tester,
  ) async {
    await _pump(
      tester,
      GtexOwnershipExperience(
        book: _book(<GtePortfolioHolding>[
          _holding(id: 'a', name: 'Ada Obi', club: 'Enyimba FC'),
        ]),
      ),
    );
    expect(find.text('Ada Obi'), findsOneWidget);
    expect(find.text('MY SQUAD'), findsOneWidget);
    expect(find.textContaining('YOU OWN 2 SHARES'), findsOneWidget);
    expect(find.text('Enyimba FC'), findsWidgets);
  });

  testWidgets('multiple holdings group by club', (WidgetTester tester) async {
    await _pump(
      tester,
      GtexOwnershipExperience(
        book: _book(<GtePortfolioHolding>[
          _holding(id: 'a', name: 'Ada Obi', club: 'Enyimba FC', value: 40),
          _holding(id: 'b', name: 'Bala Sule', club: 'Enyimba FC', value: 20),
          _holding(id: 'c', name: 'Chidi Eze', club: 'Rangers Intl', value: 10),
        ]),
      ),
    );
    expect(find.text('Ada Obi'), findsOneWidget);
    // Two clubs -> two group headers, Enyimba first (higher combined value).
    expect(find.text('Enyimba FC'), findsWidgets);
    expect(find.text('Rangers Intl'), findsWidgets);
    await tester.scrollUntilVisible(
      find.text('Chidi Eze'),
      400,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.text('Chidi Eze'), findsOneWidget);
  });

  testWidgets('a losing position is coloured and labelled as such', (
    WidgetTester tester,
  ) async {
    await _pump(
      tester,
      GtexOwnershipExperience(
        book: _book(<GtePortfolioHolding>[
          _holding(
            id: 'a',
            name: 'Ada Obi',
            club: 'Enyimba FC',
            price: 8,
            value: 16,
            pl: -4,
            plPct: -20,
          ),
        ]),
      ),
    );
    expect(find.textContaining('-20.0%'), findsWidgets);
  });

  testWidgets('mark-pending position never shows a fake P/L', (
    WidgetTester tester,
  ) async {
    await _pump(
      tester,
      GtexOwnershipExperience(
        book: _book(<GtePortfolioHolding>[
          _holding(
            id: 'a',
            name: 'Ada Obi',
            club: 'Enyimba FC',
            avg: 0,
            price: 0,
            value: 0,
            pl: 0,
            plPct: 0,
          ),
        ]),
      ),
    );
    expect(find.text('Mark pending'), findsOneWidget);
    expect(find.textContaining('0.0%'), findsNothing);
  });

  testWidgets('tapping a holding routes through the provided player opener', (
    WidgetTester tester,
  ) async {
    String? opened;
    await _pump(
      tester,
      GtexOwnershipExperience(
        book: _book(<GtePortfolioHolding>[
          _holding(id: 'plr_42', name: 'Ada Obi', club: 'Enyimba FC'),
        ]),
        onOpenPlayer: (String id) => opened = id,
      ),
    );
    await tester.tap(find.text('Ada Obi'));
    await tester.pump();
    expect(opened, 'plr_42');
  });

  testWidgets('club-share holdings render as an explicit section', (
    WidgetTester tester,
  ) async {
    const GtexClubShareHolding lagos = GtexClubShareHolding(
      clubId: 'club-lagos',
      clubName: 'Lagos Eclipse FC',
      sharesOwned: 40,
      averagePriceCoin: 1,
      sharePriceCoin: 1.3,
      marketValueCoin: 52,
      costBasisCoin: 40,
      unrealizedPlCoin: 12,
      unrealizedPlPercent: 30,
      performanceScore: 0.4,
      winRate: 0.6,
    );
    await _pump(
      tester,
      GtexOwnershipExperience(
        book: GtexOwnershipBook.empty(),
        clubOwnership: const GtexClubOwnershipPortfolio(
          clubCount: 1,
          totalMarketValueCoin: 52,
          totalCostBasisCoin: 40,
          totalUnrealizedPlCoin: 12,
          holdings: <GtexClubShareHolding>[lagos],
        ),
      ),
    );
    expect(find.text('MY CLUB INTERESTS'), findsOneWidget);
    expect(find.text('Lagos Eclipse FC'), findsOneWidget);
    expect(find.textContaining('40 shares'), findsOneWidget);
  });

  testWidgets('club-share performance signal is honest when there is no history', (
    WidgetTester tester,
  ) async {
    const GtexClubShareHolding flat = GtexClubShareHolding(
      clubId: 'club-x',
      clubName: 'Kano Pillars',
      sharesOwned: 10,
      averagePriceCoin: 1,
      sharePriceCoin: 1,
      marketValueCoin: 10,
      costBasisCoin: 10,
      unrealizedPlCoin: 0,
    );
    await _pump(
      tester,
      GtexOwnershipExperience(
        book: GtexOwnershipBook.empty(),
        clubOwnership: const GtexClubOwnershipPortfolio(
          clubCount: 1,
          totalMarketValueCoin: 10,
          totalCostBasisCoin: 10,
          totalUnrealizedPlCoin: 0,
          holdings: <GtexClubShareHolding>[flat],
        ),
      ),
    );
    expect(
      find.text('No settled GTEX matches behind this price yet.'),
      findsOneWidget,
    );
  });

  testWidgets('club-share sync failure is surfaced without hiding the squad', (
    WidgetTester tester,
  ) async {
    await _pump(
      tester,
      GtexOwnershipExperience(
        book: _book(<GtePortfolioHolding>[
          _holding(id: 'a', name: 'Ada Obi', club: 'Enyimba FC'),
        ]),
        clubError: 'Club interests could not be synced right now.',
      ),
    );
    expect(find.text('Ada Obi'), findsOneWidget);
    expect(find.text('Club interests unavailable'), findsOneWidget);
  });

  for (final double width in <double>[360, 420, 768, 1024, 1440]) {
    testWidgets('renders without overflow at ${width.toInt()}px', (
      WidgetTester tester,
    ) async {
      await _pump(
        tester,
        GtexOwnershipExperience(
          book: _book(<GtePortfolioHolding>[
            _holding(id: 'a', name: 'Ada Obi', club: 'Enyimba FC', value: 40),
            _holding(id: 'b', name: 'Bala Sule', club: 'Rangers Intl', value: 20),
          ]),
          clubOwnership: const GtexClubOwnershipPortfolio(
            clubCount: 1,
            totalMarketValueCoin: 52,
            totalCostBasisCoin: 40,
            totalUnrealizedPlCoin: 12,
            holdings: <GtexClubShareHolding>[
              GtexClubShareHolding(
                clubId: 'c',
                clubName: 'Lagos Eclipse FC',
                sharesOwned: 40,
                averagePriceCoin: 1,
                sharePriceCoin: 1.3,
                marketValueCoin: 52,
                costBasisCoin: 40,
                unrealizedPlCoin: 12,
              ),
            ],
          ),
        ),
        width: width,
      );
      expect(tester.takeException(), isNull);
    });
  }
}
