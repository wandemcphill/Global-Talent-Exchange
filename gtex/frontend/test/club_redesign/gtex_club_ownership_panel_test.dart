import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/club_redesign/models/gtex_club_ownership_models.dart';
import 'package:gte_frontend/features/club_redesign/widgets/gtex_club_ownership_panel.dart';

Widget _host(Widget child) => MaterialApp(
      home: Scaffold(
        body: SingleChildScrollView(child: child),
      ),
    );

void main() {
  testWidgets('empty book states "you don\'t own part of any club yet" and shows no zero', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _host(
        GtexClubOwnershipPanel(portfolio: GtexClubOwnershipPortfolio.empty()),
      ),
    );

    expect(
      find.text('You don’t own part of any club yet'),
      findsOneWidget,
    );
    expect(find.textContaining('0%'), findsNothing);
    expect(find.textContaining('0.00 coin'), findsNothing);
  });

  testWidgets('populated book renders the stake in football language', (
    WidgetTester tester,
  ) async {
    const GtexClubOwnershipPortfolio portfolio = GtexClubOwnershipPortfolio(
      clubCount: 1,
      totalMarketValueCoin: 39.6,
      totalCostBasisCoin: 30,
      totalUnrealizedPlCoin: 9.6,
      holdings: <GtexClubShareHolding>[
        GtexClubShareHolding(
          clubId: 'club-1',
          clubName: 'Port Harcourt Dynamos',
          sharesOwned: 30,
          averagePriceCoin: 1,
          sharePriceCoin: 1.32,
          marketValueCoin: 39.6,
          costBasisCoin: 30,
          unrealizedPlCoin: 9.6,
          unrealizedPlPercent: 32,
          ownershipPercent: 3,
          holderCount: 12,
          performanceScore: 0.42,
          winRate: 0.6,
          fanDemandScore: 0.18,
          governanceEnabled: true,
        ),
      ],
    );

    await tester.pumpWidget(_host(const GtexClubOwnershipPanel(portfolio: portfolio)));

    expect(find.text('Port Harcourt Dynamos'), findsOneWidget);
    expect(
      find.textContaining('You own 30 shares'),
      findsOneWidget,
    );
    expect(find.textContaining('Share price is moving on'), findsOneWidget);
  });

  testWidgets('a club with no settled matches does not claim performance is driving price', (
    WidgetTester tester,
  ) async {
    const GtexClubOwnershipPortfolio portfolio = GtexClubOwnershipPortfolio(
      clubCount: 1,
      totalMarketValueCoin: 5,
      totalCostBasisCoin: 5,
      totalUnrealizedPlCoin: 0,
      holdings: <GtexClubShareHolding>[
        GtexClubShareHolding(
          clubId: 'club-2',
          clubName: 'Kano Comets',
          sharesOwned: 5,
          averagePriceCoin: 1,
          sharePriceCoin: 1,
          marketValueCoin: 5,
          costBasisCoin: 5,
          unrealizedPlCoin: 0,
          holderCount: 1,
        ),
      ],
    );

    await tester.pumpWidget(_host(const GtexClubOwnershipPanel(portfolio: portfolio)));

    expect(
      find.text('No settled GTEX matches yet — the share price sits at its base.'),
      findsOneWidget,
    );
    expect(find.textContaining('Share price is moving on'), findsNothing);
  });

  testWidgets('error with an empty book renders a blocked state with retry', (
    WidgetTester tester,
  ) async {
    int retries = 0;
    await tester.pumpWidget(
      _host(
        GtexClubOwnershipPanel(
          portfolio: GtexClubOwnershipPortfolio.empty(),
          errorMessage: 'Club ownership service is unavailable.',
          onRetry: () => retries += 1,
        ),
      ),
    );

    expect(find.text('Club ownership unavailable'), findsOneWidget);
    await tester.tap(find.text('Retry'));
    expect(retries, 1);
  });
}
