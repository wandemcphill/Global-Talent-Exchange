import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/match_gift_api.dart';
import 'package:gte_frontend/widgets/match/broadcast/gtex_gifting_sheet.dart';

void main() {
  const List<MatchGiftCatalogItem> catalog = <MatchGiftCatalogItem>[
    MatchGiftCatalogItem(
      key: 'fan_chant',
      label: 'Fan Chant',
      description: 'A chant from the stands.',
      fanCoinAmount: 2,
      rarity: 'common',
    ),
    MatchGiftCatalogItem(
      key: 'legend_card_reveal',
      label: 'Legend Card Reveal',
      description: 'A premium card reveal.',
      fanCoinAmount: 150,
      rarity: 'epic',
    ),
    MatchGiftCatalogItem(
      key: 'ballon_dor',
      label: 'Ballon d’Or',
      description: 'The ultimate ceremony.',
      fanCoinAmount: 10000,
      rarity: 'mythic',
      legalStatus: 'requires_review',
    ),
    MatchGiftCatalogItem(
      key: 'pending_review_crown',
      label: 'Crown Ceremony',
      description: 'A pending-review premium celebration.',
      fanCoinAmount: 2500,
      rarity: 'epic',
      legalStatus: 'pending_review',
    ),
  ];

  testWidgets('selects a catalogue gift and submits it to the intended recipient',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(430, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    String? sentKey;
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: Builder(builder: (BuildContext context) => TextButton(
          key: const Key('open-gift-lounge'),
          onPressed: () => GtexGiftingSheet.show(
            context,
            recipientLabel: 'Sample Player',
            catalogLoader: () async => catalog,
            onSelected: (MatchGiftCatalogItem gift) async => sentKey = gift.key,
          ),
          child: const Text('Gift'),
        )),
      ),
    ));
    await tester.tap(find.byKey(const Key('open-gift-lounge')));
    await tester.pumpAndSettle();
    expect(find.text('THE GIFT LOUNGE'), findsOneWidget);
    expect(find.text('Sending to Sample Player'), findsOneWidget);
    await tester.tap(find.byKey(const Key('gtex-gift-card-fan_chant')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('gtex-gift-send-button')));
    await tester.pumpAndSettle();
    expect(sentKey, 'fan_chant');
  });

  testWidgets('blocks gifts flagged for legal review', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(430, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    String? sentKey;
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: Builder(builder: (BuildContext context) => TextButton(
          onPressed: () => GtexGiftingSheet.show(
            context,
            catalogLoader: () async => catalog,
            onSelected: (MatchGiftCatalogItem gift) async => sentKey = gift.key,
          ),
          child: const Text('Gift'),
        )),
      ),
    ));
    await tester.tap(find.text('Gift'));
    await tester.pumpAndSettle();
    for (final String key in <String>[
      'ballon_dor',
      'pending_review_crown',
    ]) {
      final Finder giftCard = find.byKey(Key('gtex-gift-card-$key'));
      await tester.ensureVisible(giftCard);
      await tester.pumpAndSettle();
      await tester.tap(giftCard);
      await tester.pumpAndSettle();
      expect(find.text('Under review'), findsOneWidget);
      expect(
        tester.widget<FilledButton>(
          find.byKey(const Key('gtex-gift-send-button')),
        ).onPressed,
        isNull,
      );
    }
    expect(sentKey, isNull);
  });
}
