import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';
import 'package:gte_frontend/features/launch_control_redesign/launch_control_feature_gate.dart';
import 'package:gte_frontend/features/navigation/model/gtex_shell_navigation_model.dart';
import 'package:gte_frontend/features/owner_console/data/owner_console_api.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

class _CountingOwnerTransport implements GteTransport {
  int controlCenterRequestCount = 0;

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    if (request.uri.path.contains('/owner/control-center')) {
      controlCenterRequestCount += 1;
    }
    return GteTransportResponse(
      statusCode: 200,
      body: <String, Object?>{
        'club': <String, Object?>{
          'club_id': 'club-lagos',
          'club_name': 'Lagos Stars FC',
          'value': 125000,
          'value_trend': 4.5,
          'world_day': 10,
        },
        'wallet_balance': 48000,
        'inbox': const <Object?>[],
        'matches': const <Object?>[],
        'squad': const <Object?>[],
      },
    );
  }
}

Widget _buildResponsiveShellFixture({
  required ShellNavigationModel navigationModel,
}) {
  return MaterialApp(
    theme: GteShellTheme.build(),
    home: GtexShellScaffold(
      navigationModel: navigationModel,
      selectedSlotId: GtexShellSlotId.home,
      onSelectSlot: (_) {},
      worldPulseRail: Container(
        key: const Key('f2-world-pulse-rail'),
        width: 280,
        color: GtexColors.navy.bgSurface,
        child: const Center(child: Text('World Pulse Rail')),
      ),
      topBar: GtexTopBar(
        title: 'GTEX Command',
        subtitle: 'Club & Football Economy',
        availableWorkspaces: navigationModel.availableWorkspaces,
        activeWorkspace: navigationModel.activeWorkspace,
        onWorkspaceSelected: (_) {},
        ownedClubs: const <GtexOwnedClubOption>[
          GtexOwnedClubOption(
            id: 'club-lagos',
            name: 'Lagos Stars FC',
            slug: 'lagos-stars-fc',
          ),
        ],
        activeClubId: 'club-lagos',
        activeClubName: 'Lagos Stars FC',
        onClubSelected: (_) {},
        attentionCount: 3,
        onOpenAttention: () {},
        onOpenSearch: () {},
        walletBalanceGtc: 24500,
        onOpenWallet: () {},
        onOpenProfile: () {},
        isAuthenticated: true,
        userInitials: 'AO',
      ),
      child: ListView(
        padding: const EdgeInsets.all(GtexSpacing.md),
        children: <Widget>[
          const Align(
            alignment: Alignment.centerLeft,
            child: GtexPortrait(
              seed: 'regen-f2-101',
              position: 'ST',
              nationalityCode: 'NGA',
              playerName: 'Victor Adeyemi',
              size: GtexPortraitSize.sm48,
            ),
          ),
          const SizedBox(height: GtexSpacing.sm),
          Wrap(
            spacing: GtexSpacing.xs,
            runSpacing: GtexSpacing.xs,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: <Widget>[
              GtexStatusChip.fromBackendStatus('confirmed', compact: true),
              GtexPolicyChip.fromBackendMode('automatic', compact: true),
              const GtexMoney(
                amount: 12500,
                unit: GtexCurrencyUnit.gtc,
              ),
            ],
          ),
          const SizedBox(height: GtexSpacing.md),
          GtexAttentionCard(
            title: 'Approve academy intake shortlist',
            subtitle:
                'Head of Youth Development submitted 3 West African prospects.',
            variant: GtexAttentionVariant.approval,
            state: GtexAttentionState.unread,
            dueLabel: 'Due 2d',
            whoActsNextLabel: 'OWNER ACTS NEXT',
            onPrimaryAction: () {},
          ),
        ],
      ),
    ),
  );
}

