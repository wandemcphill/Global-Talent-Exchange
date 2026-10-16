import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';
import 'package:gte_frontend/features/player_detail/gtex_player_navigator.dart';
import 'package:gte_frontend/features/social/data/gtex_community_pulse_provider.dart';
import 'package:gte_frontend/features/social/data/gtex_community_social_api.dart';
import 'package:gte_frontend/features/social/data/gtex_community_social_models.dart';
import 'package:gte_frontend/features/social/models/gtex_community_models.dart';
import 'package:gte_frontend/features/social/widgets/gtex_community_pulse_panel.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

class _FakeSocialApi extends GtexCommunitySocialApi {
  _FakeSocialApi()
    : super(
        client: GteAuthedApi(
          config: const GteRepositoryConfig(
            baseUrl: 'http://127.0.0.1:8000',
            mode: GteBackendMode.fixture,
          ),
          transport: GteHttpTransport(),
          accessToken: 'test-token',
          mode: GteBackendMode.fixture,
        ),
      );

  final List<String> followed = <String>[];
  final List<String> unfollowed = <String>[];
  Object? failWith;

  @override
  Future<GtexSocialFollow> follow({
    required String targetType,
    String? clubId,
    String? playerId,
  }) async {
    if (failWith != null) {
      throw failWith!;
    }
    followed.add('$targetType:${playerId ?? clubId}');
    return GtexSocialFollow(
      id: 'f',
      targetKey: '$targetType:${playerId ?? clubId}',
      targetType: targetType,
      clubId: clubId,
      playerId: playerId,
    );
  }

  @override
  Future<void> unfollow({
    required String targetType,
    String? clubId,
    String? playerId,
  }) async {
    unfollowed.add('$targetType:${playerId ?? clubId}');
  }
}

const GtexCommunitySignal _ownedMove = GtexCommunitySignal(
  id: 'yours-market-p1',
  object: GtexCommunityObject.player,
  lane: GtexCommunityLane.yours,
  headline: 'Ada Obi moved +4.2%',
  detail: 'You own 2 shares.',
  socialProof: '7 owners',
  action: GtexCommunityAction.openPlayer,
  playerId: 'p1',
  isFollowable: true,
);

const GtexCommunitySignal _unknownProof = GtexCommunitySignal(
  id: 'world-market-p2',
  object: GtexCommunityObject.market,
  lane: GtexCommunityLane.world,
  headline: 'Bola Uche moved -1.1%',
  detail: 'Player market value, last 24 hours.',
  action: GtexCommunityAction.openPlayer,
  playerId: 'p2',
  isFollowable: true,
);

const GtexCommunitySignal _clubSignal = GtexCommunitySignal(
  id: 'yours-club-c1',
  object: GtexCommunityObject.club,
  lane: GtexCommunityLane.yours,
  headline: 'Lagos Eclipse FC: Your position +32.0%',
  detail: 'Club form is feeding the share price.',
  socialProof: '18 owners',
  action: GtexCommunityAction.openClub,
  clubId: 'c1',
  isFollowable: true,
);

Widget _host({
  required AsyncValue<GtexCommunityPulse> pulse,
  _FakeSocialApi? api,
  VoidCallback? onOpenClub,
  VoidCallback? onOpenLogin,
  List<String>? openedPlayers,
  Size size = const Size(1440, 1200),
}) {
  return ProviderScope(
    overrides: [
      communityPulseProvider.overrideWith(
        (Ref ref) => pulse.when(
          data: (GtexCommunityPulse value) => Future<GtexCommunityPulse>.value(value),
          error: (Object error, StackTrace stack) =>
              Future<GtexCommunityPulse>.error(error, stack),
          loading: () => Completer<GtexCommunityPulse>().future,
        ),
      ),
      if (api != null) communitySocialApiProvider.overrideWithValue(api),
    ],
    child: MaterialApp(
      theme: GteShellTheme.build(),
      home: MediaQuery(
        data: MediaQueryData(size: size),
        child: Scaffold(
          body: GtexPlayerNavigator(
            openPlayer: (String id) async => openedPlayers?.add(id),
            child: SingleChildScrollView(
              child: GtexCommunityPulsePanel(
                onOpenLogin: onOpenLogin,
                onOpenClub: onOpenClub,
              ),
            ),
          ),
        ),
      ),
    ),
  );
}

