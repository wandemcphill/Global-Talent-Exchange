import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/club_lineup_repository.dart';
import 'package:gte_frontend/features/club/gtex_lineup_editor_screen.dart';

void main() {
  final List<LineupSquadPlayer> players = List<LineupSquadPlayer>.generate(
    9,
    (int index) => LineupSquadPlayer(
      playerId: 'player-$index',
      name: 'Substitute Player $index',
      position: index.isEven ? 'MID' : 'DEF',
    ),
  );

  Future<void> pumpBench(WidgetTester tester, double width) {
    return tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: width,
            child: GtexLineupSubstitutes(
              players: players,
              selectedPlayerId: null,
              onSelect: (_) {},
            ),
          ),
        ),
      ),
    );
  }

  testWidgets('renders every substitute in an accessible mobile grid', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await pumpBench(tester, 390);

    expect(find.text('SUBSTITUTES'), findsOneWidget);
    for (final LineupSquadPlayer player in players) {
      expect(find.text(player.name), findsOneWidget);
    }
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'uses the wider adaptive grid without clipping at tablet and desktop widths',
    (WidgetTester tester) async {
      for (final double width in <double>[768, 1440]) {
        await tester.binding.setSurfaceSize(Size(width, 900));
        await pumpBench(tester, width);
        expect(find.text('Substitute Player 8'), findsOneWidget);
        expect(tester.takeException(), isNull);
      }
      addTearDown(() => tester.binding.setSurfaceSize(null));
    },
  );
}