void main() {
  group('Phase F2 — Document L1 Responsive Breakpoints', () {
    const List<Size> breakpoints = <Size>[
      Size(360, 640),
      Size(390, 844),
      Size(768, 1024),
      Size(1280, 900),
    ];

    final ShellNavigationModel navigationModel = ShellNavigationModel(
      capabilities: const GtexShellCapabilities(
        isAuthenticated: true,
        ownedClubIds: <String>['club-lagos'],
        activeClubId: 'club-lagos',
        isCoinTrader: true,
        unreadInboxCount: 2,
        unreadNotificationCount: 1,
      ),
    );

    for (final Size viewport in breakpoints) {
      testWidgets(
        'renders GtexShellScaffold and canonical components without overflow at ${viewport.width.toInt()}x${viewport.height.toInt()}',
        (WidgetTester tester) async {
          tester.view.physicalSize = viewport;
          tester.view.devicePixelRatio = 1.0;
          addTearDown(() {
            tester.view.resetPhysicalSize();
            tester.view.resetDevicePixelRatio();
          });

          await tester.pumpWidget(
            _buildResponsiveShellFixture(navigationModel: navigationModel),
          );
          await tester.pumpAndSettle();

          expect(tester.takeException(), isNull);
          expect(find.byKey(const Key('gtex-shell-scaffold')), findsOneWidget);
          expect(find.byKey(const Key('gtex-top-bar')), findsOneWidget);
          expect(
            find.text('Approve academy intake shortlist'),
            findsOneWidget,
          );
          expect(find.text('12,500 GTC'), findsOneWidget);

          if (viewport.width < GtexBreakpoints.mobile) {
            expect(find.byType(GtexNavBar), findsOneWidget);
            expect(find.byType(GtexNavRail), findsNothing);
            expect(find.byKey(const Key('f2-world-pulse-rail')), findsNothing);
          } else if (viewport.width < GtexBreakpoints.desktop) {
            expect(find.byType(GtexNavBar), findsNothing);
            expect(find.byType(GtexNavRail), findsOneWidget);
            expect(find.byKey(const Key('f2-world-pulse-rail')), findsNothing);
          } else {
            expect(find.byType(GtexNavBar), findsNothing);
            expect(find.byType(GtexNavRail), findsOneWidget);
            expect(
              find.byKey(const Key('f2-world-pulse-rail')),
              findsOneWidget,
            );
          }
        },
      );
    }
  });

  group('Phase F2 — Document L2 Accessibility & Text Scale (1.0, 1.3, 2.0)', () {
    const List<double> textScales = <double>[1.0, 1.3, 2.0];

    for (final double scale in textScales) {
      testWidgets(
        'renders canonical components with Semantics labels and zero overflow at TextScaler.linear($scale)',
        (WidgetTester tester) async {
          tester.view.physicalSize = const Size(768, 1024);
          tester.view.devicePixelRatio = 1.0;
          addTearDown(() {
            tester.view.resetPhysicalSize();
            tester.view.resetDevicePixelRatio();
          });

          final SemanticsHandle semantics = tester.ensureSemantics();
          try {
            await tester.pumpWidget(
              MaterialApp(
                theme: GteShellTheme.build(),
                builder: (BuildContext context, Widget? child) {
                  return MediaQuery(
                    data: MediaQuery.of(
                      context,
                    ).copyWith(textScaler: TextScaler.linear(scale)),
                    child: child!,
                  );
                },
                home: Scaffold(
                  body: ListView(
                    padding: const EdgeInsets.all(GtexSpacing.md),
                    children: <Widget>[
                      const Align(
                        alignment: Alignment.centerLeft,
                        child: GtexPortrait(
                          seed: 'regen-a11y-1',
                          position: 'CM',
                          nationalityCode: 'NGA',
                          playerName: 'Kaito Mensah',
                          size: GtexPortraitSize.md72,
                        ),
                      ),
                      const SizedBox(height: GtexSpacing.sm),
                      Wrap(
                        spacing: GtexSpacing.xs,
                        runSpacing: GtexSpacing.xs,
                        children: <Widget>[
                          GtexStatusChip.fromBackendStatus('under_review'),
                          GtexStatusChip.fromBackendStatus('retracted'),
                          GtexPolicyChip.fromBackendMode('owner_only'),
                          const GtexMoney(
                            amount: 4800,
                            unit: GtexCurrencyUnit.gtx,
                            isPending: true,
                          ),
                        ],
                      ),
                      const SizedBox(height: GtexSpacing.sm),
                      GtexAttentionCard(
                        title: 'Contract renewal decision',
                        subtitle:
                            'First-team midfielder enters final 6 months of deal.',
                        variant: GtexAttentionVariant.decision,
                        state: GtexAttentionState.unread,
                        dueLabel: 'Due 3d',
                        whoActsNextLabel: 'OWNER ACTS NEXT',
                        onPrimaryAction: () {},
                      ),
                    ],
                  ),
                ),
              ),
            );
            await tester.pumpAndSettle();

            expect(tester.takeException(), isNull);
            expect(
              find.bySemanticsLabel(RegExp(r'Portrait of Kaito Mensah')),
              findsOneWidget,
            );
            expect(
              find.bySemanticsLabel(RegExp(r'Status: In review')),
              findsOneWidget,
            );
            expect(
              find.bySemanticsLabel(RegExp(r'Status: Retracted')),
              findsOneWidget,
            );
            expect(
              find.bySemanticsLabel(RegExp(r'Delegation policy: Owner only')),
              findsOneWidget,
            );
            expect(
              find.bySemanticsLabel(RegExp(r'4,800 GTX \(Pending\)')),
              findsOneWidget,
            );
            expect(
              find.bySemanticsLabel(
                RegExp(r'Contract renewal decision, Unread'),
              ),
              findsOneWidget,
            );
          } finally {
            semantics.dispose();
          }
        },
      );
    }
  });

  group('Phase F2 — Document L4 Performance & Side-Effect Guards', () {
    test(
      'GtexLaunchControlFeatureGate caches flags per session and makes 0 additional fetches on repeated checks',
      () async {
        GtexLaunchControlFeatureGate.clearCache();
        expect(GtexLaunchControlFeatureGate.networkFetchCountForTesting, 0);

        final GtexFeatureGateDecision firstDecision =
            await GtexLaunchControlFeatureGate.resolveFeatureKey(
              featureKey: 'transfer_hub',
              route: '/football/transfer-center',
              baseUrl: 'http://127.0.0.1:8000',
              backendMode: GteBackendMode.fixture,
              accessToken: 'session-token-f2',
              isAdmin: false,
            );
        expect(firstDecision.featureKey, equals('transfer_hub'));
        expect(GtexLaunchControlFeatureGate.networkFetchCountForTesting, 1);

        // Subsequent checks for the same session token & backend mode hit the cache.
        for (int i = 0; i < 4; i++) {
          final GtexFeatureGateDecision cachedDecision =
              await GtexLaunchControlFeatureGate.resolveFeatureKey(
                featureKey: 'transfer_hub',
                route: '/football/transfer-center',
                baseUrl: 'http://127.0.0.1:8000',
                backendMode: GteBackendMode.fixture,
                accessToken: 'session-token-f2',
                isAdmin: false,
              );
          expect(cachedDecision.allowed, equals(firstDecision.allowed));
        }

        expect(GtexLaunchControlFeatureGate.networkFetchCountForTesting, 1);
      },
    );

    testWidgets(
      'OwnerConsoleApi has no periodic timer polling /owner/control-center (Scenario 26)',
      (WidgetTester tester) async {
        final _CountingOwnerTransport transport = _CountingOwnerTransport();
        final OwnerConsoleApi api = OwnerConsoleApi(
          client: GteAuthedApi(
            config: const GteRepositoryConfig(
              baseUrl: 'http://127.0.0.1:8000',
              mode: GteBackendMode.live,
            ),
            transport: transport,
            accessToken: 'owner-token',
            mode: GteBackendMode.live,
          ),
          activeClubId: 'club-lagos',
        );

        // Instantiating OwnerConsoleApi and advancing 5 minutes triggers 0 background requests.
        await tester.pump(const Duration(minutes: 5));
        expect(transport.controlCenterRequestCount, 0);

        // A single explicit call triggers exactly 1 request and does not start any polling timer.
        await api.fetchControlCenter();
        expect(transport.controlCenterRequestCount, 1);

        await tester.pump(const Duration(minutes: 5));
        expect(transport.controlCenterRequestCount, 1);

        final File apiSourceFile = File(
          'lib/features/owner_console/data/owner_console_api.dart',
        );
        expect(apiSourceFile.existsSync(), isTrue);
        final String source = apiSourceFile.readAsStringSync();
        expect(source.contains('Timer.periodic'), isFalse);
      },
    );
  });
}
