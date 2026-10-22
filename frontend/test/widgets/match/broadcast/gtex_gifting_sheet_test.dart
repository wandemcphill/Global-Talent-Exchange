import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/match_gift_api.dart';
import 'package:gte_frontend/widgets/match/broadcast/gtex_gifting_sheet.dart';

void main() {
  const List<MatchGiftCatalogItem> catalog = <MatchGiftCatalogItem>[
    MatchGiftCatalogItem(
      key: 'fan_chant',
      label: 'Fan Chant',
      description: 'Bring the terraces to life.',
      fanCoinAmount: 2,
      currencyLabel: 'Fan Coin',
      rarity: 'common',
    ),
    MatchGiftCatalogItem(
      key: 'legend_card_reveal',
      label: 'Legend Card Reveal',
      description: 'A premium player-card reveal.',
      fanCoinAmount: 150,
      currencyLabel: 'Fan Coin',
      rarity: 'epic',
    ),
    MatchGiftCatalogItem(
      key: 'ballon_dor',
      label: 'Ballon d’Or',
      description: 'A full ceremony for the ultimate football gift.',
      fanCoinAmount: 10000,
      currencyLabel: 'Fan Coin',
      rarity: 'mythic',
      legalStatus: 'requires_review',
    ),
  ];

  setUp(() {
    TestWidgetsFlutterBinding.ensureInitialized();
  });

  testWidgets('presents the canonical catalogue and sends the selected gift', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(430, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    String? sentGiftKey;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Builder(
            builder: (BuildContext context) => TextButton(
              key: const Key('open-gift-lounge'),
              onPressed: () => GtexGiftingSheet.show(
                context,
                recipientLabel: 'Sample Player',
                catalogLoader: () async => catalog,
                onSelected: (MatchGiftCatalogItem gift) async {
                  sentGiftKey = gift.key;
                },
              ),
              child: const Text('Gift'),
            ),
          ),
        ),
      ),
    );
    await tester.tap(find.byKey(const Key('open-gift-lounge')));
    await tester.pumpAndSettle();

    expect(find.text('THE GIFT LOUNGE'), findsOneWidget);
    expect(find.text('Sending to Sample Player'), findsOneWidget);
    expect(find.byKey(const Key('gtex-gift-card-fan_chant')), findsOneWidget);
    expect(find.byKey(const Key('gtex-gift-card-legend_card_reveal')), findsOneWidget);

    await tester.tap(find.byKey(const Key('gtex-gift-card-fan_chant')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('gtex-gift-send-button')));
    await tester.pumpAndSettle();

    expect(sentGiftKey, equals('fan_chant'));
  });

  testWidgets('a gift requiring review cannot be sent', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(430, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    String? sentGiftKey;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Builder(
            builder: (BuildContext context) => TextButton(
              onPressed: () => GtexGiftingSheet.show(
                context,
                catalogLoader: () async => catalog,
                onSelected: (MatchGiftCatalogItem gift) async {
                  sentGiftKey = gift.key;
                },
              ),
              child: const Text('Gift'),
            ),
          ),
        ),
      ),
    );
    await tester.tap(find.text('Gift'));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('gtex-gift-card-ballon_dor')));
    await tester.pumpAndSettle();

    expect(find.text('Under review'), findsOneWidget);
    expect(tester.widget<FilledButton>(find.byKey(const Key('gtex-gift-send-button'))).onPressed, isNull);
    expect(sentGiftKey, isNull);
  });
}