void main() {
  testWidgets('shows an honest loading state while the economy is read', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _host(pulse: const AsyncValue<GtexCommunityPulse>.loading()),
    );
    await tester.pump();
    expect(find.text('Reading the football economy'), findsOneWidget);
  });

  testWidgets('surfaces a hard failure with a retry rather than fake activity', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _host(
        pulse: AsyncValue<GtexCommunityPulse>.error(
          StateError('down'),
          StackTrace.empty,
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Community unavailable'), findsOneWidget);
    expect(find.text('Retry'), findsOneWidget);
  });

  testWidgets('an empty community says so instead of inventing rows', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _host(
        pulse: AsyncValue<GtexCommunityPulse>.data(
          GtexCommunityPulse(
            access: GtexCommunityAccess.authenticated,
            headline: buildGtexCommunityHeadline(
              access: GtexCommunityAccess.authenticated,
              worldSignals: const <GtexCommunitySignal>[],
              yourSignals: const <GtexCommunitySignal>[],
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(
      find.text('Nothing has happened around your football yet'),
      findsOneWidget,
    );
    expect(find.text('The market has not moved today'), findsOneWidget);
  });

  testWidgets('a guest sees the world lane, no personal lane, and a sign-in', (
    WidgetTester tester,
  ) async {
    bool signInTapped = false;
    await tester.pumpWidget(
      _host(
        pulse: AsyncValue<GtexCommunityPulse>.data(
          GtexCommunityPulse.anonymous(
            worldSignals: const <GtexCommunitySignal>[_unknownProof],
          ),
        ),
        onOpenLogin: () => signInTapped = true,
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Live GTEX activity'), findsOneWidget);
    expect(find.text('Your community'), findsNothing);
    expect(find.text('Follow'), findsNothing);
    await tester.tap(find.text('Sign in'));
    await tester.pumpAndSettle();
    expect(signInTapped, isTrue);
  });

  testWidgets('renders a real count and omits an unknown one', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _host(
        pulse: AsyncValue<GtexCommunityPulse>.data(
          GtexCommunityPulse(
            access: GtexCommunityAccess.authenticated,
            headline: '2 things happened around your football.',
            yourSignals: const <GtexCommunitySignal>[_ownedMove],
            worldSignals: const <GtexCommunitySignal>[_unknownProof],
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('7 owners'), findsOneWidget);
    expect(find.textContaining('0 owners'), findsNothing);
    expect(find.textContaining('owners'), findsOneWidget);
  });

  testWidgets('a partial sync is reported without hiding what did load', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _host(
        pulse: AsyncValue<GtexCommunityPulse>.data(
          GtexCommunityPulse(
            access: GtexCommunityAccess.authenticated,
            headline: '1 thing happened around your football.',
            yourSignals: const <GtexCommunitySignal>[_ownedMove],
            warnings: const <String>['Your club shares could not be loaded: 500'],
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(
      find.text('Some community sources did not answer'),
      findsOneWidget,
    );
    expect(find.text('Ada Obi moved +4.2%'), findsOneWidget);
  });

  testWidgets('a player signal routes into the canonical player detail', (
    WidgetTester tester,
  ) async {
    final List<String> opened = <String>[];
    await tester.pumpWidget(
      _host(
        pulse: AsyncValue<GtexCommunityPulse>.data(
          GtexCommunityPulse(
            access: GtexCommunityAccess.authenticated,
            headline: '1 thing happened around your football.',
            yourSignals: const <GtexCommunitySignal>[_ownedMove],
          ),
        ),
        openedPlayers: opened,
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('Open player').first);
    await tester.pumpAndSettle();
    expect(opened, <String>['p1']);
  });

  testWidgets('a club signal routes into the existing club destination', (
    WidgetTester tester,
  ) async {
    bool openedClub = false;
    await tester.pumpWidget(
      _host(
        pulse: AsyncValue<GtexCommunityPulse>.data(
          GtexCommunityPulse(
            access: GtexCommunityAccess.authenticated,
            headline: '1 thing happened around your football.',
            yourSignals: const <GtexCommunitySignal>[_clubSignal],
          ),
        ),
        onOpenClub: () => openedClub = true,
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('Open club').first);
    await tester.pumpAndSettle();
    expect(openedClub, isTrue);
  });

  testWidgets('an unroutable action renders no dead control', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _host(
        pulse: AsyncValue<GtexCommunityPulse>.data(
          GtexCommunityPulse(
            access: GtexCommunityAccess.authenticated,
            headline: '1 thing happened around your football.',
            yourSignals: const <GtexCommunitySignal>[_clubSignal],
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Open club'), findsNothing);
    expect(find.text('Lagos Eclipse FC: Your position +32.0%'), findsOneWidget);
  });

  testWidgets('following a player calls the existing follow contract once', (
    WidgetTester tester,
  ) async {
    final _FakeSocialApi api = _FakeSocialApi();
    await tester.pumpWidget(
      _host(
        pulse: AsyncValue<GtexCommunityPulse>.data(
          GtexCommunityPulse(
            access: GtexCommunityAccess.authenticated,
            headline: '1 thing happened around your football.',
            yourSignals: const <GtexCommunitySignal>[_ownedMove],
          ),
        ),
        api: api,
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('Follow'));
    await tester.pumpAndSettle();
    expect(api.followed, <String>['player:p1']);
    expect(api.unfollowed, isEmpty);
  });

  testWidgets('an already-followed target unfollows rather than re-following', (
    WidgetTester tester,
  ) async {
    final _FakeSocialApi api = _FakeSocialApi();
    await tester.pumpWidget(
      _host(
        pulse: AsyncValue<GtexCommunityPulse>.data(
          GtexCommunityPulse(
            access: GtexCommunityAccess.authenticated,
            headline: '1 thing happened around your football.',
            yourSignals: const <GtexCommunitySignal>[_ownedMove],
            followedTargets: <GtexCommunityFollowTarget>{
              GtexCommunityFollowTarget.player('p1'),
            },
          ),
        ),
        api: api,
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Following'), findsOneWidget);
    await tester.tap(find.text('Following'));
    await tester.pumpAndSettle();
    expect(api.unfollowed, <String>['player:p1']);
    expect(api.followed, isEmpty);
  });

  testWidgets('a rejected follow surfaces the error and writes nothing', (
    WidgetTester tester,
  ) async {
    final _FakeSocialApi api = _FakeSocialApi()..failWith = StateError('429');
    await tester.pumpWidget(
      _host(
        pulse: AsyncValue<GtexCommunityPulse>.data(
          GtexCommunityPulse(
            access: GtexCommunityAccess.authenticated,
            headline: '1 thing happened around your football.',
            yourSignals: const <GtexCommunitySignal>[_ownedMove],
          ),
        ),
        api: api,
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('Follow'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));
    expect(api.followed, isEmpty);
    expect(find.byType(SnackBar), findsOneWidget);
  });

  for (final double width in <double>[390, 430, 768, 1024, 1280, 1440, 1920]) {
    testWidgets('renders without overflow at ${width.toInt()}px', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = Size(width, 1400);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.reset);
      await tester.pumpWidget(
        _host(
          pulse: AsyncValue<GtexCommunityPulse>.data(
            GtexCommunityPulse(
              access: GtexCommunityAccess.authenticated,
              headline: '3 things happened around your football.',
              yourSignals: const <GtexCommunitySignal>[
                _ownedMove,
                _clubSignal,
              ],
              worldSignals: const <GtexCommunitySignal>[_unknownProof],
            ),
          ),
          size: Size(width, 1400),
        ),
      );
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      expect(find.text('Ada Obi moved +4.2%'), findsOneWidget);
    });
  }
}
