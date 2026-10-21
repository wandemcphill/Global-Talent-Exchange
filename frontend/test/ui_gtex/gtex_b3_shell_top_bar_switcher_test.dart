import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/features/club_redesign/widgets/gtex_empire_club_switcher.dart';
import 'package:gte_frontend/features/navigation/model/gtex_shell_navigation_model.dart';
import 'package:gte_frontend/features/navigation/presentation/gte_navigation_shell_screen.dart';
import 'package:gte_frontend/features/navigation/routing/gte_navigation_route.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

GteAuthSession _buildSession({
  required String role,
  String? clubId,
  String? clubName,
  List<String> permissions = const <String>[],
}) {
  return GteAuthSession.fromJson(<String, Object?>{
    'access_token': 'test-token-$role',
    'token_type': 'bearer',
    'expires_in': 3600,
    if (clubId != null) 'current_club_id': clubId,
    if (clubName != null) 'current_club_name': clubName,
    'permissions': permissions,
    'user': <String, Object?>{
      'id': 'user-$role',
      'email': '$role@gtex.test',
      'username': 'ade_$role',
      'display_name': 'Ade $role',
      'role': role,
      if (clubId != null) 'current_club_id': clubId,
      if (clubName != null) 'current_club_name': clubName,
      'permissions': permissions,
    },
  });
}

