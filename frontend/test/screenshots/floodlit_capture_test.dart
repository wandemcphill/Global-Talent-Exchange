@Tags(<String>['golden'])
library;

import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/features/competitions/live_competitions_provider.dart';
import 'package:gte_frontend/features/home/data/gtex_story_feed_ticker_provider.dart';
import 'package:gte_frontend/features/home/home_screen.dart';
import 'package:gte_frontend/features/onboarding_redesign/gtex_public_landing_screen_v2.dart';
import 'package:gte_frontend/models/story_feed_models.dart';
import 'package:gte_frontend/features/streamer_tournament_engine/data/streamer_tournament_engine_models.dart';
import 'package:gte_frontend/features/tasks/live_tasks_provider.dart';
import 'package:gte_frontend/features/transfer_market/live_market_provider.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/hosted_competition_models.dart';
import 'package:gte_frontend/features/player_card_marketplace/data/player_card_marketplace_models.dart';
import 'package:gte_frontend/features/player_card_marketplace/presentation/player_card_marketplace_controller.dart';
import 'package:gte_frontend/features/player_card_marketplace/presentation/player_card_marketplace_screen.dart';
import 'package:gte_frontend/features/profile/live_profile_provider.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/screens/gte_login_screen.dart';
import 'package:gte_frontend/screens/gte_signup_screen.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

import 'capture_market_repository.dart';

/// Renders the real Floodlit screens with bundled fonts and fixture data and
/// writes PNGs into the concept app so they can be reviewed in a browser.
///
/// `flutter test test/screenshots/floodlit_capture_test.dart --update-goldens`
const String _out = '../../../design-concepts/public/implemented';
const Key _frame = ValueKey<String>('capture-frame');

const Size _desktop = Size(1440, 1000);
const Size _mobile = Size(390, 844);

Future<ByteData> _fontFile(String path) async =>
    ByteData.sublistView(Uint8List.fromList(File(path).readAsBytesSync()));

Future<void> _loadFonts() async {
  final String flutterRoot =
      Platform.environment['FLUTTER_ROOT'] ?? '/tmp/flutter-sdk';
  final Map<String, List<String>> families = <String, List<String>>{
    'BarlowCondensed': <String>[
      'assets/fonts/BarlowCondensed-Regular.ttf',
      'assets/fonts/BarlowCondensed-SemiBold.ttf',
      'assets/fonts/BarlowCondensed-Bold.ttf',
    ],
    'DMMono': <String>[
      'assets/fonts/DMMono-Regular.ttf',
      'assets/fonts/DMMono-Medium.ttf',
    ],
    'Inter': <String>['assets/fonts/Inter.ttf'],
    // Families referenced in lib/ but not bundled in pubspec; on device they
    // fall back to a system font, so map them to the closest bundled face.
    'Barlow Condensed': <String>['assets/fonts/BarlowCondensed-Bold.ttf'],
    'Barlow': <String>['assets/fonts/BarlowCondensed-SemiBold.ttf'],
    'JetBrains Mono': <String>['assets/fonts/DMMono-Medium.ttf'],
    'Courier': <String>['assets/fonts/DMMono-Regular.ttf'],
    'DM Sans': <String>['assets/fonts/Inter.ttf'],
    // Material widgets without an explicit family fall back to Roboto.
    'Roboto': <String>['assets/fonts/Inter.ttf'],
    'MaterialIcons': <String>[
      '$flutterRoot/bin/cache/artifacts/material_fonts/MaterialIcons-Regular.otf',
    ],
  };
  for (final MapEntry<String, List<String>> family in families.entries) {
    final FontLoader loader = FontLoader(family.key);
    for (final String path in family.value) {
      loader.addFont(_fontFile(path));
    }
    await loader.load();
  }
}

