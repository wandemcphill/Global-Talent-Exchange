import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/controllers/club_ops_controller.dart';
import 'package:gte_frontend/data/club_ops_api.dart';
import 'package:gte_frontend/data/club_ops_fixtures.dart';
import 'package:gte_frontend/features/club_hub/widgets/club_hub_components.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('Club HQ operations panel renders loaded production sections', (
    WidgetTester tester,
  ) async {
    final ClubOpsController controller = ClubOpsController(
      api: ClubOpsApi.fixture(),
      clubId: 'royal-lagos-fc',
      clubName: 'Royal Lagos FC',
    );
    _seedClubOps(controller);

    await tester.pumpWidget(
      _Harness(
        child: ClubHqOperationsPanel(
          data: null,
          operationsController: controller,
        ),
      ),
    );
    await _pumpPanel(tester);

    expect(find.text('Club HQ readiness'), findsOneWidget);
    expect(find.text('Finance snapshot'), findsOneWidget);
    expect(find.text('Academy'), findsOneWidget);
    expect(find.text('Staff'), findsOneWidget);
    expect(find.text('Sponsorships'), findsOneWidget);
    expect(find.text('Branding'), findsOneWidget);
    expect(find.text('Trophies'), findsOneWidget);
    expect(find.text('Rankings'), findsOneWidget);
    expect(find.textContaining('Net monthly movement'), findsOneWidget);
    expect(
      find.textContaining('dedicated staff roster endpoint still pending'),
      findsOneWidget,
    );

    controller.dispose();
  });

  testWidgets(
    'Club HQ operations panel blocks missing authoritative payloads',
    (WidgetTester tester) async {
      await tester.pumpWidget(
        const _Harness(
          child: ClubHqOperationsPanel(data: null, operationsController: null),
        ),
      );
      await _pumpPanel(tester);

      expect(
        find.text(
          'Club operations controller is not mounted on this route yet.',
        ),
        findsOneWidget,
      );
      expect(find.text('BLOCKED'), findsWidgets);
      expect(
        find.text('No finance payload is mounted; HQ will not infer cashflow.'),
        findsOneWidget,
      );
      expect(
        find.text(
          'Club dashboard payload is required before HQ readiness can open.',
        ),
        findsOneWidget,
      );
    },
  );

  testWidgets('Club HQ operations panel exposes backend error state', (
    WidgetTester tester,
  ) async {
    final ClubOpsController controller = ClubOpsController(
      api: ClubOpsApi.fixture(),
      clubId: 'royal-lagos-fc',
      clubName: 'Royal Lagos FC',
    )..clubErrorMessage = 'Unable to reach club operations backend.';

    await tester.pumpWidget(
      _Harness(
        child: ClubHqOperationsPanel(
          data: null,
          operationsController: controller,
        ),
      ),
    );
    await _pumpPanel(tester);

    expect(
      find.text('Unable to reach club operations backend.'),
      findsOneWidget,
    );
    expect(find.text('ERROR'), findsWidgets);
    expect(
      find.text('Finance payload failed to load from club operations.'),
      findsOneWidget,
    );

    controller.dispose();
  });
}

Future<void> _pumpPanel(WidgetTester tester) async {
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 250));
}

void _seedClubOps(ClubOpsController controller) {
  controller
    ..finance = fixtureClubFinance('royal-lagos-fc', 'Royal Lagos FC')
    ..sponsorships = fixtureSponsorships('royal-lagos-fc', 'Royal Lagos FC')
    ..academy = fixtureAcademy('royal-lagos-fc', 'Royal Lagos FC')
    ..scouting = fixtureScouting('royal-lagos-fc', 'Royal Lagos FC')
    ..youthPipeline = fixtureYouthPipeline('royal-lagos-fc', 'Royal Lagos FC');
}

class _Harness extends StatelessWidget {
  const _Harness({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      theme: GteShellTheme.build(),
      home: Scaffold(
        body: SingleChildScrollView(child: SizedBox(width: 1000, child: child)),
      ),
    );
  }
}
