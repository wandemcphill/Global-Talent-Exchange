import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/features/launch_control_redesign/launch_control_feature_gate.dart';
import 'package:gte_frontend/features/launch_control_redesign/launch_control_models.dart';
import 'package:gte_frontend/features/navigation/presentation/gte_navigation_shell_screen.dart';
import 'package:gte_frontend/features/navigation/presentation/gtex_shell_feature_flag.dart';
import 'package:gte_frontend/features/navigation/routing/gte_navigation_route.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

class _LaneCounterProbe extends StatefulWidget {
  const _LaneCounterProbe({required this.label});

  final String label;

  @override
  State<_LaneCounterProbe> createState() => _LaneCounterProbeState();
}

class _LaneCounterProbeState extends State<_LaneCounterProbe> {
  int _counter = 0;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Text('${widget.label}: $_counter'),
          ElevatedButton(
            key: Key('increment-${widget.label}'),
            onPressed: () {
              setState(() {
                _counter += 1;
              });
            },
            child: Text('Increment ${widget.label}'),
          ),
        ],
      ),
    );
  }
}

void main() {
  setUp(() {
    GtexLaunchControlFeatureGate.clearCache();
    GtexShellFeatureFlag.setRuntimeOverride(null);
  });

  tearDown(() {
    GtexLaunchControlFeatureGate.clearCache();
    GtexShellFeatureFlag.setRuntimeOverride(null);
  });

  group('Phase B1 — GtexLaunchControlFeatureGate session caching', () {
    test(
      'caches client flags across repeated gated route evaluations so lane switches make 0 extra fetches',
      () async {
        expect(GtexLaunchControlFeatureGate.networkFetchCountForTesting, 0);

        final GtexFeatureGateDecision firstDecision =
            await GtexLaunchControlFeatureGate.resolveRoutePath(
              route: '/football/transfer-center',
              baseUrl: 'http://127.0.0.1:8000',
              backendMode: GteBackendMode.fixture,
              accessToken: 'token-owner-1',
              isAdmin: false,
            );
        expect(firstDecision.featureKey, 'transfer_hub');
        expect(GtexLaunchControlFeatureGate.networkFetchCountForTesting, 1);

        // Subsequent gated route evaluations for the same session reuse cache.
        final GtexFeatureGateDecision secondDecision =
            await GtexLaunchControlFeatureGate.resolveRoutePath(
              route: '/football/transfer-center',
              baseUrl: 'http://127.0.0.1:8000',
              backendMode: GteBackendMode.fixture,
              accessToken: 'token-owner-1',
              isAdmin: false,
            );
        final GtexFeatureGateDecision thirdDecision =
            await GtexLaunchControlFeatureGate.resolveRoutePath(
              route: '/player-cards',
              baseUrl: 'http://127.0.0.1:8000',
              backendMode: GteBackendMode.fixture,
              accessToken: 'token-owner-1',
              isAdmin: false,
            );

        expect(secondDecision.allowed, firstDecision.allowed);
        expect(thirdDecision.featureKey, 'player_card_marketplace');
        expect(
          GtexLaunchControlFeatureGate.networkFetchCountForTesting,
          1,
          reason:
              'Switching between gated lanes within a session must not trigger additional flag fetches.',
        );
      },
    );

    test('primeFlags seeds cache without any network fetch', () async {
      GtexLaunchControlFeatureGate.primeFlags(
        baseUrl: 'http://127.0.0.1:8000',
        backendMode: GteBackendMode.live,
        accessToken: 'primed-token',
        flags: const <GtexClientFeatureFlag>[
          GtexClientFeatureFlag(
            featureKey: 'transfer_hub',
            title: 'Transfer Hub',
            launchState: GtexLaunchState.public,
            enabled: true,
            route: '/football/transfer-center',
            maintenanceMessage: null,
          ),
        ],
      );

      final GtexFeatureGateDecision decision =
          await GtexLaunchControlFeatureGate.resolveRoutePath(
            route: '/football/transfer-center',
            baseUrl: 'http://127.0.0.1:8000',
            backendMode: GteBackendMode.live,
            accessToken: 'primed-token',
            isAdmin: false,
          );

      expect(decision.allowed, isTrue);
      expect(GtexLaunchControlFeatureGate.networkFetchCountForTesting, 0);
    });
  });

  group('Phase B1 — Shell v3 per-lane state preservation', () {
    testWidgets(
      'retains mounted lane state across lane switches when enableShellV3 is true',
      (WidgetTester tester) async {
        tester.view.physicalSize = const Size(1440, 960);
        tester.view.devicePixelRatio = 1.0;
        addTearDown(() {
          tester.view.resetPhysicalSize();
          tester.view.resetDevicePixelRatio();
        });

        final GteExchangeController controller = GteExchangeController(
          api: GteExchangeApiClient.fixture(),
        );

        await tester.pumpWidget(
          MaterialApp(
            theme: GteShellTheme.build(),
            home: GteNavigationShellScreen(
              controller: controller,
              apiBaseUrl: 'http://127.0.0.1:8000',
              backendMode: GteBackendMode.fixture,
              enableShellV3: true,
              customLaneBuilders: <GtePrimaryDestination, WidgetBuilder>{
                GtePrimaryDestination.home:
                    (_) => const _LaneCounterProbe(label: 'HomeLane'),
                GtePrimaryDestination.club:
                    (_) => const _LaneCounterProbe(label: 'ClubLane'),
              },
            ),
          ),
        );
        await tester.pump();

        expect(find.text('HomeLane: 0'), findsOneWidget);
        await tester.tap(find.byKey(const Key('increment-HomeLane')));
        await tester.pump();
        expect(find.text('HomeLane: 1'), findsOneWidget);

        // Switch to Club lane via rail/nav item.
        await tester.tap(find.text('Club').first);
        await tester.pump();
        expect(find.text('ClubLane: 0'), findsOneWidget);

        // Switch back to Home lane and verify counter state was retained.
        await tester.tap(find.text('Home').first);
        await tester.pumpAndSettle();
        expect(find.text('HomeLane: 1'), findsOneWidget);
      },
    );
  });
}