Future<void> _capture(
  WidgetTester tester, {
  required String name,
  required Size size,
  required Widget child,
  Future<void> Function(WidgetTester tester)? settle,
}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.reset);
  debugDisableShadows = false;
  try {
    await tester.pumpWidget(RepaintBoundary(key: _frame, child: child));
    if (settle != null) {
      await settle(tester);
    } else {
      for (int i = 0; i < 30; i += 1) {
        await tester.pump(const Duration(milliseconds: 50));
      }
    }
    while (tester.takeException() != null) {}
    await expectLater(find.byKey(_frame), matchesGoldenFile('$_out/$name.png'));
  } finally {
    debugDisableShadows = true;
  }
}

Widget _home() => ProviderScope(
  overrides: [
    isAuthenticatedProvider.overrideWithValue(true),
    profileDataProvider.overrideWith(
      (Ref ref) async => const ProfileData(
        authenticated: true,
        user: <String, Object?>{
          'id': 'u1',
          'role': 'user',
          'display_name': 'Ayo McPhill',
        },
        affinityProfile: <String, Object?>{},
        club: <String, Object?>{'id': 'c1', 'name': 'Ibadan Lions FC'},
        followers: 0,
        following: 0,
      ),
    ),
    marketDashboardProvider.overrideWith(
      (Ref ref) async => const MarketDashboardData(
        playerShares: <PlayerShareSummary>[
          PlayerShareSummary(
            playerId: 'p1',
            playerName: 'Victor Osimhen',
            position: 'ST',
            nationality: 'NGA',
            currentClubName: 'Galatasaray',
            age: 27,
            currentValueCredits: 98000,
            marketInterestScore: 91,
            marketStatus: 'active',
            marketMessage: 'Trading',
            sharePriceCoin: 42.6,
          ),
          PlayerShareSummary(
            playerId: 'p2',
            playerName: 'Amina Okoro',
            position: 'CM',
            nationality: 'NGA',
            currentClubName: 'Ibadan Lions FC',
            age: 19,
            currentValueCredits: 21000,
            marketInterestScore: 84,
            marketStatus: 'active',
            marketMessage: 'Trading',
            sharePriceCoin: 12.4,
          ),
          PlayerShareSummary(
            playerId: 'p3',
            playerName: 'Bukayo Saka',
            position: 'RW',
            nationality: 'ENG',
            currentClubName: 'Arsenal',
            age: 25,
            currentValueCredits: 120000,
            marketInterestScore: 88,
            marketStatus: 'active',
            marketMessage: 'Trading',
            sharePriceCoin: 55.1,
          ),
        ],
        holdings: <PlayerShareHoldingSummary>[
          PlayerShareHoldingSummary(
            playerId: 'p1',
            shareCount: 120,
            averageCostCoin: 38.2,
            dividendsEarnedCoin: 310,
          ),
        ],
        transferListings: <TransferListingSummary>[],
        wallet: MarketWalletSnapshot(
          coinBalance: 18450,
          creditBalance: 6200,
          totalEquity: 248320,
          canTradeMarket: true,
          canDeposit: true,
          canWithdraw: true,
          complianceMessage: '+4.8% this week',
        ),
        authenticated: true,
        warnings: <String>[],
      ),
    ),
    competitionHubProvider.overrideWith(
      (Ref ref) async => const CompetitionHubData(
        gtexCompetitions: <CompetitionSummary>[],
        hostedCompetitions: <HostedCompetition>[],
        streamerTournaments: <StreamerTournament>[],
      ),
    ),
    storyFeedTickerProvider.overrideWith(
      (Ref ref) async => <StoryFeedItem>[
        StoryFeedItem(
          id: 's1',
          storyType: 'transfer',
          title: 'Osimhen shares climb 6% after brace',
          body: '',
          audience: 'public',
          subjectType: 'player',
          subjectId: 'p1',
          countryCode: 'NG',
          featured: true,
          createdAt: DateTime(2026, 10, 13),
          metadata: const <String, Object?>{},
        ),
      ],
    ),
    liveTasksProvider.overrideWith(
      (Ref ref) async => const LiveTasksData(
        authenticated: true,
        featureEnabled: true,
        challenges: <DailyChallengeSummary>[],
        claimsToday: <DailyChallengeClaimSummary>[],
        currentStreak: 6,
        longestStreak: 14,
        nextBonusAmount: 250,
      ),
    ),
  ],
  child: MaterialApp(
    debugShowCheckedModeBanner: false,
    theme: GteShellTheme.build(),
    home: const Scaffold(body: HomeScreen()),
  ),
);

