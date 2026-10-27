@Tags(<String>['golden'])
library;

import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/transfer_center/live_transfer_center_provider.dart';
import 'package:gte_frontend/features/transfer_center/presentation/gtex_transfers_hub_panel.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

const String _out = '../../../design-concepts/public/implemented';
const Key _frame = ValueKey<String>('capture-frame');

const Size _desktop = Size(1440, 1000);
const Size _mobile = Size(390, 844);

Future<ByteData> _fontFile(String path) async =>
    ByteData.sublistView(Uint8List.fromList(File(path).readAsBytesSync()));

Future<void> _loadFonts() async {
  final Map<String, List<String>> families = <String, List<String>>{
    'Inter': <String>['assets/fonts/Inter.ttf'],
    'BarlowCondensed': <String>[
      'assets/fonts/BarlowCondensed-Regular.ttf',
      'assets/fonts/BarlowCondensed-SemiBold.ttf',
      'assets/fonts/BarlowCondensed-Bold.ttf',
    ],
    'DMMono': <String>[
      'assets/fonts/DMMono-Regular.ttf',
      'assets/fonts/DMMono-Medium.ttf',
    ],
  };

  for (final MapEntry<String, List<String>> entry in families.entries) {
    final FontLoader loader = FontLoader(entry.key);
    for (final String path in entry.value) {
      if (File(path).existsSync()) {
        loader.addFont(_fontFile(path));
      }
    }
    await loader.load();
  }
}

Future<void> _capture(
  WidgetTester tester, {
  required String name,
  required Size size,
  required Widget child,
}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.reset);
  try {
    await tester.pumpWidget(RepaintBoundary(key: _frame, child: child));
    for (int i = 0; i < 30; i += 1) {
      await tester.pump(const Duration(milliseconds: 50));
    }
    while (tester.takeException() != null) {}
    await expectLater(find.byKey(_frame), matchesGoldenFile('$_out/$name.png'));
  } finally {}
}

Widget _transfersWidget() {
  final List<TransferCenterListingRecord> listings =
      <TransferCenterListingRecord>[
        const TransferCenterListingRecord(
          id: 'listing-1',
          playerId: 'player-osimhen',
          playerName: 'Victor Osimhen',
          sellingClubId: 'club-galata',
          currentClubName: 'Galatasaray',
          basePrice: 75000000,
          currentHighestBid: 82000000,
          highestBidderId: 'club-lagos',
          status: 'open',
          watchlistCount: 14,
          bidCount: 5,
          marketSignal: 'World Class Striker in Peak Demand',
          channel: 'market:listing-1',
          timeRemaining: 18400,
          negotiationId: 'neg-1',
          bidders: <Map<String, Object?>>[],
        ),
        const TransferCenterListingRecord(
          id: 'listing-2',
          playerId: 'player-lookman',
          playerName: 'Ademola Lookman',
          sellingClubId: 'club-atalanta',
          currentClubName: 'Atalanta',
          basePrice: 55000000,
          currentHighestBid: 60000000,
          highestBidderId: 'club-lagos',
          status: 'open',
          watchlistCount: 9,
          bidCount: 2,
          marketSignal: 'Ballon d\'Or Nominated Winger',
          channel: 'market:listing-2',
          timeRemaining: 9200,
          negotiationId: 'neg-2',
          bidders: <Map<String, Object?>>[],
        ),
      ];

  final List<TransferHubOfferRecord> offers = <TransferHubOfferRecord>[
    const TransferHubOfferRecord(
      id: 'offer-open',
      listingId: 'listing-1',
      offerType: 'transfer',
      sellerClubId: 'club-lagos',
      bidderClubId: 'club-accra',
      cashAmount: 82000000,
      sellOnPercentage: 15,
      status: 'open',
      playerId: 'player-osimhen',
      playerName: 'Victor Osimhen',
      message: 'Structured sporting transfer proposal: 82M GTC upfront + 15% sell-on',
    ),
    const TransferHubOfferRecord(
      id: 'offer-accepted',
      listingId: 'listing-2',
      offerType: 'loan_to_buy',
      sellerClubId: 'club-lagos',
      bidderClubId: 'club-cairo',
      cashAmount: 45000000,
      status: 'accepted',
      playerId: 'player-lookman',
      playerName: 'Ademola Lookman',
      resolvedAt: '2026-10-22',
    ),
  ];

  final List<TransferNegotiationRecord> negotiations =
      <TransferNegotiationRecord>[
        const TransferNegotiationRecord(
          id: 'neg-active',
          listingId: 'listing-1',
          playerId: 'player-osimhen',
          playerName: 'Victor Osimhen',
          sellingClubId: 'club-galata',
          bidderClubId: 'club-lagos',
          status: 'awaiting_contract_offer',
          wageOfferAmount: 220000,
          contractYears: 4,
          expectedRole: 'Key Striker',
          playerInterestLevel: 'high',
          coachStance: 'approve',
          coachReason: 'Essential focal point for tactical progression.',
          agentAction: 'counter_offer',
          concerns: <String>['Performance bonus structure requested'],
        ),
      ];

  final List<TransferShortlistEntryRecord> shortlist =
      <TransferShortlistEntryRecord>[
        const TransferShortlistEntryRecord(
          id: 'short-1',
          clubId: 'club-lagos',
          playerId: 'player-osimhen',
          playerName: 'Victor Osimhen',
          source: 'scouting',
          discoveryScore: 94,
          listingId: 'listing-1',
          estimatedFeeCredits: 75000000,
        ),
        const TransferShortlistEntryRecord(
          id: 'short-2',
          clubId: 'club-lagos',
          playerId: 'player-adeyemi',
          playerName: 'Tobi Adeyemi',
          source: 'regen_scouting',
          discoveryScore: 89,
          estimatedFeeCredits: 18000,
        ),
      ];

  return MaterialApp(
    debugShowCheckedModeBanner: false,
    theme: ThemeData.dark().copyWith(
      scaffoldBackgroundColor: GtexColors.surfaceBase,
    ),
    home: Scaffold(
      backgroundColor: GtexColors.surfaceBase,
      body: SingleChildScrollView(
        child: GtexTransfersHubPanel(
          activeClubId: 'club-lagos',
          listings: listings,
          offers: offers,
          negotiations: negotiations,
          shortlist: shortlist,
        ),
      ),
    ),
  );
}

void main() {
  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    await _loadFonts();
  });

  testWidgets('capture transfers hub desktop', (WidgetTester tester) async {
    await _capture(
      tester,
      name: 'flutter-transfers-hub-desktop',
      size: _desktop,
      child: _transfersWidget(),
    );
  });

  testWidgets('capture transfers hub mobile', (WidgetTester tester) async {
    await _capture(
      tester,
      name: 'flutter-transfers-hub-mobile',
      size: _mobile,
      child: _transfersWidget(),
    );
  });
}
