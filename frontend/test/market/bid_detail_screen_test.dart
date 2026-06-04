import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/market/presentation/widgets/market_models.dart';
import 'package:gte_frontend/features/market/presentation/widgets/market_widgets.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('bid timeline renders lifecycle statuses and reservation truth', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: Scaffold(
          body: SingleChildScrollView(
            child: BidEventTimeline(
              bids: <MarketBidViewModel>[
                _bid(
                  id: 'bid-pending',
                  status: 'pending',
                  reservationStatus: 'reserved',
                  reservedAmount: 91,
                  reservationReference: 'transfer-market-bid:bid-pending',
                ),
                _bid(id: 'bid-counter', status: 'counter'),
                _bid(id: 'bid-accepted', status: 'accepted'),
                _bid(id: 'bid-rejected', status: 'rejected'),
                _bid(id: 'bid-withdrawn', status: 'withdrawn'),
              ],
            ),
          ),
        ),
      ),
    );

    expect(find.text('Pending'), findsOneWidget);
    expect(find.text('Counter'), findsOneWidget);
    expect(find.text('Accepted'), findsOneWidget);
    expect(find.text('Rejected'), findsOneWidget);
    expect(find.text('Withdrawn'), findsOneWidget);
    expect(find.text('Status: reserved'), findsOneWidget);
    expect(find.text('Reserved amount: 91 GTex'), findsOneWidget);
    expect(
      find.text('Reference: transfer-market-bid:bid-pending'),
      findsOneWidget,
    );
    expect(
      find.text('Status: Reservation not reported by backend'),
      findsWidgets,
    );
  });
}

MarketBidViewModel _bid({
  required String id,
  required String status,
  String? reservationStatus,
  double? reservedAmount,
  String? reservationReference,
}) {
  return MarketBidViewModel(
    id: id,
    clubId: 'club-$id',
    clubName: 'Club $id',
    amount: 91,
    status: marketBidLifecycleStatusFrom(status),
    statusLabel: status,
    isHighest: id == 'bid-pending',
    timestamp: DateTime.utc(2026, 6, 2),
    walletReservationStatus: reservationStatus,
    walletReservedAmount: reservedAmount,
    walletReservationReference: reservationReference,
  );
}