Map<String, Object?> _sale(
  String id,
  String name,
  String club,
  String position,
  int price,
  int rating,
  int gsi,
  String band, {
  bool regen = false,
}) => <String, Object?>{
  'listing_id': 'listing-$id',
  'listing_type': 'sale',
  'player_card_id': 'card-$id',
  'player_id': 'player-$id',
  'player_name': name,
  'listing_owner_user_id': 'seller-$id',
  'status': 'open',
  'availability': 'available',
  'is_negotiable': true,
  'asset_origin': regen ? 'regen_newgen' : 'real_player',
  'is_regen_newgen': regen,
  'is_creator_linked': false,
  'available_quantity': 2,
  'sale_price_credits': price,
  'average_rating': rating,
  'global_scouting_index': gsi,
  'gsi_band': band,
  'tier_code': position,
  'tier_name': regen ? 'Regen Prospect' : 'First Team',
  'rarity_rank': 4,
  'edition_code': 'launch',
  'club_name': club,
  'position': position,
};

Widget _market() {
  final PlayerCardMarketplaceController
  controller = PlayerCardMarketplaceController(
    repository: CaptureMarketplaceRepository(
      marketSales: PlayerCardMarketplaceSearchResult.fromJson(<String, Object?>{
        'total': 6,
        'limit': 20,
        'offset': 0,
        'items': <Object?>[
          _sale(
            '1',
            'Victor Osimhen',
            'Galatasaray',
            'ST',
            84,
            86,
            91,
            'World Class',
          ),
          _sale('2', 'Ademola Lookman', 'Atalanta', 'LW', 72, 84, 88, 'Elite'),
          _sale(
            '3',
            'Calvin Bassey',
            'Fulham',
            'CB',
            41,
            79,
            80,
            'Established',
          ),
          _sale(
            '4',
            'Tobi Adeyemi',
            'Ibadan Lions FC',
            'CM',
            18,
            68,
            77,
            'Rising',
            regen: true,
          ),
          _sale('5', 'Alex Iwobi', 'Fulham', 'CAM', 38, 78, 79, 'Established'),
          _sale(
            '6',
            'Stanley Nwabali',
            'Chippa United',
            'GK',
            22,
            74,
            75,
            'Established',
          ),
        ],
      }),
    ),
  );
  return MaterialApp(
    debugShowCheckedModeBanner: false,
    theme: GteShellTheme.build(),
    home: PlayerCardMarketplaceScreen(
      baseUrl: 'https://example.test',
      backendMode: GteBackendMode.fixture,
      accessToken: 'token-1',
      currentUserId: 'user-1',
      controller: controller,
    ),
  );
}

