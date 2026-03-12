import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/controllers/club_controller.dart';
import 'package:gte_frontend/data/club_api.dart';
import 'package:gte_frontend/models/club_catalog_models.dart';
import 'package:gte_frontend/screens/clubs/club_catalog_screen.dart';
import 'package:gte_frontend/widgets/clubs/catalog_item_card.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('club catalog confirms transparent purchase flow',
      (WidgetTester tester) async {
    final ClubController controller = ClubController(
      api: ClubApi.fixture(),
      clubId: 'royal-lagos-fc',
    );
    controller.load();

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: ClubCatalogScreen(controller: controller),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 700));

    expect(find.text('Transparent cosmetic catalog'), findsOneWidget);

    await tester.scrollUntilVisible(
      find.text('Gold trim pack'),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    expect(
      find.ancestor(
        of: find.text('Gold trim pack'),
        matching: find.byType(CatalogItemCard),
      ),
      findsOneWidget,
    );
    final Finder goldTrimCard = find.ancestor(
      of: find.text('Gold trim pack'),
      matching: find.byType(CatalogItemCard),
    );
    final Finder purchaseButton = find.descendant(
      of: goldTrimCard,
      matching: find.widgetWithText(FilledButton, 'Purchase'),
    );
    await tester.dragUntilVisible(
      purchaseButton,
      find.byType(ListView),
      const Offset(0, -200),
    );
    await tester.drag(find.byType(ListView), const Offset(0, -180));
    await tester.pump();
    await tester.tap(purchaseButton);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('Purchase confirmation'), findsOneWidget);

    await tester.tap(find.text('Confirm purchase'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 1400));

    expect(
      controller.catalog.any(
        (ClubCatalogItem item) =>
            item.title == 'Gold trim pack' &&
            item.ownershipStatus != CatalogOwnershipStatus.available,
      ),
      isTrue,
    );
  });
}
