import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/features/transfer_market/live_market_provider.dart';
import 'package:gte_frontend/features/transfer_market/transfer_market_screen.dart';
import 'package:gte_frontend/shared/models/auth_session.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';

void main() {
  testWidgets(
    'market screen keeps wallet, shares, listings, and holdings segmented',
    (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authProvider.overrideWith(
              (Ref ref) => const AuthSession(
                userId: 'user-1',
                accessToken: 'token-1',
                refreshToken: 'refresh-1',
                sessionId: 'session-1',
                role: 'user',
              ),
            ),
            marketDashboardProvider.overrideWith((Ref ref) async {
              return const MarketDashboardData(
                playerShares: <PlayerShareSummary>[
                  PlayerShareSummary(
                    playerId: 'player-1',
                    playerName: 'Cole Palmer',
                    position: 'AM',
                    nationality: 'England',
                    currentClubName: 'Chelsea',
                    age: 24,
                    currentValueCredits: 1250,
                    marketInterestScore: 91,
                    marketStatus: 'active',
                    marketMessage: 'Share market is live.',
                    sharePriceCoin: 16,
                    totalShares: 1000,
                    circulatingShares: 700,
                  ),
                  PlayerShareSummary(
                    playerId: 'player-3',
                    playerName: 'Lamine Yamal',
                    position: 'RW',
                    nationality: 'Spain',
                    currentClubName: 'Barcelona',
                    age: 18,
                    currentValueCredits: 1325,
                    marketInterestScore: 98,
                    marketStatus: 'unissued',
                    marketMessage: 'Market initializing.',
                  ),
                ],
                holdings: <PlayerShareHoldingSummary>[
                  PlayerShareHoldingSummary(
                    playerId: 'player-1',
                    shareCount: 12,
                    averageCostCoin: 14,
                    dividendsEarnedCoin: 24,
                  ),
                ],
                transferListings: <TransferListingSummary>[
                  TransferListingSummary(
                    id: 'listing-1',
                    playerId: 'player-2',
                    playerName: 'William Saliba',
                    currentClubName: 'Arsenal',
                    currentHighestBid: 82,
                    basePrice: 70,
                    status: 'open',
                    watchlistCount: 4,
                    bidCount: 2,
                    marketSignal: 'Live transfer listing',
                    channel: 'market:listing-1',
                    timeRemaining: 600,
                  ),
                ],
                wallet: MarketWalletSnapshot(
                  coinBalance: 120,
                  creditBalance: 40,
                  totalEquity: 160,
                  canTradeMarket: true,
                  canDeposit: true,
                  canWithdraw: true,
                  complianceMessage:
                      'Wallet and compliance state loaded from live backend.',
                ),
                authenticated: true,
                warnings: <String>[],
              );
            }),
          ],
          child: const MaterialApp(
            home: Scaffold(body: TransferMarketScreen()),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('Market'), findsOneWidget);
      await _scrollTo(tester, find.text('Wallet & Compliance'));
      expect(find.text('Wallet & Compliance'), findsOneWidget);
      await _scrollTo(tester, find.text('Player Shares'));
      expect(find.text('Player Shares'), findsOneWidget);
      expect(find.text('Search-only real players'), findsOneWidget);
      await _scrollTo(tester, find.text('Transfer Listings'));
      expect(find.text('Transfer Listings'), findsOneWidget);
      await _scrollTo(tester, find.text('Share Holdings'));
      expect(find.text('Share Holdings'), findsOneWidget);
      expect(find.text('Cole Palmer'), findsWidgets);
      expect(find.text('Lamine Yamal'), findsWidgets);
      expect(find.text('William Saliba'), findsOneWidget);
      expect(
        find.text('Verified club context required for transfer actions'),
        findsOneWidget,
      );
      expect(find.widgetWithText(FilledButton, 'Buy'), findsOneWidget);
    },
  );

  testWidgets('market screen exposes sign-in recovery in preview mode', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          authProvider.overrideWith((Ref ref) => null),
          marketDashboardProvider.overrideWith((Ref ref) async {
            return const MarketDashboardData(
              playerShares: <PlayerShareSummary>[
                PlayerShareSummary(
                  playerId: 'player-1',
                  playerName: 'Jude Bellingham',
                  position: 'CM',
                  nationality: 'England',
                  currentClubName: 'Real Madrid',
                  age: 22,
                  currentValueCredits: 1500,
                  marketInterestScore: 96,
                  marketStatus: 'active',
                  marketMessage: 'Share market is live.',
                  sharePriceCoin: 22,
                  totalShares: 1000,
                  circulatingShares: 810,
                ),
              ],
              holdings: <PlayerShareHoldingSummary>[],
              transferListings: <TransferListingSummary>[
                TransferListingSummary(
                  id: 'listing-1',
                  playerId: 'player-2',
                  playerName: 'Victor Osimhen',
                  currentClubName: 'Napoli',
                  currentHighestBid: 95,
                  basePrice: 84,
                  status: 'open',
                  watchlistCount: 6,
                  bidCount: 3,
                  marketSignal: 'Live transfer listing',
                  channel: 'market:listing-1',
                  timeRemaining: 900,
                ),
              ],
              wallet: null,
              authenticated: false,
              warnings: <String>[],
            );
          }),
        ],
        child: const MaterialApp(home: Scaffold(body: TransferMarketScreen())),
      ),
    );

    await tester.pumpAndSettle();

    await _scrollTo(tester, find.text('Resolve market access'));
    expect(find.text('Resolve market access'), findsOneWidget);
    expect(find.text('Sign in to unlock market access'), findsOneWidget);
    expect(find.widgetWithText(FilledButton, 'Sign in'), findsWidgets);
    await _scrollTo(tester, find.text('Sign in to bid on transfer listings'));
    expect(find.text('Sign in to bid on transfer listings'), findsOneWidget);
  });
}

Future<void> _scrollTo(WidgetTester tester, Finder finder) async {
  await tester.scrollUntilVisible(
    finder,
    240,
    scrollable: find.byType(Scrollable).first,
  );
  await tester.pumpAndSettle();
}
