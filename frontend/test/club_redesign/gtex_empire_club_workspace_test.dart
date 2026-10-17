import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/features/club_redesign/presentation/gtex_empire_club_workspace.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';

void main() {
  for (final Size viewport in <Size>[
    const Size(390, 844),
    const Size(1440, 900),
  ]) {
    testWidgets(
      'club workspace scrolls its header and bounds an Expanded child at '
      '${viewport.width}x${viewport.height}',
      (WidgetTester tester) async {
        tester.view.physicalSize = viewport;
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);
        final GteExchangeController controller = GteExchangeController(
          api: GteExchangeApiClient.fixture(),
        );
        addTearDown(controller.dispose);

        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(
              body: GtexEmpireClubWorkspace(
                controller: controller,
                activeClubId: 'club-1',
                activeClubName: 'Club One',
                child: Column(
                  children: <Widget>[
                    const Expanded(child: SizedBox.expand()),
                    ElevatedButton(
                      key: const ValueKey<String>('workspace-button'),
                      onPressed: () {},
                      child: const Text('Open club desk'),
                    ),
                  ],
                ),
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();

        expect(tester.takeException(), isNull);
        await tester.scrollUntilVisible(
          find.byKey(const ValueKey<String>('workspace-button')),
          120,
        );
        expect(find.text('Open club desk'), findsOneWidget);
        expect(tester.takeException(), isNull);
      },
    );
  }
}