Widget _cardsGallery() {
  return MaterialApp(
    debugShowCheckedModeBanner: false,
    theme: GteShellTheme.build(),
    home: Scaffold(
      backgroundColor: GtexColors.surfaceBase,
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(32),
        child: Wrap(
          spacing: 24,
          runSpacing: 24,
          children: <Widget>[
            SizedBox(
              width: 360,
              child: GtexPlayerCard(
                name: 'Victor Osimhen',
                position: 'ST',
                clubName: 'Galatasaray',
                nationality: 'Nigeria',
                countryCode: 'NG',
                priceLabel: '84 GTC',
                ratingLabel: '86',
                overallLabel: '86',
                gsiLabel: '91',
                gsiTierLabel: 'World Class',
                ageLabel: '26',
                formResults: const <String>['W', 'W', 'D', 'W', 'L'],
                onTap: () {},
                onAddToShortlist: () {},
                onBuyNow: () {},
                buyNowLabel: 'Negotiate',
              ),
            ),
            SizedBox(
              width: 360,
              child: GtexPlayerCard(
                name: 'Calvin Bassey',
                position: 'CB',
                clubName: 'Fulham',
                nationality: 'Nigeria',
                countryCode: 'NG',
                priceLabel: '41 GTC',
                ratingLabel: '79',
                overallLabel: '79',
                gsiLabel: '80',
                gsiTierLabel: 'Established',
                ageLabel: '25',
                formResults: const <String>['D', 'W', 'W', 'L', 'W'],
                onTap: () {},
                onAddToShortlist: () {},
                onBuyNow: () {},
                buyNowLabel: 'Negotiate',
              ),
            ),
            const SizedBox(
              width: 300,
              child: GtexRegenCard(
                name: 'Tobi Adeyemi',
                archetype: 'Deep-lying playmaker',
                nationality: 'Nigeria',
                countryCode: 'NG',
                potentialLabel: '88',
                ageLabel: '17',
                position: 'CM',
                gsiLabel: '77',
                gsiTierLabel: 'Rising',
                ratingLabel: '68',
                valueLabel: '18 GTC',
                generationLabel: 'Gen 2',
                storyLine:
                    'Academy graduate with elite vision and press resistance.',
                traitLabels: <String>[
                  'Vision',
                  'Press resistant',
                  'Long passer',
                ],
              ),
            ),
            const SizedBox(
              width: 300,
              child: GtexRegenCard(
                name: 'Kemi Balogun',
                archetype: 'Inside forward',
                nationality: 'Nigeria',
                countryCode: 'NG',
                potentialLabel: '91',
                ageLabel: '16',
                position: 'LW',
                gsiLabel: '74',
                gsiTierLabel: 'Prospect',
                ratingLabel: '64',
                valueLabel: '12 GTC',
                generationLabel: 'Gen 1',
                storyLine:
                    'Explosive first step, cuts inside onto her right foot.',
                traitLabels: <String>['Pace', 'Dribbler'],
              ),
            ),
          ],
        ),
      ),
    ),
  );
}

void main() {
  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    await _loadFonts();
  });

  testWidgets('cards', (WidgetTester tester) async {
    await _capture(
      tester,
      name: 'cards',
      size: const Size(1440, 900),
      child: _cardsGallery(),
    );
  });

  for (final MapEntry<String, Size> vp
      in <String, Size>{'desktop': _desktop, 'mobile': _mobile}.entries) {
    testWidgets('landing ${vp.key}', (WidgetTester tester) async {
      await _capture(
        tester,
        name: 'landing-${vp.key}',
        size: vp.value,
        child: const MaterialApp(
          debugShowCheckedModeBanner: false,
          home: GtexPublicLandingScreenV2(),
        ),
        settle: (WidgetTester t) async {
          await t.runAsync(
            () => Future<void>.delayed(const Duration(milliseconds: 500)),
          );
          await t.pump();
        },
      );
    });

    testWidgets('dashboard ${vp.key}', (WidgetTester tester) async {
      await _capture(
        tester,
        name: 'dashboard-${vp.key}',
        size: vp.value,
        child: _home(),
      );
    });

    testWidgets('discover ${vp.key}', (WidgetTester tester) async {
      await _capture(
        tester,
        name: 'discover-${vp.key}',
        size: vp.value,
        child: _market(),
        settle: (WidgetTester t) => t.pumpAndSettle(),
      );
    });

    testWidgets('login ${vp.key}', (WidgetTester tester) async {
      await _capture(
        tester,
        name: 'login-${vp.key}',
        size: vp.value,
        child: MaterialApp(
          debugShowCheckedModeBanner: false,
          home: GteLoginScreen(
            controller: GteExchangeController(
              api: GteExchangeApiClient.fixture(),
            ),
          ),
        ),
        settle: (WidgetTester t) => t.pumpAndSettle(),
      );
    });

    testWidgets('signup ${vp.key}', (WidgetTester tester) async {
      await _capture(
        tester,
        name: 'signup-${vp.key}',
        size: vp.value,
        child: MaterialApp(
          debugShowCheckedModeBanner: false,
          theme: GteShellTheme.build(),
          home: GteSignupScreen(
            controller: GteExchangeController(
              api: GteExchangeApiClient.fixture(),
            ),
          ),
        ),
        settle: (WidgetTester t) => t.pumpAndSettle(),
      );
    });
  }
}
