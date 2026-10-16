import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/regen_redesign/data/gtex_regen_demo_dossier.dart';
import 'package:gte_frontend/features/regen_redesign/data/gtex_regen_repository.dart';
import 'package:gte_frontend/features/regen_redesign/models/gtex_regen_dossier.dart';
import 'package:gte_frontend/features/regen_redesign/models/gtex_regen_wire_models.dart';
import 'package:gte_frontend/features/regen_redesign/widgets/gtex_regen_ownership_actions.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

/// The write half of OWN. These are the only two verbs the regen lane calls
/// that change server state, so they get the strictest treatment: withheld
/// entirely when signed out, and never reporting success they did not get.
class _SignedOutRepository extends DemoGtexRegenRepository {
  const _SignedOutRepository();

  @override
  bool get canActOnOwnership => false;
}

class _RecordingRepository extends DemoGtexRegenRepository {
  _RecordingRepository();

  final List<bool> listingCalls = <bool>[];
  final List<GtexRegenOfferDraft> quoteCalls = <GtexRegenOfferDraft>[];

  @override
  Future<RegenLifecycleState?> setTransferListing(
    String playerId, {
    required bool listed,
    String? reason,
  }) async {
    listingCalls.add(listed);
    return demoRegenLifecycle(transferListed: listed);
  }

  @override
  Future<RegenOfferQuote> quoteContractOffer(
    String playerId,
    GtexRegenOfferDraft draft,
  ) async {
    quoteCalls.add(draft);
    return demoRegenOfferQuote(draft);
  }
}

class _FailingRepository extends DemoGtexRegenRepository {
  const _FailingRepository();

  @override
  Future<RegenLifecycleState?> setTransferListing(
    String playerId, {
    required bool listed,
    String? reason,
  }) async {
    throw StateError('listing rejected by the server');
  }
}

void main() {
  Future<void> pumpActions(
    WidgetTester tester,
    GtexRegenRepository repository, {
    ValueChanged<RegenLifecycleState?>? onLifecycleChanged,
    double width = 420,
  }) async {
    tester.view.physicalSize = Size(width, 1600);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: GtexRegenOwnershipActions(
              repository: repository,
              dossier: demoRegenDossier('r-001'),
              onLifecycleChanged: onLifecycleChanged,
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  group('authentication gate', () {
    testWidgets('a signed-out session gets no write controls at all', (
      WidgetTester tester,
    ) async {
      await pumpActions(tester, const _SignedOutRepository());

      expect(find.text('Sign in to act'), findsOneWidget);
      expect(find.byType(GtexBlockedState), findsOneWidget);
      // Controls that would fail on auth are withheld, not disabled-in-place.
      expect(find.text('List for transfer'), findsNothing);
      expect(find.text('Get quote'), findsNothing);
    });

    testWidgets('a signed-in session gets both verbs', (
      WidgetTester tester,
    ) async {
      await pumpActions(tester, _RecordingRepository());

      expect(find.text('List for transfer'), findsOneWidget);
      expect(find.text('Get quote'), findsOneWidget);
    });
  });

  group('transfer listing', () {
    testWidgets('lists the regen and reports the change upward', (
      WidgetTester tester,
    ) async {
      final _RecordingRepository repository = _RecordingRepository();
      final List<RegenLifecycleState?> changes = <RegenLifecycleState?>[];

      await pumpActions(
        tester,
        repository,
        onLifecycleChanged: changes.add,
      );
      await tester.tap(find.text('List for transfer'));
      await tester.pumpAndSettle();

      expect(repository.listingCalls, <bool>[true]);
      expect(changes, hasLength(1));
      expect(changes.single?.transferListed, isTrue);
    });

    testWidgets('a rejected listing surfaces the error and claims nothing', (
      WidgetTester tester,
    ) async {
      await pumpActions(tester, const _FailingRepository());

      await tester.tap(find.text('List for transfer'));
      await tester.pumpAndSettle();

      expect(find.byType(GtexErrorBanner), findsOneWidget);
      expect(find.textContaining('rejected by the server'), findsOneWidget);
      // The button must still read "List for transfer": the state did not
      // change, so the UI must not imply that it did.
      expect(find.text('List for transfer'), findsOneWidget);
      expect(find.text('Remove from transfer list'), findsNothing);
    });
  });

  group('contract offer quote', () {
    testWidgets('refuses to quote without a club and a salary', (
      WidgetTester tester,
    ) async {
      final _RecordingRepository repository = _RecordingRepository();
      await pumpActions(tester, repository);

      await tester.tap(find.text('Get quote'));
      await tester.pumpAndSettle();

      expect(repository.quoteCalls, isEmpty);
      expect(find.textContaining('Enter an offering club id'), findsOneWidget);
    });

    testWidgets('quotes an affordable offer and says it is covered', (
      WidgetTester tester,
    ) async {
      final _RecordingRepository repository = _RecordingRepository();
      await pumpActions(tester, repository);

      await tester.enterText(find.byType(TextField).first, 'club-1');
      await tester.enterText(find.byType(TextField).last, '10000');
      await tester.tap(find.text('Get quote'));
      await tester.pumpAndSettle();

      expect(repository.quoteCalls, hasLength(1));
      expect(repository.quoteCalls.single.offeringClubId, 'club-1');
      expect(repository.quoteCalls.single.contractYears, 3);
      expect(find.text('Covered by the wallet'), findsOneWidget);
    });

    testWidgets('states the shortfall plainly when the wallet cannot cover', (
      WidgetTester tester,
    ) async {
      await pumpActions(tester, _RecordingRepository());

      await tester.enterText(find.byType(TextField).first, 'club-1');
      await tester.enterText(find.byType(TextField).last, '40000');
      await tester.tap(find.text('Get quote'));
      await tester.pumpAndSettle();

      // 40000 x 3 years = 120000 against a 50000 wallet.
      expect(find.text('Short by 70000'), findsOneWidget);
      expect(find.text('Covered by the wallet'), findsNothing);
    });

    testWidgets('cannot request a contract length the backend would reject', (
      WidgetTester tester,
    ) async {
      await pumpActions(tester, _RecordingRepository());

      final Slider slider = tester.widget<Slider>(find.byType(Slider));
      // The backend caps contract_years at 1..5.
      expect(slider.min, 1);
      expect(slider.max, 5);
    });
  });

  group('responsive widths', () {
    for (final double width in <double>[360, 420, 768, 1024]) {
      testWidgets('ownership actions hold together at ${width}px', (
        WidgetTester tester,
      ) async {
        await pumpActions(tester, _RecordingRepository(), width: width);

        expect(
          tester.takeException(),
          isNull,
          reason: 'ownership actions overflowed at ${width}px',
        );
      });
    }
  });
}
