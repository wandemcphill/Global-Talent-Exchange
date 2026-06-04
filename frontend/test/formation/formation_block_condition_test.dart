import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/formation/formation.dart';

void main() {
  test('INVARIANT-3: fewer than 11 eligible players blocks editor', () {
    final FormationEditorBlock? block = evaluateFormationEditorBlock(
      eligiblePlayerCount: 10,
      role: 'club.owner',
    );

    expect(block, isNotNull);
    expect(block!.reason, insufficientEligiblePlayersMessage);
    expect(block.ctaRoute, '/app/squad');
  });

  test('owner and manager roles can edit with 11 eligible players', () {
    expect(
      evaluateFormationEditorBlock(eligiblePlayerCount: 11, role: 'club.owner'),
      isNull,
    );
    expect(
      evaluateFormationEditorBlock(
        eligiblePlayerCount: 11,
        role: 'club.manager',
      ),
      isNull,
    );
  });

  test('INVARIANT-4: unrecognised role becomes blocked, not thrown', () {
    expect(
      () => evaluateFormationEditorBlock(
        eligiblePlayerCount: 11,
        role: 'academy.oracle',
      ),
      returnsNormally,
    );

    final FormationEditorBlock? block = evaluateFormationEditorBlock(
      eligiblePlayerCount: 11,
      role: 'academy.oracle',
    );

    expect(block, isNotNull);
    expect(block!.reason, roleFormationBlockedMessage);
  });
}