void main() {
  group('Phase B3 — GtexTopBar, Workspace Switcher & Club Switcher', () {
    testWidgets(
      'switches workspace in GtexTopBar and updates 5-slot phone bottom navigation bar',
      (WidgetTester tester) async {
        tester.view.physicalSize = const Size(390, 844);
        tester.view.devicePixelRatio = 1.0;
        addTearDown(() {
          tester.view.resetPhysicalSize();
          tester.view.resetDevicePixelRatio();
        });

        final GteExchangeController controller = GteExchangeController(
          api: GteExchangeApiClient.fixture(),
        );
        // Multi-role user: Club Owner + Coin Trader
        controller.session = _buildSession(
          role: 'trader',
          clubId: 'club-lagos',
          clubName: 'Lagos FC',
          permissions: const <String>['coin_trader'],
        );

        await tester.pumpWidget(
          MaterialApp(
            theme: GteShellTheme.build(),
            home: GteNavigationShellScreen(
              controller: controller,
              apiBaseUrl: 'http://127.0.0.1:8000',
              backendMode: GteBackendMode.fixture,
              enableShellV3: true,
              attentionBadgeCount: 4,
              customLaneBuilders: <GtePrimaryDestination, WidgetBuilder>{
                GtePrimaryDestination.home:
                    (_) => const Center(child: Text('Home Stub')),
              },
            ),
          ),
        );
        await tester.pumpAndSettle();

        // Default workspace for club owner is Club: Home, Club, Matchday, Market, More
        expect(find.byKey(const Key('gtex-top-bar')), findsOneWidget);
        expect(
          find.byKey(const Key('gtex-workspace-switcher-button')),
          findsOneWidget,
        );
        expect(find.byKey(const Key('gtex-nav-slot-club')), findsOneWidget);
        expect(
          find.byKey(const Key('gtex-top-bar-attention-badge')),
          findsOneWidget,
        );
        expect(find.text('4'), findsOneWidget);

        // Open Workspace Switcher and switch to Trader workspace.
        await tester.tap(
          find.byKey(const Key('gtex-workspace-switcher-button')),
        );
        await tester.pumpAndSettle();
        await tester.tap(find.byKey(const Key('gtex-workspace-option-trader')));
        await tester.pumpAndSettle();

        // Trader workspace slots: Home, Trader Desk, Market, Wallet, More
        expect(
          find.byKey(const Key('gtex-nav-slot-traderDesk')),
          findsOneWidget,
        );
        expect(find.byKey(const Key('gtex-nav-slot-wallet')), findsOneWidget);
      },
    );

    testWidgets(
      'club switcher in GtexTopBar updates active club id in controller and club-scoped lanes',
      (WidgetTester tester) async {
        tester.view.physicalSize = const Size(1280, 900);
        tester.view.devicePixelRatio = 1.0;
        addTearDown(() {
          tester.view.resetPhysicalSize();
          tester.view.resetDevicePixelRatio();
        });

        final GteExchangeController controller = GteExchangeController(
          api: GteExchangeApiClient.fixture(),
        );
        controller.session = _buildSession(
          role: 'user',
          clubId: 'club-lagos',
          clubName: 'Lagos FC',
        );

        await tester.pumpWidget(
          MaterialApp(
            theme: GteShellTheme.build(),
            home: GteNavigationShellScreen(
              controller: controller,
              apiBaseUrl: 'http://127.0.0.1:8000',
              backendMode: GteBackendMode.fixture,
              enableShellV3: true,
              initialRoute: const GteNavigationRoute.club(),
              initialOwnedClubs: const <GtexOwnedClubOption>[
                GtexOwnedClubOption(
                  id: 'club-lagos',
                  name: 'Lagos FC',
                  slug: 'lagos-fc',
                ),
                GtexOwnedClubOption(
                  id: 'club-accra',
                  name: 'Accra United',
                  slug: 'accra-united',
                ),
              ],
              customLaneBuilders: <GtePrimaryDestination, WidgetBuilder>{
                GtePrimaryDestination.club:
                    (_) => Center(
                      child: Text(
                        'ActiveClub:${controller.session?.user.rawJson['current_club_id']}',
                      ),
                    ),
              },
            ),
          ),
        );
        await tester.pumpAndSettle();

        expect(find.text('ActiveClub:club-lagos'), findsOneWidget);
        expect(
          find.byKey(const Key('gtex-club-switcher-button')),
          findsOneWidget,
        );

        // Open Club Switcher in TopBar and select Accra United.
        await tester.tap(find.byKey(const Key('gtex-club-switcher-button')));
        await tester.pumpAndSettle();
        await tester.tap(find.byKey(const Key('gtex-club-option-club-accra')));
        await tester.pumpAndSettle();

        expect(find.text('ActiveClub:club-accra'), findsOneWidget);
        expect(find.text('Accra United'), findsWidgets);
      },
    );

    testWidgets(
      'More sheet opens on phone and displays secondary destinations from ShellNavigationModel',
      (WidgetTester tester) async {
        tester.view.physicalSize = const Size(390, 844);
        tester.view.devicePixelRatio = 1.0;
        addTearDown(() {
          tester.view.resetPhysicalSize();
          tester.view.resetDevicePixelRatio();
        });

        final GteExchangeController controller = GteExchangeController(
          api: GteExchangeApiClient.fixture(),
        );
        controller.session = _buildSession(
          role: 'admin',
          clubId: 'club-lagos',
          clubName: 'Lagos FC',
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
                    (_) => const Center(child: Text('Home Stub')),
                GtePrimaryDestination.community:
                    (_) => const Center(child: Text('Community Stub')),
              },
            ),
          ),
        );
        await tester.pumpAndSettle();

        // Tap Slot 5 (More) on the compact bottom navigation bar.
        await tester.tap(find.byKey(const Key('gtex-nav-slot-more')));
        await tester.pumpAndSettle();

        expect(
          find.byKey(const Key('gtex-more-destination-newsroom')),
          findsOneWidget,
        );
        expect(
          find.byKey(const Key('gtex-more-destination-world')),
          findsOneWidget,
        );
        expect(
          find.byKey(const Key('gtex-more-destination-community')),
          findsOneWidget,
        );
        expect(
          find.byKey(const Key('gtex-more-destination-admin')),
          findsOneWidget,
        );

        // Select Community from the More sheet and verify navigation.
        await tester.tap(
          find.byKey(const Key('gtex-more-destination-community')),
        );
        await tester.pumpAndSettle();
        expect(find.text('Community Stub'), findsOneWidget);
      },
    );
  });
}
