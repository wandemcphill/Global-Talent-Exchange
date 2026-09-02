@Tags(<String>['golden'])
library;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

/// Visual QA captures for the refinement pass. Regenerate with
/// `flutter test test/ux_refinement/visual_qa_golden_test.dart --update-goldens`.
///
/// Tagged `golden` and excluded from CI (`--exclude-tags golden`) because these
/// captures are platform-dependent. Measured: all three pass on Windows, where
/// they were generated, and fail on `ubuntu-latest` with small, *identical*
/// pixel deltas on every run (browse_grid_mobile 1.70%, browse_grid_desktop
/// 0.60%, master_detail_tablet 0.93%) across four unrelated backend-only
/// commits. That signature is font rasterisation differing between platforms,
/// not a UI regression - these player-card grids are text-heavy, so glyph
/// antialiasing dominates the diff.
///
/// Left running in CI they were a permanently red gate that masked genuine
/// frontend regressions. To put them back in CI, regenerate the PNGs on Linux
/// (a one-off `flutter test --update-goldens` job on `ubuntu-latest`) and drop
/// the tag - goldens are only valid on the platform that produced them.
void main() {
  Widget card({
    required String name,
    required String club,
    required String price,
    List<String> form = const <String>['W', 'W', 'D', 'L', 'W'],
  }) {
    return GtexPlayerCard(
      name: name,
      position: 'ST',
      clubName: club,
      nationality: 'Nigeria',
      priceLabel: price,
      ratingLabel: '84',
      formResults: form,
      onTap: () {},
      onAddToShortlist: () {},
      onBuyNow: () {},
      buyNowLabel: 'Negotiate',
    );
  }

  Widget grid(double width, List<Widget> children) {
    final int cross = width >= 1100 ? 3 : (width >= 680 ? 2 : 1);
    return MaterialApp(
      theme: ThemeData.dark(),
      home: Scaffold(
        backgroundColor: GtexColors.surfaceBase,
        body: GridView(
          padding: const EdgeInsets.all(GtexSpacing.md),
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: cross,
            crossAxisSpacing: GtexSpacing.sm,
            mainAxisSpacing: GtexSpacing.sm,
            mainAxisExtent: 132,
          ),
          children: children,
        ),
      ),
    );
  }

  testWidgets('market browse grid - mobile', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      grid(390, <Widget>[
        card(
          name: 'Emmanuel Adebayo-Oluwaseun',
          club: 'Real Sporting Clube de Portugal B',
          price: '1,240,000 GTC',
        ),
        card(name: 'Ada Eze', club: 'Enyimba FC', price: '9 GTC'),
        card(
          name: 'Jean-Baptiste Nkemdirim-Okonkwo',
          club: 'FC',
          price: '98,765,432 GTC',
          form: const <String>[],
        ),
      ]),
    );
    await tester.pump();
    await expectLater(
      find.byType(GridView),
      matchesGoldenFile('../goldens/ux_refinement/browse_grid_mobile.png'),
    );
  });

  testWidgets('market browse grid - desktop', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1440, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      grid(1440, <Widget>[
        card(
          name: 'Emmanuel Adebayo-Oluwaseun',
          club: 'Real Sporting Clube de Portugal B',
          price: '1,240,000 GTC',
        ),
        card(name: 'Ada Eze', club: 'Enyimba FC', price: '9 GTC'),
        card(
          name: 'Jean-Baptiste Nkemdirim-Okonkwo',
          club: 'Wydad Athletic Club Casablanca',
          price: '98,765,432 GTC',
        ),
      ]),
    );
    await tester.pump();
    await expectLater(
      find.byType(GridView),
      matchesGoldenFile('../goldens/ux_refinement/browse_grid_desktop.png'),
    );
  });

  testWidgets('master detail - tablet keeps summary reachable', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(900, 700);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      MaterialApp(
        theme: ThemeData.dark(),
        home: Scaffold(
          backgroundColor: GtexColors.surfaceBase,
          body: GtexMasterDetailScaffold(
            title: 'Transfer Hub',
            subtitle: 'Browse and sign players',
            leftPanel: const Center(child: Text('Filters')),
            detail: GridView(
              padding: const EdgeInsets.all(GtexSpacing.md),
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 1,
                mainAxisSpacing: GtexSpacing.sm,
                mainAxisExtent: 132,
              ),
              children: <Widget>[
                card(
                  name: 'Emmanuel Adebayo-Oluwaseun',
                  club: 'Real Sporting Clube de Portugal B',
                  price: '1,240,000 GTC',
                ),
                card(name: 'Ada Eze', club: 'Enyimba FC', price: '9 GTC'),
              ],
            ),
            rightPanel: const Center(child: Text('Selected player')),
          ),
        ),
      ),
    );
    await tester.pump();
    await expectLater(
      find.byType(GtexMasterDetailScaffold),
      matchesGoldenFile('../goldens/ux_refinement/master_detail_tablet.png'),
    );
  });
}
