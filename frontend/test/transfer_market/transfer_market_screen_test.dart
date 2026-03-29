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
      expect(find.text('Wallet & Compliance'), findsOneWidget);
      expect(find.text('Player Shares'), findsOneWidget);
      expect(find.text('Transfer Listings'), findsOneWidget);
      expect(find.text('Share Holdings'), findsOneWidget);
      expect(find.text('Cole Palmer'), findsWidgets);
      expect(find.text('William Saliba'), findsOneWidget);
      expect(
        find.text(
          'Bidding and watchlisting are blocked because this session has no verified club context.',
        ),
        findsOneWidget,
      );
    },
  );
}
